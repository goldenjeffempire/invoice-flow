import json
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
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse

from .models import (
    Invoice,
    UserProfile,
    EngagementMetric,
    UserFeedback,
    ReminderLog,
    ReminderRule,
    PaymentSettings,
)
from django.db.models import Sum, Count
from .auth_services import AuthenticationService, RegistrationService, PasswordService
from .forms import (
    LoginForm,
    SignUpForm,
    EmailOnlyForm,
    PasswordResetConfirmForm,
    InvoiceForm,
    LineItemFormSet,
    ReminderRuleForm,
)
from .sendgrid_service import SendGridEmailService
from .services import AnalyticsService, InvoiceService

def _parse_request_payload(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()

def robots_txt_view(request):
    content = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    return HttpResponse(content.encode('utf-8'), content_type="text/plain")

def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)

def custom_500_view(request):
    return render(request, "500.html", status=500)

def landing_view(request):
    if request.user.is_authenticated:
        return redirect("invoices:dashboard")
    return render(request, "pages/landing.html")

# Landing page views removed.

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

def _render_public_page(request, template_name="pages/landing.html"):
    return redirect('invoices:home')

def features_view(request):
    return render(request, "pages/features.html")

def about_view(request):
    return render(request, "pages/about.html")

def contact_view(request):
    return render(request, "pages/contact.html")

def faq_api(request):
    faq_data = [
        {
            "id": 1,
            "question": "How quickly can I start sending invoices?",
            "answer": "You can create and send your first invoice within minutes of signing up. Our intuitive editor guides you through adding client details, line items, and payment terms. No complex setup required."
        },
        {
            "id": 2,
            "question": "What payment methods do my clients have?",
            "answer": "Your clients can pay via bank transfer, card payments, or mobile money through our integrated payment partners. All transactions are secured with bank-level encryption and PCI DSS compliance."
        },
        {
            "id": 3,
            "question": "How do automated reminders work?",
            "answer": "Set up reminder rules once, and our system automatically sends professional follow-up emails before due dates, on due dates, and for overdue invoices. You can customize the timing, frequency, and messaging for each reminder stage."
        },
        {
            "id": 4,
            "question": "Can I customize my invoice branding?",
            "answer": "Absolutely. Add your company logo, choose brand colors, set custom payment terms, and include personalized notes. Your invoices will look professional and consistent with your brand identity."
        },
        {
            "id": 5,
            "question": "Is my financial data secure?",
            "answer": "Security is our priority. We use 256-bit SSL encryption, multi-factor authentication, and comply with international data protection standards. Your data is backed up daily and stored in secure, redundant data centers."
        },
        {
            "id": 6,
            "question": "What analytics and reports are available?",
            "answer": "Track revenue trends, payment timelines, client payment behavior, and invoice status in real-time. Export detailed reports for accounting, identify your best clients, and forecast cash flow with our analytics dashboard."
        }
    ]
    return JsonResponse({"faqs": faq_data, "status": "success"})

def terms_view(request):
    return redirect('invoices:home')

def privacy_view(request):
    return redirect('invoices:home')

def security_view(request):
    return redirect('invoices:home')

def faq_view(request):
    return redirect('invoices:home')

def support_view(request):
    return redirect('invoices:home')

def careers_view(request):
    return redirect('invoices:home')

def blog_view(request):
    return redirect('invoices:home')

def robots_txt_view(request):
    content = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    return HttpResponse(content.encode('utf-8'), content_type="text/plain")

def waitlist_subscribe(request):
    return redirect('invoices:home')

@login_required
def payment_history(request):
    from .models import Payment
    payments = Payment.objects.filter(invoice__user=request.user).select_related('invoice').order_by('-created_at')
    return render(request, "pages/payment_history.html", {
        "payments": payments,
        "active": "payments"
    })

