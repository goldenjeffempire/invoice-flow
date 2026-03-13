"""
InvoiceFlow Dashboard Views
Command-centre with KPIs, charts, aging, alerts, and activity feed.
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth, TruncWeek
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..models import (
    Client,
    Expense,
    Invoice,
    Notification,
    Payment,
    RecurringSchedule,
    UserProfile,
)

logger = logging.getLogger(__name__)


def _pct(value, total):
    if not total:
        return 0
    return round(float(value or 0) / float(total) * 100, 1)


def _safe_float(val):
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


# ─── Main Dashboard View ───────────────────────────────────────────────────────

@login_required
def dashboard_overview(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        if not profile.onboarding_completed:
            return redirect('invoices:onboarding_router')

        workspace = profile.current_workspace
        if not workspace:
            return redirect('invoices:onboarding_router')

        today = timezone.now().date()
        som = today.replace(day=1)
        last_30 = today - timedelta(days=30)
        last_90 = today - timedelta(days=90)

        kpis = _calculate_kpis(workspace, today, som, last_30)
        cashflow_data = _get_cashflow_data(workspace, last_90, today)
        aging_buckets = _get_aging_data(workspace, today)
        recent_invoices = _get_recent_invoices(workspace, limit=8)
        upcoming_due = _get_upcoming_due(workspace, today, limit=6)
        smart_alerts = _generate_smart_alerts(workspace, today, kpis)
        quick_stats = _get_quick_stats(workspace, today, som)
        top_clients = _get_top_clients(workspace, limit=5)
        revenue_chart = _get_revenue_chart_data(workspace)

        inv_qs = Invoice.objects.filter(workspace=workspace)
        status_counts = {
            'paid': inv_qs.filter(status=Invoice.Status.PAID, paid_at__date__gte=som).count(),
            'sent': inv_qs.filter(status=Invoice.Status.SENT).count(),
            'overdue': inv_qs.filter(status=Invoice.Status.OVERDUE).count(),
            'draft': inv_qs.filter(status=Invoice.Status.DRAFT).count(),
        }

        total_aging = sum(_safe_float(v.get('amount', 0)) for v in aging_buckets.values()) or 1
        aging_data = {
            'current': {
                'amount': _safe_float(aging_buckets.get('current', {}).get('amount', 0)),
                'pct': _pct(aging_buckets.get('current', {}).get('amount', 0), total_aging),
                'count': aging_buckets.get('current', {}).get('count', 0),
            },
            'days_1_30': {
                'amount': _safe_float(aging_buckets.get('1_30', {}).get('amount', 0)),
                'pct': _pct(aging_buckets.get('1_30', {}).get('amount', 0), total_aging),
                'count': aging_buckets.get('1_30', {}).get('count', 0),
            },
            'days_31_60': {
                'amount': _safe_float(aging_buckets.get('31_60', {}).get('amount', 0)),
                'pct': _pct(aging_buckets.get('31_60', {}).get('amount', 0), total_aging),
                'count': aging_buckets.get('31_60', {}).get('count', 0),
            },
            'days_61_90': {
                'amount': _safe_float(aging_buckets.get('61_90', {}).get('amount', 0)),
                'pct': _pct(aging_buckets.get('61_90', {}).get('amount', 0), total_aging),
                'count': aging_buckets.get('61_90', {}).get('count', 0),
            },
            'days_90p': {
                'amount': _safe_float(aging_buckets.get('90_plus', {}).get('amount', 0)),
                'pct': _pct(aging_buckets.get('90_plus', {}).get('amount', 0), total_aging),
                'count': aging_buckets.get('90_plus', {}).get('count', 0),
            },
        }

        ctx = {
            'workspace': workspace,
            'profile': profile,
            'today': today,
            'kpis': kpis,
            'quick_stats': quick_stats,
            'cashflow_json': json.dumps(cashflow_data),
            'revenue_json': json.dumps(revenue_chart),
            'status_json': json.dumps(status_counts),
            'aging_data': aging_data,
            'recent_invoices': recent_invoices,
            'upcoming_due': upcoming_due,
            'smart_alerts': smart_alerts,
            'top_clients': top_clients,
        }
        return render(request, 'pages/dashboard/overview.html', ctx)

    except Exception as e:
        logger.error("Dashboard error: %s", e, exc_info=True)
        try:
            profile = request.user.profile
            workspace = profile.current_workspace
        except Exception:
            profile = None
            workspace = None
        return render(request, 'pages/dashboard/overview.html', {
            'error': 'Unable to load dashboard data. Please refresh.',
            'profile': profile,
            'workspace': workspace,
            'kpis': {},
            'quick_stats': {},
            'cashflow_json': '[]',
            'revenue_json': '{"labels":[],"values":[]}',
            'status_json': '{"paid":0,"sent":0,"overdue":0,"draft":0}',
            'aging_data': {},
            'recent_invoices': [],
            'upcoming_due': [],
            'smart_alerts': [],
            'top_clients': [],
        })


# ─── Async API Endpoints ───────────────────────────────────────────────────────

@login_required
@require_GET
def dashboard_kpis_api(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        workspace = profile.current_workspace
        if not workspace:
            return JsonResponse({'error': 'No workspace'}, status=400)
        today = timezone.now().date()
        kpis = _calculate_kpis(workspace, today, today.replace(day=1), today - timedelta(days=30))
        serial = {k: float(v) if isinstance(v, Decimal) else v for k, v in kpis.items()}
        return JsonResponse({'kpis': serial})
    except Exception as e:
        logger.error("KPIs API error: %s", e)
        return JsonResponse({'error': 'Failed'}, status=500)


@login_required
@require_GET
def dashboard_alerts_api(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        workspace = profile.current_workspace
        if not workspace:
            return JsonResponse({'error': 'No workspace'}, status=400)
        today = timezone.now().date()
        kpis = _calculate_kpis(workspace, today, today.replace(day=1), today - timedelta(days=30))
        alerts = _generate_smart_alerts(workspace, today, kpis)
        return JsonResponse({'alerts': alerts})
    except Exception as e:
        logger.error("Alerts API error: %s", e)
        return JsonResponse({'error': 'Failed'}, status=500)


@login_required
@require_GET
def dashboard_chart_api(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        workspace = profile.current_workspace
        if not workspace:
            return JsonResponse({'error': 'No workspace'}, status=400)
        today = timezone.now().date()
        last_90 = today - timedelta(days=90)
        return JsonResponse({
            'revenue': _get_revenue_chart_data(workspace),
            'cashflow': _get_cashflow_data(workspace, last_90, today),
        })
    except Exception as e:
        logger.error("Chart API error: %s", e)
        return JsonResponse({'error': 'Failed'}, status=500)


# ─── Business Logic Helpers ────────────────────────────────────────────────────

def _calculate_kpis(workspace, today, start_of_month, last_30_days):
    try:
        inv = Invoice.objects.filter(workspace=workspace)

        revenue_month = inv.filter(
            status=Invoice.Status.PAID,
            paid_at__date__gte=start_of_month,
        ).aggregate(t=Coalesce(Sum('total_amount'), Decimal('0')))['t']

        outstanding = inv.filter(
            status__in=[
                Invoice.Status.SENT, Invoice.Status.VIEWED,
                Invoice.Status.PART_PAID, Invoice.Status.OVERDUE,
            ]
        ).aggregate(t=Coalesce(Sum('amount_due'), Decimal('0')))['t']

        overdue_amount = inv.filter(
            status=Invoice.Status.OVERDUE
        ).aggregate(t=Coalesce(Sum('amount_due'), Decimal('0')))['t']

        overdue_count = inv.filter(status=Invoice.Status.OVERDUE).count()
        invoices_this_month = inv.filter(created_at__date__gte=start_of_month).count()
        paid_count_month = inv.filter(
            paid_at__date__gte=start_of_month, status=Invoice.Status.PAID
        ).count()

        prev_start = (start_of_month - timedelta(days=1)).replace(day=1)
        prev_revenue = inv.filter(
            status=Invoice.Status.PAID,
            paid_at__date__gte=prev_start,
            paid_at__date__lt=start_of_month,
        ).aggregate(t=Coalesce(Sum('total_amount'), Decimal('0')))['t']

        revenue_change = 0.0
        if prev_revenue > 0:
            revenue_change = float((revenue_month - prev_revenue) / prev_revenue * 100)

        paid_recent = inv.filter(paid_at__date__gte=last_30_days, status=Invoice.Status.PAID)
        avg_days = 0
        if paid_recent.exists():
            days_list = [
                (i.paid_at.date() - i.issue_date).days
                for i in paid_recent if i.paid_at and i.issue_date
            ]
            avg_days = int(sum(days_list) / len(days_list)) if days_list else 0

        collection_rate = 0.0
        if invoices_this_month > 0:
            collection_rate = round(paid_count_month / invoices_this_month * 100, 1)

        return {
            'revenue_month': revenue_month,
            'outstanding': outstanding,
            'overdue_amount': overdue_amount,
            'overdue_count': overdue_count,
            'avg_payment_days': avg_days,
            'invoices_this_month': invoices_this_month,
            'paid_count_month': paid_count_month,
            'revenue_change': round(revenue_change, 1),
            'collection_rate': collection_rate,
            'prev_revenue': prev_revenue,
        }
    except Exception as e:
        logger.error("KPI calculation error: %s", e)
        return {
            'revenue_month': Decimal('0'), 'outstanding': Decimal('0'),
            'overdue_amount': Decimal('0'), 'overdue_count': 0,
            'avg_payment_days': 0, 'invoices_this_month': 0,
            'paid_count_month': 0, 'revenue_change': 0.0,
            'collection_rate': 0.0, 'prev_revenue': Decimal('0'),
        }


def _get_cashflow_data(workspace, start_date, end_date):
    try:
        payments = (
            Payment.objects.filter(
                invoice__workspace=workspace,
                payment_date__gte=start_date,
                payment_date__lte=end_date,
                status='completed',
            )
            .annotate(week=TruncWeek('payment_date'))
            .values('week')
            .annotate(income=Sum('amount'))
            .order_by('week')
        )

        expenses = (
            Expense.objects.filter(
                workspace=workspace,
                expense_date__gte=start_date,
                expense_date__lte=end_date,
                status='approved',
            )
            .annotate(week=TruncWeek('expense_date'))
            .values('week')
            .annotate(outflow=Sum('amount'))
            .order_by('week')
        )

        pay_dict = {p['week']: float(p['income'] or 0) for p in payments}
        exp_dict = {e['week']: float(e['outflow'] or 0) for e in expenses}
        all_weeks = sorted(set(pay_dict) | set(exp_dict))

        data = []
        for week in all_weeks:
            income = pay_dict.get(week, 0)
            outflow = exp_dict.get(week, 0)
            data.append({
                'week': week.strftime('%b %d') if week else '',
                'income': income,
                'expenses': outflow,
                'net': round(income - outflow, 2),
            })
        return data[-12:] if len(data) > 12 else data
    except Exception as e:
        logger.error("Cashflow error: %s", e)
        return []


def _get_aging_data(workspace, today):
    try:
        invoices = Invoice.objects.filter(
            workspace=workspace,
            status__in=[
                Invoice.Status.SENT, Invoice.Status.VIEWED,
                Invoice.Status.PART_PAID, Invoice.Status.OVERDUE,
            ],
        )
        buckets = {
            'current': {'count': 0, 'amount': Decimal('0'), 'label': 'Current'},
            '1_30': {'count': 0, 'amount': Decimal('0'), 'label': '1–30 days'},
            '31_60': {'count': 0, 'amount': Decimal('0'), 'label': '31–60 days'},
            '61_90': {'count': 0, 'amount': Decimal('0'), 'label': '61–90 days'},
            '90_plus': {'count': 0, 'amount': Decimal('0'), 'label': '90+ days'},
        }
        for inv in invoices:
            days = (today - inv.due_date).days if inv.due_date and inv.due_date < today else 0
            amt = inv.amount_due or Decimal('0')
            if days <= 0:
                key = 'current'
            elif days <= 30:
                key = '1_30'
            elif days <= 60:
                key = '31_60'
            elif days <= 90:
                key = '61_90'
            else:
                key = '90_plus'
            buckets[key]['count'] += 1
            buckets[key]['amount'] += amt
        return buckets
    except Exception as e:
        logger.error("Aging error: %s", e)
        return {}


def _get_recent_invoices(workspace, limit=8):
    try:
        return (
            Invoice.objects.filter(workspace=workspace)
            .select_related('client')
            .order_by('-created_at')[:limit]
        )
    except Exception as e:
        logger.error("Recent invoices error: %s", e)
        return []


def _get_upcoming_due(workspace, today, limit=6):
    try:
        return (
            Invoice.objects.filter(
                workspace=workspace,
                status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID],
                due_date__gte=today,
                due_date__lte=today + timedelta(days=30),
            )
            .select_related('client')
            .order_by('due_date')[:limit]
        )
    except Exception as e:
        logger.error("Upcoming due error: %s", e)
        return []


def _generate_smart_alerts(workspace, today, kpis):
    alerts = []
    try:
        overdue_count = kpis.get('overdue_count', 0)
        if overdue_count:
            alerts.append({
                'type': 'warning',
                'icon': 'alert-triangle',
                'title': f'{overdue_count} Overdue Invoice{"s" if overdue_count != 1 else ""}',
                'message': f"{overdue_count} invoice{'s' if overdue_count != 1 else ''} past due — send reminders to recover revenue.",
                'action_url': '/invoices/?status=overdue',
                'action_label': 'View Overdue',
                'priority': 1,
            })

        due_soon = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED],
            due_date__gte=today,
            due_date__lte=today + timedelta(days=3),
        ).count()
        if due_soon:
            alerts.append({
                'type': 'info',
                'icon': 'clock',
                'title': f'{due_soon} Invoice{"s" if due_soon != 1 else ""} Due Within 3 Days',
                'message': f"{'These invoices are' if due_soon != 1 else 'This invoice is'} due very soon.",
                'action_url': '/invoices/?due_soon=true',
                'action_label': 'Send Reminders',
                'priority': 2,
            })

        draft_count = Invoice.objects.filter(workspace=workspace, status=Invoice.Status.DRAFT).count()
        if draft_count:
            alerts.append({
                'type': 'neutral',
                'icon': 'file-text',
                'title': f'{draft_count} Draft Invoice{"s" if draft_count != 1 else ""}',
                'message': f"{draft_count} invoice{'s are' if draft_count != 1 else ' is'} saved as drafts.",
                'action_url': '/invoices/?status=draft',
                'action_label': 'Review Drafts',
                'priority': 3,
            })

        if kpis.get('revenue_change', 0) > 20:
            alerts.append({
                'type': 'success',
                'icon': 'trending-up',
                'title': f"Revenue Up {kpis['revenue_change']:.1f}% This Month",
                'message': "Great work — your revenue is growing compared to last month.",
                'action_url': '/reports/revenue/',
                'action_label': 'View Report',
                'priority': 4,
            })

        alerts.sort(key=lambda x: x['priority'])
    except Exception as e:
        logger.error("Smart alerts error: %s", e)

    return alerts[:4]


def _get_quick_stats(workspace, today, start_of_month):
    try:
        total_clients = Client.objects.filter(workspace=workspace).count()
        active_clients = Client.objects.filter(
            workspace=workspace,
            invoices__created_at__date__gte=start_of_month,
        ).distinct().count()

        recurring_active = RecurringSchedule.objects.filter(workspace=workspace, status='active').count()
        recurring_value = RecurringSchedule.objects.filter(
            workspace=workspace, status='active'
        ).aggregate(t=Coalesce(Sum('base_amount'), Decimal('0')))['t']

        total_expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=start_of_month,
        ).aggregate(t=Coalesce(Sum('amount'), Decimal('0')))['t']

        return {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'recurring_schedules': recurring_active,
            'recurring_value': recurring_value,
            'expenses_month': total_expenses,
        }
    except Exception as e:
        logger.error("Quick stats error: %s", e)
        return {
            'total_clients': 0, 'active_clients': 0,
            'recurring_schedules': 0, 'recurring_value': Decimal('0'),
            'expenses_month': Decimal('0'),
        }


def _get_top_clients(workspace, limit=5):
    try:
        return (
            Client.objects.filter(workspace=workspace)
            .annotate(
                total_revenue=Sum(
                    'invoices__total_amount',
                    filter=Q(invoices__status=Invoice.Status.PAID),
                ),
                invoice_count=Count(
                    'invoices',
                    filter=Q(invoices__status=Invoice.Status.PAID),
                ),
            )
            .exclude(total_revenue=None)
            .order_by('-total_revenue')[:limit]
        )
    except Exception as e:
        logger.error("Top clients error: %s", e)
        return []


def _get_revenue_chart_data(workspace):
    try:
        data = (
            Invoice.objects.filter(
                workspace=workspace,
                status=Invoice.Status.PAID,
                paid_at__isnull=False,
            )
            .annotate(month=TruncMonth('paid_at'))
            .values('month')
            .annotate(total=Sum('total_amount'))
            .order_by('-month')[:6]
        )
        labels, values = [], []
        for entry in reversed(list(data)):
            labels.append(entry['month'].strftime('%b %Y'))
            values.append(float(entry['total']))
        return {'labels': labels, 'values': values}
    except Exception as e:
        logger.error("Revenue chart error: %s", e)
        return {'labels': [], 'values': []}
