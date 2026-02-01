from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import Invoice, Payment, WorkspaceMember

@login_required
def dashboard_overview(request):
    workspace = request.workspace
    now = timezone.now()
    
    # Revenue KPIs
    revenue_mtd = Invoice.objects.filter(
        workspace=workspace, status='paid', updated_at__month=now.month, updated_at__year=now.year
    ).aggregate(total=Sum('line_items__quantity' * 'line_items__unit_price'))['total'] or Decimal('0.00')
    
    # Aging Buckets for Outstanding Invoices
    outstanding = Invoice.objects.filter(workspace=workspace, status='unpaid')
    aging = {
        '0-7': outstanding.filter(created_at__gte=now - timedelta(days=7)).count(),
        '8-30': outstanding.filter(created_at__lt=now - timedelta(days=7), created_at__gte=now - timedelta(days=30)).count(),
        '31-60': outstanding.filter(created_at__lt=now - timedelta(days=30), created_at__gte=now - timedelta(days=60)).count(),
        '60+': outstanding.filter(created_at__lt=now - timedelta(days=60)).count(),
    }
    
    # Insights
    insights = []
    overdue_count = outstanding.filter(created_at__lt=now - timedelta(days=30)).count()
    if overdue_count > 0:
        insights.append({
            'type': 'risk',
            'title': f'{overdue_count} Overdue Invoices',
            'message': 'Consider sending reminders to improve cashflow.',
            'action_text': 'View Overdue',
            'action_url': '/list/?status=unpaid'
        })
        
    if not workspace.tax_id_number:
        insights.append({
            'type': 'setup',
            'title': 'Complete Business Profile',
            'message': 'Add your Tax ID to ensure compliance.',
            'action_text': 'Go to Settings',
            'action_url': '/settings/'
        })

    context = {
        'revenue_mtd': revenue_mtd,
        'aging': aging,
        'insights': insights,
        'recent_invoices': Invoice.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    }
    return render(request, 'pages/dashboard.html', context)
