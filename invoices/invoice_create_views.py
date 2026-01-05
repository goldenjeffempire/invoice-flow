import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from .models import Invoice, LineItem, UserProfile
from .invoice_forms import InvoiceForm, LineItemFormSet

logger = logging.getLogger(__name__)

@login_required
def create_invoice(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = LineItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save(commit=False)
                    invoice.user = request.user
                    invoice.save()
                    
                    formset.instance = invoice
                    formset.save()
                    
                    messages.success(request, f"Invoice {invoice.invoice_id} created successfully!")
                    return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            except Exception as e:
                logger.error(f"Error creating invoice: {e}")
                messages.error(request, "An error occurred while creating the invoice. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill with user profile data
        initial_data = {
            "business_name": profile.company_name,
            "business_email": profile.business_email or request.user.email,
            "business_phone": profile.business_phone,
            "business_address": profile.business_address,
            "currency": profile.default_currency,
            "tax_rate": profile.default_tax_rate,
        }
        form = InvoiceForm(initial=initial_data)
        formset = LineItemFormSet()

    return render(request, "invoices/create_invoice.html", {
        "form": form,
        "formset": formset,
        "page_title": "Create New Invoice",
        "active": "create_invoice"
    })

@login_required
def calculate_totals(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        tax_rate = float(data.get("tax_rate", 0))
        discount = float(data.get("discount", 0))
        
        subtotal = sum(float(item.get("quantity", 0)) * float(item.get("unit_price", 0)) for item in items)
        discount_amount = (subtotal * discount) / 100
        taxable_amount = subtotal - discount_amount
        tax_amount = (taxable_amount * tax_rate) / 100
        total = taxable_amount + tax_amount
        
        return JsonResponse({
            "subtotal": round(subtotal, 2),
            "discount_amount": round(discount_amount, 2),
            "tax_amount": round(tax_amount, 2),
            "total": round(total, 2)
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": str(e)}, status=400)
