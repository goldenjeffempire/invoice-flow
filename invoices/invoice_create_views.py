from __future__ import annotations
import json
import logging
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.http import JsonResponse
from .models import Invoice, LineItem, UserProfile, InvoiceTemplate

logger = logging.getLogger(__name__)

@login_required
@transaction.atomic
def create_invoice(request):
    """Modernized Create Invoice view with robust validation and handling."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_clients = Invoice.objects.filter(user=request.user).order_by("-created_at")[:10]
    
    if request.method == "POST":
        try:
            # Extract basic info
            business_name = request.POST.get("business_name")
            business_email = request.POST.get("business_email")
            business_phone = request.POST.get("business_phone", "")
            business_address = request.POST.get("business_address")
            
            client_name = request.POST.get("client_name")
            client_email = request.POST.get("client_email")
            client_phone = request.POST.get("client_phone", "")
            client_address = request.POST.get("client_address")
            
            invoice_date = request.POST.get("invoice_date")
            due_date = request.POST.get("due_date")
            currency = request.POST.get("currency", "NGN")
            tax_rate = Decimal(request.POST.get("tax_rate", "0") or "0")
            discount = Decimal(request.POST.get("discount", "0") or "0")
            notes = request.POST.get("notes", "")
            reminders_enabled = request.POST.get("automated_reminders_enabled") == "on"
            
            # Validation
            if not all([business_name, business_email, client_name, client_email, invoice_date]):
                messages.error(request, "Please fill in all required business and client details.")
                return redirect("invoices:create_invoice")

            # Create Invoice
            invoice = Invoice.objects.create(
                user=request.user,
                business_name=business_name,
                business_email=business_email,
                business_phone=business_phone,
                business_address=business_address,
                client_name=client_name,
                client_email=client_email,
                client_phone=client_phone,
                client_address=client_address,
                invoice_date=invoice_date,
                due_date=due_date,
                currency=currency,
                tax_rate=tax_rate,
                discount=discount,
                notes=notes,
                automated_reminders_enabled=reminders_enabled,
                status=Invoice.Status.UNPAID
            )
            
            # Process Line Items
            line_items_data = json.loads(request.POST.get("line_items", "[]"))
            if not line_items_data:
                LineItem.objects.create(
                    invoice=invoice,
                    description="Standard Service",
                    quantity=1,
                    unit_price=0
                )
            else:
                for item in line_items_data:
                    if item.get("description"):
                        LineItem.objects.create(
                            invoice=invoice,
                            description=item["description"],
                            quantity=Decimal(str(item.get("quantity", 1))),
                            unit_price=Decimal(str(item.get("unit_price", 0)))
                        )
            
            from .services import AnalyticsService
            AnalyticsService.invalidate_user_cache(request.user.id)
            
            messages.success(request, f"Invoice {invoice.invoice_id} has been created successfully!")
            return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            
        except Exception as e:
            logger.error(f"Error creating invoice for user {request.user.id}: {str(e)}")
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect("invoices:create_invoice")

    context = {
        "recent_clients": recent_clients,
        "active": "create_invoice",
        "page_title": "Create Invoice",
        "today": timezone.now().date(),
    }
    return render(request, "invoices/create_invoice.html", context)

@login_required
def load_template(request):
    """Placeholder for template loading functionality."""
    return JsonResponse({'success': False, 'message': 'Not implemented yet'})

@login_required
def validate_invoice_form(request):
    """Placeholder for form validation functionality."""
    return JsonResponse({'success': True, 'errors': {}})

@login_required
def calculate_totals(request):
    """Placeholder for totals calculation functionality."""
    return JsonResponse({'success': False, 'message': 'Not implemented yet'})
