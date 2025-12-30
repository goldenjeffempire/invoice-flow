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
def create_invoice_start(request):
    """
    Unified, production-grade invoice creation view.
    """
    from .forms import InvoiceForm
    from .services import InvoiceService
    from django.utils import timezone
    from datetime import timedelta

    if request.method == "POST":
        try:
            line_items_data = json.loads(request.POST.get("line_items_json", "[]"))
            if not line_items_data:
                messages.error(request, "Please add at least one item to your invoice.")
                return redirect('invoices:create_invoice_start')

            # We use InvoiceService to handle the heavy lifting
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
                # Handle form errors
                for field, errors in form.errors.items():
                    messages.error(request, f"{field.title()}: {', '.join(errors)}")
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            messages.error(request, "An unexpected error occurred. Please try again.")

    context = {
        'today': timezone.now().date(),
        'default_due_date': timezone.now().date() + timedelta(days=30),
        'active': 'create_invoice_start'
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
