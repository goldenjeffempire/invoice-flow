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
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="50/h", method="POST", block=True)
def create_invoice_start(request):
    """
    Step 1: Invoice details and client information.
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        details_form = InvoiceDetailsForm(request.POST)
        client_form = ClientDetailsForm(request.POST)
        
        if details_form.is_valid() and client_form.is_valid():
            # Store in session for multi-step form
            request.session['invoice_details'] = {
                'invoice_number': details_form.cleaned_data.get('invoice_number'),
                'invoice_date': str(details_form.cleaned_data['invoice_date']),
                'due_date': str(details_form.cleaned_data['due_date']),
                'currency': details_form.cleaned_data['currency'],
                'description': details_form.cleaned_data.get('description', ''),
            }
            request.session['client_details'] = {
                'client_name': client_form.cleaned_data['client_name'],
                'client_email': client_form.cleaned_data['client_email'],
                'client_phone': client_form.cleaned_data.get('client_phone', ''),
                'client_address': client_form.cleaned_data.get('client_address', ''),
            }
            request.session.modified = True
            
            logger.info(f"User {request.user.username} started invoice creation")
            return redirect('invoices:create_invoice_items')
        else:
            for field, errors in details_form.errors.items():
                for error in errors:
                    messages.error(request, f"Details - {field}: {error}")
            for field, errors in client_form.errors.items():
                for error in errors:
                    messages.error(request, f"Client - {field}: {error}")
    else:
        today = timezone.now().date()
        default_due_date = today + timezone.timedelta(days=30)
        details_form = InvoiceDetailsForm(initial={
            'invoice_date': today,
            'due_date': default_due_date,
            'currency': user_profile.default_currency,
        })
        client_form = ClientDetailsForm()

    context = {
        'step': 1,
        'details_form': details_form,
        'client_form': client_form,
        'user_profile': user_profile,
        'today': timezone.now().date(),
        'default_due_date': timezone.now().date() + timezone.timedelta(days=30),
        'currencies': [
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('NGN', 'Nigerian Naira'),
            ('INR', 'Indian Rupee'),
            ('CAD', 'Canadian Dollar'),
            ('AUD', 'Australian Dollar'),
        ],
        'draft_data': {},
    }
    return render(request, 'invoices/create_invoice_start.html', context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="50/h", method="POST", block=True)
def create_invoice_items(request):
    """
    Step 2: Add line items to invoice.
    """
    invoice_details = request.session.get('invoice_details')
    client_details = request.session.get('client_details')
    
    if not invoice_details or not client_details:
        messages.error(request, "Please complete step 1 first.")
        return redirect('invoices:create_invoice_start')

    if request.method == "POST":
        try:
            line_items_json = request.POST.get('line_items', '[]')
            line_items_data = json.loads(line_items_json)
            
            if not line_items_data:
                messages.error(request, "Please add at least one line item.")
                return redirect('invoices:create_invoice_items')
            
            # Validate each line item
            for item_data in line_items_data:
                form = LineItemForm(item_data)
                if not form.is_valid():
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Item - {field}: {error}")
                    return redirect('invoices:create_invoice_items')
            
            request.session['line_items'] = line_items_data
            request.session.modified = True
            
            logger.info(f"User {request.user.username} added {len(line_items_data)} line items")
            return redirect('invoices:create_invoice_taxes')
        except json.JSONDecodeError:
            messages.error(request, "Invalid line items data.")
            return redirect('invoices:create_invoice_items')
        except Exception as e:
            logger.exception(f"Error processing line items for user {request.user.username}")
            messages.error(request, "An error occurred while processing line items.")
            return redirect('invoices:create_invoice_items')

    line_items = request.session.get('line_items', [])
    context = {
        'step': 2,
        'invoice_details': invoice_details,
        'client_details': client_details,
        'line_items': line_items,
    }
    return render(request, 'invoices/create_invoice_items.html', context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="50/h", method="POST", block=True)
def create_invoice_taxes(request):
    """
    Step 3: Tax and discount configuration.
    """
    invoice_details = request.session.get('invoice_details')
    line_items = request.session.get('line_items')
    
    if not invoice_details or not line_items:
        messages.error(request, "Please complete previous steps first.")
        return redirect('invoices:create_invoice_start')

    if request.method == "POST":
        tax_form = TaxesDiscountsForm(request.POST)
        
        if tax_form.is_valid():
            request.session['tax_discount'] = {
                'tax_rate': str(tax_form.cleaned_data.get('tax_rate', '0.00')),
                'discount_type': tax_form.cleaned_data.get('discount_type', 'none'),
                'discount_value': str(tax_form.cleaned_data.get('discount_value', '0.00')),
            }
            request.session.modified = True
            
            return redirect('invoices:create_invoice_review')
        else:
            for field, errors in tax_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        user_profile = UserProfile.objects.get(user=request.user)
        tax_form = TaxesDiscountsForm(initial={
            'tax_rate': user_profile.default_tax_rate,
        })

    context = {
        'step': 3,
        'tax_form': tax_form,
        'invoice_details': invoice_details,
    }
    return render(request, 'invoices/create_invoice_taxes.html', context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="50/h", method="POST", block=True)
def create_invoice_review(request):
    """
    Step 4: Final review and submission.
    """
    invoice_details = request.session.get('invoice_details')
    client_details = request.session.get('client_details')
    line_items = request.session.get('line_items')
    tax_discount = request.session.get('tax_discount', {})
    
    if not all([invoice_details, client_details, line_items]):
        messages.error(request, "Please complete all required steps.")
        return redirect('invoices:create_invoice_start')

    if request.method == "POST":
        preview_form = InvoicePreviewForm(request.POST)
        
        if preview_form.is_valid():
            try:
                with transaction.atomic():
                    # Create invoice
                    invoice = Invoice.objects.create(
                        user=request.user,
                        client_name=client_details['client_name'],
                        client_email=client_details['client_email'],
                        client_phone=client_details.get('client_phone', ''),
                        client_address=client_details.get('client_address', ''),
                        invoice_number=invoice_details.get('invoice_number'),
                        invoice_date=invoice_details['invoice_date'],
                        due_date=invoice_details['due_date'],
                        currency=invoice_details['currency'],
                        description=invoice_details.get('description', ''),
                        notes=preview_form.cleaned_data.get('notes', ''),
                        payment_terms=preview_form.cleaned_data.get('payment_terms', ''),
                        tax_rate=Decimal(tax_discount.get('tax_rate', '0.00')),
                        discount_type=tax_discount.get('discount_type', 'none'),
                        discount_value=Decimal(tax_discount.get('discount_value', '0.00')),
                        status='draft' if preview_form.cleaned_data.get('save_as_draft') else 'sent',
                    )
                    
                    # Create line items
                    for item_data in line_items:
                        LineItem.objects.create(
                            invoice=invoice,
                            description=item_data['description'],
                            quantity=Decimal(str(item_data['quantity'])),
                            unit_price=Decimal(str(item_data['unit_price'])),
                        )
                    
                    logger.info(f"Invoice {invoice.id} created by {request.user.username}")
                    
                    # Send email if requested
                    if preview_form.cleaned_data.get('send_invoice'):
                        try:
                            from .sendgrid_service import SendGridEmailService
                            email_service = SendGridEmailService()
                            email_service.send_invoice_email(invoice)
                            logger.info(f"Invoice {invoice.id} email sent to {invoice.client_email}")
                        except Exception as e:
                            logger.warning(f"Failed to send invoice email: {e}")
                    
                    # Clear session
                    for key in ['invoice_details', 'client_details', 'line_items', 'tax_discount']:
                        if key in request.session:
                            del request.session[key]
                    request.session.modified = True
                    
                    messages.success(request, f"Invoice created successfully!")
                    return redirect('invoices:invoice_detail', invoice_id=invoice.id)
                    
            except Exception as e:
                logger.exception(f"Error creating invoice for user {request.user.username}")
                messages.error(request, "An error occurred while creating the invoice.")
                return redirect('invoices:create_invoice_review')
        else:
            for field, errors in preview_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        preview_form = InvoicePreviewForm()

    # Calculate totals
    subtotal = Decimal('0.00')
    for item in line_items:
        subtotal += Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
    
    tax_rate = Decimal(tax_discount.get('tax_rate', '0.00'))
    discount_type = tax_discount.get('discount_type', 'none')
    discount_value = Decimal(tax_discount.get('discount_value', '0.00'))
    
    tax_amount = subtotal * (tax_rate / 100) if tax_rate > 0 else Decimal('0.00')
    
    if discount_type == 'percentage':
        discount_amount = subtotal * (discount_value / 100)
    elif discount_type == 'fixed':
        discount_amount = discount_value
    else:
        discount_amount = Decimal('0.00')
    
    total = subtotal - discount_amount + tax_amount

    context = {
        'step': 4,
        'preview_form': preview_form,
        'invoice_details': invoice_details,
        'client_details': client_details,
        'line_items': line_items,
        'tax_discount': tax_discount,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'discount_amount': discount_amount,
        'total': total,
    }
    return render(request, 'invoices/create_invoice_review.html', context)


@login_required
@require_POST
@csrf_protect
@ratelimit(key="user", rate="50/h", method="POST", block=True)
def save_invoice_draft(request):
    """
    AJAX endpoint to save invoice as draft during creation.
    """
    try:
        invoice_details = request.session.get('invoice_details')
        client_details = request.session.get('client_details')
        line_items = request.session.get('line_items', [])
        
        if not all([invoice_details, client_details, line_items]):
            return JsonResponse({'success': False, 'error': 'Incomplete invoice data'}, status=400)
        
        with transaction.atomic():
            invoice = Invoice.objects.create(
                user=request.user,
                client_name=client_details['client_name'],
                client_email=client_details['client_email'],
                status='draft',
            )
            
            for item_data in line_items:
                LineItem.objects.create(
                    invoice=invoice,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data['quantity'])),
                    unit_price=Decimal(str(item_data['unit_price'])),
                )
            
            logger.info(f"Draft invoice {invoice.id} saved by {request.user.username}")
        
        return JsonResponse({'success': True, 'invoice_id': invoice.id})
    except Exception as e:
        logger.exception(f"Error saving draft invoice for user {request.user.username}")
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)
