import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from ..models import Client, ClientPortalToken, ClientPortalSession, Invoice, InvoicePayment
from ..services.portal_service import ClientPortalService
from ..services import PDFService

logger = logging.getLogger(__name__)

def portal_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        client = Client.objects.filter(email__iexact=email).first()
        if client:
            magic_link = ClientPortalService.generate_magic_link(client, request.META.get('REMOTE_ADDR'))
            ClientPortalService.send_magic_link(client, magic_link)
        
        # Always show success to prevent email enumeration
        messages.success(request, "If an account exists for this email, a secure access link has been sent.")
        return redirect('invoices:portal_login')
    
    return render(request, 'invoices/portal/login.html')

def portal_authenticate(request, token):
    portal_token = get_object_or_404(ClientPortalToken, token=token)
    
    if not portal_token.is_valid:
        messages.error(request, "This link has expired or already been used.")
        return redirect('invoices:portal_login')
    
    portal_token.mark_used()
    session = ClientPortalService.create_session(portal_token.client, request)
    
    request.session['client_portal_session'] = session.session_key
    return redirect('invoices:portal_dashboard')

def get_portal_session(request):
    session_key = request.session.get('client_portal_session')
    if not session_key:
        return None
    
    session = ClientPortalSession.objects.filter(session_key=session_key, is_active=True).first()
    if session and session.is_valid:
        return session
    return None

def portal_dashboard(request):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    client = session.client
    invoices = Invoice.objects.filter(client=client).order_by('-created_at')
    
    context = {
        'client': client,
        'invoices': invoices,
        'summary': {
            'total_outstanding': sum(inv.amount_due for inv in invoices if inv.status != Invoice.Status.PAID),
            'paid_count': invoices.filter(status=Invoice.Status.PAID).count(),
            'pending_count': invoices.exclude(status__in=[Invoice.Status.PAID, Invoice.Status.VOID]).count(),
        }
    }
    return render(request, 'invoices/portal/dashboard.html', context)

def portal_invoice_detail(request, invoice_id):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    invoice = get_object_or_404(Invoice, id=invoice_id, client=session.client)
    payments = invoice.payments.filter(status=InvoicePayment.PaymentStatus.COMPLETED)
    
    return render(request, 'invoices/portal/invoice_detail.html', {
        'invoice': invoice,
        'payments': payments
    })

def portal_profile(request):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    client = session.client
    if request.method == 'POST':
        client.name = request.POST.get('name', client.name)
        client.phone = request.POST.get('phone', client.phone)
        client.billing_address = request.POST.get('billing_address', client.billing_address)
        client.save()
        messages.success(request, "Billing details updated successfully.")
        return redirect('invoices:portal_profile')
        
    return render(request, 'invoices/portal/profile.html', {'client': client})

def portal_logout(request):
    session_key = request.session.pop('client_portal_session', None)
    if session_key:
        ClientPortalSession.objects.filter(session_key=session_key).update(is_active=False)
    return redirect('invoices:portal_login')
