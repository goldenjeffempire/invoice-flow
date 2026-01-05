import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from .models import Invoice, LineItem
from .forms import InvoiceForm

@login_required
def create_invoice(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        line_items_data = request.POST.get("line_items")
        
        if form.is_valid():
            try:
                line_items = json.loads(line_items_data) if line_items_data else []
                if not line_items:
                    messages.error(request, "Please add at least one line item.")
                else:
                    with transaction.atomic():
                        invoice = form.save(commit=False)
                        invoice.user = request.user
                        invoice.status = Invoice.Status.UNPAID
                        invoice.save()
                        
                        for item in line_items:
                            LineItem.objects.create(
                                invoice=invoice,
                                description=item.get("description", ""),
                                quantity=Decimal(str(item.get("quantity", 1))),
                                unit_price=Decimal(str(item.get("unit_price", 0)))
                            )
                        
                        messages.success(request, f"Invoice {invoice.invoice_id} created successfully!")
                        return redirect("invoices:invoice_detail", invoice_id=invoice.id)
            except Exception as e:
                messages.error(request, f"Error creating invoice: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                    
    return render(request, "invoices/create_invoice.html")
