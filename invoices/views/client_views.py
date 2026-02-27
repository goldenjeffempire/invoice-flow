from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.utils import timezone
from ..models import Client, ClientNote, CommunicationLog, ActivityLog, Invoice

@login_required
def client_list(request):
    workspace = request.user.profile.current_workspace
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'active')
    
    clients = Client.objects.filter(workspace=workspace)
    
    if query:
        clients = clients.filter(
            Q(name__icontains=query) | 
            Q(email__icontains=query) | 
            Q(phone__icontains=query)
        )
    
    # We don't have a formal "is_active" field yet in the model based on initial read, 
    # but the task mentions a status badge. Let's assume they are all active for now 
    # or check if we should add a field. 
    # Looking at the existing template, it just hardcodes "Active".
    
    clients = clients.order_by('name')
    
    for client in clients:
        invoices = client.invoices.all()
        client.total_invoiced = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        client.total_paid = invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        client.outstanding_amount = invoices.exclude(status='paid').aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        last_invoice = invoices.order_by('-issue_date').first()
        client.last_invoice_date = last_invoice.issue_date if last_invoice else None
        client.invoice_count = invoices.count()
        client.is_active = True # Placeholder until field is added if necessary

    return render(request, 'pages/clients/list.html', {
        'clients': clients,
        'query': query,
        'status_filter': status_filter
    })

@login_required
def client_detail(request, client_id):
    workspace = request.user.profile.current_workspace
    client = get_object_or_404(Client, id=client_id, workspace=workspace)
    
    if request.method == 'POST' and request.POST.get('action') == 'add_note':
        content = request.POST.get('content')
        if content:
            ClientNote.objects.create(
                client=client,
                user=request.user,
                content=content
            )
            messages.success(request, "Note added.")
            return redirect('invoices:client_detail', client_id=client.id)

    invoices = client.invoices.all().order_by('-issue_date')
    estimates = client.estimates.all().order_by('-created_at')
    # Assuming payments are linked to invoices
    from ..models import Payment
    payments = Payment.objects.filter(invoice__client=client).order_by('-payment_date')
    
    notes = client.client_notes.all().order_by('-created_at')
    comms = client.comms_logs.all().order_by('-sent_at')
    
    # Stats
    stats = {
        'total_invoiced': invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_paid': invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
        'outstanding': invoices.aggregate(Sum('amount_due'))['amount_due__sum'] or 0,
        'invoice_count': invoices.count(),
    }
    
    activities = ActivityLog.objects.filter(
        workspace=workspace, 
        resource_type='client', 
        resource_id=str(client.id)
    ).order_by('-created_at')[:20]

    return render(request, 'pages/clients/detail.html', {
        'client': client,
        'notes': notes,
        'comms': comms,
        'invoices': invoices,
        'estimates': estimates,
        'payments': payments,
        'activities': activities,
        'stats': stats
    })

@login_required
def client_delete(request, client_id):
    workspace = request.user.profile.current_workspace
    client = get_object_or_404(Client, id=client_id, workspace=workspace)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f"Client {name} deleted successfully.")
        return redirect('invoices:client_list')
    return redirect('invoices:client_detail', client_id=client.id)

@login_required
def client_create(request):
    workspace = request.user.profile.current_workspace
    if request.method == 'POST':
        client = Client.objects.create(
            workspace=workspace,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone', ''),
            billing_address=request.POST.get('billing_address', ''),
            currency=request.POST.get('currency', 'USD'),
            tax_id=request.POST.get('tax_id', '')
        )
        ActivityLog.objects.create(
            workspace=workspace,
            user=request.user,
            action="Created client",
            resource_type="client",
            resource_id=str(client.id)
        )
        messages.success(request, f"Client {client.name} created successfully.")
        return redirect('invoices:client_detail', client_id=client.id)
    return render(request, 'pages/clients/form.html')

@login_required
def client_edit(request, client_id):
    workspace = request.user.profile.current_workspace
    client = get_object_or_404(Client, id=client_id, workspace=workspace)
    if request.method == 'POST':
        client.name = request.POST.get('name')
        client.email = request.POST.get('email')
        client.phone = request.POST.get('phone', '')
        client.billing_address = request.POST.get('billing_address', '')
        client.currency = request.POST.get('currency', 'USD')
        client.tax_id = request.POST.get('tax_id', '')
        client.save()
        messages.success(request, "Client updated successfully.")
        return redirect('invoices:client_detail', client_id=client.id)
    return render(request, 'pages/clients/form.html', {'client': client})