@login_required
def payment_detail(request, payment_id):
    from .models import Payment
    payment = get_object_or_404(Payment, id=payment_id, invoice__user=request.user)
    return render(request, "pages/payment_detail.html", {
        "payment": payment,
        "active": "payments"
    })

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
@require_POST
def invoice_delete(request, invoice_id):
    return delete_invoice(request, invoice_id)

@login_required
def invoice_pdf(request, invoice_id):
    return download_invoice_pdf(request, invoice_id)

@login_required
def settings_page(request):
    return settings_view(request)

@login_required
@require_POST
def profile_update_ajax(request):
    payload = _parse_request_payload(request)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.company_name = payload.get("company_name", profile.company_name)
    profile.business_email = payload.get("business_email", profile.business_email)
    profile.business_phone = payload.get("business_phone", profile.business_phone)
    profile.business_address = payload.get("business_address", profile.business_address)
    profile.default_currency = payload.get("default_currency", profile.default_currency)
    profile.invoice_prefix = payload.get("invoice_prefix", profile.invoice_prefix)
    if "default_tax_rate" in payload:
        try:
            profile.default_tax_rate = Decimal(str(payload.get("default_tax_rate", profile.default_tax_rate)))
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid tax rate."}, status=400)
    profile.save()
    return JsonResponse({"success": True, "message": "Profile updated."})

@login_required
@require_POST
def security_update_ajax(request):
    payload = _parse_request_payload(request)
    current_password = payload.get("current_password", "")
    new_password = payload.get("new_password", "")
    if not current_password or not new_password:
        return JsonResponse({"success": False, "message": "Both current and new passwords are required."}, status=400)
    success, message = PasswordService.change_password(request.user, current_password, new_password)
    if success:
        return JsonResponse({"success": True, "message": message})
    return JsonResponse({"success": False, "message": message}, status=400)

@login_required
@require_POST
def notifications_update_ajax(request):
    payload = _parse_request_payload(request)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    notification_fields = [
        "notify_invoice_created",
        "notify_payment_received",
        "notify_invoice_viewed",
        "notify_invoice_overdue",
        "notify_weekly_summary",
        "notify_security_alerts",
        "notify_password_changes",
    ]
    for field in notification_fields:
        if field in payload:
            profile_value = str(payload[field]).lower() in {"1", "true", "yes", "on"}
            setattr(profile, field, profile_value)
    profile.save()
    return JsonResponse({"success": True, "message": "Notification preferences updated."})

@login_required
def reminder_dashboard(request):
    rules = ReminderRule.objects.filter(user=request.user).order_by("trigger_type", "days_delta")
    form = ReminderRuleForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            reminder_rule = form.save(commit=False)
            reminder_rule.user = request.user
            reminder_rule.save()
            messages.success(request, "Reminder rule saved.")
            return redirect("invoices:reminder_dashboard")
        messages.error(request, "Please correct the errors below.")
    return render(
        request,
        "pages/reminder_settings.html",
        {
            "rules": rules,
            "form": form,
            "active": "settings",
        },
    )

@login_required
def reminder_settings(request):
    return reminder_dashboard(request)

def track_reminder_click(request, log_id):
    reminder_log = get_object_or_404(ReminderLog, id=log_id)
    if reminder_log.clicked_at is None:
        reminder_log.clicked_at = timezone.now()
        reminder_log.save(update_fields=["clicked_at"])
    return redirect("invoices:public_invoice", invoice_id=reminder_log.invoice.invoice_id)

def track_reminder_open(request, log_id):
    reminder_log = get_object_or_404(ReminderLog, id=log_id)
    if reminder_log.opened_at is None:
        reminder_log.opened_at = timezone.now()
        reminder_log.save(update_fields=["opened_at"])
    pixel = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
        b"\x00\x00\x02\x02D\x01\x00;"
    )
    response = HttpResponse(pixel, content_type="image/gif")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response

