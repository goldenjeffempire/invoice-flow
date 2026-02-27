"""
Production-Grade Dashboard Views
Real-time command center with KPIs, cashflow, invoice aging, quick actions, and smart alerts.
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, Avg
from django.db.models.functions import TruncMonth, TruncWeek, Coalesce
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..models import (
    Invoice, Client, Payment, Expense, RecurringSchedule,
    UserProfile, Workspace, Notification
)

logger = logging.getLogger(__name__)


@login_required
def dashboard_overview(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if not profile.email_verified:
            return redirect('invoices:verification_sent')
        
        if not profile.onboarding_completed:
            return redirect('invoices:onboarding_router')
        
        workspace = profile.current_workspace
        if not workspace:
            return redirect('invoices:onboarding_router')
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        last_30_days = today - timedelta(days=30)
        last_90_days = today - timedelta(days=90)
        
        kpis = _calculate_kpis(workspace, today, start_of_month, last_30_days)
        cashflow_raw = _get_cashflow_data(workspace, last_90_days, today)
        aging_raw = _get_aging_data(workspace, today)
        recent_invoices = _get_recent_invoices(workspace, limit=10)
        upcoming_payments = _get_upcoming_payments(workspace, today)
        smart_alerts = _generate_smart_alerts(workspace, today, kpis)
        quick_stats = _get_quick_stats(workspace, today, start_of_month)
        
        invoices = Invoice.objects.filter(workspace=workspace)
        # Additional data for T001
        revenue_chart_data = json.dumps(_get_revenue_chart_data(workspace))
        status_chart_data = json.dumps({
            'paid': invoices.filter(status=Invoice.Status.PAID, created_at__date__gte=start_of_month).count(),
            'sent': invoices.filter(status=Invoice.Status.SENT, created_at__date__gte=start_of_month).count(),
            'overdue': invoices.filter(status=Invoice.Status.OVERDUE, created_at__date__gte=start_of_month).count(),
        })
        activity_feed = _get_activity_feed(workspace)
        
        top_clients = Client.objects.filter(workspace=workspace).annotate(
            total_revenue=Sum('invoices__total_amount', filter=Q(invoices__status=Invoice.Status.PAID))
        ).order_by('-total_revenue')[:5]

        upcoming_due = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID],
            due_date__gte=today
        ).order_by('due_date')[:5]

        total_aging = sum(float(v.get('amount', 0)) for v in aging_raw.values()) if aging_raw else 1
        aging_data = {
            'current': float(aging_raw.get('current', {}).get('amount', 0)),
            'current_percent': (float(aging_raw.get('current', {}).get('amount', 0)) / total_aging * 100) if total_aging > 0 else 0,
            'days_31_60': float(aging_raw.get('31_60', {}).get('amount', 0)),
            'days_31_60_percent': (float(aging_raw.get('31_60', {}).get('amount', 0)) / total_aging * 100) if total_aging > 0 else 0,
            'days_61_90': float(aging_raw.get('61_90', {}).get('amount', 0)),
            'days_61_90_percent': (float(aging_raw.get('61_90', {}).get('amount', 0)) / total_aging * 100) if total_aging > 0 else 0,
            'days_90_plus': float(aging_raw.get('90_plus', {}).get('amount', 0)),
            'days_90_plus_percent': (float(aging_raw.get('90_plus', {}).get('amount', 0)) / total_aging * 100) if total_aging > 0 else 0,
        }
        
        cashflow_data = json.dumps(cashflow_raw) if cashflow_raw else '[]'
        
        return render(request, 'pages/dashboard/overview.html', {
            'profile': profile,
            'workspace': workspace,
            'kpis': kpis,
            'cashflow_data': cashflow_data,
            'aging_data': aging_data,
            'recent_invoices': recent_invoices,
            'upcoming_payments': upcoming_payments,
            'smart_alerts': smart_alerts,
            'quick_stats': quick_stats,
            'revenue_chart_data': revenue_chart_data,
            'status_chart_data': status_chart_data,
            'activity_feed': activity_feed,
            'top_clients': top_clients,
            'upcoming_due': upcoming_due,
        })
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render(request, 'pages/dashboard/overview.html', {
            'error': 'Unable to load dashboard data. Please try again.',
            'profile': getattr(request.user, 'profile', None),
        })


def _calculate_kpis(workspace, today, start_of_month, last_30_days):
    try:
        invoices = Invoice.objects.filter(workspace=workspace)
        
        total_revenue_month = invoices.filter(
            status=Invoice.Status.PAID,
            paid_at__date__gte=start_of_month
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        total_outstanding = invoices.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE]
        ).aggregate(total=Coalesce(Sum('amount_due'), Decimal('0')))['total']
        
        overdue_amount = invoices.filter(
            status=Invoice.Status.OVERDUE
        ).aggregate(total=Coalesce(Sum('amount_due'), Decimal('0')))['total']
        
        paid_invoices_30d = invoices.filter(
            paid_at__date__gte=last_30_days,
            status=Invoice.Status.PAID
        )
        avg_payment_days = 0
        if paid_invoices_30d.exists():
            total_days = sum([
                (inv.paid_at.date() - inv.issue_date).days
                for inv in paid_invoices_30d if inv.paid_at
            ])
            avg_payment_days = total_days // paid_invoices_30d.count() if paid_invoices_30d.count() > 0 else 0
        
        invoices_this_month = invoices.filter(created_at__date__gte=start_of_month).count()
        paid_this_month = invoices.filter(paid_at__date__gte=start_of_month).count()
        
        prev_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        prev_month_revenue = invoices.filter(
            status=Invoice.Status.PAID,
            paid_at__date__gte=prev_month_start,
            paid_at__date__lt=start_of_month
        ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        
        revenue_change = 0
        if prev_month_revenue > 0:
            revenue_change = ((total_revenue_month - prev_month_revenue) / prev_month_revenue) * 100
        
        return {
            'total_revenue_month': total_revenue_month,
            'total_outstanding': total_outstanding,
            'overdue_amount': overdue_amount,
            'avg_payment_days': avg_payment_days,
            'invoices_this_month': invoices_this_month,
            'paid_this_month': paid_this_month,
            'revenue_change': round(revenue_change, 1),
            'collection_rate': round((paid_this_month / invoices_this_month * 100) if invoices_this_month > 0 else 0, 1),
        }
    except Exception as e:
        logger.error(f"KPI calculation error: {e}")
        return {
            'total_revenue_month': Decimal('0'),
            'total_outstanding': Decimal('0'),
            'overdue_amount': Decimal('0'),
            'avg_payment_days': 0,
            'invoices_this_month': 0,
            'paid_this_month': 0,
            'revenue_change': 0,
            'collection_rate': 0,
        }


def _get_cashflow_data(workspace, start_date, end_date):
    try:
        payments = Payment.objects.filter(
            invoice__workspace=workspace,
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status='completed'
        ).annotate(
            week=TruncWeek('payment_date')
        ).values('week').annotate(
            income=Sum('amount')
        ).order_by('week')
        
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=start_date,
            expense_date__lte=end_date,
            status='approved'
        ).annotate(
            week=TruncWeek('expense_date')
        ).values('week').annotate(
            outflow=Sum('amount')
        ).order_by('week')
        
        payment_dict = {p['week']: float(p['income'] or 0) for p in payments}
        expense_dict = {e['week']: float(e['outflow'] or 0) for e in expenses}
        
        all_weeks = sorted(set(payment_dict.keys()) | set(expense_dict.keys()))
        
        data = []
        for week in all_weeks:
            income = payment_dict.get(week, 0)
            outflow = expense_dict.get(week, 0)
            data.append({
                'week': week.strftime('%b %d') if week else '',
                'income': income,
                'expenses': outflow,
                'net': income - outflow,
            })
        
        return data[-12:] if len(data) > 12 else data
        
    except Exception as e:
        logger.error(f"Cashflow data error: {e}")
        return []


def _get_aging_data(workspace, today):
    try:
        invoices = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE]
        )
        
        aging_buckets = {
            'current': {'count': 0, 'amount': Decimal('0'), 'label': 'Current'},
            '1_30': {'count': 0, 'amount': Decimal('0'), 'label': '1-30 days'},
            '31_60': {'count': 0, 'amount': Decimal('0'), 'label': '31-60 days'},
            '61_90': {'count': 0, 'amount': Decimal('0'), 'label': '61-90 days'},
            '90_plus': {'count': 0, 'amount': Decimal('0'), 'label': '90+ days'},
        }
        
        for invoice in invoices:
            days_overdue = (today - invoice.due_date).days if invoice.due_date < today else 0
            amount = invoice.amount_due or Decimal('0')
            
            if days_overdue <= 0:
                aging_buckets['current']['count'] += 1
                aging_buckets['current']['amount'] += amount
            elif days_overdue <= 30:
                aging_buckets['1_30']['count'] += 1
                aging_buckets['1_30']['amount'] += amount
            elif days_overdue <= 60:
                aging_buckets['31_60']['count'] += 1
                aging_buckets['31_60']['amount'] += amount
            elif days_overdue <= 90:
                aging_buckets['61_90']['count'] += 1
                aging_buckets['61_90']['amount'] += amount
            else:
                aging_buckets['90_plus']['count'] += 1
                aging_buckets['90_plus']['amount'] += amount
        
        return aging_buckets
        
    except Exception as e:
        logger.error(f"Aging data error: {e}")
        return {}


def _get_recent_invoices(workspace, limit=5):
    try:
        return Invoice.objects.filter(
            workspace=workspace
        ).select_related('client').order_by('-created_at')[:limit]
    except Exception as e:
        logger.error(f"Recent invoices error: {e}")
        return []


def _get_upcoming_payments(workspace, today, limit=5):
    try:
        next_30_days = today + timedelta(days=30)
        
        return Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID],
            due_date__gte=today,
            due_date__lte=next_30_days
        ).select_related('client').order_by('due_date')[:limit]
    except Exception as e:
        logger.error(f"Upcoming payments error: {e}")
        return []


def _generate_smart_alerts(workspace, today, kpis):
    alerts = []
    
    try:
        overdue_count = Invoice.objects.filter(
            workspace=workspace,
            status=Invoice.Status.OVERDUE
        ).count()
        
        if overdue_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'alert-triangle',
                'title': f'{overdue_count} Overdue Invoice{"s" if overdue_count > 1 else ""}',
                'message': f"You have {overdue_count} overdue invoice{'s' if overdue_count > 1 else ''} totaling {kpis.get('overdue_amount', 0):,.2f}",
                'action_url': '/invoices/?status=overdue',
                'action_label': 'View Overdue',
                'priority': 1,
            })
        
        due_soon = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED],
            due_date__gte=today,
            due_date__lte=today + timedelta(days=3)
        ).count()
        
        if due_soon > 0:
            alerts.append({
                'type': 'info',
                'icon': 'clock',
                'title': f'{due_soon} Invoice{"s" if due_soon > 1 else ""} Due Soon',
                'message': f"{due_soon} invoice{'s are' if due_soon > 1 else ' is'} due within the next 3 days",
                'action_url': '/invoices/?due_soon=true',
                'action_label': 'Send Reminders',
                'priority': 2,
            })
        
        draft_count = Invoice.objects.filter(
            workspace=workspace,
            status=Invoice.Status.DRAFT
        ).count()
        
        if draft_count > 0:
            alerts.append({
                'type': 'neutral',
                'icon': 'file-text',
                'title': f'{draft_count} Draft Invoice{"s" if draft_count > 1 else ""}',
                'message': f"You have {draft_count} draft invoice{'s' if draft_count > 1 else ''} ready to send",
                'action_url': '/invoices/?status=draft',
                'action_label': 'Review Drafts',
                'priority': 3,
            })
        
        if kpis.get('revenue_change', 0) > 20:
            alerts.append({
                'type': 'success',
                'icon': 'trending-up',
                'title': 'Revenue Growing!',
                'message': f"Your revenue is up {kpis['revenue_change']:.1f}% compared to last month",
                'action_url': '/reports/revenue/',
                'action_label': 'View Report',
                'priority': 4,
            })
        
        if kpis.get('avg_payment_days', 0) > 30:
            alerts.append({
                'type': 'warning',
                'icon': 'calendar',
                'title': 'Slow Payments',
                'message': f"Average payment time is {kpis['avg_payment_days']} days. Consider sending reminders earlier.",
                'action_url': '/settings/reminders/',
                'action_label': 'Adjust Settings',
                'priority': 2,
            })
        
        alerts.sort(key=lambda x: x['priority'])
        
    except Exception as e:
        logger.error(f"Smart alerts error: {e}")
    
    return alerts[:5]


def _get_quick_stats(workspace, today, start_of_month):
    try:
        total_clients = Client.objects.filter(workspace=workspace).count()
        active_clients = Client.objects.filter(
            workspace=workspace,
            invoices__created_at__date__gte=start_of_month
        ).distinct().count()
        
        recurring_active = RecurringSchedule.objects.filter(
            workspace=workspace,
            status='active'
        ).count()
        
        recurring_value = RecurringSchedule.objects.filter(
            workspace=workspace,
            status='active'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        return {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'recurring_schedules': recurring_active,
            'recurring_value': recurring_value,
        }
    except Exception as e:
        logger.error(f"Quick stats error: {e}")
        return {
            'total_clients': 0,
            'active_clients': 0,
            'recurring_schedules': 0,
            'recurring_value': Decimal('0'),
        }


@login_required
@require_GET
def dashboard_kpis_api(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        workspace = profile.current_workspace
        
        if not workspace:
            return JsonResponse({'error': 'No workspace'}, status=400)
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        last_30_days = today - timedelta(days=30)
        
        kpis = _calculate_kpis(workspace, today, start_of_month, last_30_days)
        
        kpis_serializable = {k: float(v) if isinstance(v, Decimal) else v for k, v in kpis.items()}
        
        return JsonResponse({'kpis': kpis_serializable})
        
    except Exception as e:
        logger.error(f"Dashboard KPIs API error: {e}")
        return JsonResponse({'error': 'Failed to load KPIs'}, status=500)


@login_required
@require_GET
def dashboard_alerts_api(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        workspace = profile.current_workspace
        
        if not workspace:
            return JsonResponse({'error': 'No workspace'}, status=400)
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        last_30_days = today - timedelta(days=30)
        
        kpis = _calculate_kpis(workspace, today, start_of_month, last_30_days)
        alerts = _generate_smart_alerts(workspace, today, kpis)
        
        return JsonResponse({'alerts': alerts})
        
    except Exception as e:
        logger.error(f"Dashboard alerts API error: {e}")
        return JsonResponse({'error': 'Failed to load alerts'}, status=500)


def _get_revenue_chart_data(workspace):
    try:
        data = Invoice.objects.filter(
            workspace=workspace,
            status=Invoice.Status.PAID,
            paid_at__isnull=False
        ).annotate(
            month=TruncMonth('paid_at')
        ).values('month').annotate(
            total=Sum('total_amount')
        ).order_by('month')

        labels = []
        values = []
        for entry in data[-6:]:
            labels.append(entry['month'].strftime('%b'))
            values.append(float(entry['total']))
        
        return {'labels': labels, 'values': values}
    except Exception as e:
        logger.error(f"Revenue chart data error: {e}")
        return {'labels': [], 'values': []}


def _get_activity_feed(workspace, limit=5):
    # This would typically come from a dedicated Activity model
    # Mocking for now based on Notifications or similar
    activities = Notification.objects.filter(
        user__userprofile__current_workspace=workspace
    ).order_by('-created_at')[:limit]
    
    return [{
        'title': n.title,
        'message': n.message,
        'created_at': n.created_at
    } for n in activities]
