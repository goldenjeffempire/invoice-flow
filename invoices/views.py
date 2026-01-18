import os
from decimal import Decimal
from typing import Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect

from .models import Invoice, UserProfile
from django.db.models import Sum, Count
from .auth_services import AuthenticationService, RegistrationService, PasswordService
from .forms import (
    LoginForm,
    SignUpForm,
    EmailOnlyForm,
    PasswordResetConfirmForm,
    InvoiceForm,
    LineItemFormSet,
)
from .sendgrid_service import SendGridEmailService

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "pages/home-light.html")

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect("invoices:dashboard")

    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and not url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        next_url = ""

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username_input = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]

        username = username_input
        if "@" in username_input:
            user = User.objects.filter(email__iexact=username_input).first()
            if user:
                username = user.username

        user, error_message = AuthenticationService.authenticate_user(
            request=request,
            username=username,
            password=password,
        )

        if user is None:
            if "inactive" in error_message.lower():
                messages.error(
                    request,
                    "Your account is inactive. Please verify your email. "
                    "You can request a new verification link below.",
                )
            else:
                messages.error(request, error_message)
        else:
            result = AuthenticationService.login_user(request, user)

            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)

            if not result.get("email_verified"):
                messages.warning(
                    request,
                    "Please verify your email to unlock all features.",
                )

            return redirect(next_url or "invoices:dashboard")

    return render(
        request,
        "pages/auth/login.html",
        {
            "form": form,
            "next_url": next_url,
        },
    )

@csrf_protect
def signup(request):
    if request.user.is_authenticated:
        return redirect("invoices:dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user, error_message, token = RegistrationService.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password1"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            require_email_verification=True,
        )

        if user is None:
            messages.error(request, error_message)
        else:
            if token:
                try:
                    SendGridEmailService().send_verification_email(user, token.token)
                    messages.success(
                        request,
                        "Account created! Please check your inbox to verify your email.",
                    )
                except Exception:
                    messages.warning(
                        request,
                        "Account created, but we could not send a verification email. "
                        "Please contact support.",
                    )
            return redirect("invoices:verification_sent")

    return render(request, "pages/auth/signup.html", {"form": form})


def verification_sent(request):
    return render(request, "pages/auth/verification_sent.html")


@csrf_protect
def resend_verification(request):
    form = EmailOnlyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        success, message, token = RegistrationService.resend_verification_email(email)
        if success and token:
            try:
                user = token.user
                SendGridEmailService().send_verification_email(user, token.token)
                messages.success(request, message)
                return redirect("invoices:verification_sent")
            except Exception:
                messages.warning(
                    request,
                    "Verification email could not be sent. Please contact support.",
                )
        else:
            messages.error(request, message)

    return render(request, "pages/auth/resend_verification.html", {"form": form})


def verify_email(request, token: str):
    success, message = RegistrationService.verify_email(token)
    if success:
        messages.success(request, message)
        return redirect("invoices:login")
    messages.error(request, message)
    return render(request, "pages/auth/verification_failed.html")


@csrf_protect
def password_reset_request(request):
    form = EmailOnlyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        success, message, token = PasswordService.request_password_reset(email)
        if success and token:
            try:
                SendGridEmailService().send_password_reset_email(token.user, token.token)
            except Exception:
                messages.warning(
                    request,
                    "We couldn't send the reset email. Please contact support if needed.",
                )
        messages.success(request, message)
        return redirect("invoices:password_reset_done")

    return render(request, "pages/auth/password_reset.html", {"form": form})


def password_reset_done(request):
    return render(request, "pages/auth/password_reset_done.html")


@csrf_protect
def password_reset_confirm(request, token: str):
    is_valid, user, error_message = PasswordService.validate_reset_token(token)
    if not is_valid or user is None:
        messages.error(request, error_message)
        return render(request, "pages/auth/password_reset_invalid.html")

    form = PasswordResetConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        success, message = PasswordService.reset_password(token, form.cleaned_data["new_password"])
        if success:
            messages.success(request, message)
            return redirect("invoices:login")
        messages.error(request, message)

    return render(
        request,
        "pages/auth/password_reset_confirm.html",
        {
            "form": form,
            "token": token,
        },
    )

def pricing_view(request):
    return render(request, "pages/pricing.html")

def waitlist_subscribe(request):
    return redirect('invoices:home')

def payment_history(request):
    return redirect('invoices:dashboard')

def payment_detail(request, payment_id):
    return redirect('invoices:dashboard')

