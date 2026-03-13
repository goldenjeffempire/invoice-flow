import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q

from ..models import Invoice, Notification

logger = logging.getLogger(__name__)


@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    workspace = getattr(request, 'workspace', None)
    if not workspace:
        return JsonResponse({'results': []})

    try:
        invoices = Invoice.objects.filter(
            workspace=workspace
        ).filter(
            Q(invoice_number__icontains=query) | Q(client__name__icontains=query)
        ).select_related('client').order_by('-created_at')[:5]

        for inv in invoices:
            sym = getattr(inv, 'currency_symbol', '₦')
            results.append({
                'type': 'invoice',
                'title': f"#{inv.invoice_number} – {inv.client.name if inv.client else 'Unknown'}",
                'url': f"/invoices/{inv.id}/",
                'meta': f"{sym}{inv.total_amount:,.2f} · {inv.get_status_display()}",
            })
    except Exception as e:
        logger.debug("Search invoices error: %s", e)

    try:
        from ..models import Client
        clients = Client.objects.filter(
            workspace=workspace
        ).filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        ).order_by('name')[:5]

        for client in clients:
            results.append({
                'type': 'client',
                'title': client.name,
                'url': f"/clients/{client.id}/",
                'meta': client.email or 'No email',
            })
    except Exception as e:
        logger.debug("Search clients error: %s", e)

    try:
        from ..models import Expense
        expenses = Expense.objects.filter(
            workspace=workspace
        ).filter(
            Q(description__icontains=query)
        ).order_by('-created_at')[:3]

        for exp in expenses:
            results.append({
                'type': 'expense',
                'title': exp.description or 'Expense',
                'url': f"/expenses/{exp.id}/",
                'meta': f"₦{exp.amount:,.2f}",
            })
    except Exception as e:
        logger.debug("Search expenses error: %s", e)

    try:
        from ..models import Estimate
        estimates = Estimate.objects.filter(
            workspace=workspace
        ).filter(
            Q(estimate_number__icontains=query) | Q(client__name__icontains=query)
        ).select_related('client').order_by('-created_at')[:3]

        for est in estimates:
            sym = getattr(est, 'currency_symbol', '₦')
            results.append({
                'type': 'estimate',
                'title': f"#{est.estimate_number} – {est.client.name if est.client else 'Unknown'}",
                'url': f"/estimates/{est.id}/",
                'meta': f"{sym}{est.total_amount:,.2f}",
            })
    except Exception as e:
        logger.debug("Search estimates error: %s", e)

    return JsonResponse({'results': results})


@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'ok'})


@login_required
def set_appearance_preference(request):
    if request.method == 'POST':
        mode = request.POST.get('mode', 'light')
        request.session['dark_mode'] = (mode == 'dark')
        return JsonResponse({'status': 'ok', 'mode': mode})
    return JsonResponse({'status': 'error'}, status=400)
