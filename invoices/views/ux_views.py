from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from ..models import Invoice, ActivityLog, Notification

@login_required
def global_search(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        # Search Invoices
        invoices = Invoice.objects.filter(
            Q(invoice_number__icontains=query) | Q(client__name__icontains=query)
        ).filter(workspace=request.workspace).select_related('client')[:5]
        
        for inv in invoices:
            results.append({
                'type': 'Invoice',
                'title': f"#{inv.invoice_number} - {inv.client.name}",
                'url': inv.get_absolute_url() if hasattr(inv, 'get_absolute_url') else f"/invoices/{inv.id}/",
                'meta': f"{inv.currency} {inv.total_amount}"
            })
            
        # Search Clients
        from ..models import Client
        clients = Client.objects.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        ).filter(workspace=request.workspace)[:5]
        
        for client in clients:
            results.append({
                'type': 'Client',
                'title': client.name,
                'url': f"/clients/{client.id}/",
                'meta': client.email
            })

        # Search Expenses
        from ..models import Expense
        expenses = Expense.objects.filter(
            Q(description__icontains=query) | Q(vendor__name__icontains=query)
        ).filter(workspace=request.workspace).select_related('vendor')[:5]
        
        for exp in expenses:
            results.append({
                'type': 'Expense',
                'title': exp.description or f"Expense from {exp.vendor.name if exp.vendor else 'Unknown'}",
                'url': f"/expenses/{exp.id}/",
                'meta': f"{exp.currency} {exp.amount}"
            })
        
    return JsonResponse({'results': results})

@login_required
def activity_timeline(request):
    activities = ActivityLog.objects.filter(workspace=request.workspace).order_by('-timestamp').select_related('user')[:50]
    return render(request, 'pages/activity_timeline.html', {'activities': activities})

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@login_required
def set_appearance_preference(request):
    mode = request.POST.get('mode', 'light')
    request.session['dark_mode'] = (mode == 'dark')
    return JsonResponse({'status': 'success'})
