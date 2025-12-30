"""
Production-grade Create Invoice views with comprehensive security, validation, and transaction support.
"""

import json
import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.decorators import ratelimit
from django.utils import timezone
from datetime import timedelta

from .models import Invoice, LineItem, UserProfile
from .forms import InvoiceForm
from .services import InvoiceService

if TYPE_CHECKING:
    from django.forms import BaseForm

logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def create_invoice_start(request):
    """
    Unified, production-grade invoice creation view with robust validation.
    """
    from .services import InvoiceService
    from django.utils import timezone
    from datetime import timedelta
    import json

    if request.method == "POST":
        try:
            line_items_data = json.loads(request.POST.get("line_items_json", "[]"))
            if not line_items_data or len(line_items_data) == 0:
                messages.error(request, "Please add at least one item to your invoice.")
                return redirect('invoices:create_invoice_start')

            # Validate line items data structure
            for item in line_items_data:
                if not item.get('description') or not item.get('quantity') or not item.get('unit_price'):
                    messages.error(request, "Invalid line item data. Please ensure all items have description, quantity, and price.")
                    return redirect('invoices:create_invoice_start')

            # Use Service layer for atomic creation
            invoice, form = InvoiceService.create_invoice(
                user=request.user,
                invoice_data=request.POST,
                files_data=request.FILES,
                line_items_data=line_items_data
            )

            if invoice:
                messages.success(request, f"Invoice #{invoice.invoice_id} created successfully.")
                return redirect('invoices:invoice_detail', invoice_id=invoice.id)
            else:
                for field, errors in form.errors.items():
                    messages.error(request, f"{field.replace('_', ' ').title()}: {', '.join(errors)}")
        except json.JSONDecodeError:
            messages.error(request, "Invalid data format for invoice items.")
        except Exception as e:
            logger.error(f"Critical error in invoice creation: {str(e)}", exc_info=True)
            messages.error(request, "A server error occurred while creating the invoice. Please try again.")

    # Get user defaults
    user_profile = getattr(request.user, 'userprofile', None)
    default_currency = user_profile.default_currency if user_profile else 'USD'
    default_tax = user_profile.default_tax_rate if user_profile else 0

    context = {
        'today': timezone.now().date(),
        'default_due_date': timezone.now().date() + timedelta(days=30),
        'active': 'create_invoice_start',
        'default_currency': default_currency,
        'default_tax': default_tax
    }
    return render(request, "invoices/create_invoice_modern.html", context)


@login_required
def create_invoice_items(request):
    """
    Invoice creation feature temporarily disabled.
    """
    messages.info(request, "Invoice creation feature is being redesigned. Please check back soon.")
    return redirect('invoices:invoice_list')


@login_required
def create_invoice_taxes(request):
    """
    Invoice creation feature temporarily disabled.
    """
    messages.info(request, "Invoice creation feature is being redesigned. Please check back soon.")
    return redirect('invoices:invoice_list')


@login_required
def create_invoice_review(request):
    """
    Invoice creation feature temporarily disabled.
    """
    messages.info(request, "Invoice creation feature is being redesigned. Please check back soon.")
    return redirect('invoices:invoice_list')


@login_required
def save_invoice_draft(request):
    """
    Invoice creation feature temporarily disabled.
    """
    return JsonResponse({'success': False, 'error': 'Invoice creation feature is being redesigned'}, status=503)
