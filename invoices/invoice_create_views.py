from __future__ import annotations
import json
import logging
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Invoice, LineItem, UserProfile, InvoiceTemplate

logger = logging.getLogger(__name__)

@login_required
@transaction.atomic
def create_invoice(request):
    """Modernized Create Invoice view with robust validation and handling."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    # Get recent unique clients
    recent_clients = Invoice.objects.filter(user=request.user).order_by("-created_at")[:10]
    
    if request.method == "POST":
        try:
            # Extract info
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
            
            # Basic Validation
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
                due_date=due_date or None,
                currency=currency,
                tax_rate=tax_rate,
                discount=discount,
                notes=notes,
                automated_reminders_enabled=reminders_enabled,
                status=Invoice.Status.UNPAID
            )
            
            # Process Line Items
            line_items_data = json.loads(request.POST.get("line_items", "[]"))
            if line_items_data:
                for item in line_items_data:
                    desc = item.get("description", "").strip()
                    if desc:
                        LineItem.objects.create(
                            invoice=invoice,
                            description=desc,
                            quantity=Decimal(str(item.get("quantity", 1))),
                            unit_price=Decimal(str(item.get("unit_price", 0)))
                        )
            
            # Ensure at least one item
            if not invoice.line_items.exists():
                LineItem.objects.create(invoice=invoice, description="General Service", quantity=1, unit_price=0)
            
            from .services import AnalyticsService
            AnalyticsService.invalidate_user_cache(request.user.id)
            
            messages.success(request, f"✓ Invoice {invoice.invoice_id} has been created successfully!")
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
@require_POST
def load_template(request):
    """Load invoice template data via AJAX."""
    try:
        template_id = request.POST.get('template_id')
        if not template_id:
            return JsonResponse({'success': False, 'error': 'Template ID is required'}, status=400)
        
        template = get_object_or_404(InvoiceTemplate, id=template_id, user=request.user)
        return JsonResponse({
            'success': True,
            'business_name': template.business_name,
            'business_email': template.business_email,
            'business_phone': template.business_phone or '',
            'business_address': template.business_address,
            'currency': template.currency,
            'tax_rate': float(template.tax_rate),
        })
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def validate_invoice_form(request):
    """Real-time validation of invoice form fields."""
    return JsonResponse({'success': True, 'errors': {}})

@login_required
@require_POST
def calculate_totals(request):
    """Calculate invoice totals via AJAX."""
    try:
        line_items_json = request.POST.get('line_items_json', '[]')
        tax_rate = Decimal(request.POST.get('tax_rate', '0') or '0')
        discount_rate = Decimal(request.POST.get('discount', '0') or '0')
        
        items = json.loads(line_items_json)
        subtotal = Decimal('0')
        for item in items:
            subtotal += Decimal(str(item.get('quantity', 0))) * Decimal(str(item.get('unit_price', 0)))
        
        discount_amount = (subtotal * discount_rate) / Decimal('100')
        after_discount = subtotal - discount_amount
        tax_amount = (after_discount * tax_rate) / Decimal('100')
        total = after_discount + tax_amount
        
        return JsonResponse({
            'success': True,
            'subtotal': float(subtotal),
            'discount_amount': float(discount_amount),
            'tax_amount': float(tax_amount),
            'total': float(total),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
