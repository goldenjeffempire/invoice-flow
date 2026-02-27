from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
import json
import logging
from ..models import Payment, Transaction, Workspace, Payout, Dispute, Invoice
from ..services.payment_service import PaymentService

logger = logging.getLogger(__name__)

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
    workspace = request.user.profile.current_workspace
    payments = Payment.objects.filter(workspace=workspace).select_related('invoice')
    total_collected = payments.filter(status=Payment.Status.COMPLETED).aggregate(Sum('amount'))['amount__sum'] or 0
    payouts = Payout.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    disputes = Dispute.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    
    return render(request, 'pages/payments/overview.html', {
        'payments': payments[:10],
        'total_collected': total_collected,
        'payouts': payouts,
        'disputes': disputes,
        'workspace': workspace
    })

@login_required
def transaction_list(request):
    workspace = request.user.profile.current_workspace
    transactions = Transaction.objects.filter(workspace=workspace).order_by('-created_at')
    return render(request, 'pages/payments/list.html', {'transactions': transactions})

@login_required
def payment_detail(request, payment_id):
    workspace = request.user.profile.current_workspace
    payment = get_object_or_404(Payment, id=payment_id, workspace=workspace)
    audit_logs = payment.audit_logs.all().order_by('-timestamp')
    return render(request, 'pages/payments/detail.html', {
        'payment': payment,
        'audit_logs': audit_logs
    })

@login_required
def record_offline_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=request.user.profile.current_workspace)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        method = request.POST.get('method')
        notes = request.POST.get('notes', '')
        tip = request.POST.get('tip_amount', '0')
        try:
            PaymentService.record_offline_payment(
                invoice=invoice,
                amount=amount,
                method=method,
                user=request.user,
                notes=notes,
                tip_amount=tip,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, "Offline payment recorded.")
            return redirect('invoices:invoice_detail', invoice_id=invoice.id)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    return render(request, 'pages/payments/record_offline.html', {'invoice': invoice})
