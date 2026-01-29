"""
Paystack Payment Views for InvoiceFlow.
Handles payment initiation, callbacks, webhooks, and public invoice payments.
"""

import json
import logging
import hashlib
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .auth_services import require_verified_email
from .models import Invoice, Payment, PaymentReconciliation
from .paystack_service import (
    PaystackService,
    finalize_payment_from_verification,
    get_paystack_service,
    record_reconciliation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# INITIALIZE PAYMENT
# ---------------------------------------------------------------------

@login_required
@require_POST
def initialize_payment(request):
    """
    Initialize payment with idempotency protection.
    Requires: verified email + completed MFA + identity verification.
    """
    user = request.user
    
    # ENFORCE: Email verification
    try:
        require_verified_email(user)
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "code": "EMAIL_NOT_VERIFIED"
        }, status=403)
    
    # MFA completion is optional for public payments but recommended for logged in users
    # Check if MFA is enabled for this user
    from .models import MFAProfile
    mfa_enabled = MFAProfile.objects.filter(user=user, is_enabled=True).exists()
    if mfa_enabled and not request.session.get("mfa_verified", False):
        return JsonResponse({
            "error": "MFA verification required",
            "code": "MFA_NOT_VERIFIED"
        }, status=403)
    
    invoice_id = request.POST.get("invoice_id")
    idempotency_key = request.POST.get("idempotency_key")

    if not invoice_id:
        return JsonResponse({"error": "Invalid payment request"}, status=400)

    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=user)
    if invoice.status == Invoice.Status.PAID:
        return JsonResponse({"error": "Invoice already paid"}, status=400)
    try:
        requested_amount = Decimal(request.POST.get("amount", str(invoice.total)))
    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "Invalid payment amount"}, status=400)

    amount = invoice.total
    # ENFORCE: Identity verification for high-value payments
    from .models import UserIdentityVerification
    if amount > 100000:  # Threshold for KYC
        try:
            verification = UserIdentityVerification.objects.get(user=user)
            if not verification.is_verified():
                return JsonResponse({
                    "error": "Identity verification required for large payments",
                    "code": "IDENTITY_NOT_VERIFIED"
                }, status=403)
        except UserIdentityVerification.DoesNotExist:
            return JsonResponse({
                "error": "Identity verification required for large payments",
                "code": "IDENTITY_NOT_VERIFIED"
            }, status=403)
    if amount <= 0:
        return JsonResponse({"error": "Invalid payment amount"}, status=400)
    if requested_amount != amount:
        return JsonResponse({"error": "Payment amount mismatch"}, status=400)

    if not idempotency_key:
        return JsonResponse({"error": "Idempotency key required"}, status=400)

    service = get_paystack_service()
    if not service.is_configured:
        return JsonResponse({"error": "Payment gateway not configured"}, status=503)

    reference = f"inv_{invoice.invoice_id}_{user.id}_{uuid.uuid4().hex[:8]}"
    request_data = {
        "invoice_id": invoice_id,
        "amount": str(amount),
        "currency": invoice.currency,
    }

    def process_payment():
        """Process the payment and return response."""
        try:
            payment, created = Payment.objects.get_or_create(
                reference=reference,
                defaults={
                    "user": user,
                    "invoice": invoice,
                    "amount": amount,
                    "currency": invoice.currency,
                },
            )

            if not created:
                return {"error": "Payment already initialized"}, 400

            result = service.initialize_payment(
                email=user.email,
                amount=amount,
                reference=reference,
                currency=invoice.currency,
                callback_url=settings.PAYSTACK_CALLBACK_URL,
                metadata={
                    "invoice_id": invoice.invoice_id,
                    "user_id": user.id,
                },
            )

            if result.get("configured") is False:
                return {"error": "Payment gateway not configured"}, 503

            status_code = 200 if result.get("status") == "success" else 400
            return result, status_code
        except Exception as e:
            logger.error(f"Payment initialization error: {e}")
            return {"error": "Payment processing failed"}, 500

    result, status_code, is_cached = service.get_or_create_idempotency_response(
        user_id=user.id,
        idempotency_key=idempotency_key,
        request_data=request_data,
        response_callback=process_payment,
    )

    return JsonResponse(result, status=status_code)


