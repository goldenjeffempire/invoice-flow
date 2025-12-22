import calendar
import hashlib
import json
import os
import urllib.parse
from datetime import datetime
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    InvoiceForm,
    InvoiceTemplateForm,
    RecurringInvoiceForm,
    SignUpForm,
    UserProfileForm,
)
from .models import Invoice, InvoiceTemplate, LineItem, RecurringInvoice, UserProfile
from .search_filters import InvoiceExport


def get_client_ip(request):
    """Extract client IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    return ip


def home(request):
    """Render the public landing page."""
    return render(request, "pages/home-light.html")


def signup(request):
    """Handle user registration with form validation and email verification."""
    from django.conf import settings as django_settings
    from .auth_services import RegistrationService
    from .sendgrid_service import SendGridEmailService

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            require_verification = getattr(django_settings, "REQUIRE_EMAIL_VERIFICATION", False)

            user, error = RegistrationService.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
                first_name=form.cleaned_data.get("first_name", ""),
                last_name=form.cleaned_data.get("last_name", ""),
                require_email_verification=require_verification,
            )

            if error:
                messages.error(request, error)
            elif user:
                if require_verification:
                    from .models import EmailVerificationToken
                    token = EmailVerificationToken.objects.filter(
                        user=user, token_type="signup", is_used=False
                    ).first()
                    if token:
                        try:
                            email_service = SendGridEmailService()
                            email_service.send_verification_email(user, token.token)
                        except Exception:
                            pass
                    messages.success(
                        request,
                        "Account created! Please check your email to verify your account."
                    )
                    return redirect("verification_sent")
                else:
                    login(request, user)
                    messages.success(request, "Account created successfully!")
                    return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "auth/signup.html", {"form": form})


def verify_email(request, token):
    """Verify email address using token from email link."""
    from .auth_services import RegistrationService

    success, message = RegistrationService.verify_email(token)

    if success:
        messages.success(request, message)
        return redirect("login")
    else:
        messages.error(request, message)
        return render(request, "auth/verification_failed.html", {"message": message})


def verification_sent(request):
    """Display page after signup confirming verification email was sent."""
    return render(request, "auth/verification_sent.html")


def resend_verification(request):
    """Resend verification email to user."""
    from .auth_services import RegistrationService
    from .sendgrid_service import SendGridEmailService
    from .models import EmailVerificationToken

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "auth/resend_verification.html")

        success, message = RegistrationService.resend_verification_email(email)

        if success:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(email__iexact=email, is_active=False)
                token = EmailVerificationToken.objects.filter(
                    user=user, token_type="signup", is_used=False
                ).order_by("-created_at").first()
                if token:
                    try:
                        email_service = SendGridEmailService()
                        email_service.send_verification_email(user, token.token)
                    except Exception:
                        pass
            except Exception:  # User.DoesNotExist
                pass

        messages.success(request, "If an account with this email exists and is pending verification, a new verification email has been sent.")
        return redirect("login")

    return render(request, "auth/resend_verification.html")


def forgot_password(request):
    """Handle forgot password request - send reset email."""
    from .auth_services import PasswordService
    from .sendgrid_service import SendGridEmailService

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "auth/forgot_password.html")

        success, message, token_obj = PasswordService.request_password_reset(email)

        if token_obj:
            try:
                email_service = SendGridEmailService()
                email_service.send_password_reset_email(token_obj.user, token_obj.token)
            except Exception:
                pass

        messages.success(request, message)
        return redirect("forgot_password_sent")

    return render(request, "auth/forgot_password.html")


def forgot_password_sent(request):
    """Display page confirming password reset email was sent."""
    return render(request, "auth/forgot_password_sent.html")


def reset_password(request, token):
    """Handle password reset with token from email."""
    from .auth_services import PasswordService

    if request.user.is_authenticated:
        return redirect("dashboard")

    is_valid, user, error_msg = PasswordService.validate_reset_token(token)

    if not is_valid:
        messages.error(request, error_msg)
        return render(request, "auth/reset_password_invalid.html", {"message": error_msg})

    if request.method == "POST":
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password1 or not password2:
            messages.error(request, "Please enter and confirm your new password.")
            return render(request, "auth/reset_password.html", {"token": token, "user": user})

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "auth/reset_password.html", {"token": token, "user": user})

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, "auth/reset_password.html", {"token": token, "user": user})

        success, message = PasswordService.reset_password(token, password1)

        if success:
            messages.success(request, message)
            return redirect("login")
        else:
            messages.error(request, message)
            return render(request, "auth/reset_password.html", {"token": token, "user": user})

    return render(request, "auth/reset_password.html", {"token": token, "user": user})


def login_view(request):
    """Authenticate user credentials and establish session with rate limiting and MFA support."""
    from django.conf import settings
    from django.core.cache import cache

    from .auth_services import AuthenticationService
    from .models import LoginAttempt, MFAProfile

    if request.method == "POST":
        client_ip = AuthenticationService.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password")

        lockout_threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 5)
        lockout_duration = getattr(settings, "ACCOUNT_LOCKOUT_DURATION", 900)

        ip_cache_key = f"login_attempt:ip:{client_ip}"
        user_cache_key = f"login_attempt:user:{username.lower()}" if username else None

        ip_attempts = cache.get(ip_cache_key, 0)
        user_attempts = cache.get(user_cache_key, 0) if user_cache_key else 0

        if ip_attempts >= lockout_threshold:
            messages.error(
                request,
                "Too many login attempts from this location. Please try again in 15 minutes.",
            )
            return render(request, "auth/login.html")

        if user_attempts >= lockout_threshold:
            messages.error(
                request,
                "This account is temporarily locked due to too many failed attempts. Please try again in 15 minutes.",
            )
            return render(request, "auth/login.html")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            cache.delete(ip_cache_key)
            if user_cache_key:
                cache.delete(user_cache_key)

            LoginAttempt.objects.create(
                username=username, ip_address=client_ip, user_agent=user_agent, success=True
            )

            login(request, user)

            if getattr(settings, "MFA_ENABLED", False):
                try:
                    mfa_profile = MFAProfile.objects.get(user=user)
                    if mfa_profile.is_enabled:
                        request.session["mfa_verified"] = False
                        return redirect("mfa_verify")
                except Exception:  # MFAProfile.DoesNotExist
                    pass

            request.session["mfa_verified"] = True
            return redirect("dashboard")
        else:
            cache.set(ip_cache_key, ip_attempts + 1, lockout_duration)
            if user_cache_key:
                cache.set(user_cache_key, user_attempts + 1, lockout_duration)

            LoginAttempt.objects.create(
                username=username or "unknown",
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid credentials",
            )

            messages.error(request, "Invalid username or password.")
    return render(request, "auth/login.html")


def logout_view(request):
    """End user session, clear MFA verification, and redirect to home page."""
    request.session.pop("mfa_verified", None)
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    """Display user dashboard with invoice statistics and filtered invoice list."""
    from invoices.services import AnalyticsService
    from datetime import timedelta
    from django.db.models.functions import TruncMonth
    from django.db.models import Sum, F
    from decimal import Decimal

    base_queryset = Invoice.objects.filter(user=request.user)  # type: ignore

    # Apply status filter at database level (not in Python)
    filter_status = request.GET.get("status", "all")
    if filter_status == "paid":
        invoices_queryset = base_queryset.filter(status="paid")
    elif filter_status == "unpaid":
        invoices_queryset = base_queryset.filter(status="unpaid")
    else:
        invoices_queryset = base_queryset

    # Fetch filtered invoices with prefetched line_items (efficient join)
    invoices = list(invoices_queryset.prefetch_related("line_items").order_by("-created_at")[:100])

    # Use AnalyticsService for efficient stats calculation
    stats = AnalyticsService.get_user_dashboard_stats(request.user)

    # Get monthly revenue data for chart (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_revenue = (
        base_queryset.filter(status="paid", invoice_date__gte=six_months_ago)
        .annotate(month=TruncMonth("invoice_date"))
        .values("month")
        .annotate(total=Sum(F("line_items__quantity") * F("line_items__unit_price")))
        .order_by("month")
    )

    # Format for Chart.js
    chart_labels = []
    chart_data = []
    for item in monthly_revenue:
        if item["month"]:
            chart_labels.append(item["month"].strftime("%b %Y"))
            chart_data.append(float(item["total"] or 0))

    # Get overdue invoices (unpaid and past due date)
    today = timezone.now().date()
    overdue_count = base_queryset.filter(status="unpaid", due_date__lt=today).count()

    # Get recent activity (last 10 invoice changes) with calculated total
    # Use distinct to avoid duplicates from line_items join
    recent_activity_qs = (
        base_queryset.annotate(
            total=Sum(F("line_items__quantity") * F("line_items__unit_price"))
        ).order_by("-updated_at").values(
            "id", "invoice_id", "client_name", "status", "updated_at", "total"
        ).distinct()[:10]
    )
    recent_activity = list(recent_activity_qs)

    context = {
        "invoices": invoices,
        "total_invoices": stats["total_invoices"],
        "paid_count": stats["paid_count"],
        "unpaid_count": stats["unpaid_count"],
        "total_revenue": stats["total_revenue"],
        "unique_clients": stats["unique_clients"],
        "filter_status": filter_status,
        "recent_invoices": invoices[:5],
        "pending_invoices": stats["unpaid_count"],
        "paid_invoices": stats["paid_count"],
        "overdue_count": overdue_count,
        "chart_labels": json.dumps(chart_labels),
        "chart_data": json.dumps(chart_data),
        "recent_activity": recent_activity,
    }
    return render(request, "dashboard/main.html", context)


@login_required
def invoice_list(request):
    """Display paginated invoice list with filtering, sorting, and bulk actions."""
    from datetime import timedelta
    from django.db.models import Sum, F

    base_queryset = Invoice.objects.filter(user=request.user).prefetch_related("line_items")

    # Get filter parameters
    status_filter = request.GET.get("status", "all")
    search_query = request.GET.get("search", "").strip()
    date_filter = request.GET.get("date_range", "all")
    sort_by = request.GET.get("sort", "-created_at")

    # Apply status filter
    if status_filter == "paid":
        base_queryset = base_queryset.filter(status="paid")
    elif status_filter == "unpaid":
        base_queryset = base_queryset.filter(status="unpaid")
    elif status_filter == "overdue":
        today = timezone.now().date()
        base_queryset = base_queryset.filter(status="unpaid", due_date__lt=today)

    # Apply search filter
    if search_query:
        query_filter = (
            Q(invoice_id__icontains=search_query) |  # type: ignore
            Q(client_name__icontains=search_query) |
            Q(client_email__icontains=search_query)
        )
        base_queryset = base_queryset.filter(query_filter)

    # Apply date range filter
    today = timezone.now().date()
    if date_filter == "7days":
        start_date = today - timedelta(days=7)
        base_queryset = base_queryset.filter(invoice_date__gte=start_date)
    elif date_filter == "30days":
        start_date = today - timedelta(days=30)
        base_queryset = base_queryset.filter(invoice_date__gte=start_date)
    elif date_filter == "90days":
        start_date = today - timedelta(days=90)
        base_queryset = base_queryset.filter(invoice_date__gte=start_date)
    elif date_filter == "year":
        start_date = today.replace(month=1, day=1)
        base_queryset = base_queryset.filter(invoice_date__gte=start_date)

    # Apply sorting
    valid_sorts = {
        "-created_at": "-created_at",
        "created_at": "created_at",
        "-invoice_date": "-invoice_date",
        "invoice_date": "invoice_date",
        "client_name": "client_name",
        "-client_name": "-client_name",
        "-total": "-total",
        "total": "total",
        "status": "status",
        "-status": "-status",
    }
    order_by = valid_sorts.get(sort_by, "-created_at")
    base_queryset = base_queryset.order_by(order_by)

    # Get unique clients for filter dropdown
    clients = Invoice.objects.filter(user=request.user).values_list("client_name", flat=True).distinct()[:50]

    # Pagination
    paginator = Paginator(base_queryset, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Calculate stats
    total_count = Invoice.objects.filter(user=request.user).count()
    paid_count = Invoice.objects.filter(user=request.user, status="paid").count()
    unpaid_count = Invoice.objects.filter(user=request.user, status="unpaid").count()
    overdue_count = Invoice.objects.filter(user=request.user, status="unpaid", due_date__lt=today).count()

    context = {
        "page_obj": page_obj,
        "invoices": page_obj.object_list,
        "status_filter": status_filter,
        "search_query": search_query,
        "date_filter": date_filter,
        "sort_by": sort_by,
        "clients": list(clients),
        "total_count": total_count,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "overdue_count": overdue_count,
        "today": today,
    }
    return render(request, "invoices/invoice_list.html", context)


@login_required
def bulk_invoice_action(request):
    """Handle bulk actions on invoices (mark paid, mark unpaid, delete, export)."""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("invoice_list")

    try:
        invoice_ids_str = request.POST.get("invoice_ids", "")
        action = request.POST.get("action", "")

        if not invoice_ids_str:
            messages.error(request, "No invoices selected.")
            return redirect("invoice_list")

        invoice_ids = [int(id.strip()) for id in invoice_ids_str.split(",") if id.strip()]

        if not invoice_ids:
            messages.error(request, "No invoices selected.")
            return redirect("invoice_list")

        invoices = Invoice.objects.filter(id__in=invoice_ids, user=request.user)

        if action == "mark_paid":
            count = invoices.update(status="paid")
            messages.success(request, f"{count} invoice(s) marked as paid.")
        elif action == "mark_unpaid":
            count = invoices.update(status="unpaid")
            messages.success(request, f"{count} invoice(s) marked as unpaid.")
        elif action == "delete":
            count = invoices.count()
            invoices.delete()
            from invoices.services import AnalyticsService
            AnalyticsService.invalidate_user_cache(request.user.id)
            messages.success(request, f"{count} invoice(s) deleted.")
        else:
            messages.error(request, "Invalid action.")

        return redirect("invoice_list")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("invoice_list")


@login_required
def create_invoice(request):
    from invoices.services import InvoiceService

    if request.method == "POST":
        line_items_data = json.loads(request.POST.get("line_items", "[]"))

        if not line_items_data:
            messages.error(request, "Please add at least one line item.")
            return render(
                request,
                "invoices/create_invoice.html",
                {"invoice_form": InvoiceForm(request.POST, request.FILES)},
            )

        invoice, invoice_form = InvoiceService.create_invoice(
            user=request.user,
            invoice_data=request.POST,
            files_data=request.FILES,
            line_items_data=line_items_data,
        )

        if invoice:
            messages.success(request, f"Invoice {invoice.invoice_id} created successfully!")
            return redirect("invoice_detail", invoice_id=invoice.id)  # type: ignore[union-attr]
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, "invoices/create_invoice.html", {"invoice_form": invoice_form})

    return render(request, "invoices/create_invoice.html", {"invoice_form": InvoiceForm()})


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )
    return render(request, "invoices/invoice_detail.html", {"invoice": invoice})


@login_required
def edit_invoice(request, invoice_id):
    from invoices.services import InvoiceService

    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )

    if request.method == "POST":
        line_items_data = json.loads(request.POST.get("line_items", "[]"))

        if not line_items_data:
            messages.error(request, "Please add at least one line item.")
            return render(
                request,
                "invoices/edit_invoice.html",
                {
                    "invoice_form": InvoiceForm(request.POST, request.FILES, instance=invoice),
                    "invoice": invoice,
                    "line_items_json": json.dumps([], default=str),
                },
            )

        updated_invoice, invoice_form = InvoiceService.update_invoice(
            invoice=invoice,
            invoice_data=request.POST,
            files_data=request.FILES,
            line_items_data=line_items_data,
        )

        if updated_invoice:
            messages.success(request, f"Invoice {updated_invoice.invoice_id} updated successfully!")
            return redirect("invoice_detail", invoice_id=updated_invoice.id)  # type: ignore[union-attr]
        else:
            messages.error(request, "Please correct the errors below.")
            line_items = list(invoice.line_items.values("description", "quantity", "unit_price"))
            return render(
                request,
                "invoices/edit_invoice.html",
                {
                    "invoice_form": invoice_form,
                    "invoice": invoice,
                    "line_items_json": json.dumps(line_items, default=str),
                },
            )

    line_items = list(invoice.line_items.values("description", "quantity", "unit_price"))

    return render(
        request,
        "invoices/edit_invoice.html",
        {
            "invoice_form": InvoiceForm(instance=invoice),
            "invoice": invoice,
            "line_items_json": json.dumps(line_items, default=str),
        },
    )


@login_required
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    if request.method == "POST":
        user_id = request.user.id
        invoice.delete()
        from invoices.services import AnalyticsService

        AnalyticsService.invalidate_user_cache(user_id)
        messages.success(request, "Invoice deleted successfully!")
        return redirect("dashboard")
    return render(request, "invoices/delete_invoice.html", {"invoice": invoice})


@login_required
def duplicate_invoice(request, invoice_id):
    """Duplicate an existing invoice with a new invoice ID."""
    from invoices.services import InvoiceService
    
    original = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )
    
    line_items_data = [
        {
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
        }
        for item in original.line_items.all()
    ]
    
    from datetime import date, timedelta
    today = date.today()
    due_date = today + timedelta(days=30)
    
    invoice_data = {
        "business_name": original.business_name,
        "business_email": original.business_email or "",
        "business_phone": original.business_phone or "",
        "business_address": original.business_address or "",
        "client_name": original.client_name,
        "client_email": original.client_email or "",
        "client_phone": original.client_phone or "",
        "client_address": original.client_address or "",
        "invoice_date": today.strftime("%Y-%m-%d"),
        "due_date": due_date.strftime("%Y-%m-%d"),
        "currency": original.currency,
        "tax_rate": str(original.tax_rate),
        "notes": original.notes or "",
    }
    
    class DictWrapper:
        def __init__(self, data):
            self._data = data
        def get(self, key, default=None):
            return self._data.get(key, default)
        def __getitem__(self, key):
            return self._data[key]
    
    new_invoice, _ = InvoiceService.create_invoice(
        user=request.user,
        invoice_data=DictWrapper(invoice_data),
        files_data={},
        line_items_data=line_items_data,
    )
    
    if new_invoice:
        messages.success(request, f"Invoice duplicated! New invoice: {new_invoice.invoice_id}")
        return redirect("edit_invoice", invoice_id=new_invoice.pk)
    else:
        messages.error(request, "Failed to duplicate invoice. Please try again.")
        return redirect("invoice_detail", invoice_id=invoice_id)


@login_required
def update_invoice_status(request, invoice_id):
    if request.method == "POST":
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        new_status = request.POST.get("status")
        if new_status in ["paid", "unpaid"]:
            invoice.status = new_status
            invoice.save()
            from invoices.services import AnalyticsService

            AnalyticsService.invalidate_user_cache(request.user.id)
            messages.success(request, f"Invoice status updated to {new_status}!")
        return redirect("invoice_detail", invoice_id=invoice.id)
    return redirect("dashboard")


@login_required
def generate_pdf(request, invoice_id):
    from .services import PDFService

    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )

    pdf = PDFService.generate_pdf_bytes(invoice)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{invoice.invoice_id}.pdf"'

    return response


@login_required
def send_invoice_email(request, invoice_id: int):
    from .async_tasks import AsyncTaskService

    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )

    if request.method == "POST":
        recipient_email = request.POST.get("recipient") or request.POST.get("email") or invoice.client_email

        AsyncTaskService.send_invoice_email_async(invoice.id, recipient_email)

        messages.success(
            request,
            f"Invoice #{invoice.invoice_id} is being sent to {recipient_email}. "
            "You'll be notified once delivered.",
        )
        return redirect("invoice_detail", invoice_id=invoice.id)

    return render(request, "invoices/send_email.html", {"invoice": invoice})


@login_required
def whatsapp_share(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("line_items"), id=invoice_id, user=request.user
    )

    # Enhanced WhatsApp message with emojis and better formatting
    phone_line = f"📞 {invoice.business_phone}" if invoice.business_phone else ""
    due_line = f"⏰ Due: {invoice.due_date.strftime('%B %d, %Y')}" if invoice.due_date else ""

    payment_details = ""
    if invoice.bank_name:
        payment_details = f"\n\n🏦 *Payment Details:*\nBank: {invoice.bank_name}\nAccount: {invoice.account_name}\nAccount #: {invoice.account_number}"

    notes_line = ""
    if invoice.notes:
        notes_line = f"\n\n📝 Notes: {invoice.notes}"

    message = f"""📄 *Invoice #{invoice.invoice_id}*

