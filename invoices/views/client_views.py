from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Client, ActivityLog

@login_required
def client_list(request):
    clients = Client.objects.filter(workspace=request.workspace).order_by('-created_at')
    return render(request, 'pages/clients/list.html', {'clients': clients})

@login_required
def client_create(request):
    if request.method == 'POST':
        client = Client.objects.create(
            workspace=request.workspace,
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            billing_address=request.POST.get('billing_address'),
            tax_id=request.POST.get('tax_id')
        )
        ActivityLog.objects.create(
            workspace=request.workspace,
            user=request.user,
            action="Created client",
            resource_type="client",
            resource_id=str(client.id)
        )
        messages.success(request, "Client created successfully.")
        return redirect('invoices:client_list')
    return render(request, 'pages/clients/form.html')

@login_required
def client_profile(request, pk):
    client = get_object_or_404(Client, pk=pk, workspace=request.workspace)
    return render(request, 'pages/clients/profile.html', {'client': client})
