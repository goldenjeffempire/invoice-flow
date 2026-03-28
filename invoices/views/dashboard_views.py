"""
InvoiceFlow – Dashboard View (production rebuild)
"""
from __future__ import annotations
import calendar
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import Client, Expense, Invoice, Payment, RecurringSchedule, Estimate

from django.views.decorators.http import require_GET
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _pct_change(current, previous):
    try:
        if previous and previous > 0:
            return round(float((current - previous) / previous * 100), 1)
        if current and current > 0:
            return 100.0
        return None
    except Exception:
        return None


def _monthly_trend(workspace, months=6):
    today = timezone.now().date()
    labels, revenue, expenses = [], [], []
    for i in range(months - 1, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        last_day = calendar.monthrange(year, month)[1]
        m_start = today.replace(year=year, month=month, day=1)
        m_end = today.replace(year=year, month=month, day=last_day)
        rev = Payment.objects.filter(
            invoice__workspace=workspace,
            payment_date__date__gte=m_start,
            payment_date__date__lte=m_end,
            status=Payment.Status.COMPLETED,
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        exp = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=m_start,
            expense_date__lte=m_end,
        ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        labels.append(m_start.strftime("%b '%y"))
        revenue.append(float(rev))
        expenses.append(float(exp))
    return labels, revenue, expenses


def _invoice_status_breakdown(workspace):
    qs = Invoice.objects.filter(workspace=workspace)
    return {
        "draft":     qs.filter(status="draft").count(),
        "sent":      qs.filter(status="sent").count(),
        "viewed":    qs.filter(status="viewed").count(),
        "part_paid": qs.filter(status="part_paid").count(),
        "paid":      qs.filter(status="paid").count(),
        "overdue":   qs.filter(status="overdue").count(),
    }


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    workspace = getattr(profile, "current_workspace", None) if profile else None

    if not workspace:
        return redirect("invoices:onboarding_router")

    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    invoices_qs = Invoice.objects.filter(workspace=workspace)
    payments_qs = Payment.objects.filter(invoice__workspace=workspace, status=Payment.Status.COMPLETED)
    expenses_qs = Expense.objects.filter(workspace=workspace)
    clients_qs = Client.objects.filter(workspace=workspace)

    # ── Revenue KPIs ─────────────────────────────────────────────────────
    this_month_revenue = payments_qs.filter(
        payment_date__date__gte=month_start, payment_date__date__lte=today
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    last_month_revenue = payments_qs.filter(
        payment_date__date__gte=last_month_start, payment_date__date__lte=last_month_end
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    revenue_change_pct = _pct_change(this_month_revenue, last_month_revenue)

    total_outstanding = invoices_qs.filter(
        status__in=["sent", "viewed", "part_paid", "overdue"]
    ).aggregate(t=Sum("amount_due"))["t"] or Decimal("0")

    total_overdue = invoices_qs.filter(status="overdue").aggregate(t=Sum("amount_due"))["t"] or Decimal("0")
    overdue_count = invoices_qs.filter(status="overdue").count()
    draft_count = invoices_qs.filter(status="draft").count()

    this_month_expenses = expenses_qs.filter(
        expense_date__gte=month_start, expense_date__lte=today
    ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")

    last_month_expenses = expenses_qs.filter(
        expense_date__gte=last_month_start, expense_date__lte=last_month_end
    ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")

    expenses_change_pct = _pct_change(this_month_expenses, last_month_expenses)
    net_profit = this_month_revenue - this_month_expenses

    total_clients = clients_qs.count()
    new_clients_this_month = clients_qs.filter(created_at__date__gte=month_start).count()
    all_time_paid = Payment.objects.filter(
        invoice__workspace=workspace, status=Payment.Status.COMPLETED
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    total_invoiced_mtd = invoices_qs.filter(
        issue_date__gte=month_start
    ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")

    collection_rate = None
    if total_invoiced_mtd > 0:
        collection_rate = round(float(this_month_revenue / total_invoiced_mtd * 100), 1)

    # ── Estimate Stats ────────────────────────────────────────────────────
    estimate_conversion = 0
    try:
        from ..models import Estimate
        est_total = Estimate.objects.filter(workspace=workspace).exclude(status='draft').count()
        est_accepted = Estimate.objects.filter(workspace=workspace, status='approved').count()
        if est_total > 0:
            estimate_conversion = round(est_accepted / est_total * 100, 1)
    except Exception:
        pass

    # ── Invoice status breakdown ──────────────────────────────────────────
    invoice_status_counts = _invoice_status_breakdown(workspace)
    total_invoice_count = sum(invoice_status_counts.values())

    # ── Recent data ───────────────────────────────────────────────────────
    recent_invoices = invoices_qs.select_related("client").order_by("-created_at")[:8]
    recent_payments = Payment.objects.filter(
        invoice__workspace=workspace
    ).select_related("invoice", "invoice__client").order_by("-created_at")[:6]
    invoices_due_soon = invoices_qs.filter(
        status__in=["sent", "viewed", "part_paid"],
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
    ).select_related("client").order_by("due_date")[:5]
    overdue_invoices = invoices_qs.filter(
        status="overdue"
    ).select_related("client").order_by("due_date")[:5]
    recent_expenses = expenses_qs.select_related("category").order_by("-expense_date")[:5]
    top_clients = clients_qs.annotate(
        paid_total=Sum(
            "invoices__amount_paid",
            filter=Q(invoices__status__in=["paid", "part_paid"]),
        ),
        invoice_count=Count("invoices"),
    ).filter(paid_total__gt=0).order_by("-paid_total")[:5]

    # ── Overdue aging ─────────────────────────────────────────────────────
    overdue_qs = invoices_qs.filter(status="overdue")
    aging = {
        "0_30": overdue_qs.filter(due_date__gte=today - timedelta(days=30)).aggregate(t=Sum("amount_due"))["t"] or Decimal("0"),
        "31_60": overdue_qs.filter(due_date__gte=today - timedelta(days=60), due_date__lt=today - timedelta(days=30)).aggregate(t=Sum("amount_due"))["t"] or Decimal("0"),
        "61_90": overdue_qs.filter(due_date__gte=today - timedelta(days=90), due_date__lt=today - timedelta(days=60)).aggregate(t=Sum("amount_due"))["t"] or Decimal("0"),
        "90_plus": overdue_qs.filter(due_date__lt=today - timedelta(days=90)).aggregate(t=Sum("amount_due"))["t"] or Decimal("0"),
    }

    # ── Recurring ─────────────────────────────────────────────────────────
    active_schedules = RecurringSchedule.objects.filter(workspace=workspace, status="active").count()

    # ── Charts ────────────────────────────────────────────────────────────
    chart_labels, chart_revenue, chart_expenses = _monthly_trend(workspace, months=6)

    invoice_status_items = [
        ("draft",     "Draft",     "#94a3b8"),
        ("sent",      "Sent",      "#a78bfa"),
        ("viewed",    "Viewed",    "#60a5fa"),
        ("part_paid", "Part Paid", "#2dd4bf"),
        ("paid",      "Paid",      "#4ade80"),
        ("overdue",   "Overdue",   "#f87171"),
    ]

    # ── Activity Feed ─────────────────────────────────────────────────────
    from ..models import ActivityLog
    recent_activity = []
    try:
        recent_activity = ActivityLog.objects.filter(
            workspace=workspace
        ).select_related("user").order_by("-timestamp")[:12]
    except Exception:
        pass

    ctx = {
        "workspace": workspace,
        "today": today,
        "page_title": "Dashboard",
        "kpis": {
            "this_month_revenue": this_month_revenue,
            "revenue_change_pct": revenue_change_pct,
            "total_outstanding": total_outstanding,
            "total_overdue": total_overdue,
            "overdue_count": overdue_count,
            "draft_count": draft_count,
            "total_clients": total_clients,
            "new_clients_this_month": new_clients_this_month,
            "this_month_expenses": this_month_expenses,
            "expenses_change_pct": expenses_change_pct,
            "all_time_paid": all_time_paid,
            "net_profit": net_profit,
            "net_profit_abs": abs(net_profit),
            "collection_rate": collection_rate,
            "total_invoice_count": total_invoice_count,
            "active_schedules": active_schedules,
            "estimate_conversion": estimate_conversion,
        },
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "invoices_due_soon": invoices_due_soon,
        "overdue_invoices": overdue_invoices,
        "recent_expenses": recent_expenses,
        "invoice_status_counts": invoice_status_counts,
        "invoice_status_counts_json": json.dumps(invoice_status_counts),
        "invoice_status_items": invoice_status_items,
        "top_clients": top_clients,
        "aging": aging,
        "chart_labels": json.dumps(chart_labels),
        "chart_revenue": json.dumps(chart_revenue),
        "chart_expenses": json.dumps(chart_expenses),
        "recent_activity": recent_activity,
    }
    return render(request, "pages/dashboard.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard JSON API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def _get_workspace(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "current_workspace", None) if profile else None


@login_required
@require_GET
def api_dashboard_summary(request):
    workspace = _get_workspace(request)
    if not workspace:
        return JsonResponse({"error": "No workspace"}, status=400)

    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    payments_qs = Payment.objects.filter(invoice__workspace=workspace, status=Payment.Status.COMPLETED)
    invoices_qs = Invoice.objects.filter(workspace=workspace)
    expenses_qs = Expense.objects.filter(workspace=workspace)

    this_month_revenue = payments_qs.filter(
        payment_date__date__gte=month_start, payment_date__date__lte=today
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    last_month_revenue = payments_qs.filter(
        payment_date__date__gte=last_month_start, payment_date__date__lte=last_month_end
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

    total_outstanding = invoices_qs.filter(
        status__in=["sent", "viewed", "part_paid", "overdue"]
    ).aggregate(t=Sum("amount_due"))["t"] or Decimal("0")

    total_overdue = invoices_qs.filter(status="overdue").aggregate(t=Sum("amount_due"))["t"] or Decimal("0")
    overdue_count = invoices_qs.filter(status="overdue").count()

    this_month_expenses = expenses_qs.filter(
        expense_date__gte=month_start, expense_date__lte=today
    ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")

    net_profit = this_month_revenue - this_month_expenses
    revenue_change = _pct_change(this_month_revenue, last_month_revenue)

    return JsonResponse({
        "currency_symbol": workspace.currency_symbol,
        "this_month_revenue": float(this_month_revenue),
        "last_month_revenue": float(last_month_revenue),
        "revenue_change_pct": revenue_change,
        "total_outstanding": float(total_outstanding),
        "total_overdue": float(total_overdue),
        "overdue_count": overdue_count,
        "this_month_expenses": float(this_month_expenses),
        "net_profit": float(net_profit),
        "total_clients": Client.objects.filter(workspace=workspace).count(),
        "total_invoices": invoices_qs.count(),
        "invoice_status": _invoice_status_breakdown(workspace),
    })


@login_required
@require_GET
def api_recent_invoices(request):
    workspace = _get_workspace(request)
    if not workspace:
        return JsonResponse({"error": "No workspace"}, status=400)

    limit = min(int(request.GET.get("limit", 10)), 50)
    invoices = (
        Invoice.objects.filter(workspace=workspace)
        .select_related("client")
        .order_by("-created_at")[:limit]
    )

    data = []
    for inv in invoices:
        data.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "client_name": inv.client.name if inv.client else "",
            "total_amount": float(inv.total_amount),
            "amount_due": float(inv.amount_due),
            "currency": inv.currency,
            "currency_symbol": inv.currency_symbol,
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "url": f"/invoices/{inv.id}/",
            "days_overdue": inv.days_overdue if inv.status == "overdue" else None,
        })

    return JsonResponse({"invoices": data, "count": len(data)})


@login_required
@require_GET
def api_recent_payments(request):
    workspace = _get_workspace(request)
    if not workspace:
        return JsonResponse({"error": "No workspace"}, status=400)

    limit = min(int(request.GET.get("limit", 10)), 50)
    payments = (
        Payment.objects.filter(invoice__workspace=workspace)
        .select_related("invoice", "invoice__client")
        .order_by("-payment_date")[:limit]
    )

    data = []
    for pmt in payments:
        data.append({
            "id": pmt.id,
            "invoice_number": pmt.invoice.invoice_number,
            "client_name": pmt.invoice.client.name if pmt.invoice.client else "",
            "amount": float(pmt.amount),
            "currency": pmt.currency,
            "status": pmt.status,
            "payment_date": pmt.payment_date.isoformat() if pmt.payment_date else None,
            "invoice_url": f"/invoices/{pmt.invoice.id}/",
            "payment_url": f"/payments/{pmt.id}/",
        })

    return JsonResponse({"payments": data, "count": len(data)})


@login_required
@require_GET
def api_revenue_expenses(request):
    workspace = _get_workspace(request)
    if not workspace:
        return JsonResponse({"error": "No workspace"}, status=400)

    months = min(int(request.GET.get("months", 6)), 24)
    labels, revenue, expenses = _monthly_trend(workspace, months=months)

    net = [round(r - e, 2) for r, e in zip(revenue, expenses)]

    return JsonResponse({
        "labels": labels,
        "revenue": revenue,
        "expenses": expenses,
        "net_profit": net,
        "currency_symbol": workspace.currency_symbol,
    })
