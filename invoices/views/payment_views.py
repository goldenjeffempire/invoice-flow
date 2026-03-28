from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone
import json
import logging
from datetime import datetime, timedelta

from ..models import Payment, Transaction, Payout, Dispute, Invoice
from ..services.payment_service import PaymentService

logger = logging.getLogger(__name__)


def _get_workspace(request):
    profile = getattr(request.user, 'profile', None)
    return getattr(profile, 'current_workspace', None) if profile else None


@csrf_exempt
@require_POST
def paystack_webhook(request):
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    payload = request.body

    if not PaymentService.verify_paystack_signature(payload, signature):
        return HttpResponse(status=401)

    try:
        data = json.loads(payload)
        PaymentService.handle_paystack_webhook(data)
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Paystack Webhook Processing Error: {str(e)}")
        return HttpResponse(status=500)


@login_required
def payment_overview(request):
    workspace = _get_workspace(request)
    if not workspace:
        messages.warning(request, "Please set up your workspace first.")
        return redirect('invoices:onboarding_router')

    today = timezone.now().date()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    payments_qs = Payment.objects.filter(workspace=workspace).select_related('invoice', 'invoice__client')

    # KPI stats
    total_collected = payments_qs.filter(
        status=Payment.Status.COMPLETED
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    this_month_collected = payments_qs.filter(
        status=Payment.Status.COMPLETED,
        payment_date__date__gte=month_start,
        payment_date__date__lte=today,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    last_month_collected = payments_qs.filter(
        status=Payment.Status.COMPLETED,
        payment_date__date__gte=last_month_start,
        payment_date__date__lte=last_month_end,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    pending_count = payments_qs.filter(status=Payment.Status.PENDING).count()
    pending_amount = payments_qs.filter(
        status=Payment.Status.PENDING
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    failed_count = payments_qs.filter(status=Payment.Status.FAILED).count()

    # Recent payments (last 10)
    recent_payments = payments_qs.order_by('-payment_date')[:10]

    # Payouts and disputes
    try:
        payouts = Payout.objects.filter(workspace=workspace).order_by('-created_at')[:5]
        pending_payouts_amount = Payout.objects.filter(
            workspace=workspace, status='pending'
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    except Exception:
        payouts = []
        pending_payouts_amount = Decimal('0')

    try:
        disputes = Dispute.objects.filter(workspace=workspace).order_by('-created_at')[:5]
        active_disputes = Dispute.objects.filter(workspace=workspace, status='open').count()
    except Exception:
        disputes = []
        active_disputes = 0

    # Payment method breakdown
    method_breakdown = list(
        payments_qs.filter(status=Payment.Status.COMPLETED)
        .values('payment_method')
        .annotate(count=Count('id'), total=Sum('amount'))
        .order_by('-total')
    )

    # Month-over-month change
    mom_change = None
    if last_month_collected and last_month_collected > 0:
        mom_change = round(float((this_month_collected - last_month_collected) / last_month_collected * 100), 1)
    elif this_month_collected > 0:
        mom_change = 100.0

    stats = {
        'total_collected': total_collected,
        'this_month': this_month_collected,
        'last_month': last_month_collected,
        'mom_change': mom_change,
        'pending_count': pending_count,
        'pending_amount': pending_amount,
        'failed_count': failed_count,
        'active_disputes': active_disputes,
        'pending_payouts_amount': pending_payouts_amount,
    }

    return render(request, 'pages/payments/overview.html', {
        'payments': recent_payments,
        'stats': stats,
        'total_collected': total_collected,
        'payouts': payouts,
        'disputes': disputes,
        'workspace': workspace,
        'method_breakdown': method_breakdown,
        'page_title': 'Payments',
    })


@login_required
def transaction_list(request):
    workspace = _get_workspace(request)
    if not workspace:
        messages.warning(request, "Please set up your workspace first.")
        return redirect('invoices:onboarding_router')

    # Filters
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    ordering = request.GET.get('ordering', '-payment_date')

    payments_qs = Payment.objects.filter(workspace=workspace).select_related(
        'invoice', 'invoice__client'
    )

    if search:
        payments_qs = payments_qs.filter(
            Q(invoice__invoice_number__icontains=search) |
            Q(invoice__client__name__icontains=search) |
            Q(transaction_id__icontains=search) |
            Q(provider_reference__icontains=search)
        )

    if status_filter:
        payments_qs = payments_qs.filter(status=status_filter)

    if method_filter:
        payments_qs = payments_qs.filter(payment_method=method_filter)

    if date_from:
        try:
            payments_qs = payments_qs.filter(
                payment_date__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
            )
        except ValueError:
            pass

    if date_to:
        try:
            payments_qs = payments_qs.filter(
                payment_date__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
            )
        except ValueError:
            pass

    valid_orderings = ['-payment_date', 'payment_date', '-amount', 'amount', '-created_at']
    if ordering in valid_orderings:
        payments_qs = payments_qs.order_by(ordering)
    else:
        payments_qs = payments_qs.order_by('-payment_date')

    # Also get transactions
    transactions_qs = Transaction.objects.filter(workspace=workspace).order_by('-created_at')

    paginator = Paginator(payments_qs, 25)
    page_num = request.GET.get('page', 1)
    payments_page = paginator.get_page(page_num)

    # Summary stats
    total_shown = payments_qs.filter(status=Payment.Status.COMPLETED).aggregate(
        t=Sum('amount')
    )['t'] or Decimal('0')

    status_tabs = [
        {'key': '', 'label': 'All', 'count': Payment.objects.filter(workspace=workspace).count()},
        {'key': 'completed', 'label': 'Completed', 'count': Payment.objects.filter(workspace=workspace, status='completed').count()},
        {'key': 'pending', 'label': 'Pending', 'count': Payment.objects.filter(workspace=workspace, status='pending').count()},
        {'key': 'failed', 'label': 'Failed', 'count': Payment.objects.filter(workspace=workspace, status='failed').count()},
    ]

    return render(request, 'pages/payments/list.html', {
        'payments': payments_page,
        'transactions': transactions_qs[:50],
        'current_status': status_filter,
        'status_tabs': status_tabs,
        'search_query': search,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'ordering': ordering,
        'total_shown': total_shown,
        'workspace': workspace,
        'page_title': 'Transactions',
    })


@login_required
def payment_detail(request, payment_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect('invoices:onboarding_router')

    payment = get_object_or_404(Payment, id=payment_id, workspace=workspace)
    try:
        audit_logs = payment.audit_logs.all().order_by('-created_at')
    except Exception:
        audit_logs = []

    return render(request, 'pages/payments/detail.html', {
        'payment': payment,
        'audit_logs': audit_logs,
        'workspace': workspace,
        'page_title': f'Payment — {payment.transaction_id or payment.id}',
    })


@login_required
def record_offline_payment(request, invoice_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect('invoices:onboarding_router')

    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        method = request.POST.get('method', request.POST.get('payment_method', 'bank_transfer'))
        notes = request.POST.get('notes', '')
        tip = request.POST.get('tip_amount', '0') or '0'
        try:
            PaymentService.record_offline_payment(
                invoice=invoice,
                amount=amount,
                method=method,
                user=request.user,
                notes=notes,
                tip_amount=tip,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, "Payment recorded successfully.")
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
        except Exception as e:
            logger.exception(f"Error recording offline payment: {e}")
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'pages/payments/record_offline.html', {
        'invoice': invoice,
        'workspace': workspace,
        'page_title': f'Record Payment — {invoice.invoice_number}',
    })