👔 From: *{invoice.business_name}*
{invoice.business_email}
{phone_line}

👤 To: *{invoice.client_name}*

📅 Date: {invoice.invoice_date.strftime('%B %d, %Y')}
{due_line}

💰 *Total Amount: {invoice.currency} {invoice.total:.2f}*
Status: {invoice.get_status_display().upper()}{payment_details}{notes_line}

Thank you for your business! 🙏
- {invoice.business_name}
    """.strip()

    # Clean phone number for WhatsApp
    phone = (
        invoice.client_phone.replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    whatsapp_url = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

    return render(
        request,
        "invoices/whatsapp_share.html",
        {
            "invoice": invoice,
            "whatsapp_url": whatsapp_url,
            "message_preview": message,
        },
    )


# ============================================================================
# FOOTER PAGE VIEWS - Professional Public Pages
# ============================================================================


def features(request):
    """Features page showcasing platform capabilities."""
    return render(request, "pages/features-light.html")


def pricing(request):
    """Free platform - no pricing tiers needed."""
    return render(request, "pages/pricing-light.html")


def templates_page(request):
    """Invoice templates coming soon page."""
    return render(request, "pages/templates.html")


def api_access(request):
    """API access coming soon page."""
    return render(request, "pages/api.html")


def about(request):
    """About Us page - company story and values."""
    return render(request, "pages/about-light.html")


def careers(request):
    """Careers page with open positions."""
    return render(request, "pages/careers-light.html")


def contact(request):
    """Contact page with contact form - handles form submission with rate limiting and CAPTCHA."""
    import logging

    import requests
    from django.conf import settings
    from django.core.cache import cache
    from django.core.mail import send_mail

    from .forms import ContactForm

    logger = logging.getLogger(__name__)

    # Rate limiting for contact form (5 submissions per hour per IP)
    client_ip = get_client_ip(request)
    rate_limit_key = f"contact_form:{client_ip}"
    
    # Gracefully handle cache errors (e.g., if cache table doesn't exist)
    try:
        submission_count = cache.get(rate_limit_key, 0)
    except Exception as cache_error:
        logger.warning(f"Cache error in contact form: {cache_error}")
        submission_count = 0  # Fail open - allow submission if cache unavailable

    if request.method == "POST":
        # Check rate limit
        if submission_count >= 5:
            messages.error(
                request,
                "Too many submissions. Please try again later.",
            )
            logger.warning(f"Contact form rate limit exceeded for IP: {client_ip}")
            return render(
                request, "pages/contact-light.html", {"form": ContactForm(), "rate_limited": True}
            )

        form = ContactForm(request.POST)

        # Verify hCaptcha if enabled
        hcaptcha_valid = True
        if getattr(settings, "HCAPTCHA_ENABLED", False):
            hcaptcha_response = request.POST.get("h-captcha-response", "")
            if not hcaptcha_response:
                hcaptcha_valid = False
                messages.error(request, "Please complete the CAPTCHA verification.")
            else:
                try:
                    verify_response = requests.post(
                        "https://api.hcaptcha.com/siteverify",
                        data={
                            "secret": settings.HCAPTCHA_SECRET,
                            "response": hcaptcha_response,
                            "remoteip": client_ip,
                        },
                        timeout=10,
                    )
                    result = verify_response.json()
                    hcaptcha_valid = result.get("success", False)
                    if not hcaptcha_valid:
                        messages.error(request, "CAPTCHA verification failed. Please try again.")
                        logger.warning(f"hCaptcha verification failed for IP: {client_ip}")
                except Exception as e:
                    logger.error(f"hCaptcha verification error: {e}")
                    hcaptcha_valid = True  # Fail open to not block legitimate users

        if form.is_valid() and hcaptcha_valid:
            try:
                submission = form.save(commit=False)
                submission.ip_address = client_ip
                submission.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
                submission.save()

                full_message = f"""
