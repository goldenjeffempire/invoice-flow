"""
InvoiceFlow – Dashboard View (production rebuild)
Provides rich KPIs, trend charts, activity feeds, and quick actions.
"""
from __future__ import annotations

import calendar
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import Client, Expense, Invoice, Payment

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pct_change(current: Decimal, previous: Decimal):
    if previous and previous > 0:
        return round(float((current - previous) / previous * 100), 1)
    if current and current > 0:
        return 100.0
    return None


def _monthly_trend(workspace, months: int = 6):
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
        rev = (
            Payment.objects.filter(
                invoice__workspace=workspace,
                payment_date__gte=m_start,
                payment_date__lte=m_end,
            ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        )
        exp = (
            Expense.objects.filter(
                workspace=workspace,
                expense_date__gte=m_start,
                expense_date__lte=m_end,
            ).aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        )
        labels.append(m_start.strftime("%b '%y"))
        revenue.append(float(rev))
        expenses.append(float(exp))
    return labels, revenue, expenses


def _daily_sparkline(workspace, days: int = 30):
    today = timezone.now().date()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        total = (
            Payment.objects.filter(
                invoice__workspace=workspace,
                payment_date=d,
            ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        )
        result.append(float(total))
    return result


# ─── View ─────────────────────────────────────────────────────────────────────

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
    payments_qs = Payment.objects.filter(invoice__workspace=workspace)
    expenses_qs = Expense.objects.filter(workspace=workspace)
    clients_qs = Client.objects.filter(workspace=workspace)

    # ── Revenue KPIs ─────────────────────────────────────────────────────────
    this_month_revenue = (
        payments_qs.filter(payment_date__gte=month_start, payment_date__lte=today)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )
    last_month_revenue = (
        payments_qs.filter(payment_date__gte=last_month_start, payment_date__lte=last_month_end)
        .aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )
    revenue_change_pct = _pct_change(this_month_revenue, last_month_revenue)

    total_outstanding = (
        invoices_qs.filter(status__in=["sent", "viewed", "part_paid", "overdue"])
        .aggregate(t=Sum("amount_due"))["t"] or Decimal("0")
    )
    total_overdue = (
        invoices_qs.filter(status="overdue").aggregate(t=Sum("amount_due"))["t"] or Decimal("0")
    )
    overdue_count = invoices_qs.filter(status="overdue").count()
    draft_count = invoices_qs.filter(status="draft").count()

    this_month_expenses = (
        expenses_qs.filter(expense_date__gte=month_start, expense_date__lte=today)
        .aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
    )
    last_month_expenses = (
        expenses_qs.filter(expense_date__gte=last_month_start, expense_date__lte=last_month_end)
        .aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
    )
    expenses_change_pct = _pct_change(this_month_expenses, last_month_expenses)

    net_profit = this_month_revenue - this_month_expenses

    total_clients = clients_qs.count()
    new_clients_this_month = clients_qs.filter(created_at__date__gte=month_start).count()
    all_time_paid = payments_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0")

    total_invoiced_mtd = (
        invoices_qs.filter(issue_date__gte=month_start)
        .aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
    )
    collection_rate = (
        round(float(this_month_revenue / total_invoiced_mtd * 100), 1)
        if total_invoiced_mtd > 0 else None
    )

    # ── Invoice status breakdown ───────────────────────────────────────────────
    invoice_status_counts = {
        "draft": invoices_qs.filter(status="draft").count(),
        "sent": invoices_qs.filter(status="sent").count(),
        "viewed": invoices_qs.filter(status="viewed").count(),
        "paid": invoices_qs.filter(status="paid").count(),
        "overdue": invoices_qs.filter(status="overdue").count(),
        "part_paid": invoices_qs.filter(status="part_paid").count(),
    }
    total_invoice_count = sum(invoice_status_counts.values())

    # ── Recent data ───────────────────────────────────────────────────────────
    recent_invoices = (
        invoices_qs.select_related("client").order_by("-created_at")[:8]
    )
    recent_payments = (
        payments_qs.select_related("invoice", "invoice__client").order_by("-created_at")[:6]
    )
    invoices_due_soon = (
        invoices_qs.filter(
            status__in=["sent", "viewed", "part_paid"],
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
        ).select_related("client").order_by("due_date")[:5]
    )
    recent_expenses = (
        expenses_qs.select_related("client").order_by("-expense_date")[:5]
    )
    top_clients = (
        clients_qs
        .annotate(
            paid_total=Sum(
                "invoices__amount_paid",
                filter=Q(invoices__status__in=["paid", "part_paid"]),
            ),
            invoice_count=Count("invoices"),
        )
        .filter(paid_total__gt=0)
        .order_by("-paid_total")[:5]
    )

    # ── Overdue aging ─────────────────────────────────────────────────────────
    overdue_qs = invoices_qs.filter(status="overdue")
    aging = {
        "0_30": (overdue_qs.filter(due_date__gte=today - timedelta(days=30))
                 .aggregate(t=Sum("amount_due"))["t"] or Decimal("0")),
        "31_60": (overdue_qs.filter(due_date__gte=today - timedelta(days=60),
                                    due_date__lt=today - timedelta(days=30))
                  .aggregate(t=Sum("amount_due"))["t"] or Decimal("0")),
        "61_90": (overdue_qs.filter(due_date__gte=today - timedelta(days=90),
                                    due_date__lt=today - timedelta(days=60))
                  .aggregate(t=Sum("amount_due"))["t"] or Decimal("0")),
        "90_plus": (overdue_qs.filter(due_date__lt=today - timedelta(days=90))
                    .aggregate(t=Sum("amount_due"))["t"] or Decimal("0")),
    }

    # ── Charts ────────────────────────────────────────────────────────────────
    chart_labels, chart_revenue, chart_expenses = _monthly_trend(workspace, months=6)
    sparkline = _daily_sparkline(workspace, days=30)

    import json as _json
    invoice_status_items = [
        ("draft",     "Draft",     "#94a3b8"),
        ("sent",      "Sent",      "#a78bfa"),
        ("viewed",    "Viewed",    "#60a5fa"),
        ("part_paid", "Part Paid", "#2dd4bf"),
        ("paid",      "Paid",      "#4ade80"),
        ("overdue",   "Overdue",   "#f87171"),
    ]
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
            "collection_rate": collection_rate,
            "total_invoice_count": total_invoice_count,
        },
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "invoices_due_soon": invoices_due_soon,
        "recent_expenses": recent_expenses,
        "invoice_status_counts": invoice_status_counts,
        "invoice_status_counts_json": _json.dumps(invoice_status_counts),
        "invoice_status_items": invoice_status_items,
        "top_clients": top_clients,
        "aging": aging,
        "chart_labels": _json.dumps(chart_labels),
        "chart_revenue": _json.dumps(chart_revenue),
        "chart_expenses": _json.dumps(chart_expenses),
        "sparkline": sparkline,
        "quick_actions": [],
    }
    return render(request, "pages/dashboard.html", ctx)
