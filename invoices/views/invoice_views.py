import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from ..models import Invoice, LineItem, Client, InvoiceActivity
from ..services.invoice_service import InvoiceService

@login_required
def invoice_list(request):
    workspace = request.user.profile.current_workspace
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    invoices = Invoice.objects.filter(workspace=workspace)
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(client__name__icontains=search_query)
        )
        
    return render(request, "pages/invoices/list.html", {"invoices": invoices})

@login_required
def invoice_create(request):
    workspace = request.user.profile.current_workspace
    clients = Client.objects.filter(workspace=workspace)
    
    if request.method == "POST":
        try:
            client_id = request.POST.get('client')
            client = get_object_or_404(Client, id=client_id, workspace=workspace)
            
            invoice_data = {
                'client': client,
                'issue_date': request.POST.get('issue_date'),
                'due_date': request.POST.get('due_date'),
                'currency': request.POST.get('currency', 'USD'),
                'client_memo': request.POST.get('client_memo', ''),
                'internal_notes': request.POST.get('internal_notes', ''),
            }
            
            # Simple item parsing for MVP builder
            items_json = request.POST.get('items_json', '[]')
            items_data = json.loads(items_json)
            
            invoice = InvoiceService.create_invoice(workspace, request.user, invoice_data, items_data)
            messages.success(request, f"Invoice {invoice.invoice_number} created successfully.")
            return redirect('invoices:invoice_detail', invoice_number=invoice.invoice_number)
        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
            
    return render(request, "pages/invoices/builder.html", {"clients": clients})

@login_required
def invoice_detail(request, invoice_number):
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number, workspace=request.user.profile.current_workspace)
    return render(request, "pages/invoices/detail.html", {"invoice": invoice})

@login_required
def invoice_edit(request, invoice_number):
    workspace = request.user.profile.current_workspace
    invoice = get_object_or_404(Invoice, invoice_number=invoice_number, workspace=workspace)
    clients = Client.objects.filter(workspace=workspace)
    
    if request.method == "POST":
        # Edit logic similar to create...
        pass
        
    return render(request, "pages/invoices/builder.html", {"invoice": invoice, "clients": clients})

def public_invoice_view(request, token):
    invoice = get_object_or_404(Invoice, public_token=token)
    invoice.view_count += 1
    invoice.save(update_fields=['view_count'])
    
    InvoiceActivity.objects.create(
        invoice=invoice,
        action="viewed",
        description="Invoice viewed via public link"
    )
    
    return render(request, "pages/invoices/public_pay.html", {"invoice": invoice})
