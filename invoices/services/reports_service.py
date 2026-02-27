"""
Reports Service - Production-grade reporting and analytics engine.

Provides comprehensive financial reports including:
- Revenue analytics with trends
- Accounts Receivable aging
- Cash flow analysis
- Client profitability
- Tax summary
- Expense reports
- Forecasting
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import caches
from django.db import models
from django.db.models import (
    Avg, Case, Count, DecimalField, F, Max, Min, Q, Sum, Value, When
)
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import Workspace

logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    start_date: date
    end_date: date
    label: str = ""
    
    @classmethod
    def from_preset(cls, preset: str) -> "DateRange":
        today = timezone.now().date()
        
        presets = {
            "today": (today, today, "Today"),
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1), "Yesterday"),
            "this_week": (today - timedelta(days=today.weekday()), today, "This Week"),
            "last_week": (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1), "Last Week"),
            "this_month": (today.replace(day=1), today, "This Month"),
            "last_month": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1), "Last Month"),
            "this_quarter": (cls._quarter_start(today), today, "This Quarter"),
            "last_quarter": (cls._quarter_start(today) - timedelta(days=90), cls._quarter_start(today) - timedelta(days=1), "Last Quarter"),
            "this_year": (today.replace(month=1, day=1), today, "This Year"),
            "last_year": (today.replace(year=today.year - 1, month=1, day=1), today.replace(year=today.year - 1, month=12, day=31), "Last Year"),
            "last_30_days": (today - timedelta(days=30), today, "Last 30 Days"),
            "last_90_days": (today - timedelta(days=90), today, "Last 90 Days"),
            "last_365_days": (today - timedelta(days=365), today, "Last 365 Days"),
            "all_time": (today - timedelta(days=3650), today, "All Time"),
        }
        
        if preset in presets:
            start, end, label = presets[preset]
            return cls(start_date=start, end_date=end, label=label)
        
        return cls(start_date=today - timedelta(days=30), end_date=today, label="Last 30 Days")
    
    @staticmethod
    def _quarter_start(d: date) -> date:
        quarter = (d.month - 1) // 3
        return date(d.year, quarter * 3 + 1, 1)


class ReportsService:
    """
    Production-grade reporting engine with comprehensive analytics.
    
    Features:
    - Date-range filtering with presets
    - Drill-down capabilities
    - CSV export
    - Shareable report links
    - Caching for performance
    - Forecasting
    """
    
    CACHE_PREFIX = "reports"
    CACHE_TIMEOUT = 300
    
    @classmethod
    def _get_cache(cls):
        try:
            return caches["analytics"]
        except Exception:
            return caches["default"]
    
    @classmethod
    def _cache_key(cls, workspace_id: int, report_type: str, params: Dict) -> str:
        param_str = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{cls.CACHE_PREFIX}:{workspace_id}:{report_type}:{hash_val}"
    
    @classmethod
    def invalidate_workspace_cache(cls, workspace_id: int) -> None:
        pass
    
    @classmethod
    def get_reports_home_data(cls, workspace: "Workspace", date_range: DateRange) -> Dict[str, Any]:
        from invoices.models import Invoice, Payment, Expense
        
        invoices = Invoice.objects.filter(
            workspace=workspace,
            issue_date__gte=date_range.start_date,
            issue_date__lte=date_range.end_date
        ).exclude(status=Invoice.Status.VOID)
        
        payments = Payment.objects.filter(
            workspace=workspace,
            payment_date__date__gte=date_range.start_date,
            payment_date__date__lte=date_range.end_date,
            status=Payment.Status.COMPLETED
        )
        
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_range.start_date,
            expense_date__lte=date_range.end_date,
            status__in=['approved', 'reimbursed', 'billed']
        )
        
        invoice_stats = invoices.aggregate(
            total_invoiced=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            invoice_count=Count('id'),
            avg_invoice=Coalesce(Avg('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        payment_stats = payments.aggregate(
            total_collected=Coalesce(Sum('amount'), Value(Decimal('0')), output_field=DecimalField()),
            payment_count=Count('id'),
        )
        
        expense_stats = expenses.aggregate(
            total_expenses=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            expense_count=Count('id'),
        )
        
        outstanding = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE]
        ).aggregate(
            total_outstanding=Coalesce(Sum('amount_due'), Value(Decimal('0')), output_field=DecimalField()),
            outstanding_count=Count('id'),
        )
        
        overdue = Invoice.objects.filter(
            workspace=workspace,
            due_date__lt=timezone.now().date(),
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID]
        ).aggregate(
            total_overdue=Coalesce(Sum('amount_due'), Value(Decimal('0')), output_field=DecimalField()),
            overdue_count=Count('id'),
        )
        
        net_income = payment_stats['total_collected'] - expense_stats['total_expenses']
        
        revenue_trend = cls._get_revenue_trend(workspace, date_range, 'month')
        
        return {
            "date_range": date_range,
            "kpis": {
                "total_invoiced": invoice_stats['total_invoiced'],
                "total_collected": payment_stats['total_collected'],
                "total_expenses": expense_stats['total_expenses'],
                "net_income": net_income,
                "outstanding": outstanding['total_outstanding'],
                "overdue": overdue['total_overdue'],
                "invoice_count": invoice_stats['invoice_count'],
                "payment_count": payment_stats['payment_count'],
                "expense_count": expense_stats['expense_count'],
                "avg_invoice": invoice_stats['avg_invoice'],
                "outstanding_count": outstanding['outstanding_count'],
                "overdue_count": overdue['overdue_count'],
            },
            "revenue_trend": revenue_trend,
            "quick_reports": [
                {"name": "Revenue Report", "url": "reports:revenue", "icon": "chart-bar", "color": "emerald"},
                {"name": "A/R Aging", "url": "reports:aging", "icon": "clock", "color": "amber"},
                {"name": "Cash Flow", "url": "reports:cashflow", "icon": "currency-dollar", "color": "blue"},
                {"name": "Client Profitability", "url": "reports:profitability", "icon": "users", "color": "purple"},
                {"name": "Tax Summary", "url": "reports:tax", "icon": "document-text", "color": "rose"},
                {"name": "Expense Report", "url": "reports:expense", "icon": "receipt-refund", "color": "orange"},
            ],
        }
    
    @classmethod
    def get_revenue_report(cls, workspace: "Workspace", date_range: DateRange, group_by: str = "month") -> Dict[str, Any]:
        from invoices.models import Invoice, Payment
        
        invoices = Invoice.objects.filter(
            workspace=workspace,
            issue_date__gte=date_range.start_date,
            issue_date__lte=date_range.end_date
        ).exclude(status=Invoice.Status.VOID)
        
        payments = Payment.objects.filter(
            workspace=workspace,
            payment_date__date__gte=date_range.start_date,
            payment_date__date__lte=date_range.end_date,
            status=Payment.Status.COMPLETED
        )
        
        invoice_summary = invoices.aggregate(
            total_invoiced=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            subtotal=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()),
            tax_total=Coalesce(Sum('tax_total'), Value(Decimal('0')), output_field=DecimalField()),
            discount_total=Coalesce(Sum('discount_total'), Value(Decimal('0')), output_field=DecimalField()),
            invoice_count=Count('id'),
            avg_invoice=Coalesce(Avg('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            max_invoice=Coalesce(Max('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            min_invoice=Coalesce(Min('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        payment_summary = payments.aggregate(
            total_collected=Coalesce(Sum('amount'), Value(Decimal('0')), output_field=DecimalField()),
            payment_count=Count('id'),
            avg_payment=Coalesce(Avg('amount'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        status_breakdown = invoices.values('status').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')
        
        revenue_trend = cls._get_revenue_trend(workspace, date_range, group_by)
        
        by_client = invoices.values('client__name').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            collected=Coalesce(Sum('amount_paid'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')[:10]
        
        by_currency = invoices.values('currency').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')
        
        collection_rate = Decimal('0')
        if invoice_summary['total_invoiced'] > 0:
            collection_rate = (payment_summary['total_collected'] / invoice_summary['total_invoiced'] * 100).quantize(Decimal('0.1'))
        
        invoices_list = invoices.select_related('client').order_by('-issue_date')[:100]
        
        return {
            "date_range": date_range,
            "summary": {
                **invoice_summary,
                **payment_summary,
                "collection_rate": collection_rate,
            },
            "status_breakdown": list(status_breakdown),
            "revenue_trend": revenue_trend,
            "by_client": list(by_client),
            "by_currency": list(by_currency),
            "invoices": invoices_list,
            "group_by": group_by,
        }
    
    @classmethod
    def get_aging_report(cls, workspace: "Workspace") -> Dict[str, Any]:
        from invoices.models import Invoice
        
        today = timezone.now().date()
        
        outstanding_invoices = Invoice.objects.filter(
            workspace=workspace,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE],
            amount_due__gt=0
        ).select_related('client').order_by('due_date')
        
        buckets = {
            "current": {"label": "Current (Not Yet Due)", "days": "0", "invoices": [], "total": Decimal('0'), "count": 0},
            "1_30": {"label": "1-30 Days", "days": "1-30", "invoices": [], "total": Decimal('0'), "count": 0},
            "31_60": {"label": "31-60 Days", "days": "31-60", "invoices": [], "total": Decimal('0'), "count": 0},
            "61_90": {"label": "61-90 Days", "days": "61-90", "invoices": [], "total": Decimal('0'), "count": 0},
            "over_90": {"label": "Over 90 Days", "days": "90+", "invoices": [], "total": Decimal('0'), "count": 0},
        }
        
        total_outstanding = Decimal('0')
        
        for invoice in outstanding_invoices:
            days_overdue = (today - invoice.due_date).days
            
            if days_overdue <= 0:
                bucket_key = "current"
            elif days_overdue <= 30:
                bucket_key = "1_30"
            elif days_overdue <= 60:
                bucket_key = "31_60"
            elif days_overdue <= 90:
                bucket_key = "61_90"
            else:
                bucket_key = "over_90"
            
            buckets[bucket_key]["invoices"].append({
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client.name,
                "client_id": invoice.client_id,
                "issue_date": invoice.issue_date,
                "due_date": invoice.due_date,
                "days_overdue": max(0, days_overdue),
                "total_amount": invoice.total_amount,
                "amount_paid": invoice.amount_paid,
                "amount_due": invoice.amount_due,
                "currency": invoice.currency,
                "currency_symbol": invoice.currency_symbol,
            })
            buckets[bucket_key]["total"] += invoice.amount_due
            buckets[bucket_key]["count"] += 1
            total_outstanding += invoice.amount_due
        
        by_client = {}
        for invoice in outstanding_invoices:
            client_name = invoice.client.name
            if client_name not in by_client:
                by_client[client_name] = {
                    "client_name": client_name,
                    "client_id": invoice.client_id,
                    "total_due": Decimal('0'),
                    "invoice_count": 0,
                    "oldest_invoice_date": None,
                    "oldest_due_date": None,
                }
            by_client[client_name]["total_due"] += invoice.amount_due
            by_client[client_name]["invoice_count"] += 1
            if by_client[client_name]["oldest_invoice_date"] is None or invoice.issue_date < by_client[client_name]["oldest_invoice_date"]:
                by_client[client_name]["oldest_invoice_date"] = invoice.issue_date
                by_client[client_name]["oldest_due_date"] = invoice.due_date
        
        client_aging = sorted(by_client.values(), key=lambda x: x['total_due'], reverse=True)
        
        avg_days = Decimal('0')
        if outstanding_invoices.exists():
            total_days = sum((today - inv.due_date).days for inv in outstanding_invoices if inv.due_date < today)
            overdue_count = sum(1 for inv in outstanding_invoices if inv.due_date < today)
            if overdue_count > 0:
                avg_days = Decimal(total_days) / Decimal(overdue_count)
        
        return {
            "buckets": buckets,
            "total_outstanding": total_outstanding,
            "invoice_count": outstanding_invoices.count(),
            "by_client": client_aging[:20],
            "avg_days_overdue": avg_days.quantize(Decimal('0.1')),
            "as_of_date": today,
        }
    
    @classmethod
    def get_cashflow_report(cls, workspace: "Workspace", date_range: DateRange) -> Dict[str, Any]:
        from invoices.models import Invoice, Payment, Expense
        
        payments = Payment.objects.filter(
            workspace=workspace,
            payment_date__date__gte=date_range.start_date,
            payment_date__date__lte=date_range.end_date,
            status=Payment.Status.COMPLETED
        ).annotate(
            period=TruncMonth('payment_date')
        ).values('period').annotate(
            total=Coalesce(Sum('amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('period')
        
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_range.start_date,
            expense_date__lte=date_range.end_date,
            status__in=['approved', 'reimbursed', 'billed']
        ).annotate(
            period=TruncMonth('expense_date')
        ).values('period').annotate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('period')
        
        payment_dict = {p['period'].strftime('%Y-%m'): p for p in payments}
        expense_dict = {e['period'].strftime('%Y-%m'): e for e in expenses}
        
        all_periods = set(payment_dict.keys()) | set(expense_dict.keys())
        
        cashflow_data = []
        running_balance = Decimal('0')
        total_inflows = Decimal('0')
        total_outflows = Decimal('0')
        
        for period in sorted(all_periods):
            inflow = payment_dict.get(period, {}).get('total', Decimal('0'))
            outflow = expense_dict.get(period, {}).get('total', Decimal('0'))
            net = inflow - outflow
            running_balance += net
            total_inflows += inflow
            total_outflows += outflow
            
            cashflow_data.append({
                "period": period,
                "period_label": datetime.strptime(period, '%Y-%m').strftime('%b %Y'),
                "inflow": inflow,
                "outflow": outflow,
                "net": net,
                "running_balance": running_balance,
            })
        
        payment_summary = Payment.objects.filter(
            workspace=workspace,
            payment_date__date__gte=date_range.start_date,
            payment_date__date__lte=date_range.end_date,
            status=Payment.Status.COMPLETED
        ).values('payment_method').annotate(
            total=Coalesce(Sum('amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('-total')
        
        expense_by_category = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_range.start_date,
            expense_date__lte=date_range.end_date,
            status__in=['approved', 'reimbursed', 'billed']
        ).values('category__name').annotate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('-total')
        
        return {
            "date_range": date_range,
            "cashflow_data": cashflow_data,
            "summary": {
                "total_inflows": total_inflows,
                "total_outflows": total_outflows,
                "net_cashflow": total_inflows - total_outflows,
                "ending_balance": running_balance,
            },
            "by_payment_method": list(payment_summary),
            "expenses_by_category": list(expense_by_category),
        }
    
    @classmethod
    def get_profitability_report(cls, workspace: "Workspace", date_range: DateRange) -> Dict[str, Any]:
        from invoices.models import Invoice, Payment, Expense, Client
        
        clients = Client.objects.filter(workspace=workspace).prefetch_related('invoices', 'expenses')
        
        client_data = []
        
        for client in clients:
            invoices = client.invoices.filter(
                issue_date__gte=date_range.start_date,
                issue_date__lte=date_range.end_date
            ).exclude(status=Invoice.Status.VOID)
            
            invoice_agg = invoices.aggregate(
                total_invoiced=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
                total_collected=Coalesce(Sum('amount_paid'), Value(Decimal('0')), output_field=DecimalField()),
                invoice_count=Count('id'),
            )
            
            expenses = client.expenses.filter(
                expense_date__gte=date_range.start_date,
                expense_date__lte=date_range.end_date,
                status__in=['approved', 'reimbursed', 'billed']
            )
            
            expense_agg = expenses.aggregate(
                total_expenses=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
                expense_count=Count('id'),
            )
            
            revenue = invoice_agg['total_collected']
            costs = expense_agg['total_expenses']
            profit = revenue - costs
            margin = Decimal('0')
            if revenue > 0:
                margin = (profit / revenue * 100).quantize(Decimal('0.1'))
            
            if invoice_agg['invoice_count'] > 0 or expense_agg['expense_count'] > 0:
                client_data.append({
                    "client_id": client.id,
                    "client_name": client.name,
                    "total_invoiced": invoice_agg['total_invoiced'],
                    "total_collected": revenue,
                    "total_expenses": costs,
                    "profit": profit,
                    "margin": margin,
                    "invoice_count": invoice_agg['invoice_count'],
                    "expense_count": expense_agg['expense_count'],
                })
        
        client_data.sort(key=lambda x: x['profit'], reverse=True)
        
        totals = {
            "total_revenue": sum(c['total_collected'] for c in client_data),
            "total_expenses": sum(c['total_expenses'] for c in client_data),
            "total_profit": sum(c['profit'] for c in client_data),
            "client_count": len([c for c in client_data if c['invoice_count'] > 0]),
        }
        
        totals['overall_margin'] = Decimal('0')
        if totals['total_revenue'] > 0:
            totals['overall_margin'] = (totals['total_profit'] / totals['total_revenue'] * 100).quantize(Decimal('0.1'))
        
        return {
            "date_range": date_range,
            "clients": client_data,
            "totals": totals,
            "top_profitable": client_data[:10],
            "least_profitable": list(reversed(client_data[-10:])) if len(client_data) >= 10 else list(reversed(client_data)),
        }
    
    @classmethod
    def get_tax_report(cls, workspace: "Workspace", date_range: DateRange) -> Dict[str, Any]:
        from invoices.models import Invoice, LineItem, Expense
        
        invoices = Invoice.objects.filter(
            workspace=workspace,
            issue_date__gte=date_range.start_date,
            issue_date__lte=date_range.end_date,
            status=Invoice.Status.PAID
        )
        
        tax_collected = invoices.aggregate(
            total_tax=Coalesce(Sum('tax_total'), Value(Decimal('0')), output_field=DecimalField()),
            invoice_count=Count('id'),
            total_invoiced=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            subtotal=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        tax_by_rate = LineItem.objects.filter(
            invoice__workspace=workspace,
            invoice__issue_date__gte=date_range.start_date,
            invoice__issue_date__lte=date_range.end_date,
            invoice__status=Invoice.Status.PAID,
        ).values('tax_rate').annotate(
            total_tax=Coalesce(Sum('tax_amount'), Value(Decimal('0')), output_field=DecimalField()),
            taxable_amount=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()),
            item_count=Count('id'),
        ).order_by('-tax_rate')
        
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_range.start_date,
            expense_date__lte=date_range.end_date,
            status__in=['approved', 'reimbursed', 'billed']
        )
        
        tax_paid = expenses.aggregate(
            total_tax=Coalesce(Sum('tax_amount'), Value(Decimal('0')), output_field=DecimalField()),
            expense_count=Count('id'),
            total_expenses=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        tax_by_month = invoices.annotate(
            period=TruncMonth('issue_date')
        ).values('period').annotate(
            tax_collected=Coalesce(Sum('tax_total'), Value(Decimal('0')), output_field=DecimalField()),
            invoice_count=Count('id'),
        ).order_by('period')
        
        expense_tax_by_month = expenses.annotate(
            period=TruncMonth('expense_date')
        ).values('period').annotate(
            tax_paid=Coalesce(Sum('tax_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('period')
        
        expense_tax_dict = {e['period'].strftime('%Y-%m'): e['tax_paid'] for e in expense_tax_by_month}
        
        monthly_data = []
        for row in tax_by_month:
            period_key = row['period'].strftime('%Y-%m')
            monthly_data.append({
                "period": period_key,
                "period_label": row['period'].strftime('%b %Y'),
                "tax_collected": row['tax_collected'],
                "tax_paid": expense_tax_dict.get(period_key, Decimal('0')),
                "net_tax": row['tax_collected'] - expense_tax_dict.get(period_key, Decimal('0')),
            })
        
        net_tax_liability = tax_collected['total_tax'] - tax_paid['total_tax']
        
        return {
            "date_range": date_range,
            "tax_collected": tax_collected,
            "tax_paid": tax_paid,
            "net_tax_liability": net_tax_liability,
            "by_rate": list(tax_by_rate),
            "monthly_data": monthly_data,
        }
    
    @classmethod
    def get_expense_report(cls, workspace: "Workspace", date_range: DateRange) -> Dict[str, Any]:
        from invoices.models import Expense, ExpenseCategory, Vendor
        
        expenses = Expense.objects.filter(
            workspace=workspace,
            expense_date__gte=date_range.start_date,
            expense_date__lte=date_range.end_date,
        ).select_related('category', 'vendor', 'client')
        
        summary = expenses.filter(status__in=['approved', 'reimbursed', 'billed']).aggregate(
            total_amount=Coalesce(Sum('amount'), Value(Decimal('0')), output_field=DecimalField()),
            total_tax=Coalesce(Sum('tax_amount'), Value(Decimal('0')), output_field=DecimalField()),
            total_with_tax=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            expense_count=Count('id'),
            avg_expense=Coalesce(Avg('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        )
        
        by_status = expenses.values('status').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('status')
        
        by_category = expenses.filter(
            status__in=['approved', 'reimbursed', 'billed']
        ).values('category__name', 'category__color').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')
        
        by_vendor = expenses.filter(
            status__in=['approved', 'reimbursed', 'billed'],
            vendor__isnull=False
        ).values('vendor__name').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')[:10]
        
        by_payment_method = expenses.filter(
            status__in=['approved', 'reimbursed', 'billed']
        ).values('payment_method').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
        ).order_by('-total')
        
        monthly_trend = expenses.filter(
            status__in=['approved', 'reimbursed', 'billed']
        ).annotate(
            period=TruncMonth('expense_date')
        ).values('period').annotate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('period')
        
        billable = expenses.filter(is_billable=True).aggregate(
            total_billable=Coalesce(Sum('billable_amount'), Value(Decimal('0')), output_field=DecimalField()),
            billed=Coalesce(Sum('billable_amount', filter=Q(is_billed=True)), Value(Decimal('0')), output_field=DecimalField()),
            unbilled=Coalesce(Sum('billable_amount', filter=Q(is_billed=False)), Value(Decimal('0')), output_field=DecimalField()),
            billable_count=Count('id'),
        )
        
        tax_deductible = expenses.filter(
            status__in=['approved', 'reimbursed', 'billed'],
            category__is_tax_deductible=True
        ).aggregate(
            total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        )
        
        expense_list = expenses.order_by('-expense_date')[:100]
        
        return {
            "date_range": date_range,
            "summary": summary,
            "by_status": list(by_status),
            "by_category": list(by_category),
            "by_vendor": list(by_vendor),
            "by_payment_method": list(by_payment_method),
            "monthly_trend": [
                {"period": m['period'].strftime('%b %Y'), "total": m['total'], "count": m['count']}
                for m in monthly_trend
            ],
            "billable": billable,
            "tax_deductible": tax_deductible,
            "expenses": expense_list,
        }
    
    @classmethod
    def get_forecast(cls, workspace: "Workspace", days_ahead: int = 90) -> Dict[str, Any]:
        from invoices.models import Invoice
        
        today = timezone.now().date()
        forecast_end = today + timedelta(days=days_ahead)
        
        upcoming_invoices = Invoice.objects.filter(
            workspace=workspace,
            due_date__gte=today,
            due_date__lte=forecast_end,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID],
            amount_due__gt=0
        ).select_related('client').order_by('due_date')
        
        weekly_forecast = []
        current_date = today
        while current_date <= forecast_end:
            week_end = current_date + timedelta(days=6)
            week_invoices = [inv for inv in upcoming_invoices if current_date <= inv.due_date <= week_end]
            week_total = sum(inv.amount_due for inv in week_invoices)
            weekly_forecast.append({
                "week_start": current_date,
                "week_end": week_end,
                "expected_amount": week_total,
                "invoice_count": len(week_invoices),
            })
            current_date = week_end + timedelta(days=1)
        
        total_expected = upcoming_invoices.aggregate(
            total=Coalesce(Sum('amount_due'), Value(Decimal('0')), output_field=DecimalField()),
        )['total']
        
        return {
            "today": today,
            "forecast_end": forecast_end,
            "days_ahead": days_ahead,
            "total_expected": total_expected,
            "invoice_count": upcoming_invoices.count(),
            "weekly_forecast": weekly_forecast,
            "upcoming_invoices": list(upcoming_invoices[:50]),
        }
    
    @classmethod
    def _get_revenue_trend(cls, workspace: "Workspace", date_range: DateRange, group_by: str) -> List[Dict]:
        from invoices.models import Invoice
        
        invoices = Invoice.objects.filter(
            workspace=workspace,
            issue_date__gte=date_range.start_date,
            issue_date__lte=date_range.end_date
        ).exclude(status=Invoice.Status.VOID)
        
        if group_by == "day":
            trunc_fn = TruncDate
        elif group_by == "week":
            trunc_fn = TruncWeek
        else:
            trunc_fn = TruncMonth
        
        trend_data = invoices.annotate(
            period=trunc_fn('issue_date')
        ).values('period').annotate(
            invoiced=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()),
            collected=Coalesce(Sum('amount_paid'), Value(Decimal('0')), output_field=DecimalField()),
            count=Count('id'),
        ).order_by('period')
        
        result = []
        for row in trend_data:
            period = row['period']
            if group_by == "day":
                label = period.strftime('%b %d')
            elif group_by == "week":
                label = f"Week of {period.strftime('%b %d')}"
            else:
                label = period.strftime('%b %Y')
            
            result.append({
                "period": period.isoformat() if hasattr(period, 'isoformat') else str(period),
                "label": label,
                "invoiced": row['invoiced'],
                "collected": row['collected'],
                "count": row['count'],
            })
        
        return result
    
    @classmethod
    def export_to_csv(cls, data: List[Dict], columns: List[Tuple[str, str]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([col[1] for col in columns])
        
        for row in data:
            writer.writerow([row.get(col[0], '') for col in columns])
        
        return output.getvalue()
    
    @classmethod
    def create_shared_link(
        cls,
        workspace: "Workspace",
        user: "User",
        report_type: str,
        report_params: Dict,
        expires_in_days: int = 7,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        from invoices.models import SharedReportLink
        
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        shared_link = SharedReportLink.objects.create(
            workspace=workspace,
            created_by=user,
            token=token,
            report_type=report_type,
            report_params=report_params,
            expires_at=expires_at,
            password_hash=password_hash,
        )
        
        return {
            "token": token,
            "url": f"/reports/shared/{token}/",
            "expires_at": expires_at,
            "has_password": bool(password),
        }
    
    @classmethod
    def log_report_access(
        cls,
        shared_link_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> None:
        from invoices.models import ReportAccessLog
        
        ReportAccessLog.objects.create(
            shared_link_id=shared_link_id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else "",
            user_id=user_id,
        )
