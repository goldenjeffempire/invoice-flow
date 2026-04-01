"""
Report Views - Production-grade reporting endpoints.

Provides comprehensive reporting functionality with:
- Date range filtering
- Drill-down capabilities
- CSV exports
- Shareable links
- Proper error handling and access control
"""

import csv
import hashlib
from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from invoices.models import (
    Invoice, Payment, Expense, Client, Workspace,
    SharedReportLink, ReportExport
)
from invoices.services.reports_service import ReportsService, DateRange


def get_user_workspace(user):
    """Get the current workspace for a user."""
    if hasattr(user, 'profile') and user.profile.current_workspace:
        return user.profile.current_workspace
    workspace = Workspace.objects.filter(owner=user).first()
    if not workspace:
        workspace = Workspace.objects.filter(members__user=user).first()
    return workspace


def workspace_required(view_func):
    """Decorator to ensure user has access to a workspace."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        workspace = get_user_workspace(request.user)
        if not workspace:
            messages.error(request, "No workspace found. Please complete onboarding.")
            return redirect('invoices:onboarding_router')
        request.workspace = workspace
        return view_func(request, *args, **kwargs)
    return wrapper


def parse_date_range(request) -> DateRange:
    """Parse date range from request parameters (accepts start_date/end_date or date_from/date_to)."""
    preset = request.GET.get('preset', request.GET.get('period', 'this_month'))
    start_str = request.GET.get('start_date') or request.GET.get('date_from')
    end_str = request.GET.get('end_date') or request.GET.get('date_to')

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            return DateRange(start_date=start_date, end_date=end_date, label="Custom Range")
        except ValueError:
            pass

    return DateRange.from_preset(preset)


@login_required
@workspace_required
def reports_home(request):
    """Reports dashboard with KPIs and quick access to all reports."""
    date_range = parse_date_range(request)

    try:
        data = ReportsService.get_reports_home_data(request.workspace, date_range)
    except Exception as e:
        data = {
            "date_range": date_range,
            "kpis": {},
            "revenue_trend": [],
            "quick_reports": [],
            "error": str(e),
        }

    kpis = data.get('kpis', {})
    current_preset = request.GET.get('preset', request.GET.get('period', 'this_month'))

    return render(request, 'pages/reports/home.html', {
        **data,
        "page_title": "Reports & Analytics",
        "presets": get_date_presets(),
        "current_preset": current_preset,
        "period": current_preset,
        "date_from": date_range.start_date,
        "date_to": date_range.end_date,
        "summary": {
            "revenue": kpis.get('total_collected', 0),
            "expenses": kpis.get('total_expenses', 0),
            "net_profit": kpis.get('net_income', 0),
            "paid_count": kpis.get('payment_count', 0),
        },
    })


@login_required
@workspace_required
def revenue_report(request):
    """Detailed revenue analysis report."""
    date_range = parse_date_range(request)
    group_by = request.GET.get('group_by', 'month')

    import json
    from decimal import Decimal

    try:
        data = ReportsService.get_revenue_report(request.workspace, date_range, group_by)
    except Exception as e:
        data = {"error": str(e), "date_range": date_range, "summary": {}, "revenue_trend": [], "by_client": [], "invoices": []}

    summary = data.get('summary', {})

    # Build outstanding amounts for by_client using amount_paid vs total
    raw_by_client = data.get('by_client', [])
    total_rev = sum(r.get('total', 0) for r in raw_by_client) or Decimal('1')
    by_client_transformed = []
    for row in raw_by_client:
        rev = row.get('total', Decimal('0'))
        collected = row.get('collected', Decimal('0'))
        outstanding = max(rev - collected, Decimal('0'))
        pct = (rev / total_rev * 100) if total_rev else Decimal('0')
        by_client_transformed.append({
            'client__id': row.get('client__id'),
            'client__name': row.get('client__name', 'Unknown'),
            'invoice_count': row.get('count', 0),
            'total_revenue': rev,
            'outstanding': outstanding,
            'pct': float(pct),
        })

    # Build chart data from revenue_trend
    revenue_trend = data.get('revenue_trend', [])
    chart_labels = json.dumps([r['label'] for r in revenue_trend])
    chart_data = json.dumps([float(r.get('invoiced', 0)) for r in revenue_trend])

    # Build outstanding total
    from invoices.models import Invoice as _Invoice
    outstanding_total = _Invoice.objects.filter(
        workspace=request.workspace,
        status__in=[_Invoice.Status.SENT, _Invoice.Status.VIEWED, _Invoice.Status.PART_PAID, _Invoice.Status.OVERDUE]
    ).aggregate(
        total=models.Sum('amount_due')
    )['total'] or Decimal('0')

    totals = {
        'revenue': summary.get('total_invoiced', Decimal('0')),
        'paid_count': summary.get('invoice_count', 0),
        'outstanding': outstanding_total,
        'avg_invoice': summary.get('avg_invoice', Decimal('0')),
        'collection_rate': summary.get('collection_rate', Decimal('0')),
    }

    if request.GET.get('export') == 'csv':
        invoices_qs = data.get('invoices', [])
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="revenue_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice #', 'Client', 'Issue Date', 'Amount', 'Paid', 'Status'])
        for inv in invoices_qs:
            writer.writerow([inv.invoice_number, inv.client.name, inv.issue_date, inv.total_amount, inv.amount_paid, inv.get_status_display()])
        return response

    return render(request, 'pages/reports/revenue.html', {
        **data,
        "by_client": by_client_transformed,
        "totals": totals,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "date_from": date_range.start_date,
        "date_to": date_range.end_date,
        "page_title": "Revenue Report",
        "presets": get_date_presets(),
        "current_preset": request.GET.get('preset', 'this_month'),
        "group_by": group_by,
    })


@login_required
@workspace_required
def aging_report(request):
    """Accounts Receivable aging report."""
    from decimal import Decimal

    try:
        data = ReportsService.get_aging_report(request.workspace)
    except Exception as e:
        data = {"error": str(e), "buckets": {}, "total_outstanding": Decimal('0'), "by_client": []}

    raw_buckets = data.get('buckets', {})

    # Flatten bucket data for template (keys starting with digits can't use dot notation)
    flat_buckets = {
        "total": data.get('total_outstanding', Decimal('0')),
        "current": raw_buckets.get('current', {}).get('total', Decimal('0')),
        "current_count": raw_buckets.get('current', {}).get('count', 0),
        "d31_60": raw_buckets.get('31_60', {}).get('total', Decimal('0')),
        "d31_60_count": raw_buckets.get('31_60', {}).get('count', 0),
        "d61_90": raw_buckets.get('61_90', {}).get('total', Decimal('0')),
        "d61_90_count": raw_buckets.get('61_90', {}).get('count', 0),
        "d90_plus": raw_buckets.get('over_90', {}).get('total', Decimal('0')),
        "d90_plus_count": raw_buckets.get('over_90', {}).get('count', 0),
    }

    # Build a flat list of aging rows combining all buckets, sorted by due_date
    aging_rows = []
    for bucket in raw_buckets.values():
        for inv in bucket.get('invoices', []):
            # Wrap client info so template can access row.client.name
            inv_copy = dict(inv)
            inv_copy['client'] = {'name': inv.get('client_name', ''), 'id': inv.get('client_id')}
            aging_rows.append(inv_copy)
    aging_rows.sort(key=lambda x: (-(x.get('days_overdue') or 0)))

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ar_aging.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice #', 'Client', 'Due Date', 'Days Overdue', 'Amount Due', 'Bucket'])
        for row in aging_rows:
            bucket_label = '>90d' if row.get('days_overdue', 0) > 90 else '61-90d' if row.get('days_overdue', 0) > 60 else '31-60d' if row.get('days_overdue', 0) > 30 else 'Current'
            writer.writerow([row.get('invoice_number'), row['client']['name'], row.get('due_date'), row.get('days_overdue', 0), row.get('amount_due'), bucket_label])
        return response

    return render(request, 'pages/reports/aging.html', {
        **data,
        "buckets": flat_buckets,
        "aging_rows": aging_rows,
        "page_title": "A/R Aging Report",
    })


@login_required
@workspace_required
def cashflow_report(request):
    """Cash flow analysis report."""
    import json
    from decimal import Decimal

    date_range = parse_date_range(request)

    try:
        data = ReportsService.get_cashflow_report(request.workspace, date_range)
    except Exception as e:
        data = {"error": str(e), "date_range": date_range, "cashflow_data": [], "summary": {}}

    cf_summary = data.get('summary', {})
    cashflow_data = data.get('cashflow_data', [])

    # Transform for template
    monthly_rows = [
        {
            "month": row.get('period_label', row.get('period', '')),
            "inflows": row.get('inflow', Decimal('0')),
            "outflows": row.get('outflow', Decimal('0')),
            "net": row.get('net', Decimal('0')),
            "running_balance": row.get('running_balance', Decimal('0')),
        }
        for row in cashflow_data
    ]

    totals = {
        "inflows": cf_summary.get('total_inflows', Decimal('0')),
        "outflows": cf_summary.get('total_outflows', Decimal('0')),
        "net": cf_summary.get('net_cashflow', Decimal('0')),
    }

    chart_labels = json.dumps([r['month'] for r in monthly_rows])
    chart_inflows = json.dumps([float(r['inflows']) for r in monthly_rows])
    chart_outflows = json.dumps([float(r['outflows']) for r in monthly_rows])

    return render(request, 'pages/reports/cashflow.html', {
        **data,
        "totals": totals,
        "monthly_rows": monthly_rows,
        "chart_labels": chart_labels,
        "chart_inflows": chart_inflows,
        "chart_outflows": chart_outflows,
        "date_from": date_range.start_date,
        "date_to": date_range.end_date,
        "page_title": "Cash Flow Report",
        "presets": get_date_presets(),
        "current_preset": request.GET.get('preset', 'this_month'),
    })


@login_required
@workspace_required
def profitability_report(request):
    """Client profitability analysis report."""
    date_range = parse_date_range(request)

    try:
        data = ReportsService.get_profitability_report(request.workspace, date_range)
    except Exception as e:
        data = {"error": str(e), "date_range": date_range}

    return render(request, 'pages/reports/profitability.html', {
        **data,
        "page_title": "Client Profitability Report",
        "presets": get_date_presets(),
        "current_preset": request.GET.get('preset', 'this_month'),
    })


@login_required
@workspace_required
def tax_report(request):
    """Tax summary report."""
    from decimal import Decimal

    date_range = parse_date_range(request)

    try:
        data = ReportsService.get_tax_report(request.workspace, date_range)
    except Exception as e:
        data = {"error": str(e), "date_range": date_range, "tax_collected": {}, "tax_paid": {}, "net_tax_liability": Decimal('0'), "by_rate": [], "monthly_data": []}

    tax_collected = data.get('tax_collected', {})
    tax_paid = data.get('tax_paid', {})

    totals = {
        'collected': tax_collected.get('total_tax', Decimal('0')),
        'on_expenses': tax_paid.get('total_tax', Decimal('0')),
        'net': data.get('net_tax_liability', Decimal('0')),
        'invoice_count': tax_collected.get('invoice_count', 0),
    }

    return render(request, 'pages/reports/tax.html', {
        **data,
        "totals": totals,
        "date_from": date_range.start_date,
        "date_to": date_range.end_date,
        "page_title": "Tax Summary Report",
        "presets": get_date_presets(),
        "current_preset": request.GET.get('preset', 'this_month'),
    })


@login_required
@workspace_required
def expense_report(request):
    """Expense analysis report."""
    date_range = parse_date_range(request)

    try:
        data = ReportsService.get_expense_report(request.workspace, date_range)
    except Exception as e:
        data = {"error": str(e), "date_range": date_range}

    return render(request, 'pages/reports/expense.html', {
        **data,
        "page_title": "Expense Report",
        "presets": get_date_presets(),
        "current_preset": request.GET.get('preset', 'this_month'),
    })


@login_required
@workspace_required
def forecast_report(request):
    """Cash flow forecast based on due invoices."""
    days = int(request.GET.get('days', 90))
    days = min(max(days, 30), 365)

    try:
        data = ReportsService.get_forecast(request.workspace, days)
    except Exception as e:
        data = {"error": str(e)}

    return render(request, 'pages/reports/forecast.html', {
        **data,
        "page_title": "Cash Flow Forecast",
        "days_ahead": days,
    })


@login_required
@workspace_required
def exports_hub(request):
    """Export hub for downloading report data."""
    recent_exports = ReportExport.objects.filter(
        workspace=request.workspace
    ).select_related('user')[:20]

    return render(request, 'pages/reports/exports.html', {
        "page_title": "Report Exports",
        "recent_exports": recent_exports,
        "export_options": [
            {"type": "revenue", "name": "Revenue Report", "icon": "chart-bar"},
            {"type": "aging", "name": "A/R Aging Report", "icon": "clock"},
            {"type": "cashflow", "name": "Cash Flow Report", "icon": "currency-dollar"},
            {"type": "profitability", "name": "Client Profitability", "icon": "users"},
            {"type": "tax", "name": "Tax Summary", "icon": "document-text"},
            {"type": "expense", "name": "Expense Report", "icon": "receipt-refund"},
            {"type": "invoices", "name": "All Invoices", "icon": "document"},
            {"type": "payments", "name": "All Payments", "icon": "credit-card"},
            {"type": "clients", "name": "Client List", "icon": "user-group"},
        ],
    })


@login_required
@workspace_required
@require_GET
def export_report_csv(request, report_type: str):
    """Export report data as CSV."""
    date_range = parse_date_range(request)

    export_handlers = {
        'revenue': _export_revenue_csv,
        'aging': _export_aging_csv,
        'cashflow': _export_cashflow_csv,
        'profitability': _export_profitability_csv,
        'tax': _export_tax_csv,
        'expense': _export_expense_csv,
        'invoices': _export_invoices_csv,
        'payments': _export_payments_csv,
        'clients': _export_clients_csv,
    }

    handler = export_handlers.get(report_type)
    if not handler:
        return HttpResponse("Invalid report type", status=400)

    try:
        response = handler(request.workspace, date_range)

        ReportExport.objects.create(
            workspace=request.workspace,
            user=request.user,
            report_type=report_type,
            report_params={
                "start_date": date_range.start_date.isoformat(),
                "end_date": date_range.end_date.isoformat(),
            },
            export_format='csv',
            file_name=f"{report_type}_report.csv",
            file_size=len(response.content),
        )

        return response
    except Exception as e:
        return HttpResponse(f"Export failed: {str(e)}", status=500)


def _export_revenue_csv(workspace, date_range):
    invoices = Invoice.objects.filter(
        workspace=workspace,
        issue_date__gte=date_range.start_date,
        issue_date__lte=date_range.end_date
    ).exclude(status=Invoice.Status.VOID).select_related('client').order_by('-issue_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="revenue_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Invoice #', 'Client', 'Issue Date', 'Due Date', 'Status', 'Subtotal', 'Tax', 'Discount', 'Total', 'Paid', 'Due', 'Currency'])

    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client.name if inv.client else '',
            inv.issue_date,
            inv.due_date,
            inv.get_status_display(),
            inv.subtotal,
            inv.tax_total,
            inv.discount_total,
            inv.total_amount,
            inv.amount_paid,
            inv.amount_due,
            inv.currency,
        ])

    return response


def _export_aging_csv(workspace, date_range):
    today = timezone.now().date()
    invoices = Invoice.objects.filter(
        workspace=workspace,
        status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE],
        amount_due__gt=0
    ).select_related('client').order_by('due_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="aging_report_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Invoice #', 'Client', 'Issue Date', 'Due Date', 'Days Overdue', 'Total Amount', 'Amount Paid', 'Amount Due', 'Aging Bucket', 'Currency'])

    for inv in invoices:
        days_overdue = (today - inv.due_date).days
        if days_overdue <= 0:
            bucket = "Current"
        elif days_overdue <= 30:
            bucket = "1-30 Days"
        elif days_overdue <= 60:
            bucket = "31-60 Days"
        elif days_overdue <= 90:
            bucket = "61-90 Days"
        else:
            bucket = "90+ Days"

        writer.writerow([
            inv.invoice_number,
            inv.client.name if inv.client else '',
            inv.issue_date,
            inv.due_date,
            max(0, days_overdue),
            inv.total_amount,
            inv.amount_paid,
            inv.amount_due,
            bucket,
            inv.currency,
        ])

    return response


def _export_cashflow_csv(workspace, date_range):
    data = ReportsService.get_cashflow_report(workspace, date_range)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cashflow_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Period', 'Inflows', 'Outflows', 'Net Cash Flow', 'Running Balance'])

    for row in data['cashflow_data']:
        writer.writerow([
            row['period_label'],
            row['inflow'],
            row['outflow'],
            row['net'],
            row['running_balance'],
        ])

    return response


def _export_profitability_csv(workspace, date_range):
    data = ReportsService.get_profitability_report(workspace, date_range)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="profitability_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Client', 'Total Invoiced', 'Total Collected', 'Expenses', 'Profit', 'Margin %', 'Invoice Count'])

    for client in data['clients']:
        writer.writerow([
            client['client_name'],
            client['total_invoiced'],
            client['total_collected'],
            client['total_expenses'],
            client['profit'],
            client['margin'],
            client['invoice_count'],
        ])

    return response


def _export_tax_csv(workspace, date_range):
    data = ReportsService.get_tax_report(workspace, date_range)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tax_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Period', 'Tax Collected', 'Tax Paid', 'Net Tax Liability'])

    for row in data['monthly_data']:
        writer.writerow([
            row['period_label'],
            row['tax_collected'],
            row['tax_paid'],
            row['net_tax'],
        ])

    writer.writerow([])
    writer.writerow(['Summary'])
    writer.writerow(['Total Tax Collected', data['tax_collected']['total_tax']])
    writer.writerow(['Total Tax Paid', data['tax_paid']['total_tax']])
    writer.writerow(['Net Tax Liability', data['net_tax_liability']])

    return response


def _export_expense_csv(workspace, date_range):
    expenses = Expense.objects.filter(
        workspace=workspace,
        expense_date__gte=date_range.start_date,
        expense_date__lte=date_range.end_date,
    ).select_related('category', 'vendor', 'client').order_by('-expense_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expense_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Expense #', 'Date', 'Description', 'Category', 'Vendor', 'Amount', 'Tax', 'Total', 'Status', 'Payment Method', 'Billable', 'Client', 'Currency'])

    for exp in expenses:
        writer.writerow([
            exp.expense_number,
            exp.expense_date,
            exp.description,
            exp.category.name if exp.category else '',
            exp.vendor.name if exp.vendor else '',
            exp.amount,
            exp.tax_amount,
            exp.total_amount,
            exp.get_status_display(),
            exp.get_payment_method_display(),
            'Yes' if exp.is_billable else 'No',
            exp.client.name if exp.client else '',
            exp.currency,
        ])

    return response


def _export_invoices_csv(workspace, date_range):
    return _export_revenue_csv(workspace, date_range)


def _export_payments_csv(workspace, date_range):
    payments = Payment.objects.filter(
        workspace=workspace,
        payment_date__date__gte=date_range.start_date,
        payment_date__date__lte=date_range.end_date,
    ).select_related('invoice', 'invoice__client').order_by('-payment_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payments_report_{date_range.start_date}_{date_range.end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Payment ID', 'Invoice #', 'Client', 'Date', 'Amount', 'Fee', 'Net Amount', 'Status', 'Method', 'Transaction ID', 'Currency'])

    for pmt in payments:
        client_name = ''
        if pmt.invoice and pmt.invoice.client:
            client_name = pmt.invoice.client.name
        writer.writerow([
            pmt.id,
            pmt.invoice.invoice_number if pmt.invoice else '',
            client_name,
            pmt.payment_date,
            pmt.amount,
            pmt.fee_amount,
            pmt.net_amount,
            pmt.get_status_display(),
            pmt.get_payment_method_display(),
            pmt.transaction_id,
            pmt.currency,
        ])

    return response


def _export_clients_csv(workspace, date_range):
    clients = Client.objects.filter(workspace=workspace).order_by('name')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clients_list.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone', 'Company', 'Address', 'City', 'Country', 'Created', 'Invoice Count', 'Total Revenue'])

    from django.db import models
    for client in clients:
        invoice_stats = client.invoices.exclude(status=Invoice.Status.VOID).aggregate(
            count=models.Count('id'),
            total=models.Sum('total_amount')
        )
        writer.writerow([
            client.name,
            client.email,
            client.phone,
            '',
            client.billing_address,
            client.billing_city,
            client.billing_country,
            client.created_at,
            invoice_stats['count'] or 0,
            invoice_stats['total'] or 0,
        ])

    return response


@login_required
@workspace_required
@require_POST
def create_shared_link(request):
    """Create a shareable link for a report."""
    report_type = request.POST.get('report_type')
    expires_days = int(request.POST.get('expires_days', 7))
    password = request.POST.get('password', '').strip() or None

    date_range = parse_date_range(request)

    try:
        result = ReportsService.create_shared_link(
            workspace=request.workspace,
            user=request.user,
            report_type=report_type,
            report_params={
                "start_date": date_range.start_date.isoformat(),
                "end_date": date_range.end_date.isoformat(),
                "preset": request.POST.get('preset', 'this_month'),
            },
            expires_in_days=expires_days,
            password=password,
        )
        return JsonResponse({"success": True, **result})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@workspace_required
def shared_links_list(request):
    """List all shared report links for the workspace."""
    links = SharedReportLink.objects.filter(
        workspace=request.workspace
    ).select_related('created_by').order_by('-created_at')

    return render(request, 'pages/reports/shared_links.html', {
        "page_title": "Shared Report Links",
        "links": links,
    })


@login_required
@workspace_required
@require_POST
def revoke_shared_link(request, token: str):
    """Revoke a shared report link."""
    link = get_object_or_404(SharedReportLink, workspace=request.workspace, token=token)
    link.is_active = False
    link.save(update_fields=['is_active'])
    messages.success(request, "Shared link has been revoked.")
    return redirect('invoices:shared_links_list')


def shared_report_view(request, token: str):
    """Public view for shared reports."""
    link = get_object_or_404(SharedReportLink, token=token)

    if not link.is_accessible:
        return render(request, 'pages/reports/shared_expired.html', {
            "page_title": "Report Unavailable",
        })

    if link.password_hash:
        if request.method == 'POST':
            password = request.POST.get('password', '')
            from django.contrib.auth.hashers import check_password as _check_password
            if not _check_password(password, link.password_hash):
                return render(request, 'pages/reports/shared_password.html', {
                    "page_title": "Password Required",
                    "error": "Incorrect password",
                    "token": token,
                })
        else:
            return render(request, 'pages/reports/shared_password.html', {
                "page_title": "Password Required",
                "token": token,
            })

    link.increment_view_count()

    ReportsService.log_report_access(
        shared_link_id=link.id,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        user_id=request.user.id if request.user.is_authenticated else None,
    )

    params = link.report_params
    try:
        start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d').date()
        end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d').date()
        date_range = DateRange(start_date=start_date, end_date=end_date)
    except (ValueError, TypeError):
        date_range = DateRange.from_preset(params.get('preset', 'this_month'))

    report_handlers = {
        'revenue': ReportsService.get_revenue_report,
        'aging': lambda ws, dr: ReportsService.get_aging_report(ws),
        'cashflow': ReportsService.get_cashflow_report,
        'profitability': ReportsService.get_profitability_report,
        'tax': ReportsService.get_tax_report,
        'expense': ReportsService.get_expense_report,
    }

    handler = report_handlers.get(link.report_type)
    if not handler:
        return HttpResponse("Invalid report type", status=400)

    try:
        data = handler(link.workspace, date_range)
    except Exception as e:
        data = {"error": str(e)}

    template = f'pages/reports/shared_{link.report_type}.html'

    return render(request, template, {
        **data,
        "page_title": f"Shared {link.get_report_type_display()}",
        "is_shared_view": True,
        "shared_link": link,
    })


def get_date_presets():
    """Get list of date presets for the UI."""
    return [
        {"value": "today", "label": "Today"},
        {"value": "yesterday", "label": "Yesterday"},
        {"value": "this_week", "label": "This Week"},
        {"value": "last_week", "label": "Last Week"},
        {"value": "this_month", "label": "This Month"},
        {"value": "last_month", "label": "Last Month"},
        {"value": "this_quarter", "label": "This Quarter"},
        {"value": "last_quarter", "label": "Last Quarter"},
        {"value": "this_year", "label": "This Year"},
        {"value": "last_year", "label": "Last Year"},
        {"value": "last_30_days", "label": "Last 30 Days"},
        {"value": "last_90_days", "label": "Last 90 Days"},
        {"value": "all_time", "label": "All Time"},
    ]
