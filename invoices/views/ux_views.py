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
            Q(invoice_id__icontains=query) | Q(client_name__icontains=query)
        ).select_related('user')[:5]
        
        for inv in invoices:
            results.append({
                'type': 'Invoice',
                'title': f"#{inv.invoice_id} - {inv.client_name}",
                'url': f"/invoice/{inv.invoice_id}/",
                'meta': f"{inv.currency} {inv.total if hasattr(inv, 'total') else ''}"
            })
            
        # Mock results for clients/payments since models might not be fully fleshed out
        # In a real scenario, we'd add search for Client and Payment models here
        
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
