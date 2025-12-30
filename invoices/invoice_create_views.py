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

from .models import Invoice, LineItem, UserProfile
from .invoice_create_forms import (
    InvoiceDetailsForm,
    ClientDetailsForm,
    LineItemForm,
    TaxesDiscountsForm,
    InvoicePreviewForm,
)

if TYPE_CHECKING:
    from django.forms import BaseForm

logger = logging.getLogger(__name__)


@login_required
def create_invoice_start(request):
    """
    Invoice creation feature temporarily disabled.
    """
    messages.info(request, "Invoice creation feature is being redesigned. Please check back soon.")
    return redirect('invoices:invoice_list')


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
