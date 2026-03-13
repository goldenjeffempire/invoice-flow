"""
InvoiceFlow Dashboard View
Provides the main dashboard with KPIs, charts, recent activity, and quick actions.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import Client, Expense, Invoice, Payment

logger = logging.getLogger(__name__)


def _get_sparkline(workspace, days=30):
    """Return last N days of daily revenue as a list for sparkline chart."""
    today = timezone.now().date()
    data = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        total = (
            Payment.objects.filter(
                invoice__workspace=workspace,
                payment_date=d,
            ).aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )
        data.append(float(total))
    return data


def _get_monthly_revenue(workspace, months=6):
    """Return last N months of revenue for bar/line chart."""
    today = timezone.now().date()
    labels = []
    revenue = []
    expenses = []

    for i in range(months - 1, -1, -1):
        month_offset = (today.month - 1 - i) % 12 + 1
        year_offset = today.year - ((i - today.month + 1) // 12 if (today.month - 1 - i) < 0 else 0)
        import calendar
        last_day = calendar.monthrange(year_offset, month_offset)[1]
        month_start = today.replace(year=year_offset, month=month_offset, day=1)
        month_end = today.replace(year=year_offset, month=month_offset, day=last_day)

        rev = (
            Payment.objects.filter(
                invoice__workspace=workspace,
                payment_date__gte=month_start,
                payment_date__lte=month_end,
            ).aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )
        exp = (
            Expense.objects.filter(
                workspace=workspace,
                date__gte=month_start,
                date__lte=month_end,
            ).aggregate(t=Sum("amount"))["t"]
            or Decimal("0")
        )
        labels.append(month_start.strftime("%b"))
        revenue.append(float(rev))
        expenses.append(float(exp))

    return labels, revenue, expenses


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    workspace = getattr(profile, "current_workspace", None) if profile else None

    if not workspace:
        return redirect("invoices:onboarding_router")

    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(days=1)

    invoices_qs = Invoice.objects.filter(workspace=workspace)

    total_outstanding = (
        invoices_qs.filter(
            status__in=["sent", "viewed", "part_paid", "overdue"]
        ).aggregate(t=Sum("amount_due"))["t"]
        or Decimal("0")
    )
    total_overdue = (
        invoices_qs.filter(status="overdue").aggregate(t=Sum("amount_due"))["t"]
        or Decimal("0")
    )
    overdue_count = invoices_qs.filter(status="overdue").count()
    draft_count = invoices_qs.filter(status="draft").count()

    this_month_revenue = (
        Payment.objects.filter(
            invoice__workspace=workspace,
            payment_date__gte=month_start,
            payment_date__lte=today,
        ).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )
    last_month_revenue = (
        Payment.objects.filter(
            invoice__workspace=workspace,
            payment_date__gte=last_month_start,
            payment_date__lte=last_month_end,
        ).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )

    revenue_change_pct = None
    if last_month_revenue and last_month_revenue > 0:
        revenue_change_pct = round(
            float((this_month_revenue - last_month_revenue) / last_month_revenue * 100), 1
        )

    total_clients = Client.objects.filter(workspace=workspace, is_active=True).count()
    new_clients_this_month = Client.objects.filter(
        workspace=workspace, created_at__date__gte=month_start
    ).count()

    this_month_expenses = (
        Expense.objects.filter(
            workspace=workspace,
            date__gte=month_start,
            date__lte=today,
        ).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )

    all_time_paid = (
        Payment.objects.filter(invoice__workspace=workspace).aggregate(t=Sum("amount"))["t"]
        or Decimal("0")
    )

    recent_invoices = (
        invoices_qs.select_related("client")
        .exclude(status="void")
        .order_by("-created_at")[:8]
    )

    recent_payments = (
        Payment.objects.filter(invoice__workspace=workspace)
        .select_related("invoice", "invoice__client")
        .order_by("-payment_date", "-created_at")[:5]
    )

    invoices_due_soon = (
        invoices_qs.filter(
            status__in=["sent", "viewed", "part_paid"],
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
        )
        .select_related("client")
        .order_by("due_date")[:5]
    )

    labels, revenue, expense_data = _get_monthly_revenue(workspace, months=6)
    sparkline = _get_sparkline(workspace, days=30)

    invoice_status_counts = {
        "draft": invoices_qs.filter(status="draft").count(),
        "sent": invoices_qs.filter(status="sent").count(),
        "viewed": invoices_qs.filter(status="viewed").count(),
        "paid": invoices_qs.filter(status="paid").count(),
        "overdue": invoices_qs.filter(status="overdue").count(),
        "part_paid": invoices_qs.filter(status="part_paid").count(),
    }

    top_clients = (
        Client.objects.filter(workspace=workspace)
        .annotate(
            paid_total=Sum(
                "invoices__total_amount",
                filter=Q(invoices__status="paid"),
            )
        )
        .filter(paid_total__gt=0)
        .order_by("-paid_total")[:5]
    )

    ctx = {
        "workspace": workspace,
        "today": today,
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
            "all_time_paid": all_time_paid,
        },
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
        "invoices_due_soon": invoices_due_soon,
        "invoice_status_counts": invoice_status_counts,
        "top_clients": top_clients,
        "chart_labels": labels,
        "chart_revenue": revenue,
        "chart_expenses": expense_data,
        "sparkline": sparkline,
        "page_title": "Dashboard",
    }
    return render(request, "pages/dashboard.html", ctx)
