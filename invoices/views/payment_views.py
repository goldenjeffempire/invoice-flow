from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Payment, Transaction, Workspace
from ..services.payment_service import PaymentService

@login_required
def payment_overview(request):
    workspace = request.user.profile.current_workspace
    payments = Payment.objects.filter(workspace=workspace)
    return render(request, 'pages/payments/overview.html', {'payments': payments})

@login_required
def transaction_list(request):
    workspace = request.user.profile.current_workspace
    transactions = Transaction.objects.filter(workspace=workspace)
    return render(request, 'pages/payments/list.html', {'transactions': transactions})

@login_required
def payment_detail(request, payment_id):
    workspace = request.user.profile.current_workspace
    payment = get_object_or_404(Payment, id=payment_id, workspace=workspace)
    return render(request, 'pages/payments/detail.html', {'payment': payment})