New Contact Form Submission

From: {submission.name}
Email: {submission.email}
Subject: {submission.get_subject_display()}

Message:
{submission.message}

---
IP: {submission.ip_address}
Submitted: {submission.submitted_at}
"""
                send_mail(
                    subject=f"[InvoiceFlow Contact] {submission.get_subject_display()}",
                    message=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["support@invoiceflow.com.ng"],
                    fail_silently=True,
                )
                messages.success(
                    request,
                    "Thank you for your message! We'll get back to you within 24 hours.",
                )
                logger.info(f"Contact form submitted by {submission.email}")

                # Increment rate limit counter (gracefully handle cache errors)
                try:
                    cache.set(rate_limit_key, submission_count + 1, 3600)  # 1 hour
                except Exception:
                    pass  # Cache unavailable - continue without rate limiting

                return redirect("contact")
            except Exception as e:
                logger.error(f"Contact form submission failed: {e}")
                messages.error(
                    request,
                    "Sorry, there was an issue submitting your message. Please try again.",
                )
        else:
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        if field != "__all__":
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                        else:
                            messages.error(request, error)
    else:
        form = ContactForm()

    return render(
        request,
        "pages/contact-light.html",
        {
            "form": form,
            "hcaptcha_enabled": getattr(settings, "HCAPTCHA_ENABLED", False),
            "hcaptcha_sitekey": getattr(settings, "HCAPTCHA_SITEKEY", ""),
        },
    )


def changelog(request):
    """Changelog page with version history."""
    return render(request, "pages/changelog.html")


def system_status(request):
    """System status page showing service health."""
    return render(request, "pages/status.html")


def support(request):
    """Support/Help center page."""
    return render(request, "pages/support-light.html")


def faq(request):
    """FAQ page with common questions and answers."""
    return render(request, "pages/faq-light.html")


def terms(request):
    """Terms of Service page."""
    return render(request, "pages/terms-light.html")


def privacy(request):
    """Privacy Policy page."""
    return render(request, "pages/privacy-light.html")


def security(request):
    """Security & Trust page showcasing security practices and compliance."""
    return render(request, "pages/security.html")


def blog(request):
    """Blog listing page with articles for company credibility."""
    return render(request, "pages/blog-light.html")


def blog_article(request, slug):
    """Individual blog article page with static content."""
    articles = {
        "get-paid-faster": {
            "title": "7 Proven Strategies to Get Paid Faster by Your Clients",
            "description": "Discover actionable techniques to reduce payment delays and improve your cash flow, from invoice best practices to smart follow-up strategies.",
            "date": "December 5, 2025",
            "read_time": "8 min",
            "author": "Sarah Mitchell",
            "author_bio": "Business finance consultant with 12+ years helping freelancers and small businesses optimize their cash flow.",
            "tags": ["Cash Flow", "Tips"],
            "content": """
