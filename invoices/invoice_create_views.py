"""
Production-grade Create Invoice views with comprehensive security, validation, and transaction support.
Implements modern, multi-step invoice creation workflow with real-time validation and error handling.
"""

import json
import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any

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

from .models import Invoice, LineItem, UserProfile, InvoiceTemplate
from .forms import InvoiceForm
from .services import InvoiceService
from .validators import InvoiceBusinessRules

if TYPE_CHECKING:
    from django.forms import BaseForm

logger = logging.getLogger(__name__)


class CreateInvoiceValidator:
    """Comprehensive validation for invoice creation."""
    
    @staticmethod
    def validate_line_items(items: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Validate line items structure and data."""
        if not items or len(items) == 0:
            return False, "Please add at least one item to your invoice."
        
        for idx, item in enumerate(items, 1):
            # Check required fields
            if not item.get('description', '').strip():
                return False, f"Item {idx}: Description is required."
            
            if not item.get('quantity'):
                return False, f"Item {idx}: Quantity is required."
            
            if not item.get('unit_price'):
                return False, f"Item {idx}: Unit price is required."
            
            # Validate numeric values
            try:
                qty = Decimal(str(item.get('quantity', 0)))
                if qty <= 0:
                    return False, f"Item {idx}: Quantity must be greater than zero."
                if qty > Decimal('999999.99'):
                    return False, f"Item {idx}: Quantity is too large."
            except (ValueError, TypeError):
                return False, f"Item {idx}: Quantity must be a valid number."
            
            try:
                price = Decimal(str(item.get('unit_price', 0)))
                if price < 0:
                    return False, f"Item {idx}: Unit price cannot be negative."
                if price > Decimal('999999.99'):
                    return False, f"Item {idx}: Unit price is too large."
            except (ValueError, TypeError):
                return False, f"Item {idx}: Unit price must be a valid number."
        
        return True, None
    
    @staticmethod
    def validate_invoice_dates(invoice_date: str, due_date: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validate invoice and due dates."""
        try:
            inv_date = timezone.datetime.strptime(invoice_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return False, "Invalid invoice date format."
        
        if inv_date > timezone.now().date():
            return False, "Invoice date cannot be in the future."
        
        if due_date:
            try:
                due = timezone.datetime.strptime(due_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return False, "Invalid due date format."
            
            if due < inv_date:
                return False, "Due date cannot be earlier than invoice date."
        
        return True, None


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def create_invoice_start(request):
    """
    Main Create Invoice page with comprehensive form handling.
    Displays form for client info, business info, and line items.
    """
    # Get user's default settings
    user_profile = getattr(request.user, 'profile', None)
    default_currency = user_profile.default_currency if user_profile else 'USD'
    default_tax = float(user_profile.default_tax_rate) if user_profile else 0
    
    templates = []
    recent_clients = []
    if user_profile:
        templates = list(
            user_profile.user.invoice_templates.values('id', 'name', 'currency', 'tax_rate')
        )
        # Get recent clients (last 10 unique clients)
        recent_clients = list(
            Invoice.objects.filter(user=request.user)
            .values('client_name', 'client_email', 'client_phone', 'client_address')
            .distinct()
            .order_by('-created_at')[:10]
        )
    
    if request.method == "POST":
        try:
            # Parse line items from JSON
            line_items_json = request.POST.get("line_items_json", "[]")
            line_items_data = json.loads(line_items_json)
            
            # Validate line items
            valid, error_msg = CreateInvoiceValidator.validate_line_items(line_items_data)
            if not valid:
                messages.error(request, error_msg)
                return render(request, "invoices/create_invoice.html", {
                    'form': InvoiceForm(request.POST),
                    'today': timezone.now().date(),
                    'default_due_date': timezone.now().date() + timedelta(days=30),
                    'default_currency': default_currency,
                    'default_tax': default_tax,
                    'templates': templates,
                    'recent_clients': recent_clients,
                    'active': 'create_invoice',
                })
            
            # Validate dates
            invoice_date = request.POST.get('invoice_date', str(timezone.now().date()))
            due_date = request.POST.get('due_date', '')
            date_valid, date_error = CreateInvoiceValidator.validate_invoice_dates(invoice_date, due_date)
            if not date_valid:
                messages.error(request, date_error)
                return render(request, "invoices/create_invoice.html", {
                    'form': InvoiceForm(request.POST),
                    'today': timezone.now().date(),
                    'default_due_date': timezone.now().date() + timedelta(days=30),
                    'default_currency': default_currency,
                    'default_tax': default_tax,
                    'templates': templates,
                    'recent_clients': recent_clients,
                    'active': 'create_invoice',
                })
            
            # Create invoice using service layer
            invoice, form = InvoiceService.create_invoice(
                user=request.user,
                invoice_data=request.POST,
                files_data=request.FILES,
                line_items_data=line_items_data
            )
            
            if invoice:
                messages.success(
                    request, 
                    f"✓ Invoice #{invoice.invoice_id} created successfully!"
                )
                return redirect('invoices:invoice_detail', invoice_id=invoice.id)
            else:
                # Display form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                
                return render(request, "invoices/create_invoice.html", {
                    'form': form,
                    'today': timezone.now().date(),
                    'default_due_date': timezone.now().date() + timedelta(days=30),
                    'default_currency': default_currency,
                    'default_tax': default_tax,
                    'templates': templates,
                    'recent_clients': recent_clients,
                    'active': 'create_invoice',
                })
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            messages.error(request, "Invalid data format. Please check your entries and try again.")
        except Exception as e:
            logger.error(f"Critical error in invoice creation: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while creating the invoice. Please try again.")
    
    # GET request - display empty form
    context = {
        'form': InvoiceForm(),
        'today': timezone.now().date(),
        'default_due_date': timezone.now().date() + timedelta(days=30),
        'default_currency': default_currency,
        'default_tax': default_tax,
        'templates': templates,
        'recent_clients': recent_clients,
        'active': 'create_invoice',
    }
    
    return render(request, "invoices/create_invoice.html", context)


@login_required
@csrf_protect
@require_POST
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def load_template(request):
    """
    Load invoice template data via AJAX.
    Returns template data as JSON for pre-filling the form.
    """
    try:
        template_id = request.POST.get('template_id')
        if not template_id:
            return JsonResponse({'success': False, 'error': 'Template ID is required'}, status=400)
        
        template = InvoiceTemplate.objects.get(id=template_id, user=request.user)
        
        template_data = {
            'success': True,
            'business_name': template.business_name,
            'business_email': template.business_email,
            'business_phone': template.business_phone or '',
            'business_address': template.business_address,
            'currency': template.currency,
            'tax_rate': float(template.tax_rate),
        }
        return JsonResponse(template_data)
    
    except InvoiceTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'}, status=404)
    except Exception as e:
        logger.error(f"Error loading template: {str(e)}")
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)


@login_required
@csrf_protect
@require_POST
@ratelimit(key='user', rate='20/m', method='POST', block=True)
def validate_invoice_form(request):
    """
    Real-time validation of invoice form fields via AJAX.
    Returns validation errors if any exist.
    """
    try:
        form = InvoiceForm(request.POST, request.FILES)
        
        errors = {}
        if not form.is_valid():
            for field, field_errors in form.errors.items():
                errors[field] = field_errors
        
        return JsonResponse({
            'success': len(errors) == 0,
            'errors': errors
        })
    
    except Exception as e:
        logger.error(f"Error validating form: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Validation error'}, status=500)


@login_required
@csrf_protect
@require_POST
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def calculate_totals(request):
    """
    Calculate invoice totals (subtotal, tax, total, discount) via AJAX.
    Returns calculated values based on line items and tax rate.
    """
    try:
        line_items_json = request.POST.get('line_items_json', '[]')
        tax_rate = Decimal(request.POST.get('tax_rate', '0'))
        discount_rate = Decimal(request.POST.get('discount', '0'))
        
        line_items_data = json.loads(line_items_json)
        
        subtotal = Decimal('0')
        for item in line_items_data:
            try:
                qty = Decimal(str(item.get('quantity', 0)))
                price = Decimal(str(item.get('unit_price', 0)))
                subtotal += qty * price
            except (ValueError, TypeError):
                continue
        
        # Validate rates
        if tax_rate < 0 or tax_rate > 100:
            tax_rate = Decimal('0')
        if discount_rate < 0 or discount_rate > 100:
            discount_rate = Decimal('0')
        
        # Calculate with discount applied before tax
        discount_amount = (subtotal * discount_rate) / Decimal('100')
        after_discount = subtotal - discount_amount
        tax_amount = (after_discount * tax_rate) / Decimal('100')
        total = after_discount + tax_amount
        
        return JsonResponse({
            'success': True,
            'subtotal': float(subtotal),
            'discount_amount': float(discount_amount),
            'after_discount': float(after_discount),
            'tax_amount': float(tax_amount),
            'total': float(total),
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        logger.error(f"Error calculating totals: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Calculation error'}, status=500)
