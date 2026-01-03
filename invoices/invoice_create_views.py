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
from django.views.decorators.csrf import csrf_protect
from .models import Invoice, LineItem, UserProfile, InvoiceTemplate
from .forms import InvoiceForm
from .services import InvoiceService, AnalyticsService

logger = logging.getLogger(__name__)

@login_required
@transaction.atomic
@csrf_protect
def create_invoice(request):
    """Modernized Create Invoice view with robust validation and handling."""
    # Pre-populate business details from user profile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_clients = Invoice.objects.filter(user=request.user).order_by("-created_at")[:10]
    
    if request.method == "POST":
        try:
            line_items_json = request.POST.get("line_items", "[]")
            line_items_data = json.loads(line_items_json)
            
            if not line_items_data:
                messages.error(request, "Please add at least one line item.")
                return redirect("invoices:create_invoice")

            # Use Service layer for creation to ensure consistency
            invoice, form = InvoiceService.create_invoice(
                user=request.user,
                invoice_data=request.POST,
                files_data=request.FILES,
                line_items_data=line_items_data
            )
            
            if invoice:
                messages.success(request, f"✓ Invoice {invoice.invoice_id} created successfully!")
                return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            else:
                # Handle form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                return redirect("invoices:create_invoice")
                
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            messages.error(request, f"Failed to create invoice: {str(e)}")
            return redirect("invoices:create_invoice")

    context = {
        "recent_clients": recent_clients,
        "active": "create_invoice",
        "page_title": "Create Invoice",
        "today": timezone.now().date(),
        "user_profile": profile,
    }
    return render(request, "invoices/create_invoice.html", context)

@login_required
@require_POST
@csrf_protect
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
@csrf_protect
def validate_invoice_form(request):
    """Real-time validation of invoice form fields."""
    form = InvoiceForm(request.POST, request.FILES)
    if form.is_valid():
        return JsonResponse({'success': True, 'errors': {}})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

@login_required
@require_POST
@csrf_protect
def calculate_totals(request):
    """Calculate invoice totals via AJAX for real-world usage."""
    try:
        line_items_json = request.POST.get('line_items_json', '[]')
        tax_rate = Decimal(request.POST.get('tax_rate', '0') or '0')
        discount_rate = Decimal(request.POST.get('discount', '0') or '0')
        
        items = json.loads(line_items_json)
        subtotal = Decimal('0')
        for item in items:
            qty = Decimal(str(item.get('quantity', 0) or 0))
            price = Decimal(str(item.get('unit_price', 0) or 0))
            subtotal += qty * price
        
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
        logger.error(f"Calculation error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