<p>Getting paid on time is one of the biggest challenges facing freelancers and small business owners. Late payments can seriously impact your cash flow, making it difficult to cover expenses and grow your business. Here are seven proven strategies to help you get paid faster.</p>

<h2>1. Set Clear Payment Terms Upfront</h2>
<p>Before starting any project, clearly communicate your payment terms. Include these in your contract and reiterate them on every invoice. Specify:</p>
<ul>
<li>Payment due date (e.g., Net 15 or Net 30)</li>
<li>Accepted payment methods</li>
<li>Late payment fees or interest charges</li>
<li>Any early payment discounts you offer</li>
</ul>

<h2>2. Invoice Immediately After Delivery</h2>
<p>Don't wait to send your invoice. The longer you delay, the longer you'll wait for payment. Send your invoice as soon as you complete the work or deliver the product. With InvoiceFlow, you can create and send professional invoices in under 60 seconds.</p>

<h2>3. Make It Easy to Pay</h2>
<p>Offer multiple payment options to remove friction from the payment process. Accept credit cards, bank transfers, PayPal, and other popular payment methods. The easier you make it to pay, the faster you'll receive payment.</p>

<h2>4. Send Friendly Payment Reminders</h2>
<p>Automate your follow-up process with payment reminders. Send a gentle reminder a few days before the due date, on the due date, and a follow-up if payment is late. InvoiceFlow's automated reminder feature handles this for you.</p>

<h2>5. Offer Early Payment Incentives</h2>
<p>Consider offering a small discount (2-5%) for early payment. A client who pays within 10 days instead of 30 can significantly improve your cash flow. Frame it as a benefit: "Save 2% when you pay within 10 days."</p>

<h2>6. Require Deposits for Larger Projects</h2>
<p>For substantial projects, request a deposit upfront (typically 25-50% of the total). This reduces your risk, ensures client commitment, and provides working capital to cover project costs.</p>

<h2>7. Build Strong Client Relationships</h2>
<p>Clients who value your relationship are more likely to prioritize your invoices. Provide excellent service, communicate proactively, and be professional in all interactions. Happy clients pay faster.</p>

<blockquote>The key to getting paid faster isn't just about chasing payments—it's about setting up systems that make timely payment the natural outcome.</blockquote>

<h2>Implementing These Strategies</h2>
<p>Start by reviewing your current invoicing process and identify where improvements can be made. InvoiceFlow makes it easy to implement all these strategies with professional invoice templates, automated reminders, and multiple payment options—all designed to help you get paid faster.</p>
""",
        },
        "professional-invoice-guide": {
            "title": "The Complete Guide to Creating Professional Invoices",
            "description": "Learn what makes an invoice professional, the essential elements every invoice needs, and common mistakes that can delay your payments.",
            "date": "December 1, 2025",
            "read_time": "10 min",
            "author": "James Rodriguez",
            "author_bio": "Small business advisor specializing in financial operations and bookkeeping best practices.",
            "tags": ["Invoicing", "Best Practices"],
            "content": """
<p>A professional invoice does more than request payment—it reflects your brand, builds trust, and can actually speed up how quickly you get paid. Here's everything you need to know about creating invoices that impress clients and encourage prompt payment.</p>

<h2>Essential Elements of a Professional Invoice</h2>
<p>Every invoice should include these core elements:</p>

