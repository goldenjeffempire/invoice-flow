import json
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Invoice, LineItem, UserProfile
from .forms import InvoiceForm

logger = logging.getLogger(__name__)

@login_required
def create_invoice(request):
    """Professional invoice creation with real-time interactivity and atomic persistence."""
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        line_items_data = request.POST.get("line_items")
        
        if form.is_valid():
            try:
                line_items = json.loads(line_items_data) if line_items_data else []
                valid_items = [i for i in line_items if i.get('description', '').strip()]
                
                if not valid_items:
                    messages.error(request, "Invoice must contain at least one valid line item.")
                else:
                    with transaction.atomic():
                        invoice = form.save(commit=False)
                        invoice.user = request.user
                        invoice.status = Invoice.Status.UNPAID
                        invoice.save()
                        
                        for item in valid_items:
                            LineItem.objects.create(
                                invoice=invoice,
                                description=item.get("description", "").strip(),
                                quantity=Decimal(str(item.get("quantity", 1))),
                                unit_price=Decimal(str(item.get("unit_price", 0)))
                            )
                        
                        messages.success(request, f"Invoice {invoice.invoice_id} created successfully!")
                        return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            except Exception as e:
                logger.error(f"Error creating invoice: {e}")
                messages.error(request, "Failed to save invoice due to a system error.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    
    try:
        profile = request.user.profile
    except Exception:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
    context = {
        "currency_choices": Invoice.CURRENCY_CHOICES,
        "default_currency": profile.default_currency or "USD",
        "default_due_date": timezone.now().date() + timedelta(days=30),
        "active": "invoices"
    }
    return render(request, "invoices/create_invoice.html", context)
