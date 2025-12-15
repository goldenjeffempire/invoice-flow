"""
Payment Settings Views for InvoiceFlow.
Handles payment configuration, subaccounts, recipients, and payout management.
"""

import json
import logging
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import PaymentRecipientForm, PaymentSettingsForm, SubaccountSetupForm
from .models import (
    Payment,
    PaymentCard,
    PaymentPayout,
    PaymentRecipient,
    PaymentSettings,
    UserProfile,
)
from .paystack_service import get_paystack_service

logger = logging.getLogger(__name__)


@login_required
@require_GET
def payment_settings_dashboard(request):
    """Main payment settings dashboard showing overview of payment configuration."""
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    recipients = PaymentRecipient.objects.filter(user=request.user, is_active=True)
    saved_cards = PaymentCard.objects.filter(user=request.user, is_active=True)
    recent_payments = Payment.objects.filter(user=request.user).order_by("-created_at")[:10]
    recent_payouts = PaymentPayout.objects.filter(user=request.user).order_by("-created_at")[:5]
    
    paystack = get_paystack_service()
    
    payment_stats = {
        "total_received": Payment.objects.filter(user=request.user, status="success").count(),
        "total_amount": sum(
            p.amount for p in Payment.objects.filter(user=request.user, status="success")
        ),
        "pending_payments": Payment.objects.filter(user=request.user, status="pending").count(),
    }
    
    context = {
        "payment_settings": payment_settings,
        "profile": profile,
        "recipients": recipients,
        "saved_cards": saved_cards,
        "recent_payments": recent_payments,
        "recent_payouts": recent_payouts,
        "payment_stats": payment_stats,
        "paystack_configured": paystack.is_configured,
        "has_subaccount": profile.has_payment_setup(),
    }
    
    return render(request, "payments/payment_settings.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def payment_preferences(request):
    """Configure payment acceptance preferences."""
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = PaymentSettingsForm(request.POST, instance=payment_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment preferences updated successfully.")
            return redirect("payment_settings")
    else:
        form = PaymentSettingsForm(instance=payment_settings)
    
    return render(request, "payments/payment_preferences.html", {
        "form": form,
        "payment_settings": payment_settings,
    })


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="5/m", method="POST", block=True)
def setup_subaccount(request):
    """Set up Paystack subaccount for receiving payments directly."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        messages.error(request, "Payment gateway is not configured. Please contact support.")
        return redirect("payment_settings")
    
    banks_result = paystack.list_banks("nigeria")
    banks = banks_result.get("banks", []) if banks_result.get("status") == "success" else []
    
    if request.method == "POST":
        form = SubaccountSetupForm(request.POST)
        if form.is_valid():
            business_name = form.cleaned_data["business_name"]
            bank_code = form.cleaned_data["bank_code"]
            account_number = form.cleaned_data["account_number"]
            contact_email = form.cleaned_data["contact_email"]
            contact_phone = form.cleaned_data.get("contact_phone", "")
            
            verify_result = paystack.verify_account_number(account_number, bank_code)
            if verify_result.get("status") != "success":
                messages.error(request, f"Account verification failed: {verify_result.get('message', 'Unknown error')}")
                return render(request, "payments/setup_subaccount.html", {
                    "form": form,
                    "banks": banks,
                    "profile": profile,
                })
            
            account_name = verify_result.get("account_name", "")
            
            bank_name = ""
            for bank in banks:
                if bank.get("code") == bank_code:
                    bank_name = bank.get("name", "")
                    break
            
            result = paystack.create_subaccount(
                business_name=business_name,
                bank_code=bank_code,
                account_number=account_number,
                percentage_charge=Decimal("0"),
                primary_contact_email=contact_email,
                primary_contact_phone=contact_phone,
            )
            
            if result.get("status") == "success":
                profile.paystack_subaccount_code = result["subaccount_code"]
                profile.paystack_bank_code = bank_code
                profile.paystack_account_number = account_number
                profile.paystack_account_name = account_name
                profile.paystack_settlement_bank = bank_name
                profile.paystack_subaccount_active = True
                profile.save()
                
                logger.info(f"Subaccount created for user {request.user.username}: {result['subaccount_code']}")
                messages.success(request, "Payment account set up successfully! You can now receive payments directly.")
                return redirect("payment_settings")
            else:
                logger.error(f"Subaccount creation failed for user {request.user.username}: {result.get('message')}")
                messages.error(request, f"Failed to set up payment account: {result.get('message', 'Unknown error')}")
    else:
        initial = {
            "business_name": profile.company_name or "",
            "contact_email": request.user.email or profile.business_email or "",
        }
        form = SubaccountSetupForm(initial=initial)
    
    return render(request, "payments/setup_subaccount.html", {
        "form": form,
        "banks": banks,
        "profile": profile,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def verify_bank_account(request):
    """AJAX endpoint to verify a bank account number."""
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        return JsonResponse({"status": "error", "message": "Payment gateway not configured"}, status=400)
    
    try:
        data = json.loads(request.body)
        account_number = data.get("account_number", "").strip()
        bank_code = data.get("bank_code", "").strip()
        
        if not account_number or not bank_code:
            return JsonResponse({"status": "error", "message": "Account number and bank code are required"}, status=400)
        
        if not account_number.isdigit() or len(account_number) != 10:
            return JsonResponse({"status": "error", "message": "Invalid account number format"}, status=400)
        
        result = paystack.verify_account_number(account_number, bank_code)
        
        if result.get("status") == "success":
            return JsonResponse({
                "status": "success",
                "account_name": result.get("account_name", ""),
                "account_number": result.get("account_number", ""),
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": result.get("message", "Could not verify account"),
            }, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid request data"}, status=400)
    except Exception as e:
        logger.exception(f"Error verifying bank account: {str(e)}")
        return JsonResponse({"status": "error", "message": "An error occurred"}, status=500)


@login_required
@require_GET
def list_banks(request):
    """AJAX endpoint to get list of supported banks."""
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        return JsonResponse({"status": "error", "message": "Payment gateway not configured"}, status=400)
    
    country = request.GET.get("country", "nigeria")
    result = paystack.list_banks(country)
    
    if result.get("status") == "success":
        banks = [
            {"code": b.get("code"), "name": b.get("name")}
            for b in result.get("banks", [])
            if b.get("active", True)
        ]
        return JsonResponse({"status": "success", "banks": banks})
    else:
        return JsonResponse({"status": "error", "message": result.get("message", "Failed to fetch banks")}, status=400)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def manage_recipients(request):
    """View and manage payment recipients/bank accounts."""
    recipients = PaymentRecipient.objects.filter(user=request.user, is_active=True)
    paystack = get_paystack_service()
    
    banks_result = paystack.list_banks("nigeria") if paystack.is_configured else {"banks": []}
    banks = banks_result.get("banks", []) if banks_result.get("status") == "success" else []
    
    if request.method == "POST":
        form = PaymentRecipientForm(request.POST)
        if form.is_valid():
            recipient = form.save(commit=False)
            recipient.user = request.user
            recipient.is_verified = True
            recipient.save()
            
            messages.success(request, f"Recipient '{recipient.name}' added successfully.")
            return redirect("manage_recipients")
    else:
        form = PaymentRecipientForm()
    
    return render(request, "payments/manage_recipients.html", {
        "recipients": recipients,
        "form": form,
        "banks": banks,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def delete_recipient(request, recipient_id):
    """Delete a payment recipient."""
    recipient = get_object_or_404(PaymentRecipient, id=recipient_id, user=request.user)
    recipient_name = recipient.name
    recipient.is_active = False
    recipient.save()
    
    messages.success(request, f"Recipient '{recipient_name}' has been removed.")
    return redirect("manage_recipients")


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def set_primary_recipient(request, recipient_id):
    """Set a recipient as the primary payout destination."""
    recipient = get_object_or_404(PaymentRecipient, id=recipient_id, user=request.user, is_active=True)
    
    PaymentRecipient.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    recipient.is_primary = True
    recipient.save()
    
    messages.success(request, f"'{recipient.name}' is now your primary payout account.")
    return redirect("manage_recipients")


@login_required
@require_GET
def saved_cards(request):
    """View saved payment cards."""
    cards = PaymentCard.objects.filter(user=request.user, is_active=True)
    
    return render(request, "payments/saved_cards.html", {
        "cards": cards,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def delete_card(request, card_id):
    """Delete a saved payment card."""
    card = get_object_or_404(PaymentCard, id=card_id, user=request.user)
    card.is_active = False
    card.save()
    
    messages.success(request, "Card has been removed from your account.")
    return redirect("saved_cards")


@login_required
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def set_primary_card(request, card_id):
    """Set a card as the primary payment method."""
    card = get_object_or_404(PaymentCard, id=card_id, user=request.user, is_active=True)
    
    PaymentCard.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    card.is_primary = True
    card.save()
    
    messages.success(request, f"Card ending in {card.last4} is now your primary payment method.")
    return redirect("saved_cards")


@login_required
@require_GET
def payment_history(request):
    """View payment transaction history."""
    payments = Payment.objects.filter(user=request.user).order_by("-created_at")
    
    status_filter = request.GET.get("status", "")
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    return render(request, "payments/payment_history.html", {
        "payments": payments,
        "status_filter": status_filter,
    })


@login_required
@require_GET
def payout_history(request):
    """View payout/withdrawal history."""
    payouts = PaymentPayout.objects.filter(user=request.user).order_by("-created_at")
    
    return render(request, "payments/payout_history.html", {
        "payouts": payouts,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="3/h", method="POST", block=True)
def toggle_subaccount(request):
    """Enable or disable subaccount for direct payments."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if not profile.paystack_subaccount_code:
        messages.error(request, "No payment account configured. Please set up your payment account first.")
        return redirect("payment_settings")
    
    profile.paystack_subaccount_active = not profile.paystack_subaccount_active
    profile.save()
    
    status = "enabled" if profile.paystack_subaccount_active else "disabled"
    messages.success(request, f"Direct payments have been {status}.")
    
    logger.info(f"Subaccount {status} for user {request.user.username}")
    return redirect("payment_settings")


@login_required
@require_GET
def payment_detail(request, payment_id):
    """View details of a specific payment."""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    return render(request, "payments/payment_detail.html", {
        "payment": payment,
    })
