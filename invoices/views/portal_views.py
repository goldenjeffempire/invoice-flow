import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from django.http import HttpResponse
from ..models import Client, ClientPortalToken, ClientPortalSession, Invoice, InvoicePayment
from ..services.portal_service import ClientPortalService
from ..services import PDFService

logger = logging.getLogger(__name__)

def get_portal_session(request):
    session_key = request.session.get('client_portal_session')
    if not session_key:
        return None
    
    session = ClientPortalSession.objects.filter(session_key=session_key, is_active=True).first()
    if session and session.is_valid:
        return session
    return None

def portal_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        client = Client.objects.filter(email__iexact=email).first()
        if client:
            ip = request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')
            magic_link = ClientPortalService.generate_magic_link(client, ip, ua)
            ClientPortalService.send_magic_link(client, magic_link)
        
        messages.success(request, "If an account exists for this email, a secure access link has been sent. Please check your inbox.")
        return redirect('invoices:portal_login')
    
    return render(request, 'invoices/portal/login.html')

def portal_authenticate(request, token):
    portal_token = get_object_or_404(ClientPortalToken, token=token)
    
    if not portal_token.is_valid:
        messages.error(request, "This secure link has expired or already been used.")
        return redirect('invoices:portal_login')
    
    portal_token.mark_used()
    session = ClientPortalService.create_session(portal_token.client, request)
    
    request.session['client_portal_session'] = session.session_key
    return redirect('invoices:portal_dashboard')

def portal_dashboard(request):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    client = session.client
    invoices = Invoice.objects.filter(client=client).order_by('-issue_date', '-created_at')
    
    # Calculate stats
    total_invoiced = invoices.exclude(status=Invoice.Status.VOID).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = invoices.filter(status=Invoice.Status.PAID).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_outstanding = invoices.exclude(status__in=[Invoice.Status.PAID, Invoice.Status.VOID]).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
    
    context = {
        'client': client,
        'invoices': invoices[:10],
        'total_invoices_count': invoices.count(),
        'stats': {
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
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

def portal_invoice_pdf(request, invoice_id):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    invoice = get_object_or_404(Invoice, id=invoice_id, client=session.client)
    pdf_service = PDFService()
    pdf_content = pdf_service.generate_invoice_pdf(invoice)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    return response

def portal_profile(request):
    session = get_portal_session(request)
    if not session:
        return redirect('invoices:portal_login')
    
    client = session.client
    if request.method == 'POST':
        client.billing_address = request.POST.get('billing_address', client.billing_address)
        client.phone = request.POST.get('phone', client.phone)
        client.save()
        messages.success(request, "Billing information updated successfully.")
        return redirect('invoices:portal_profile')
        
    return render(request, 'invoices/portal/profile.html', {'client': client})

def portal_logout(request):
    session_key = request.session.pop('client_portal_session', None)
    if session_key:
        ClientPortalSession.objects.filter(session_key=session_key).update(is_active=False)
    messages.info(request, "You have been logged out of the client portal.")
    return redirect('invoices:portal_login')
