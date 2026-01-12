from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Invoice, UserProfile, LineItem
from django.db.models import Sum, Count, Q

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

@login_required
def dashboard(request):
    user_invoices = Invoice.objects.filter(user=request.user)
    
    total_revenue = Decimal('0.00')
    total_outstanding = Decimal('0.00')
    total_overdue = Decimal('0.00')
    
    for inv in user_invoices:
        if inv.status == 'paid':
            total_revenue += inv.total
        elif inv.status == 'unpaid':
            total_outstanding += inv.total
        elif inv.status == 'overdue':
            total_overdue += inv.total

    formatted_stats = {
        'total_count': user_invoices.count(),
        'revenue': '{:,.2f}'.format(total_revenue),
        'outstanding': '{:,.2f}'.format(total_outstanding),
        'overdue': '{:,.2f}'.format(total_overdue),
    }

    recent_invoices = user_invoices.order_by('-created_at')[:5]
    
    return render(request, "pages/dashboard.html", {
        "stats": formatted_stats, 
        "recent_invoices": recent_invoices,
        "active": "dashboard"
    })

@login_required
def invoices_list(request):
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "pages/invoices_list.html", {
        "invoices": invoices,
        "active": "invoices"
    })

@login_required
def invoice_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                
                invoice = Invoice.objects.create(
                    user=request.user,
                    client_name=request.POST.get('client_name'),
                    client_email=request.POST.get('client_email'),
                    due_date=request.POST.get('due_date'),
                    currency=request.POST.get('currency', 'USD'),
                    tax_rate=Decimal(request.POST.get('tax_rate', '0')),
                    business_name=profile.company_name or request.user.get_full_name() or request.user.username,
                    business_email=profile.business_email or request.user.email
                )
                
                descriptions = request.POST.getlist('item_description[]')
                quantities = request.POST.getlist('item_quantity[]')
                prices = request.POST.getlist('item_price[]')
                
                for desc, qty, price in zip(descriptions, quantities, prices):
                    if desc and qty and price:
                        LineItem.objects.create(
                            invoice=invoice,
                            description=desc,
                            quantity=Decimal(qty),
                            unit_price=Decimal(price)
                        )
                
                messages.success(request, "Invoice created successfully!")
                return redirect('invoices_list')
        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
            
    return render(request, "pages/invoice_create.html", {"active": "invoices"})

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        new_status = request.POST.get('status')
        if new_status in dict(Invoice.Status.choices):
            invoice.status = new_status
            invoice.save()
            messages.success(request, f"Invoice {invoice_id} status updated to {invoice.get_status_display()}.")
            return redirect('invoice_detail', invoice_id=invoice_id)
            
    return render(request, "pages/invoice_detail.html", {
        "invoice": invoice,
        "active": "invoices"
    })

@login_required
def analytics(request):
    user_invoices = Invoice.objects.filter(user=request.user)
    
    # Revenue by month
    revenue_data = user_invoices.filter(status='paid').extra(
        select={'month': "EXTRACT(MONTH FROM created_at)"}
    ).values('month').annotate(total=Sum('total')).order_by('month')
    
    # Payment status distribution
    status_counts = user_invoices.values('status').annotate(count=Count('id'))
    
    return render(request, "pages/analytics.html", {
        "revenue_data": list(revenue_data),
        "status_counts": list(status_counts),
        "active": "analytics"
    })

@login_required
def clients(request):
    clients_list = Invoice.objects.filter(user=request.user).values(
        'client_name', 'client_email'
    ).annotate(
        total_invoiced=Sum('total'),
        invoice_count=Count('id')
    ).order_by('client_name')
    
    return render(request, "pages/clients.html", {
        "clients": clients_list,
        "active": "clients"
    })

@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.company_name = request.POST.get('company_name', '')
        profile.business_email = request.POST.get('business_email', '')
        profile.save()
        messages.success(request, "Settings updated successfully!")
        
    return render(request, "pages/settings.html", {
        "profile": profile,
        "active": "settings"
    })

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

@login_required
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"INVOICE: {invoice.invoice_id}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Date: {invoice.created_at.strftime('%Y-%m-%d')}")
    p.drawString(100, 705, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")
    p.drawString(100, 680, f"Client: {invoice.client_name}")
    p.drawString(100, 665, f"Email: {invoice.client_email}")
    
    p.line(100, 650, 500, 650)
    
    y = 630
    p.drawString(100, y, "Items:")
    y -= 20
    for item in invoice.items.all():
        p.drawString(120, y, f"{item.description} - {item.quantity} x ${item.unit_price} = ${item.total_price}")
        y -= 15
        
    p.line(100, y, 500, y)
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, f"Total Amount: ${invoice.total}")
    
    p.showPage()
    p.save()
    return response

@login_required
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        invoice.delete()
        messages.success(request, f"Invoice {invoice_id} deleted.")
        return redirect('invoices_list')
    return redirect('invoice_detail', invoice_id=invoice_id)

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def logout_view(request):
    logout(request)
    return redirect("home")

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)

@login_required
def send_reminder(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    try:
        message = Mail(
            from_email='noreply@invoiceflow.com',
            to_emails=invoice.client_email,
            subject=f'Payment Reminder: Invoice {invoice.invoice_id}',
            html_content=f'<p>Hello {invoice.client_name},</p><p>This is a reminder that payment for invoice {invoice.invoice_id} of ${invoice.total} is due on {invoice.due_date}.</p>'
        )
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
        messages.success(request, f"Reminder sent to {invoice.client_email}")
    except Exception as e:
        messages.error(request, f"Failed to send reminder: {str(e)}")
    return redirect('invoice_detail', invoice_id=invoice_id)
    return render(request, "pages/home-light.html", status=500)