<h3>Your Business Information</h3>
<ul>
<li><strong>Business name and logo</strong> - Consistent branding builds recognition</li>
<li><strong>Contact information</strong> - Email, phone, and address</li>
<li><strong>Tax identification number</strong> - Required in many jurisdictions</li>
</ul>

<h3>Client Information</h3>
<ul>
<li>Client's business name or individual name</li>
<li>Billing address</li>
<li>Contact person (if applicable)</li>
</ul>

<h3>Invoice Details</h3>
<ul>
<li><strong>Unique invoice number</strong> - Essential for record-keeping</li>
<li><strong>Invoice date</strong> - When the invoice was issued</li>
<li><strong>Due date</strong> - When payment is expected</li>
<li><strong>Payment terms</strong> - Net 15, Net 30, etc.</li>
</ul>

<h3>Line Items</h3>
<p>Clearly describe each product or service with:</p>
<ul>
<li>Description of work or items</li>
<li>Quantity</li>
<li>Unit price</li>
<li>Line total</li>
</ul>

<h2>Design Matters: Making Your Invoice Look Professional</h2>
<p>The visual design of your invoice communicates professionalism. Key design principles include:</p>
<ul>
<li><strong>Clean layout</strong> with clear visual hierarchy</li>
<li><strong>Consistent branding</strong> - Use your brand colors and fonts</li>
<li><strong>Readable fonts</strong> - Avoid decorative fonts for financial documents</li>
<li><strong>White space</strong> - Don't crowd information together</li>
</ul>

<h2>Common Invoice Mistakes to Avoid</h2>
<p>These mistakes can delay payment or create confusion:</p>
<ol>
<li><strong>Missing or unclear payment terms</strong> - Always specify when and how to pay</li>
<li><strong>Vague descriptions</strong> - Be specific about what you're billing for</li>
<li><strong>Math errors</strong> - Double-check all calculations</li>
<li><strong>Wrong client details</strong> - Verify names and addresses</li>
<li><strong>No payment instructions</strong> - Make it clear how to pay you</li>
</ol>

<h2>Adding Personal Touches</h2>
<p>Small details can make a big difference:</p>
<ul>
<li>Include a brief thank you note</li>
<li>Reference the specific project or purchase</li>
<li>Add your signature for a personal touch</li>
</ul>

<blockquote>A professional invoice isn't just a payment request—it's a representation of your brand and attention to detail.</blockquote>

<h2>Streamline Your Invoicing with InvoiceFlow</h2>
<p>Creating professional invoices doesn't have to be time-consuming. InvoiceFlow provides beautifully designed templates that include all essential elements, automatic calculations, and easy customization options. Spend less time on paperwork and more time on what you do best.</p>
""",
        },
        "freelance-pricing-strategies": {
            "title": "How to Set Your Freelance Rates Without Undervaluing Your Work",
            "description": "A comprehensive guide to pricing your services competitively while ensuring you're paid what you're worth in today's market.",
            "date": "November 28, 2025",
            "read_time": "12 min",
            "author": "Emma Chen",
            "author_bio": "Career coach and pricing strategist who has helped over 500 freelancers increase their income.",
            "tags": ["Business Growth", "Strategy"],
            "content": """
<p>Pricing is one of the most challenging aspects of freelancing. Set your rates too low, and you'll burn out while barely covering expenses. Set them too high without proper positioning, and you might struggle to find clients. Here's how to find the sweet spot.</p>

