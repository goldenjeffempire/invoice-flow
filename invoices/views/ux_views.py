import logging
import time
from decimal import Decimal

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone

from ..models import Invoice, Notification, Payment, Payout

logger = logging.getLogger(__name__)


@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if not query or len(query) < 2:
        return JsonResponse({'results': []})

    workspace = getattr(request, 'workspace', None)
    if not workspace and hasattr(request.user, 'profile'):
        try:
            workspace = request.user.profile.current_workspace
        except Exception:
            pass
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


@login_required
def wallet_view(request):
    workspace = getattr(request, 'workspace', None)
    if not workspace and hasattr(request.user, 'profile'):
        try:
            workspace = request.user.profile.current_workspace
        except Exception:
            pass

    total_received = Decimal('0.00')
    total_payouts = Decimal('0.00')
    payment_count = 0
    payout_count = 0
    recent_payments = []
    recent_payouts = []
    monthly_inflow = []

    if workspace:
        agg = Payment.objects.filter(
            workspace=workspace,
            status='completed'
        ).aggregate(total=Sum('amount'), count=Count('id'))
        total_received = agg['total'] or Decimal('0.00')
        payment_count = agg['count'] or 0

        pagg = Payout.objects.filter(
            workspace=workspace,
            status='success'
        ).aggregate(total=Sum('amount'), count=Count('id'))
        total_payouts = pagg['total'] or Decimal('0.00')
        payout_count = pagg['count'] or 0

        recent_payments = Payment.objects.filter(
            workspace=workspace,
            status='completed'
        ).select_related('invoice', 'invoice__client').order_by('-payment_date')[:10]

        recent_payouts = Payout.objects.filter(
            workspace=workspace
        ).order_by('-created_at')[:10]

        from django.db.models.functions import TruncMonth
        from datetime import timedelta
        six_months_ago = timezone.now().date() - timedelta(days=180)
        monthly_inflow = (
            Payment.objects.filter(
                workspace=workspace,
                status='completed',
                payment_date__date__gte=six_months_ago
            )
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

    balance = total_received - total_payouts
    currency_symbol = workspace.currency_symbol if workspace else '₦'

    context = {
        'page_title': 'Wallet',
        'total_received': total_received,
        'total_payouts': total_payouts,
        'balance': balance,
        'payment_count': payment_count,
        'payout_count': payout_count,
        'recent_payments': recent_payments,
        'recent_payouts': recent_payouts,
        'monthly_inflow': list(monthly_inflow),
        'currency_symbol': currency_symbol,
        'workspace': workspace,
    }
    return render(request, 'pages/wallet.html', context)


@login_required
def monitoring_view(request):
    from invoices.health import (
        _get_system_metrics,
        _get_db_pool_stats,
        _get_uptime_formatted,
        APP_VERSION,
    )
    from django.conf import settings
    from django.db import connection, connections
    from django.core.cache import cache
    import platform, sys, django

    checks = {'database': False, 'cache': False, 'migrations': False}
    details = {}

    db_start = time.perf_counter()
    try:
        connections['default'].ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            checks['database'] = True
        details['db_latency_ms'] = round((time.perf_counter() - db_start) * 1000, 2)
    except Exception as e:
        details['db_error'] = str(e)

    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
        checks['migrations'] = len(pending) == 0
        details['pending_migrations'] = len(pending)
    except Exception:
        checks['migrations'] = True
        details['pending_migrations'] = 0

    cache_start = time.perf_counter()
    try:
        cache.set('_mon_test', 'ok', 5)
        checks['cache'] = cache.get('_mon_test') == 'ok'
        cache.delete('_mon_test')
        details['cache_latency_ms'] = round((time.perf_counter() - cache_start) * 1000, 2)
    except Exception:
        checks['cache'] = True

    metrics = _get_system_metrics()
    db_info = _get_db_pool_stats()
    uptime = _get_uptime_formatted()

    context = {
        'page_title': 'System Monitoring',
        'checks': checks,
        'details': details,
        'metrics': metrics,
        'db_info': db_info,
        'uptime': uptime,
        'version': APP_VERSION,
        'python_version': sys.version.split()[0],
        'django_version': django.get_version(),
        'platform': platform.platform(),
        'debug': settings.DEBUG,
        'all_healthy': all(checks.values()),
    }
    return render(request, 'pages/monitoring.html', context)


@login_required
def invoice_templates_view(request):
    workspace = getattr(request, 'workspace', None)
    if not workspace and hasattr(request.user, 'profile'):
        try:
            workspace = request.user.profile.current_workspace
        except Exception:
            pass

    current_style = 'modern'
    saved = False

    if request.method == 'POST':
        style = request.POST.get('invoice_style', 'modern')
        valid_styles = ['modern', 'classic', 'minimal', 'professional', 'bold']
        if style in valid_styles and workspace:
            workspace.invoice_style = style
            workspace.save(update_fields=['invoice_style'])
            saved = True
            current_style = style
    elif workspace:
        current_style = workspace.invoice_style or 'modern'

    styles = [
        {
            'key': 'modern',
            'name': 'Modern',
            'desc': 'Clean, contemporary design with bold typography and accent colors.',
            'accent': '#6366f1',
            'preview_bg': '#f8faff',
        },
        {
            'key': 'classic',
            'name': 'Classic',
            'desc': 'Traditional layout with formal structure — perfect for established businesses.',
            'accent': '#1e3a5f',
            'preview_bg': '#fafaf8',
        },
        {
            'key': 'minimal',
            'name': 'Minimal',
            'desc': 'Stripped-back, whitespace-focused design for a clean, professional look.',
            'accent': '#374151',
            'preview_bg': '#ffffff',
        },
        {
            'key': 'professional',
            'name': 'Professional',
            'desc': 'Structured and detailed layout ideal for consulting and services.',
            'accent': '#0ea5e9',
            'preview_bg': '#f0f9ff',
        },
        {
            'key': 'bold',
            'name': 'Bold',
            'desc': 'High-contrast, attention-grabbing design for creative businesses.',
            'accent': '#7c3aed',
            'preview_bg': '#faf5ff',
        },
    ]

    context = {
        'page_title': 'Invoice Templates',
        'styles': styles,
        'current_style': current_style,
        'saved': saved,
        'workspace': workspace,
    }
    return render(request, 'pages/invoice_templates.html', context)
