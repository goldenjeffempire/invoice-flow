from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from ..models import Invoice, Client, Payment

@login_required
def dashboard_overview(request):
    workspace = request.user.profile.current_workspace
    if not workspace:
        # If no workspace is selected, try to get the user's default workspace
        workspace = request.user.workspace_memberships.first().workspace if request.user.workspace_memberships.exists() else None
        if workspace:
            request.user.profile.current_workspace = workspace
            request.user.profile.save()
    
    if not workspace:
        return render(request, 'pages/dashboard/overview.html', {'no_workspace': True})

    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Financial Metrics
    total_revenue = Payment.objects.filter(
        workspace=workspace, 
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    monthly_revenue = Payment.objects.filter(
        workspace=workspace,
        status='completed',
        completed_at__gte=start_of_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    overdue_total = Invoice.objects.filter(
        workspace=workspace,
        status='overdue'
    ).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
    
    pending_total = Invoice.objects.filter(
        workspace=workspace,
        status__in=['sent', 'viewed', 'part_paid']
    ).aggregate(Sum('amount_due'))['amount_due__sum'] or 0

    recent_invoices = Invoice.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    recent_payments = Payment.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    
    return render(request, 'pages/dashboard/overview.html', {
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'overdue_total': overdue_total,
        'pending_total': pending_total,
        'recent_invoices': recent_invoices,
        'recent_payments': recent_payments,
        'workspace': workspace
    })