@login_required
@require_POST
def payment_settings_update_ajax(request):
    payload = _parse_request_payload(request)
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    bool_fields = [
        "enable_card_payments",
        "enable_bank_transfers",
        "enable_mobile_money",
        "enable_ussd",
        "auto_payout",
        "send_payment_receipt",
        "send_payout_notification",
    ]
    for field in bool_fields:
        if field in payload:
            setattr(payment_settings, field, str(payload[field]).lower() in {"1", "true", "yes", "on"})
    for field in [
        "preferred_currency",
        "payout_schedule",
        "payment_instructions",
        "paystack_public_key",
        "paystack_secret_key",
        "paystack_webhook_secret",
        "bank_name",
        "account_number_encrypted",
        "account_name",
        "webhook_secret",
    ]:
        if field in payload:
            setattr(payment_settings, field, payload.get(field, getattr(payment_settings, field)))
    if "payout_threshold" in payload:
        try:
            payment_settings.payout_threshold = Decimal(str(payload.get("payout_threshold", payment_settings.payout_threshold)))
        except Exception:
            return JsonResponse({"success": False, "message": "Invalid payout threshold."}, status=400)
    payment_settings.save()
    return JsonResponse({"success": True, "message": "Payment settings updated."})

def mfa_setup(request):
    from invoiceflow.mfa import mfa_setup as mfa_setup_view
    return mfa_setup_view(request)

def mfa_verify(request):
    from invoiceflow.mfa import mfa_verify as mfa_verify_view
    return mfa_verify_view(request)

def mfa_disable(request):
    from invoiceflow.mfa import mfa_disable as mfa_disable_view
    return mfa_disable_view(request)

def mfa_backup_codes(request):
    from invoiceflow.mfa import mfa_regenerate_recovery as mfa_regenerate_recovery_view
    return mfa_regenerate_recovery_view(request)

@require_POST
def record_engagement(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Authentication required."}, status=401)
    payload = _parse_request_payload(request)
    metric_type = payload.get("metric_type")
    if metric_type not in dict(EngagementMetric.MetricType.choices):
        return JsonResponse({"success": False, "message": "Invalid metric type."}, status=400)
    invoice = None
    invoice_id = payload.get("invoice_id")
    if invoice_id:
        invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    try:
        value = float(payload.get("value", 0.0))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "message": "Invalid metric value."}, status=400)
    metadata = payload.get("metadata", {}) or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {"raw": metadata}
    EngagementMetric.objects.create(
        user=request.user,
        invoice=invoice,
        metric_type=metric_type,
        element_id=payload.get("element_id", ""),
        value=value,
        metadata=metadata,
    )
    return JsonResponse({"success": True})