<h2>Understanding Your True Costs</h2>
<p>Before setting rates, you need to understand what you actually need to earn. Consider:</p>
<ul>
<li><strong>Living expenses</strong> - Rent, utilities, food, transportation</li>
<li><strong>Business expenses</strong> - Software, equipment, marketing, insurance</li>
<li><strong>Taxes</strong> - Self-employment taxes can be 25-35% of income</li>
<li><strong>Time off</strong> - Vacation, sick days, holidays (you're not billing 52 weeks/year)</li>
<li><strong>Non-billable time</strong> - Admin, marketing, learning (typically 30-50% of work time)</li>
</ul>

<h2>Calculating Your Minimum Rate</h2>
<p>Here's a simple formula to find your baseline hourly rate:</p>
<ol>
<li>Total annual income needed: $75,000</li>
<li>Add business expenses: +$15,000 = $90,000</li>
<li>Account for taxes (30%): $90,000 ÷ 0.70 = $128,571</li>
<li>Billable hours per year (20 hrs/week × 48 weeks): 960 hours</li>
<li>Minimum hourly rate: $128,571 ÷ 960 = $134/hour</li>
</ol>

<h2>Moving Beyond Hourly Rates</h2>
<p>While hourly rates are a good starting point, consider project-based or value-based pricing:</p>

<h3>Project-Based Pricing</h3>
<ul>
<li>Easier for clients to budget</li>
<li>Rewards efficiency—the faster you work, the more you earn per hour</li>
<li>Reduces scope creep concerns</li>
</ul>

<h3>Value-Based Pricing</h3>
<ul>
<li>Price based on the value you deliver to the client</li>
<li>If your work generates $100K for a client, charging $10K is reasonable</li>
<li>Requires understanding client's business and goals</li>
</ul>

<h2>Researching Market Rates</h2>
<p>Understand what others in your field charge:</p>
<ul>
<li>Join freelancer communities and forums</li>
<li>Check job postings for comparable positions</li>
<li>Use salary comparison websites</li>
<li>Ask fellow freelancers (many are willing to share)</li>
</ul>

<h2>Positioning Yourself for Higher Rates</h2>
<p>To command premium rates, focus on:</p>
<ol>
<li><strong>Specialization</strong> - Specialists earn more than generalists</li>
<li><strong>Portfolio quality</strong> - Showcase your best work prominently</li>
<li><strong>Testimonials</strong> - Social proof builds confidence</li>
<li><strong>Clear communication</strong> - Professional interactions justify professional rates</li>
<li><strong>Continuous learning</strong> - Stay current in your field</li>
</ol>

<h2>Having the Rate Conversation</h2>
<p>When discussing rates with potential clients:</p>
<ul>
<li>Be confident—don't apologize for your rates</li>
<li>Focus on value, not time</li>
<li>Have a range ready (e.g., "Projects like this typically run $5,000-8,000")</li>
<li>Be willing to walk away from poor-fit clients</li>
</ul>

<blockquote>Your rates aren't just about paying bills—they're about building a sustainable business that allows you to do your best work.</blockquote>

<h2>Raising Your Rates</h2>
<p>As you gain experience and build your reputation, gradually increase your rates:</p>
<ul>
<li>Raise rates for new clients first</li>
<li>Give existing clients advance notice (30-60 days)</li>
<li>Aim for 10-20% increases annually</li>
<li>Base increases on the value you now provide</li>
</ul>

<h2>Track Everything with InvoiceFlow</h2>
<p>Understanding your business finances is crucial for pricing decisions. InvoiceFlow helps you track revenue, analyze which services are most profitable, and ensure you're billing for all your work. Professional invoicing also reinforces your professional image—supporting your premium rates.</p>
""",
        },
    }

    article = articles.get(slug)
    if not article:
        from django.http import Http404

        raise Http404("Article not found")

    return render(request, "pages/blog_article.html", {"article": article})


def components_showcase(request):
    """Phase 1 Design System - Component showcase page."""
    return render(request, "components-showcase.html")


def offline(request):
    """Offline page for PWA support."""
    return render(request, "pages/offline.html")


def newsletter_signup(request):
    """Handle newsletter signup form submissions."""
    import logging

    from .models import Waitlist

    logger = logging.getLogger(__name__)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if email:
            try:
                waitlist_entry, created = Waitlist.objects.get_or_create(
                    email=email, defaults={"feature": "general"}
                )
                if created:
                    messages.success(
                        request,
                        "Thanks for subscribing! You'll receive updates and tips soon.",
                    )
                    logger.info(f"Newsletter signup: {email}")
                else:
                    messages.info(
                        request,
                        "You're already subscribed! We'll keep you updated.",
                    )
            except Exception as e:
                logger.error(f"Newsletter signup failed: {e}")
                messages.error(
                    request,
                    "Something went wrong. Please try again later.",
                )
        else:
            messages.error(request, "Please enter a valid email address.")

    referer = request.META.get("HTTP_REFERER", "/")
    return redirect(referer if referer else "home")


# ============================================================================
# SETTINGS PAGES
# ============================================================================


@login_required
def settings_view(request):
    """Redirect to profile settings page."""
    return redirect("settings_profile")


@login_required
def settings_profile(request):
    """Profile Information settings page."""
    from .forms import UserDetailsForm

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    message = None
    message_type = None

    if request.method == "POST":
        user_form = UserDetailsForm(request.POST, instance=request.user)

        if user_form.is_valid():
            user_form.save()
            message = "Profile information updated successfully!"
            message_type = "success"
        else:
            message = "Please fix the errors below."
            message_type = "error"
    else:
        user_form = UserDetailsForm(instance=request.user)

    context = {
        "user_form": user_form,
        "profile": profile,
        "message": message,
        "message_type": message_type,
        "active_tab": "profile",
    }

    return render(request, "pages/settings-profile.html", context)


@login_required
def settings_business(request):
    """Business Settings page."""
    from .forms import UserProfileForm

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    message = None
    message_type = None

    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if profile_form.is_valid():
            profile_form.save()
            message = "Business settings updated successfully!"
            message_type = "success"
        else:
            message = "Please fix the errors below."
            message_type = "error"
    else:
        profile_form = UserProfileForm(instance=profile)

    context = {
        "profile_form": profile_form,
        "profile": profile,
        "message": message,
        "message_type": message_type,
        "active_tab": "business",
    }

    return render(request, "pages/settings-business.html", context)


@login_required
def settings_security(request):
    """Security & Password settings page with rate limiting on password changes."""
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.hashers import check_password
    from django.core.cache import cache

    from .auth_services import AuthenticationService

    message = None
    message_type = None

    if request.method == "POST":
        client_ip = AuthenticationService.get_client_ip(request)
        cache_key = f"password_change_attempt:{client_ip}:{request.user.id}"
        attempt_count = cache.get(cache_key, 0)

        if attempt_count >= 5:
            message = "Too many password change attempts. Please try again in 1 hour."
            message_type = "error"
            password_form = PasswordChangeForm()
        else:
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                current = password_form.cleaned_data.get("current_password")
                new = password_form.cleaned_data.get("new_password")

                if not check_password(current, request.user.password):
                    cache.set(cache_key, attempt_count + 1, 3600)
                    message = "Current password is incorrect."
                    message_type = "error"
                    password_form = PasswordChangeForm()
                else:
                    cache.delete(cache_key)
                    request.user.set_password(new)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    message = "Password updated successfully!"
                    message_type = "success"
                    password_form = PasswordChangeForm()
            else:
                message = "Please fix the errors below."
                message_type = "error"
    else:
        password_form = PasswordChangeForm()

    context = {
        "password_form": password_form,
        "message": message,
        "message_type": message_type,
        "active_tab": "security",
    }

    return render(request, "pages/settings-security.html", context)


@login_required
def settings_notifications(request):
    """Email Notifications settings page."""
    from .forms import NotificationPreferencesForm

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    message = None
    message_type = None

    if request.method == "POST":
        notification_form = NotificationPreferencesForm(request.POST, instance=profile)

        if notification_form.is_valid():
            notification_form.save()
            message = "Notification preferences updated successfully!"
            message_type = "success"
        else:
            message = "Please fix the errors below."
            message_type = "error"
    else:
        notification_form = NotificationPreferencesForm(instance=profile)

    context = {
        "notification_form": notification_form,
        "profile": profile,
        "message": message,
        "message_type": message_type,
        "active_tab": "notifications",
    }

    return render(request, "pages/settings-notifications.html", context)


@login_required
def settings_payments(request):
    """Payment Settings page - configure bank account for direct payments."""
    import json
    from decimal import Decimal
    from .paystack_service import get_paystack_service
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    paystack = get_paystack_service()
    
    message = None
    message_type = None
    banks = []
    
    if paystack.is_configured:
        banks_result = paystack.list_banks()
        if banks_result.get("status") == "success":
            banks = banks_result.get("banks", [])
    
    if request.method == "POST":
        action = request.POST.get("action", "save")
        
        if action == "disable":
            profile.paystack_subaccount_active = False
            profile.paystack_subaccount_code = None
            profile.paystack_bank_code = None
            profile.paystack_account_number = None
            profile.paystack_account_name = None
            profile.paystack_settlement_bank = None
            profile.save()
            message = "Payment account removed successfully."
            message_type = "success"
        else:
            bank_code = request.POST.get("bank_code", "").strip()
            account_number = request.POST.get("account_number", "").strip()
            account_name = request.POST.get("account_name", "").strip()
            enable_direct = request.POST.get("enable_direct_payments") == "on"
            
            if not bank_code or not account_number:
                message = "Please select a bank and enter your account number."
                message_type = "error"
            elif len(account_number) != 10 or not account_number.isdigit():
                message = "Please enter a valid 10-digit account number."
                message_type = "error"
            elif not account_name:
                message = "Please verify your account before saving."
                message_type = "error"
            else:
                bank_name = ""
                for bank in banks:
                    if bank.get("code") == bank_code:
                        bank_name = bank.get("name", "")
                        break
                
                if profile.paystack_subaccount_code:
                    result = paystack.update_subaccount(
                        profile.paystack_subaccount_code,
                        business_name=profile.company_name or request.user.get_full_name() or request.user.username,
                        active=enable_direct,
                    )
                else:
                    result = paystack.create_subaccount(
                        business_name=profile.company_name or request.user.get_full_name() or request.user.username,
                        bank_code=bank_code,
                        account_number=account_number,
                        percentage_charge=Decimal("0"),
                        primary_contact_email=request.user.email,
                        primary_contact_name=request.user.get_full_name() or request.user.username,
                    )
                
                if result.get("status") == "success":
                    profile.paystack_subaccount_code = result.get("subaccount_code", profile.paystack_subaccount_code)
                    profile.paystack_bank_code = bank_code
                    profile.paystack_account_number = account_number
                    profile.paystack_account_name = account_name
                    profile.paystack_settlement_bank = bank_name
                    profile.paystack_subaccount_active = enable_direct
                    profile.save()
                    message = "Payment settings saved successfully!"
                    message_type = "success"
                else:
                    message = f"Failed to set up payment account: {result.get('message', 'Unknown error')}"
                    message_type = "error"
    
    context = {
        "profile": profile,
        "banks": banks,
        "message": message,
        "message_type": message_type,
        "active_tab": "payments",
        "paystack_configured": paystack.is_configured,
    }
    
    return render(request, "pages/settings-payments.html", context)


@login_required
def settings_billing(request):
    """Billing & Account settings page with optimized database queries."""
    from django.db.models import DecimalField, F, Sum, Value
    from django.db.models.functions import Coalesce

    now = datetime.now()
    invoices = Invoice.objects.filter(user=request.user)

    stats = invoices.aggregate(
        invoice_count=Count(
            "id", filter=Q(invoice_date__month=now.month, invoice_date__year=now.year)
        ),
        paid_invoices=Count("id", filter=Q(status="paid")),
    )

    pending_amount = LineItem.objects.filter(
        invoice__user=request.user, invoice__status="unpaid"
    ).aggregate(
        total=Coalesce(
            Sum(F("quantity") * F("unit_price")),
            Value(Decimal("0")),
            output_field=DecimalField(max_digits=15, decimal_places=2),
        )
    )[
        "total"
    ] or Decimal(
        "0"
    )

    context = {
        "active_tab": "billing",
        "invoice_count": stats["invoice_count"] or 0,
        "paid_invoices": stats["paid_invoices"] or 0,
        "pending_amount": f"${pending_amount:,.2f}" if pending_amount > 0 else "$0.00",
    }

    return render(request, "pages/settings-billing.html", context)


@login_required
def analytics(request):
    from invoices.services import AnalyticsService

    # Get optimized analytics stats
    stats = AnalyticsService.get_user_analytics_stats(request.user)
    top_clients = AnalyticsService.get_top_clients(request.user, limit=10)

    # Get monthly trend data
    invoices = Invoice.objects.filter(user=request.user)
    now = datetime.now()

    monthly_data_raw = (
        invoices.annotate(month=TruncMonth("invoice_date"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    data_by_month = {}
    for item in monthly_data_raw:
        if item["month"]:
            month_date = item["month"].date() if hasattr(item["month"], "date") else item["month"]
            key = (month_date.year, month_date.month)
            data_by_month[key] = item["count"]

    monthly_labels = []
    monthly_data = []

    for i in range(6, -1, -1):
        year = now.year
        month = now.month - i
        while month < 1:
            month += 12
            year -= 1

        month_name = calendar.month_name[month][:3] + " " + str(year)
        monthly_labels.append(month_name)

        count = data_by_month.get((year, month), 0)
        monthly_data.append(count)

    recent_invoices = invoices.prefetch_related("line_items").order_by("-created_at")[:10]

    context = {
        "total_invoices": stats["total_invoices"],
        "paid_invoices": stats["paid_invoices"],
        "unpaid_invoices": stats["unpaid_invoices"],
        "total_revenue": stats["total_revenue"],
        "outstanding_amount": stats["outstanding_amount"],
        "average_invoice": stats["average_invoice"],
        "payment_rate": stats["payment_rate"],
        "current_month_invoices": stats["current_month_invoices"],
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_data": json.dumps(monthly_data),
        "top_clients": top_clients,
        "recent_invoices": recent_invoices,
    }

    return render(request, "invoices/analytics.html", context)


# Admin Views (Production-ready admin dashboard for platform management)


def staff_member_required(view_func):
    """Decorator requiring user to be logged in and have staff access (is_active and is_staff)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect("login")
        if not (request.user.is_active and request.user.is_staff):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return wrapper


@staff_member_required
def admin_dashboard(request):
    from django.contrib.auth.models import User

    total_users = User.objects.count()
    total_invoices = Invoice.objects.count()

    # Optimize query with prefetch_related to avoid N+1
    paid_invoices_qs = Invoice.objects.filter(status="paid").prefetch_related("line_items")  # type: ignore
    total_revenue = (
        sum(inv.total for inv in paid_invoices_qs) if paid_invoices_qs.exists() else Decimal("0")
    )
    paid_invoices = paid_invoices_qs.count()
    paid_rate = (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0

    context = {
        "total_users": total_users,
        "total_invoices": total_invoices,
        "total_revenue": total_revenue,
        "paid_rate": paid_rate,
    }
    return render(request, "admin/dashboard.html", context)


@staff_member_required
def admin_users(request):
    return render(request, "admin/users.html")


@staff_member_required
def admin_content(request):
    return render(request, "admin/content.html")


@staff_member_required
def admin_settings(request):
    return render(request, "admin/settings.html")


@login_required
def profile(request):
    """User profile management view."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "invoices/profile.html", {"form": form, "profile": profile})


@login_required
def invoice_templates(request):
    """Manage invoice templates."""
    templates = InvoiceTemplate.objects.filter(user=request.user)  # type: ignore

    if request.method == "POST":
        form = InvoiceTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()
            messages.success(request, "Template created successfully!")
            return redirect("invoice_templates")
    else:
        form = InvoiceTemplateForm()

    return render(request, "invoices/templates.html", {"templates": templates, "form": form})


@login_required
def delete_template(request, template_id):
    """Delete invoice template."""
    template = get_object_or_404(InvoiceTemplate, id=template_id, user=request.user)
    template.delete()
    messages.success(request, "Template deleted successfully!")
    return redirect("invoice_templates")


@login_required
def recurring_invoices(request):
    """Manage recurring invoices."""
    recurring = RecurringInvoice.objects.filter(user=request.user)  # type: ignore

    if request.method == "POST":
        form = RecurringInvoiceForm(request.POST)
        if form.is_valid():
            rec_invoice = form.save(commit=False)
            rec_invoice.user = request.user
            rec_invoice.save()
            messages.success(request, "Recurring invoice created successfully!")
            return redirect("recurring_invoices")
    else:
        form = RecurringInvoiceForm()

    return render(
        request, "invoices/recurring.html", {"recurring_invoices": recurring, "form": form}
    )


@login_required
def bulk_export(request):
    """Export multiple invoices at once."""
    invoice_ids = request.POST.getlist("invoice_ids")
    export_format = request.POST.get("format", "csv")

    if not invoice_ids:
        messages.error(request, "Please select at least one invoice.")
        return redirect("dashboard")

    invoices = Invoice.objects.filter(id__in=invoice_ids, user=request.user).prefetch_related("line_items")  # type: ignore

    if export_format == "csv":
        csv_data = InvoiceExport.export_to_csv(invoices)
        response = HttpResponse(csv_data.encode("utf-8"), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="invoices.csv"'
        return response
    elif export_format == "pdf":
        pdfs = InvoiceExport.bulk_export_pdfs(invoices)
        if not pdfs:
            messages.error(request, "No invoices could be exported.")
            return redirect("dashboard")
        if len(pdfs) == 1:
            response = HttpResponse(pdfs[0][1], content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{pdfs[0][0]}.pdf"'
            return response
        else:
            messages.info(request, f"Exported {len(pdfs)} invoices.")
            return redirect("dashboard")

    messages.error(request, "Invalid export format.")
    return redirect("dashboard")


@login_required
def bulk_delete(request):
    """Delete multiple invoices at once."""
    if request.method == "POST":
        invoice_ids = request.POST.getlist("invoice_ids")
        if invoice_ids:
            deleted_count, _ = Invoice.objects.filter(id__in=invoice_ids, user=request.user).delete()  # type: ignore
            if deleted_count > 0:
                from invoices.services import AnalyticsService

                AnalyticsService.invalidate_user_cache(request.user.id)
            messages.success(request, f"Deleted {deleted_count} invoice(s).")
        return redirect("dashboard")
    return redirect("dashboard")


def waitlist_subscribe(request):
    """Handle email capture from Coming Soon pages and landing page."""
    from .forms import WaitlistForm

    if request.method == "POST":
        form = WaitlistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "You're on the list! We'll notify you soon.")
            return redirect(request.META.get("HTTP_REFERER", "home"))
        else:
            if (
                form.errors
                and "email" in form.errors
                and "already" in str(form.errors["email"][0]).lower()
            ):
                messages.info(request, "This email is already on our waitlist!")
            else:
                messages.error(request, "Please enter a valid email address.")
            return redirect(request.META.get("HTTP_REFERER", "home"))

    return redirect("home")


def custom_404(request, exception):
    """Custom 404 error handler."""
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    """Custom 500 error handler."""
    return render(request, "errors/500.html", status=500)


def robots_txt(request):
    """Dynamic robots.txt with proper sitemap URL."""
    scheme = request.scheme
    host = request.get_host()
    base_url = f"{scheme}://{host}"

    content = f"""User-agent: *
Allow: /
Allow: /features/
Allow: /pricing/
Allow: /about/
Allow: /contact/
Allow: /faq/
Allow: /terms/
Allow: /privacy/

Disallow: /admin/
Disallow: /settings/
Disallow: /api/
Disallow: /invoices/
Disallow: /profile/
Disallow: /recurring/
Disallow: /bulk/
Disallow: /my-templates/
Disallow: /health/
Disallow: /static/js/
Disallow: /static/css/

Sitemap: {base_url}/sitemap.xml

Crawl-delay: 1
"""
    return HttpResponse(content.encode("utf-8"), content_type="text/plain; charset=utf-8")


def service_worker(request):
    """Serve the service worker from root for proper PWA scope."""
    import os
    from django.conf import settings

    sw_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / "static", "js", "sw.js")
    
    if not os.path.exists(sw_path):
        sw_path = settings.BASE_DIR / "static" / "js" / "sw.js"
    
    try:
        with open(sw_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "// Service worker not found"
    
    response = HttpResponse(content.encode("utf-8"), content_type="application/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@login_required
def export_invoices_csv(request):
    """Export invoices to CSV format."""
    import csv
    from django.utils import timezone
    
    ids_param = request.GET.get("ids", "")
    status_filter = request.GET.get("status", "all")
    search_query = request.GET.get("search", "")
    
    invoices = Invoice.objects.filter(user=request.user).prefetch_related("line_items")
    
    if ids_param:
        invoice_ids = [int(id.strip()) for id in ids_param.split(",") if id.strip()]
        invoices = invoices.filter(id__in=invoice_ids)
    else:
        if status_filter and status_filter != "all":
            if status_filter == "overdue":
                invoices = invoices.filter(status="unpaid", due_date__lt=timezone.now().date())
            else:
                invoices = invoices.filter(status=status_filter)
        
        if search_query:
            query_filter = (
                Q(invoice_id__icontains=search_query) |  # type: ignore
                Q(client_name__icontains=search_query) |
                Q(client_email__icontains=search_query)
            )
            invoices = invoices.filter(query_filter)
    
    invoices = invoices.order_by("-created_at")
    
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="invoices_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        "Invoice ID",
        "Client Name",
        "Client Email",
        "Client Phone",
        "Invoice Date",
        "Due Date",
        "Currency",
        "Subtotal",
        "Tax Rate",
        "Tax Amount",
        "Total",
        "Status",
        "Created At",
        "Business Name",
        "Notes"
    ])
    
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_id,
            invoice.client_name,
            invoice.client_email or "",
            invoice.client_phone or "",
            invoice.invoice_date.strftime("%Y-%m-%d") if invoice.invoice_date else "",
            invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "",
            invoice.currency,
            str(invoice.subtotal),
            str(invoice.tax_rate),
            str(invoice.tax_amount),
            str(invoice.total),
            invoice.status,
            invoice.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            invoice.business_name or "",
            invoice.notes or ""
        ])
    
    return response


def public_invoice(request, invoice_id: int):
    """Display invoice publicly without authentication for payment."""
    from invoices.paystack_service import get_paystack_service
    
    invoice = get_object_or_404(Invoice.objects.prefetch_related("line_items"), id=invoice_id)
    paystack = get_paystack_service()
    payment_enabled = paystack.is_configured and invoice.user.userprofile.paystack_subaccount_active
    
    return render(request, "invoices/public_invoice.html", {
        "invoice": invoice,
        "payment_enabled": payment_enabled,
    })


def public_payment(request, invoice_id: int):
    """Initiate Paystack payment for an invoice."""
    from invoices.paystack_service import get_paystack_service
    from invoices.models import Payment
    import uuid
    
    invoice = get_object_or_404(Invoice.objects.prefetch_related("line_items"), id=invoice_id)
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        messages.error(request, "Payment gateway is not configured.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    profile = invoice.user.userprofile
    if not profile.paystack_subaccount_active:
        messages.error(request, "This invoice cannot be paid online.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    # Generate unique payment reference
    reference = f"INV{invoice.id}_{uuid.uuid4().hex[:8].upper()}"
    
    # Initialize payment with Paystack
    callback_url = request.build_absolute_uri(f"/payment-callback/?reference={reference}")
    metadata = {
        "invoice_id": invoice.id,
        "client_email": invoice.client_email,
        "business_name": invoice.business_name,
    }
    
    result = paystack.initialize_payment(
        email=invoice.client_email,
        amount=invoice.total,
        currency=invoice.currency,
        reference=reference,
        callback_url=callback_url,
        metadata=metadata,
        subaccount_code=profile.paystack_subaccount_code,
        bearer="subaccount",
    )
    
    if result.get("status") != "success":
        messages.error(request, "Could not initialize payment. Please try again.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    # Create Payment record
    Payment.objects.create(
        invoice=invoice,
        user=invoice.user,
        reference=reference,
        amount=invoice.total,
        currency=invoice.currency,
        customer_email=invoice.client_email,
        customer_name=invoice.client_name,
        status="pending",
        gateway="paystack",
        subaccount_code=profile.paystack_subaccount_code,
        metadata=metadata,
    )
    
    # Redirect to Paystack checkout
    return redirect(result["authorization_url"])


def payment_callback(request):
    """Handle Paystack payment callback."""
    from invoices.paystack_service import get_paystack_service
    from invoices.models import Payment
    
    reference = request.GET.get("reference")
    
    if not reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("invoice_list")
    
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        messages.error(request, "Payment record not found.")
        return redirect("invoice_list")
    
    paystack = get_paystack_service()
    verify_result = paystack.verify_payment(reference)
    
    if verify_result.get("status") != "success":
        payment.status = "failed"
        payment.error_message = verify_result.get("message", "Verification failed")
        payment.save()
        messages.error(request, "Payment verification failed.")
        return redirect("public_invoice", invoice_id=payment.invoice.id)
    
    if not verify_result.get("verified"):
        payment.status = "failed"
        payment.error_message = "Payment not confirmed by gateway"
        payment.save()
        messages.error(request, "Payment was not completed.")
        return redirect("public_invoice", invoice_id=payment.invoice.id)
    
    # Payment successful - update records
    payment.status = "success"
    payment.paid_at = timezone.now()
    payment.external_reference = verify_result.get("reference")
    payment.channel = verify_result.get("channel")
    payment.save()
    
    # Update invoice status
    invoice = payment.invoice
    invoice.status = "paid"
    invoice.payment_reference = reference
    invoice.save()
    
    messages.success(request, f"Payment successful! Invoice {invoice.invoice_id} has been marked as paid.")
    return redirect("public_invoice", invoice_id=invoice.id)


def payment_webhook(request):
    """Handle Paystack webhook notifications."""
    from invoices.models import Payment
    import hmac
    
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)
    
    # Verify webhook signature
    paystack_signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE", "")
    secret_key = os.environ.get("PAYSTACK_SECRET_KEY", "")
    
    if not paystack_signature or not secret_key:
        return HttpResponse("Unauthorized", status=401)
    
    body = request.body
    hash_obj = hmac.new(secret_key.encode(), body, hashlib.sha512)
    computed_signature = hash_obj.hexdigest()
    
    if computed_signature != paystack_signature:
        return HttpResponse("Unauthorized", status=401)
    
    try:
        data = json.loads(body)
        event = data.get("event")
        
        if event == "charge.success":
            reference = data["data"].get("reference")
            try:
                payment = Payment.objects.get(reference=reference)
                payment.status = "success"
                payment.paid_at = timezone.now()
                payment.save()
                
                invoice = payment.invoice
                invoice.status = "paid"
                invoice.payment_reference = reference
                invoice.save()
            except Payment.DoesNotExist:
                pass
        
        return HttpResponse("OK", status=200)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
