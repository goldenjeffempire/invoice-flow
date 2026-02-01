from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Client, ClientNote, CommunicationLog, ActivityLog, Invoice

@login_required
def client_list(request):
    workspace = request.user.profile.current_workspace
    clients = Client.objects.filter(workspace=workspace).order_by('name')
    return render(request, 'pages/clients/list.html', {'clients': clients})

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

    notes = client.client_notes.all().order_by('-created_at')
    comms = client.comms_logs.all().order_by('-sent_at')
    return render(request, 'pages/clients/detail.html', {
        'client': client,
        'notes': notes,
        'comms': comms
    })

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