@require_POST
def submit_feedback(request):
    payload = _parse_request_payload(request)
    try:
        rating = int(payload.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    if rating not in range(1, 6):
        return JsonResponse({"success": False, "message": "Rating must be between 1 and 5."}, status=400)
    page_url = payload.get("page_url")
    if not page_url:
        return JsonResponse({"success": False, "message": "Page URL is required."}, status=400)
    
    # Redact PII from user agent if needed, but here we just ensure we don't log it raw if we were logging
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    is_mobile = payload.get("is_mobile")
    if is_mobile is None:
        is_mobile = "mobile" in user_agent.lower()
    UserFeedback.objects.create(
        user=request.user if request.user.is_authenticated else None,
        rating=rating,
        comment=payload.get("comment", ""),
        page_url=page_url,
        user_agent=user_agent,
        is_mobile=bool(is_mobile),
    )
    return JsonResponse({"success": True, "message": "Feedback received. Thank you!"})

@login_required
def dashboard(request):
    from django.core.cache import cache
    cache_key = f"dashboard_stats_{request.user.id}"
    stats = cache.get(cache_key)
    if not stats:
        stats = AnalyticsService.get_user_dashboard_stats(request.user)
        cache.set(cache_key, stats, 300)

    recent_invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # We use stats directly from AnalyticsService which already has the correct keys
    return render(request, "pages/dashboard.html", {
        "stats": stats, 
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
                
                # Schedule reminders for the new invoice
                InvoiceService.schedule_reminders(invoice)
                
                AnalyticsService.invalidate_user_cache(request.user.id)
            messages.success(request, "Invoice created successfully!")
            return redirect("invoices:invoice_detail", invoice_id=invoice.invoice_id)
        messages.error(request, "Please correct the errors below.")
    else:
        from .utils import _get_invoice_initial
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
    lookup: dict[str, object]
    if str(invoice_id).isdigit():
        lookup = {"pk": invoice_id}
    else:
        lookup = {"invoice_id": invoice_id}
    invoice = get_object_or_404(Invoice, user=request.user, **lookup)
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
    stats = AnalyticsService.get_user_analytics_stats(request.user)
    return render(request, "pages/analytics.html", stats)

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
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile.company_name = request.POST.get("company_name", profile.company_name)
        profile.business_email = request.POST.get("business_email", profile.business_email)
        profile.business_phone = request.POST.get("business_phone", profile.business_phone)
        profile.business_address = request.POST.get("business_address", profile.business_address)
        profile.default_currency = request.POST.get("default_currency", profile.default_currency)
        profile.invoice_prefix = request.POST.get("invoice_prefix", profile.invoice_prefix)
        if request.POST.get("default_tax_rate"):
            try:
                profile.default_tax_rate = Decimal(request.POST.get("default_tax_rate", profile.default_tax_rate))
            except Exception:
                messages.error(request, "Tax rate must be a valid number.")
        notification_fields = [
            "notify_invoice_created",
            "notify_payment_received",
            "notify_invoice_viewed",
            "notify_invoice_overdue",
            "notify_weekly_summary",
            "notify_security_alerts",
            "notify_password_changes",
        ]
        for field in notification_fields:
            setattr(profile, field, bool(request.POST.get(field)))
        profile.save()
        payment_settings.enable_card_payments = bool(request.POST.get("enable_card_payments"))
        payment_settings.enable_bank_transfers = bool(request.POST.get("enable_bank_transfers"))
        payment_settings.enable_mobile_money = bool(request.POST.get("enable_mobile_money"))
        payment_settings.enable_ussd = bool(request.POST.get("enable_ussd"))
        payment_settings.auto_payout = bool(request.POST.get("auto_payout"))
        payment_settings.send_payment_receipt = bool(request.POST.get("send_payment_receipt"))
        payment_settings.send_payout_notification = bool(request.POST.get("send_payout_notification"))
        payment_settings.preferred_currency = request.POST.get(
            "preferred_currency", payment_settings.preferred_currency
        )
        payment_settings.payout_schedule = request.POST.get(
            "payout_schedule", payment_settings.payout_schedule
        )
        payment_settings.payment_instructions = request.POST.get(
            "payment_instructions", payment_settings.payment_instructions
        )
        payment_settings.save()
        messages.success(request, "Settings updated successfully!")

    return render(
        request,
        "pages/settings.html",
        {
            "profile": profile,
            "payment_settings": payment_settings,
            "active": "settings",
        },
    )

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    canvas = None
    letter = None

@login_required
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    
    try:
        from django.template.loader import render_to_string
        from weasyprint import HTML
        
        html_string = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice})
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf_file = html.write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect("invoices:invoice_detail", invoice_id=invoice_id)

@login_required
@require_POST
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=request.user)
    invoice.delete()
    messages.success(request, f"Invoice {invoice_id} deleted.")
    return redirect("invoices:invoices_list")

def custom_404(request, exception):
    return render(request, "pages/landing.html", status=404)

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    SendGridAPIClient = None
    Mail = None

def logout_view(request):
    from .services import AuthenticationService
    AuthenticationService.logout_user(request)
    return redirect("invoices:home")

def custom_500(request):
    return render(request, "pages/landing.html", status=500)

@login_required
@require_POST
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
