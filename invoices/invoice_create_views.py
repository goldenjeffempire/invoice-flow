import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from .models import Invoice, UserProfile
from .invoice_forms import EnterpriseInvoiceForm, EnterpriseLineItemFormSet

logger = logging.getLogger(__name__)

@login_required
def create_invoice(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = EnterpriseInvoiceForm(request.POST)
        formset = EnterpriseLineItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    invoice = form.save(commit=False)
                    invoice.user = request.user
                    invoice.save()
                    
                    formset.instance = invoice
                    formset.save()
                    
                    messages.success(request, f"Invoice {invoice.invoice_id} successfully generated.")
                    return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            except Exception as e:
                logger.error(f"Enterprise Invoice Creation Error: {e}")
                messages.error(request, "A system error occurred. Our team has been notified.")
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for form_in_set in formset:
                for error in form_in_set.non_field_errors():
                    messages.error(request, error)
    else:
        initial_data = {
            "business_name": profile.company_name,
            "business_email": profile.business_email or request.user.email,
            "business_phone": profile.business_phone,
            "business_address": profile.business_address,
            "currency": profile.default_currency,
            "tax_rate": profile.default_tax_rate,
            "invoice_date": timezone.now().date(),
        }
        form = EnterpriseInvoiceForm(initial=initial_data)
        formset = EnterpriseLineItemFormSet()

    return render(request, "invoices/create_invoice.html", {
        "form": form,
        "formset": formset,
        "page_title": "Enterprise Invoice Builder",
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
        discount_rate = float(data.get("discount", 0))
        
        subtotal = sum(float(item.get("qty", 0)) * float(item.get("price", 0)) for item in items)
        discount_amt = (subtotal * discount_rate) / 100
        taxable_amt = subtotal - discount_amt
        tax_amt = (taxable_amt * tax_rate) / 100
        total = taxable_amt + tax_amt
        
        return JsonResponse({
            "subtotal": round(subtotal, 2),
            "discount_amt": round(discount_amt, 2),
            "tax_amt": round(tax_amt, 2),
            "total": round(total, 2)
        })
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({"error": "Invalid calculation parameters"}, status=400)