# ---------------------------------------------------------------------
# PAYSTACK WEBHOOK
# ---------------------------------------------------------------------

@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook with hardened security."""
    service = PaystackService()
    client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")).split(",")[0].strip()
    rate_key = f"paystack_webhook_rate:{client_ip}"
    rate_limit = getattr(settings, "PAYSTACK_WEBHOOK_RATE_LIMIT", 120)
    rate_window = getattr(settings, "PAYSTACK_WEBHOOK_RATE_WINDOW", 60)
    current_count = cache.get(rate_key, 0)
    if current_count >= rate_limit:
        logger.warning("Paystack webhook rate limit exceeded for IP: %s", client_ip)
        return HttpResponse(status=429)
    cache.set(rate_key, current_count + 1, rate_window)

    signature = request.headers.get("X-Paystack-Signature", "")
    payload = request.body

    # Signature verification (stateless/fast)
    if not service.verify_webhook_signature(payload, signature):
        logger.warning(f"Invalid Paystack signature: {signature[:10]}...")
        return HttpResponse("Unauthorized", status=401)

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        logger.error("Invalid Paystack webhook payload JSON")
        return HttpResponse("Invalid JSON", status=400)

    event_id = str(event.get("data", {}).get("id", ""))
    if not event_id:
        # Some Paystack events use a different structure or top-level ID
        event_id = str(event.get("id", ""))
        
    if not event_id:
        logger.warning("Missing event ID in Paystack webhook")
        return HttpResponse("Missing event ID", status=400)

    # Idempotency check (prevent replay attacks)
    if service.is_webhook_processed(event_id):
        logger.info(f"Paystack webhook {event_id} already processed. Skipping.")
        return HttpResponse("Already processed", status=200)

    event_type = event.get("event")
    # We only care about success for now to avoid noise
    if event_type != "charge.success":
        logger.info(f"Ignoring Paystack event type: {event_type}")
        return HttpResponse("Event ignored", status=200)

    reference = event.get("data", {}).get("reference", "")
    if not reference:
        logger.warning("Missing payment reference in webhook")
        return HttpResponse(status=400)

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(
                reference=reference
            )
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for reference: {reference}")
            return HttpResponse(status=404)

        # Skip already verified payments
        if payment.status == Payment.Status.SUCCESS:
            logger.debug(f"Payment {reference} already verified")
            return HttpResponse(status=200)

        # Verify transaction with Paystack (server-to-server)
        verification = service.verify_transaction(reference)

        if verification.get("status") == "error":
            logger.error(f"Paystack verification error for {reference}: {verification.get('message')}")
            return HttpResponse("Provider verification error", status=503)

        payload_hash = hashlib.sha256(payload).hexdigest()

        if not verification.get("verified"):
            logger.warning(f"Payment verification failed for {reference}")
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            record_reconciliation(
                payment=payment,
                status=PaymentReconciliation.ReconciliationStatus.FAILED,
                paystack_status=str(verification.get("raw", {}).get("status", "")),
                amount_match=True,
                currency_match=True,
                status_match=False,
                error="Verification failed",
            )
            service.mark_webhook_processed(
                event_id,
                provider="paystack",
                event_type=event_type,
                reference=reference,
                payload_hash=payload_hash,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return HttpResponse("Verified as failed", status=200)

        # Amount validation (prevent tampering)
        if verification["amount"] != payment.amount:
            logger.error(f"Amount mismatch for {reference}: {verification['amount']} != {payment.amount}")
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            record_reconciliation(
                payment=payment,
                status=PaymentReconciliation.ReconciliationStatus.MISMATCH,
                paystack_status=str(verification.get("raw", {}).get("status", "")),
                amount_match=False,
                currency_match=True,
                status_match=False,
                error="Amount mismatch",
            )
            service.mark_webhook_processed(
                event_id,
                provider="paystack",
                event_type=event_type,
                reference=reference,
                payload_hash=payload_hash,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return HttpResponse("Amount mismatch", status=400)

        # Currency validation
        if verification.get("currency", "").upper() != payment.currency.upper():
            logger.error(f"Currency mismatch for {reference}: {verification.get('currency')} != {payment.currency}")
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            record_reconciliation(
                payment=payment,
                status=PaymentReconciliation.ReconciliationStatus.MISMATCH,
                paystack_status=str(verification.get("raw", {}).get("status", "")),
                amount_match=True,
                currency_match=False,
                status_match=False,
                error="Currency mismatch",
            )
            service.mark_webhook_processed(
                event_id,
                provider="paystack",
                event_type=event_type,
                reference=reference,
                payload_hash=payload_hash,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return HttpResponse("Currency mismatch", status=400)

        service.mark_webhook_processed(
            event_id,
            provider="paystack",
            event_type=event_type,
            reference=reference,
            payload_hash=payload_hash,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # Finalize payment
        finalize_payment_from_verification(
            payment=payment,
            verification=verification,
        )
        logger.info(f"Payment {reference} verified and finalized")

    return HttpResponse(status=200)


# ---------------------------------------------------------------------
# INITIATE INVOICE PAYMENT (logged-in user)
# ---------------------------------------------------------------------

@login_required
@require_POST
def initiate_invoice_payment(request, invoice_id):
    """Initiate payment for an invoice (logged-in user)."""
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    
    if invoice.status == "paid":
        return JsonResponse({"error": "Invoice already paid"}, status=400)

    service = get_paystack_service()
    if not service.is_configured:
        return JsonResponse({"error": "Payment gateway not configured"}, status=503)
    
    reference = f"inv_{invoice.invoice_id}_{request.user.id}_{uuid.uuid4().hex[:8]}"
    
    payment, created = Payment.objects.get_or_create(
        invoice=invoice,
        user=request.user,
        status=Payment.Status.PENDING,
        defaults={
            "reference": reference,
            "amount": invoice.total,
            "currency": invoice.currency,
        },
    )
    
    if not created and payment.status == Payment.Status.PENDING:
        reference = payment.reference
    elif not created:
        return JsonResponse({"error": "Payment already processed"}, status=400)
    
    callback_url = request.build_absolute_uri(
        f"/payments/callback/{invoice.invoice_id}/"
    )
    
    result = service.initialize_payment(
        email=request.user.email,
        amount=invoice.total,
        reference=reference,
        currency=invoice.currency,
        callback_url=callback_url,
        metadata={
            "invoice_id": invoice.invoice_id,
            "user_id": request.user.id,
        },
    )
    
    if result.get("status") == "success":
        return JsonResponse({
            "authorization_url": result["authorization_url"],
            "reference": result["reference"],
        })
    
    return JsonResponse({"error": result.get("message", "Payment initialization failed")}, status=400)


# ---------------------------------------------------------------------
# PAYMENT CALLBACK (logged-in user)
# ---------------------------------------------------------------------

@login_required
@require_GET
def payment_callback(request, invoice_id):
    """Handle Paystack callback after payment (logged-in user)."""
    reference = request.GET.get("reference")
    
    if not reference:
        return redirect("invoices:dashboard")
    
    try:
        payment = Payment.objects.get(reference=reference, user=request.user)
    except Payment.DoesNotExist:
        return redirect("invoices:dashboard")

    if not payment.invoice or payment.invoice.invoice_id != invoice_id:
        return redirect("invoices:dashboard")
    
    if payment.status == Payment.Status.SUCCESS:
        return redirect("invoices:invoice_detail", invoice_id=invoice_id)
    
    service = get_paystack_service()
    verification = service.verify_transaction(reference)
    
    if verification.get("verified"):
        finalize_payment_from_verification(payment=payment, verification=verification)
    else:
        record_reconciliation(
            payment=payment,
            status=PaymentReconciliation.ReconciliationStatus.FAILED,
            paystack_status=str(verification.get("raw", {}).get("status", "")),
            amount_match=True,
            currency_match=True,
            status_match=False,
            error=verification.get("message", "Verification failed"),
        )
    
    return redirect("invoices:invoice_detail", invoice_id=invoice_id)


# ---------------------------------------------------------------------
# PAYMENT STATUS
# ---------------------------------------------------------------------

@login_required
@require_GET
def payment_status(request, invoice_id):
    """Get payment status for an invoice."""
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    
    try:
        payment = Payment.objects.filter(invoice=invoice).latest("created_at")
        return JsonResponse({
            "status": payment.status,
            "verified": payment.status == Payment.Status.SUCCESS,
            "amount": str(payment.amount),
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        })
    except Payment.DoesNotExist:
        return JsonResponse({"status": "no_payment", "verified": False})


# ---------------------------------------------------------------------
# PUBLIC INVOICE VIEW (no login required)
# ---------------------------------------------------------------------

@require_GET
def public_invoice_view(request, invoice_id):
    """View invoice for public payment (no login required)."""
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    
    if invoice.status == "paid":
        return render(request, "payments/invoice_paid.html", {"invoice": invoice})
    
    # If platform integrated, we use the master public key
    paystack_public_key = getattr(settings, "PAYSTACK_PUBLIC_KEY", "")
    paystack_configured = bool(paystack_public_key)
    
    # Check for payment preferences
    from .models import PaymentSettings
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=invoice.user)
    
    context = {
        "invoice": invoice,
        "paystack_configured": paystack_configured,
        "paystack_public_key": paystack_public_key,
        "payment_settings": payment_settings,
    }
    
    return render(request, "payments/public_invoice.html", context)


# ---------------------------------------------------------------------
# PUBLIC INITIATE PAYMENT (no login required)
# ---------------------------------------------------------------------

@csrf_exempt
@require_POST
def public_initiate_payment(request, invoice_id):
    """Initiate payment for a public invoice (no login required)."""
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    
    if invoice.status == "paid":
        return JsonResponse({"error": "Invoice already paid"}, status=400)

    service = get_paystack_service()
    if not service.is_configured:
        return JsonResponse({"error": "Payment gateway not configured"}, status=503)
    
    email = request.POST.get("email") or invoice.client_email
    if not email:
        return JsonResponse({"error": "Email address required"}, status=400)
    
    reference = f"pub_{invoice.invoice_id}_{uuid.uuid4().hex[:8]}"
    
    payment = Payment.objects.create(
        invoice=invoice,
        user=invoice.user,
        reference=reference,
        amount=invoice.total,
        currency=invoice.currency,
        status=Payment.Status.PENDING,
    )
    
    callback_url = request.build_absolute_uri(
        f"/pay/{invoice.invoice_id}/callback/"
    )
    
    result = service.initialize_payment(
        email=email,
        amount=invoice.total,
        reference=reference,
        currency=invoice.currency,
        callback_url=callback_url,
        metadata={
            "invoice_id": invoice.invoice_id,
            "public_payment": True,
        },
    )
    
    if result.get("status") == "success":
        return JsonResponse({
            "authorization_url": result["authorization_url"],
            "reference": result["reference"],
        })
    
    payment.status = Payment.Status.FAILED
    payment.save(update_fields=["status"])
    
    return JsonResponse({"error": result.get("message", "Payment initialization failed")}, status=400)


# ---------------------------------------------------------------------
# PUBLIC PAYMENT CALLBACK (no login required)
# ---------------------------------------------------------------------

@require_GET
def public_payment_callback(request, invoice_id):
    """Handle Paystack callback after public payment."""
    reference = request.GET.get("reference")
    
    if not reference:
        return redirect("public_invoice", invoice_id=invoice_id)
    
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        return redirect("public_invoice", invoice_id=invoice_id)

    if not payment.invoice or payment.invoice.invoice_id != invoice_id:
        return redirect("public_invoice", invoice_id=invoice_id)
    
    if payment.status == Payment.Status.SUCCESS:
        return render(request, "payments/payment_success.html", {"invoice": payment.invoice})
    
    service = get_paystack_service()
    verification = service.verify_transaction(reference)
    
    if verification.get("verified"):
        finalize_payment_from_verification(payment=payment, verification=verification)
        return render(request, "payments/payment_success.html", {"invoice": payment.invoice})
    
    record_reconciliation(
        payment=payment,
        status=PaymentReconciliation.ReconciliationStatus.FAILED,
        paystack_status=str(verification.get("raw", {}).get("status", "")),
        amount_match=True,
        currency_match=True,
        status_match=False,
        error=verification.get("message", "Verification failed"),
    )
    
    return render(request, "payments/payment_failed.html", {"invoice": payment.invoice})