@login_required
def invoice_edit(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        form = InvoiceForm(request.POST, instance=invoice)
        formset = LineItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Invoice updated successfully.")
            return redirect("invoices:invoice_detail", invoice_id=invoice.invoice_id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = InvoiceForm(instance=invoice)
        formset = LineItemFormSet(instance=invoice)
    return render(
        request,
        "pages/invoice_create.html",
        {
            "form": form,
            "formset": formset,
            "form_title": f"Edit Invoice {invoice.invoice_id}",
            "form_description": "Update invoice details and line items.",
            "submit_label": "Save Changes",
            "active": "invoices",
            "invoice": invoice,
        },
    )

@login_required
def invoice_delete(request, invoice_id):
    return delete_invoice(request, invoice_id)

@login_required
def invoice_pdf(request, invoice_id):
    return download_invoice_pdf(request, invoice_id)

def settings_page(request):
    return redirect('invoices:settings')

def profile_update_ajax(request):
    return redirect('invoices:settings')

def security_update_ajax(request):
    return redirect('invoices:settings')

def notifications_update_ajax(request):
    return redirect('invoices:settings')

def reminder_dashboard(request):
    return redirect('invoices:settings')

def reminder_settings(request):
    return redirect('invoices:settings')

def track_reminder_click(request, log_id):
    return redirect('invoices:home')

def track_reminder_open(request, log_id):
    return redirect('invoices:home')

def payment_settings_update_ajax(request):
    return redirect('invoices:settings')

def mfa_setup(request):
    return redirect('invoices:settings')

def mfa_verify(request):
    return redirect('invoices:settings')

def mfa_disable(request):
    return redirect('invoices:settings')

def mfa_backup_codes(request):
    return redirect('invoices:settings')

def record_engagement(request):
    return redirect('invoices:home')

def submit_feedback(request):
    return redirect('invoices:home')

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
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        formset = LineItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.user = request.user
                invoice.save()
                formset.instance = invoice
                formset.save()
            messages.success(request, "Invoice created successfully!")
            return redirect("invoices:invoice_detail", invoice_id=invoice.invoice_id)
        messages.error(request, "Please correct the errors below.")
    else:
        form = InvoiceForm(initial=_get_invoice_initial(profile))
        formset = LineItemFormSet()
    return render(
        request,
        "pages/invoice_create.html",
        {
            "form": form,
            "formset": formset,
            "form_title": "New Invoice",
            "form_description": "Create a professional invoice in minutes.",
            "submit_label": "Generate Invoice",
            "active": "invoices",
        },
    )

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        new_status = request.POST.get('status')
        if new_status in dict(Invoice.Status.choices):
            invoice.status = new_status
            invoice.save()
            messages.success(request, f"Invoice {invoice_id} status updated to {invoice.get_status_display()}.")
            return redirect("invoices:invoice_detail", invoice_id=invoice_id)
            
    return render(
        request,
        "pages/invoice_detail.html",
        {
            "invoice": invoice,
            "status_choices": Invoice.Status.choices,
            "active": "invoices",
        },
    )

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
    p.drawString(100, 720, f"Date: {invoice.invoice_date.strftime('%Y-%m-%d')}")
    due_date = invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "N/A"
    p.drawString(100, 705, f"Due Date: {due_date}")
    p.drawString(100, 690, f"Client: {invoice.client_name}")
    p.drawString(100, 675, f"Email: {invoice.client_email}")
    
    p.line(100, 650, 500, 650)
    
    y = 630
    p.drawString(100, y, "Items:")
    y -= 20
    for item in invoice.line_items.all():
        line_total = item.total
        p.drawString(
            120,
            y,
            f"{item.description} - {item.quantity} x {invoice.currency} {item.unit_price} = {invoice.currency} {line_total}",
        )
        y -= 15
        
    p.line(100, y, 500, y)
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, f"Total Amount: {invoice.currency} {invoice.total}")
    
    p.showPage()
    p.save()
    return response

@login_required
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    if request.method == "POST":
        invoice.delete()
        messages.success(request, f"Invoice {invoice_id} deleted.")
        return redirect("invoices:invoices_list")
    return redirect("invoices:invoice_detail", invoice_id=invoice_id)

def custom_404(request, exception):
    return render(request, "pages/home-light.html", status=404)

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def logout_view(request):
    AuthenticationService.logout_user(request)
    return redirect("invoices:home")

def custom_500(request):
    return render(request, "pages/home-light.html", status=500)

@login_required
def send_reminder(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    try:
        due_date = invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "N/A"
        message = Mail(
            from_email='noreply@invoiceflow.com',
            to_emails=invoice.client_email,
            subject=f'Payment Reminder: Invoice {invoice.invoice_id}',
            html_content=(
                f"<p>Hello {invoice.client_name},</p>"
                f"<p>This is a reminder that payment for invoice {invoice.invoice_id} "
                f"of {invoice.currency} {invoice.total} is due on {due_date}.</p>"
            ),
        )
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
        messages.success(request, f"Reminder sent to {invoice.client_email}")
    except Exception as e:
        messages.error(request, f"Failed to send reminder: {str(e)}")
    return redirect("invoices:invoice_detail", invoice_id=invoice_id)


def _get_invoice_initial(profile: UserProfile) -> Dict[str, object]:
    default_name = profile.company_name or ""
    default_email = profile.business_email or ""
    default_phone = profile.business_phone or ""
    default_address = profile.business_address or ""
    return {
        "business_name": default_name,
        "business_email": default_email,
        "business_phone": default_phone,
        "business_address": default_address,
        "currency": profile.default_currency or "USD",
        "tax_rate": profile.default_tax_rate or Decimal("0.00"),
        "invoice_date": timezone.localdate(),
    }
