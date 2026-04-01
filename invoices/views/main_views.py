"""
InvoiceFlow – Main Views
Rebuilt auth views: Login, Sign-Up, Logout, Password Reset, Session Management.
All other app views (landing, pages, settings, etc.) preserved.
"""
from __future__ import annotations

import logging
import os

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_GET
from django_ratelimit.decorators import ratelimit

from ..auth_services import AuthService, MFAService, SessionService, InvitationService
from ..forms import (
    LoginForm,
    SignUpForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    MFAVerifyForm,
    MFASetupVerifyForm,
    MFADisableForm,
    ResendVerificationForm,
    ChangePasswordForm,
    NewsletterSubscribeForm,
)
from ..models import MFAProfile, NewsletterSubscriber

logger = logging.getLogger(__name__)


# ============================================================================
# Utility / System Views
# ============================================================================

def landing_view(request):
    if request.user.is_authenticated:
        return redirect("invoices:dashboard")
    return render(request, "pages/landing.html")


def favicon_view(request):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="8" fill="#6366f1"/>'
        '<path d="M9 8h9l5 5v11a2 2 0 01-2 2H9a2 2 0 01-2-2V10a2 2 0 012-2z" fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M18 8v5h5" fill="none" stroke="white" stroke-width="2" stroke-linejoin="round"/>'
        '<line x1="11" y1="17" x2="21" y2="17" stroke="white" stroke-width="2" stroke-linecap="round"/>'
        '<line x1="11" y1="21" x2="17" y2="21" stroke="white" stroke-width="2" stroke-linecap="round"/>'
        '</svg>'
    )
    return HttpResponse(svg, content_type="image/svg+xml")


def robots_txt_view(request):
    return HttpResponse(b"User-agent: *\nDisallow: /admin/", content_type="text/plain")


def health_check_view(request):
    return HttpResponse(b"OK")


def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)


def custom_500_view(request):
    return render(request, "500.html", status=500)


# ============================================================================
# Authentication Views
# ============================================================================

@csrf_protect
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def signup_view(request):
    """
    User registration. On success → redirect to verification sent page.
    Email verification is required before first login.
    """
    if request.user.is_authenticated:
        return redirect("invoices:onboarding_router")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                full_name = form.cleaned_data.get("full_name", "").strip()
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                user, message = AuthService.register_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    request=request,
                )
                if user:
                    user.first_name = first_name
                    user.last_name = last_name
                    user.save(update_fields=["first_name", "last_name"])
                    request.session["pending_verify_email"] = user.email
                    return redirect("invoices:verification_sent")
                else:
                    messages.error(request, message)
            except Exception as exc:
                logger.error("Signup view error: %s", exc)
                messages.error(request, "We couldn't create your account right now. Please try again.")
    else:
        form = SignUpForm()

    return render(request, "pages/auth/signup.html", {"form": form})


@csrf_protect
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def login_view(request):
    """
    Login with email/username + password.
    Supports 'remember_me' (2-week session) and 'next' redirect.
    """
    if request.user.is_authenticated:
        return redirect("invoices:onboarding_router")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                user, message, requires_mfa = AuthService.authenticate_user(
                    request=request,
                    username_or_email=form.cleaned_data["username_or_email"],
                    password=form.cleaned_data["password"],
                )
                if user:
                    if requires_mfa:
                        request.session["pending_user_id"] = user.id
                        request.session["pending_login_remember"] = form.cleaned_data.get("remember_me", False)
                        return redirect("invoices:mfa_verify")

                    AuthService.complete_login(request, user)

                    remember = form.cleaned_data.get("remember_me", False)
                    if remember:
                        request.session.set_expiry(60 * 60 * 24 * 14)  # 2 weeks
                    else:
                        request.session.set_expiry(0)  # browser session

                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")

                    next_url = request.GET.get("next", "")
                    if next_url:
                        from django.utils.http import url_has_allowed_host_and_scheme
                        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                            return redirect(next_url)
                    return redirect("invoices:dashboard")
                else:
                    messages.error(request, message)
            except Exception as exc:
                logger.error("Login view error: %s", exc)
                messages.error(request, "Login failed. Please try again.")
    else:
        form = LoginForm()

    return render(request, "pages/auth/login.html", {"form": form, "next": request.GET.get("next", "")})


def logout_view(request):
    """
    Sign out the current user.  Accepts GET for convenience (also handles POST).
    """
    if request.user.is_authenticated:
        AuthService.logout_user(request)
        messages.info(request, "You've been signed out successfully.")
    return redirect("invoices:home")



# ============================================================================
# Password Reset
# ============================================================================

@csrf_protect
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def password_reset_request(request):
    """
    Step 1: User submits email → we send a secure 1-hour reset link.
    Always shows a success-type page to prevent user enumeration.
    """
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            AuthService.request_password_reset(
                email=form.cleaned_data["email"],
                request=request,
            )
            return redirect("invoices:password_reset_done")
    else:
        form = PasswordResetRequestForm()

    return render(request, "pages/auth/password_reset.html", {"form": form})


def password_reset_done(request):
    """Step 2: Informational page — 'check your email'."""
    return render(request, "pages/auth/password_reset_done.html")


@csrf_protect
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def password_reset_confirm(request, token):
    """
    Step 3: User clicks link in email → validate token → set new password.
    """
    is_valid, token_obj, error = AuthService.validate_reset_token(token)

    if not is_valid:
        return render(request, "pages/auth/password_reset_invalid.html", {"message": error})

    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            success, msg = AuthService.complete_password_reset(
                token=token,
                new_password=form.cleaned_data["password"],
                request=request,
            )
            if success:
                messages.success(request, msg)
                return redirect("invoices:login")
            else:
                messages.error(request, msg)
    else:
        form = PasswordResetConfirmForm()

    return render(request, "pages/auth/password_reset_confirm.html", {"form": form, "token": token})


# ============================================================================
# MFA Views (kept intact for users who have MFA enabled)
# ============================================================================

@csrf_protect
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def mfa_verify(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    pending_user_id = request.session.get("pending_user_id")
    if not pending_user_id:
        messages.error(request, "Session expired. Please sign in again.")
        return redirect("invoices:login")

    try:
        user = User.objects.get(id=pending_user_id)
    except User.DoesNotExist:
        messages.error(request, "Session expired. Please sign in again.")
        return redirect("invoices:login")

    if request.method == "POST":
        form = MFAVerifyForm(request.POST)
        if form.is_valid():
            success, message = MFAService.verify_mfa(user=user, code=form.cleaned_data["code"], request=request)
            if success:
                remember = request.session.pop("pending_login_remember", False)
                del request.session["pending_user_id"]
                AuthService.complete_login(request, user, mfa_verified=True)
                if remember:
                    request.session.set_expiry(60 * 60 * 24 * 14)
                else:
                    request.session.set_expiry(0)
                messages.success(request, "Welcome back!")
                return redirect("invoices:dashboard")
            else:
                messages.error(request, message)
    else:
        form = MFAVerifyForm()

    return render(request, "pages/auth/mfa_verify.html", {
        "form": form,
        "remaining_codes": MFAService.get_remaining_codes(user),
    })


@login_required
def mfa_setup(request):
    if MFAService.is_mfa_enabled(request.user):
        messages.info(request, "Two-factor authentication is already enabled.")
        return redirect("invoices:security_settings")

    secret = request.session.get("mfa_setup_secret")
    qr_code = request.session.get("mfa_setup_qr_code")

    if request.method == "POST":
        form = MFASetupVerifyForm(request.POST)
        if not secret:
            messages.error(request, "Setup session expired. Please try again.")
            return redirect("invoices:mfa_setup")
        if form.is_valid():
            success, backup_codes, message = MFAService.enable_mfa(
                user=request.user, secret=secret, code=form.cleaned_data["code"], request=request
            )
            if success:
                request.session.pop("mfa_setup_secret", None)
                request.session.pop("mfa_setup_qr_code", None)
                request.session["mfa_backup_codes"] = backup_codes
                messages.success(request, message)
                return redirect("invoices:mfa_backup_codes")
            else:
                messages.error(request, message)
    else:
        form = MFASetupVerifyForm()
        secret, qr_code, _ = MFAService.generate_setup_data(request.user)
        request.session["mfa_setup_secret"] = secret
        request.session["mfa_setup_qr_code"] = qr_code

    return render(request, "pages/auth/mfa_setup.html", {
        "form": form,
        "qr_code": qr_code,
        "secret": secret,
        "authenticator_apps": [
            "Google Authenticator",
            "Authy",
            "1Password",
            "Microsoft Authenticator",
            "Bitwarden",
        ],
    })


@login_required
def mfa_backup_codes(request):
    backup_codes = request.session.get("mfa_backup_codes")
    if not backup_codes:
        try:
            mfa_profile = request.user.mfa_profile
            if mfa_profile.is_enabled and not mfa_profile.recovery_codes_viewed:
                backup_codes = mfa_profile.recovery_codes
        except MFAProfile.DoesNotExist:
            pass

    if not backup_codes:
        messages.info(request, "No backup codes to display.")
        return redirect("invoices:security_settings")

    if "mfa_backup_codes" in request.session:
        del request.session["mfa_backup_codes"]
        try:
            mp = request.user.mfa_profile
            mp.recovery_codes_viewed = True
            mp.save(update_fields=["recovery_codes_viewed"])
        except MFAProfile.DoesNotExist:
            pass

    return render(request, "pages/auth/mfa_backup_codes.html", {"backup_codes": backup_codes})


@login_required
@csrf_protect
def mfa_disable(request):
    if not MFAService.is_mfa_enabled(request.user):
        messages.info(request, "Two-factor authentication is not enabled.")
        return redirect("invoices:security_settings")

    if request.method == "POST":
        form = MFADisableForm(request.POST)
        if form.is_valid():
            success, message = MFAService.disable_mfa(
                user=request.user, password=form.cleaned_data["password"], request=request
            )
            if success:
                messages.success(request, message)
                return redirect("invoices:security_settings")
            else:
                messages.error(request, message)
    else:
        form = MFADisableForm()

    return render(request, "pages/auth/mfa_disable.html", {"form": form})


# ============================================================================
# Security Settings & Session Management
# ============================================================================

@login_required
def security_settings(request):
    return redirect("/settings/#security")


@login_required
@require_POST
@csrf_protect
def revoke_session(request, session_id):
    success, message = SessionService.revoke_session(
        user=request.user, session_id=session_id, request=request
    )
    if _is_ajax(request):
        return JsonResponse({"ok": success, "message": message})
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect("invoices:security_settings")


@login_required
@require_POST
@csrf_protect
def revoke_all_sessions(request):
    success, message = SessionService.revoke_all_other_sessions(user=request.user, request=request)
    if _is_ajax(request):
        return JsonResponse({"ok": success, "message": message})
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect("invoices:security_settings")


@login_required
@require_POST
@csrf_protect
def change_password(request):
    current = request.POST.get("current_password", "")
    new_pw = request.POST.get("new_password", "")
    confirm = request.POST.get("confirm_password", "")

    if new_pw != confirm:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": "New passwords don't match."})
        messages.error(request, "New passwords don't match.")
        return redirect("invoices:security_settings")

    success, message = AuthService.change_password(
        user=request.user,
        current_password=current,
        new_password=new_pw,
        request=request,
    )
    if _is_ajax(request):
        return JsonResponse({"ok": success, "message": message})
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("invoices:security_settings")


# ============================================================================
# Invitation Acceptance
# ============================================================================

def accept_invitation(request, token):
    is_valid, invitation, error = InvitationService.validate_invitation(token)

    if not is_valid:
        return render(request, "pages/auth/invitation_invalid.html", {"message": error})

    if not request.user.is_authenticated:
        request.session["pending_invitation"] = token
        messages.info(request, "Please sign in or create an account to accept this invitation.")
        return redirect("invoices:login")

    if request.method == "POST":
        success, message = InvitationService.accept_invitation(
            token=token, user=request.user, request=request
        )
        if success:
            messages.success(request, message)
            return redirect("invoices:dashboard")
        else:
            messages.error(request, message)

    return render(request, "pages/auth/accept_invitation.html", {"invitation": invitation})


# ============================================================================
# Static / Marketing Pages
# ============================================================================

def pricing_view(request):
    starter_features = [
        "5 invoices per month",
        "2 clients",
        "Basic PDF templates",
        "Email invoicing",
        "Payment tracking",
        "Expense tracking (10/mo)",
    ]
    pro_features = [
        "Unlimited invoices",
        "Unlimited clients",
        "Premium PDF templates",
        "Automated reminders",
        "Recurring billing",
        "Estimates & quotes",
        "Client portal",
        "Expense management",
        "Analytics & reports",
        "Multi-currency",
        "Paystack & Stripe payments",
        "Priority email support",
    ]
    business_features = [
        "Everything in Pro",
        "Multiple workspaces",
        "Team members (5 seats)",
        "Advanced reporting",
        "Custom branding & logo",
        "API access",
        "Role-based permissions",
        "Bulk invoice actions",
        "CSV/PDF exports",
        "Dedicated support",
    ]
    comparison_rows = [
        {"feature": "Invoices per month", "starter": "5", "pro": "Unlimited", "business": "Unlimited"},
        {"feature": "Clients", "starter": "2", "pro": "Unlimited", "business": "Unlimited"},
        {"feature": "PDF invoice generation", "starter": True, "pro": True, "business": True},
        {"feature": "Automated payment reminders", "starter": False, "pro": True, "business": True},
        {"feature": "Recurring billing", "starter": False, "pro": True, "business": True},
        {"feature": "Estimates & quotes", "starter": False, "pro": True, "business": True},
        {"feature": "Client portal", "starter": False, "pro": True, "business": True},
        {"feature": "Expense management", "starter": "Basic", "pro": True, "business": True},
        {"feature": "Analytics & reports", "starter": False, "pro": True, "business": True},
        {"feature": "Multi-currency support", "starter": False, "pro": True, "business": True},
        {"feature": "Online payments (Stripe/Paystack)", "starter": False, "pro": True, "business": True},
        {"feature": "Multiple workspaces", "starter": False, "pro": False, "business": True},
        {"feature": "Team members", "starter": "1 user", "pro": "2 users", "business": "5 users"},
        {"feature": "Custom branding", "starter": False, "pro": True, "business": True},
        {"feature": "API access", "starter": False, "pro": False, "business": True},
        {"feature": "Priority support", "starter": False, "pro": True, "business": True},
    ]
    faqs = [
        {"question": "Is there a free trial?", "answer": "Yes! The Starter plan is free forever. Pro and Business plans include a 14-day free trial — no credit card required."},
        {"question": "Can I change plans later?", "answer": "Absolutely. You can upgrade, downgrade, or cancel at any time. When you upgrade, you're charged on a prorated basis for the remainder of your billing period."},
        {"question": "What payment methods do you accept?", "answer": "We accept all major credit and debit cards (Visa, Mastercard, Amex), and bank transfers via Paystack for Nigerian customers."},
        {"question": "Is my data secure?", "answer": "Yes. All data is encrypted in transit and at rest. We use bank-grade security, MFA authentication, and maintain strict data isolation between workspaces."},
        {"question": "Can I export my data?", "answer": "Yes, you can export your invoices, clients, and expense data as PDF or CSV at any time on all plans."},
        {"question": "Do you offer discounts for nonprofits or students?", "answer": "Yes — contact our support team with proof of eligibility and we'll apply a 30% discount to your Pro or Business plan."},
    ]
    return render(request, "pages/pricing.html", {
        "starter_features": starter_features,
        "pro_features": pro_features,
        "business_features": business_features,
        "comparison_rows": comparison_rows,
        "faqs": faqs,
    })


def about_view(request):
    return render(request, "pages/about.html")


def features_view(request):
    return render(request, "pages/features.html")


def contact_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        errors = {}
        if not first_name:
            errors["first_name"] = "First name is required."
        if not last_name:
            errors["last_name"] = "Last name is required."
        if not email:
            errors["email"] = "Email address is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."
        if not subject:
            errors["subject"] = "Please select a subject."
        if not message:
            errors["message"] = "Message cannot be empty."

        if errors:
            messages.error(request, "Please correct the errors below.")
            return render(request, "pages/contact.html", {
                "form_errors": errors,
                "form_data": request.POST,
            })

        logger.info(
            "Contact form submission from %s %s <%s> re: %s",
            first_name, last_name, email, subject,
        )
        messages.success(
            request,
            f"Thank you, {first_name}! Your message has been received. "
            "We'll get back to you within 24 hours.",
        )
        return redirect("invoices:contact")

    return render(request, "pages/contact.html")


def faq_view(request):
    return render(request, "pages/faq.html")


def terms_view(request):
    return render(request, "pages/terms.html")


def privacy_view(request):
    return render(request, "pages/privacy.html")


def security_view(request):
    if request.user.is_authenticated:
        return redirect("invoices:security_settings")
    return render(request, "pages/security.html")


def use_cases_view(request):
    return render(request, "pages/use_cases.html")


def templates_view(request):
    return render(request, "pages/templates.html")


def integrations_view(request):
    return render(request, "pages/integrations.html")


def resources_view(request):
    return render(request, "pages/resources.html")


@login_required
def settings_page(request):
    user = request.user
    profile = user.profile
    workspace = getattr(profile, 'current_workspace', None)

    mfa_enabled = False
    remaining_codes = 0
    try:
        mfa_enabled = MFAService.is_mfa_enabled(user)
        if mfa_enabled:
            remaining_codes = MFAService.get_remaining_codes(user)
    except Exception:
        pass

    from ..models import SecurityEvent
    security_events = SecurityEvent.objects.filter(user=user).order_by('-created_at')[:10]

    sessions = []
    current_session_key = request.session.session_key
    try:
        sessions = SessionService.get_user_sessions(user)
        for s in sessions:
            s.is_current = s.session_key == current_session_key
    except Exception:
        pass

    from ..models import UserProfile
    context = {
        'profile': profile,
        'workspace': workspace,
        'user': user,
        'page_title': 'Settings',
        'mfa_enabled': mfa_enabled,
        'remaining_codes': remaining_codes,
        'security_events': security_events,
        'sessions': sessions,
        'business_types': UserProfile.BUSINESS_TYPE_CHOICES,
        'invoice_styles': UserProfile.INVOICE_STYLE_CHOICES,
        'currencies': UserProfile.CURRENCY_CHOICES,
        'active_tab': request.GET.get('tab', 'profile'),
    }
    return render(request, "pages/settings.html", context)


# ============================================================================
# AJAX / API helpers (settings page)
# ============================================================================

def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _detect_image_type(header: bytes) -> str | None:
    """
    Detect image type from magic bytes — replaces the removed imghdr stdlib
    module (dropped in Python 3.13).  Returns 'jpeg', 'png', 'gif', 'webp',
    or None for unrecognised data.
    """
    if header[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if header[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None


@login_required
@require_POST
@csrf_protect
def profile_update_ajax(request):
    try:
        profile = request.user.profile
        user = request.user

        full_name = request.POST.get("full_name", "").strip()
        if not full_name:
            return JsonResponse({"success": False, "message": "Full name is required."}, status=400)
        if len(full_name) > 150:
            return JsonResponse({"success": False, "message": "Name is too long (max 150 chars)."}, status=400)

        parts = full_name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.save(update_fields=["first_name", "last_name"])

        timezone_val = request.POST.get("timezone", "").strip()
        locale_val = request.POST.get("locale", "").strip()
        if timezone_val:
            profile.timezone = timezone_val
        if locale_val:
            profile.locale = locale_val
        profile.save(update_fields=["timezone", "locale", "updated_at"])

        from ..models import SecurityEvent
        SecurityEvent.objects.create(
            user=user,
            event_type="profile_updated",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            severity="info",
            details={"fields": ["full_name", "timezone", "locale"]},
        )

        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Profile updated successfully."})
        messages.success(request, "Profile updated successfully.")
    except Exception as exc:
        logger.error("Profile update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to update profile."}, status=500)
        messages.error(request, "Failed to update profile.")
    return redirect("invoices:settings")


@login_required
@require_POST
@csrf_protect
def security_update_ajax(request):
    try:
        profile = request.user.profile
        profile.notify_security_alerts = request.POST.get("notify_security_alerts") == "on"
        profile.notify_password_changes = request.POST.get("notify_password_changes") == "on"
        profile.save(update_fields=["notify_security_alerts", "notify_password_changes"])
        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Security preferences updated."})
        messages.success(request, "Security preferences updated.")
    except Exception as exc:
        logger.error("Security update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to update security preferences."}, status=500)
        messages.error(request, "Failed to update security preferences.")
    return redirect("invoices:settings")


@login_required
@require_POST
@csrf_protect
def notifications_update_ajax(request):
    try:
        profile = request.user.profile
        profile.notify_invoice_created = request.POST.get("notify_invoice_created") == "on"
        profile.notify_payment_received = request.POST.get("notify_payment_received") == "on"
        profile.notify_invoice_viewed = request.POST.get("notify_invoice_viewed") == "on"
        profile.notify_invoice_overdue = request.POST.get("notify_invoice_overdue") == "on"
        profile.notify_weekly_summary = request.POST.get("notify_weekly_summary") == "on"
        profile.notify_security_alerts = request.POST.get("notify_security_alerts") == "on"
        profile.save(update_fields=[
            "notify_invoice_created", "notify_payment_received", "notify_invoice_viewed",
            "notify_invoice_overdue", "notify_weekly_summary", "notify_security_alerts",
        ])
        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Notification preferences saved."})
        messages.success(request, "Notification preferences updated.")
    except Exception as exc:
        logger.error("Notifications update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to save notifications."}, status=500)
    return redirect("invoices:settings")


@login_required
@require_POST
@csrf_protect
def payment_settings_update_ajax(request):
    try:
        profile = request.user.profile
        profile.accept_card_payments = request.POST.get("accept_card_payments") == "on"
        profile.accept_bank_transfers = request.POST.get("accept_bank_transfers") == "on"
        profile.accept_mobile_money = request.POST.get("accept_mobile_money") == "on"
        payment_instructions = request.POST.get("payment_instructions", "").strip()
        profile.payment_instructions = payment_instructions
        profile.save(update_fields=[
            "accept_card_payments",
            "accept_bank_transfers",
            "accept_mobile_money",
            "payment_instructions",
        ])
        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Payment settings updated."})
        messages.success(request, "Payment settings updated.")
    except Exception as exc:
        logger.error("Payment settings update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to update payment settings."}, status=500)
        messages.error(request, "Failed to update payment settings.")
    return redirect("invoices:settings")


@login_required
def reminder_dashboard(request):
    workspace = None
    if hasattr(request.user, 'profile'):
        try:
            workspace = request.user.profile.current_workspace
        except Exception:
            pass

    from ..models import Invoice, ReminderRule

    context = {'rules': ReminderRule.objects.filter(user=request.user)}

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            days = request.POST.get('days_delta', '').strip()
            trigger = request.POST.get('trigger_type', '').strip()
            if days.lstrip('-').isdigit() and trigger:
                ReminderRule.objects.create(
                    user=request.user,
                    days_delta=int(days),
                    trigger_type=trigger,
                )
                messages.success(request, 'Reminder rule created.')
            else:
                messages.error(request, 'Please fill in all required fields.')
            return redirect('invoices:reminder_dashboard')
        elif action == 'delete':
            rule_id = request.POST.get('rule_id')
            ReminderRule.objects.filter(id=rule_id, user=request.user).delete()
            messages.success(request, 'Rule deleted.')
            return redirect('invoices:reminder_dashboard')

    if workspace:
        context['overdue_count'] = Invoice.objects.filter(
            workspace=workspace, status='overdue'
        ).count()
        context['outstanding_count'] = Invoice.objects.filter(
            workspace=workspace, status__in=['sent', 'viewed', 'part_paid', 'overdue']
        ).count()
    return render(request, "pages/reminder_settings.html", context)


@login_required
def reminder_settings(request):
    return redirect("invoices:reminder_dashboard")


@login_required
def track_reminder_click(request, log_id):
    return redirect("invoices:dashboard")


@login_required
def track_reminder_open(request, log_id):
    return HttpResponse(
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;',
        content_type='image/gif'
    )


@login_required
@require_POST
@csrf_protect
def record_engagement(request):
    try:
        event = request.POST.get("event", "unknown")[:100]
        page = request.POST.get("page", "")[:200]
        logger.info("engagement event=%s page=%s user=%s", event, page, request.user.id)
    except Exception:
        pass
    return JsonResponse({"success": True})


@login_required
@require_POST
@csrf_protect
def submit_feedback(request):
    try:
        rating = request.POST.get("rating", "")
        message = request.POST.get("message", "").strip()[:2000]
        category = request.POST.get("category", "general")[:50]
        logger.info(
            "feedback user=%s rating=%s category=%s message_len=%d",
            request.user.id, rating, category, len(message)
        )
        # Store feedback in session so user gets a confirmation
        request.session["feedback_submitted"] = True
    except Exception as exc:
        logger.error("Feedback submission error: %s", exc)
    return JsonResponse({"success": True, "message": "Thank you for your feedback!"})


@login_required
@require_POST
@csrf_protect
def settings_business_update(request):
    try:
        profile = request.user.profile

        company_name       = request.POST.get('company_name', '').strip()[:255]
        business_email     = request.POST.get('business_email', '').strip()[:254]
        business_phone     = request.POST.get('business_phone', '').strip()[:50]
        business_address   = request.POST.get('business_address', '').strip()
        business_city      = request.POST.get('business_city', '').strip()[:100]
        business_state     = request.POST.get('business_state', '').strip()[:100]
        business_country   = request.POST.get('business_country', '').strip()[:100]
        business_postal_code = request.POST.get('business_postal_code', '').strip()[:20]
        business_website   = request.POST.get('business_website', '').strip()
        business_type      = request.POST.get('business_type', '').strip()
        default_currency   = request.POST.get('default_currency', '').strip()
        tax_id_number      = request.POST.get('tax_id_number', '').strip()[:50]

        if business_email:
            try:
                validate_email(business_email)
            except ValidationError:
                if _is_ajax(request):
                    return JsonResponse({"success": False, "message": "Invalid business email address."}, status=400)
                messages.error(request, "Invalid business email address.")
                return redirect("invoices:settings")

        profile.company_name         = company_name
        profile.business_email       = business_email
        profile.business_phone       = business_phone
        profile.business_address     = business_address
        profile.business_city        = business_city
        profile.business_state       = business_state
        profile.business_country     = business_country
        profile.business_postal_code = business_postal_code
        profile.business_website     = business_website
        if business_type:
            profile.business_type = business_type
        if default_currency:
            profile.default_currency = default_currency
        if tax_id_number is not None:
            profile.tax_id_number = tax_id_number
        profile.save(update_fields=[
            'company_name', 'business_email', 'business_phone', 'business_address',
            'business_city', 'business_state', 'business_country', 'business_postal_code',
            'business_website', 'business_type', 'default_currency', 'tax_id_number',
        ])

        from ..models import SecurityEvent
        SecurityEvent.objects.create(
            user=request.user,
            event_type="business_info_updated",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            severity="info",
            details={"company": company_name},
        )

        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Business information updated successfully."})
        messages.success(request, "Business information updated successfully.")
    except Exception as exc:
        logger.error("Business settings update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to update business information."}, status=500)
        messages.error(request, "Failed to update business information.")
    return redirect("invoices:settings")


@login_required
@require_POST
@csrf_protect
def settings_branding_update(request):
    try:
        profile = request.user.profile
        import re
        hex_re = re.compile(r'^#[0-9a-fA-F]{6}$')

        primary_color = request.POST.get('primary_color', '').strip()
        secondary_color = request.POST.get('secondary_color', '').strip()
        accent_color = request.POST.get('accent_color', '').strip()
        invoice_style = request.POST.get('invoice_style', '').strip()
        invoice_prefix = request.POST.get('invoice_prefix', '').strip()[:10]
        invoice_start_number = request.POST.get('invoice_start_number', '').strip()

        if primary_color and hex_re.match(primary_color):
            profile.primary_color = primary_color
        if secondary_color and hex_re.match(secondary_color):
            profile.secondary_color = secondary_color
        if accent_color and hex_re.match(accent_color):
            profile.accent_color = accent_color
        if invoice_style:
            profile.invoice_style = invoice_style
        if invoice_prefix:
            profile.invoice_prefix = invoice_prefix
        if invoice_start_number.isdigit():
            profile.invoice_start_number = int(invoice_start_number)

        profile.save(update_fields=[
            'primary_color', 'secondary_color', 'accent_color',
            'invoice_style', 'invoice_prefix', 'invoice_start_number',
        ])

        if _is_ajax(request):
            return JsonResponse({"success": True, "message": "Branding settings updated successfully."})
        messages.success(request, "Branding settings updated successfully.")
    except Exception as exc:
        logger.error("Branding settings update error: %s", exc)
        if _is_ajax(request):
            return JsonResponse({"success": False, "message": "Failed to update branding settings."}, status=500)
        messages.error(request, "Failed to update branding settings.")
    return redirect("invoices:settings")


@login_required
@require_POST
@csrf_protect
def avatar_upload(request):
    """Upload and store user profile avatar."""
    avatar_file = request.FILES.get("avatar")
    if not avatar_file:
        return JsonResponse({"success": False, "message": "No file provided."}, status=400)

    max_size = 5 * 1024 * 1024
    if avatar_file.size > max_size:
        return JsonResponse({"success": False, "message": "File too large (max 5 MB)."}, status=400)

    header = avatar_file.read(512)
    avatar_file.seek(0)
    img_type = _detect_image_type(header)
    if img_type not in ("jpeg", "png", "webp", "gif"):
        return JsonResponse({"success": False, "message": "Invalid image type. Use JPG, PNG, WebP, or GIF."}, status=400)

    from django.core.files.storage import default_storage
    from django.utils.crypto import get_random_string

    profile = request.user.profile
    ext = {"jpeg": "jpg", "png": "png", "webp": "webp", "gif": "gif"}.get(img_type, "jpg")
    filename = f"avatars/user_{request.user.pk}_{get_random_string(8)}.{ext}"

    if profile.company_logo:
        try:
            default_storage.delete(profile.company_logo.name)
        except Exception:
            pass

    saved_path = default_storage.save(filename, avatar_file)
    profile.company_logo = saved_path
    profile.save(update_fields=["company_logo"])

    avatar_url = request.build_absolute_uri(profile.company_logo.url)
    return JsonResponse({"success": True, "message": "Avatar updated.", "avatar_url": avatar_url})


@login_required
@require_POST
@csrf_protect
def email_change_request(request):
    """Change account email after password verification."""
    new_email = request.POST.get("new_email", "").strip().lower()
    current_password = request.POST.get("current_password", "")

    if not new_email:
        return JsonResponse({"success": False, "message": "New email address is required."}, status=400)

    try:
        validate_email(new_email)
    except ValidationError:
        return JsonResponse({"success": False, "message": "Please enter a valid email address."}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
        return JsonResponse({"success": False, "message": "This email address is already in use."}, status=400)

    user = authenticate(request, username=request.user.username, password=current_password)
    if user is None:
        return JsonResponse({"success": False, "message": "Current password is incorrect."}, status=403)

    old_email = request.user.email
    request.user.email = new_email
    request.user.save(update_fields=["email"])

    from ..models import SecurityEvent
    SecurityEvent.objects.create(
        user=request.user,
        event_type="email_changed",
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        severity="warning",
        details={"old_email": old_email, "new_email": new_email},
    )

    return JsonResponse({"success": True, "message": "Email address updated successfully.", "new_email": new_email})


def faq_api(request):
    faqs = [
        {
            "category": "Getting Started",
            "question": "How do I create my first invoice?",
            "answer": "Click 'New Invoice' from your dashboard or the Invoices menu. Add your client, line items, and payment details, then send it directly from InvoiceFlow.",
        },
        {
            "category": "Getting Started",
            "question": "Do I need a credit card to sign up?",
            "answer": "No. You can create a free account and start invoicing right away with no credit card required.",
        },
        {
            "category": "Payments",
            "question": "How do clients pay their invoices?",
            "answer": "Clients receive a payment link with their invoice. They can pay via card, bank transfer, or mobile money depending on the payment methods you've enabled.",
        },
        {
            "category": "Payments",
            "question": "What currencies are supported?",
            "answer": "We support NGN, USD, EUR, GBP, GHS, KES, ZAR, and more. You can set a default currency per workspace or choose per invoice.",
        },
        {
            "category": "Invoices",
            "question": "Can I set up recurring invoices?",
            "answer": "Yes. You can schedule recurring invoices to be automatically generated and sent on a daily, weekly, monthly, or custom schedule.",
        },
        {
            "category": "Invoices",
            "question": "Can I add my company logo and brand colours?",
            "answer": "Absolutely. Upload your logo and choose your brand colour in the Branding settings. Every invoice will automatically reflect your brand.",
        },
        {
            "category": "Security",
            "question": "Is my data secure?",
            "answer": "Yes. We use bank-grade TLS encryption for all data in transit and at rest. You can also enable two-factor authentication for extra security.",
        },
        {
            "category": "Billing",
            "question": "Can I export my data?",
            "answer": "Yes. You can export invoices, client lists, and payment records as CSV or PDF at any time from the Reports section.",
        },
    ]
    query = request.GET.get("q", "").lower()
    if query:
        faqs = [f for f in faqs if query in f["question"].lower() or query in f["answer"].lower()]
    return JsonResponse({"faqs": faqs})


# ============================================================================
# Email Verification
# ============================================================================

@require_GET
def verification_sent(request):
    """Show a page confirming that the verification email was sent."""
    return render(request, "pages/auth/verification_sent.html", {
        "email": request.session.get("pending_verify_email", ""),
    })


def verify_email(request, token):
    """Verify a user's email address using a signed token."""
    from ..models import EmailToken
    try:
        token_obj = EmailToken.objects.get(
            token=token,
            token_type=EmailToken.TokenType.VERIFY,
        )
    except EmailToken.DoesNotExist:
        return render(request, "pages/auth/verification_failed.html", {
            "message": "Invalid verification link. Please request a new one.",
        })

    if token_obj.used_at is not None:
        return render(request, "pages/auth/verification_failed.html", {
            "message": "This verification link has already been used.",
        })

    if token_obj.is_expired:
        return render(request, "pages/auth/verification_failed.html", {
            "message": "This verification link has expired. Please request a new one.",
        })

    user = token_obj.user
    user.is_active = True
    user.save(update_fields=["is_active"])
    token_obj.used_at = timezone.now()
    token_obj.save(update_fields=["used_at"])

    from ..models import UserProfile
    UserProfile.objects.filter(user=user).update(email_verified=True)

    messages.success(request, "Your email has been verified. You can now sign in.")
    return redirect("invoices:login")


@csrf_protect
def resend_verification(request):
    """Allow users to request a new verification email."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if email:
            from django.contrib.auth import get_user_model
            _User = get_user_model()
            try:
                user = _User.objects.get(email__iexact=email, is_active=False)
                from ..auth_services import EmailService
                EmailService.send_verification_email(user, request)
            except _User.DoesNotExist:
                pass
        messages.success(request, "If an unverified account exists with that email, we've sent a new verification link.")
        return redirect("invoices:verification_sent")
    return render(request, "pages/auth/resend_verification.html")


@login_required
def security_activity(request):
    from ..models import SecurityEvent
    events = SecurityEvent.objects.filter(user=request.user).order_by("-created_at")[:50]
    return render(request, "pages/auth/security_activity.html", {"events": events})


# ============================================================================
# Newsletter
# ============================================================================

@require_POST
@csrf_protect
@ratelimit(key="ip", rate="5/h", block=True)
def newsletter_subscribe(request):
    form = NewsletterSubscribeForm(request.POST)
    if not form.is_valid():
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
        messages.error(request, "Please enter a valid email address.")
        return redirect("invoices:home")

    email = form.cleaned_data["email"]
    first_name = form.cleaned_data.get("first_name", "")
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()

    try:
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "ip_address": ip or None,
                "source": "landing_page",
            },
        )
        if not created and subscriber.status == NewsletterSubscriber.Status.UNSUBSCRIBED:
            subscriber.status = NewsletterSubscriber.Status.ACTIVE
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=["status", "unsubscribed_at"])
            message = "Welcome back! You've been re-subscribed to our newsletter."
        elif created:
            message = "You're subscribed! Thanks for joining the InvoiceFlow community."
        else:
            message = "You're already subscribed — we'll keep you in the loop!"

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": message})
        messages.success(request, message)
    except Exception:
        logger.exception("Newsletter subscription error for %s", email)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Something went wrong. Please try again."}, status=500)
        messages.error(request, "Something went wrong. Please try again.")

    return redirect("invoices:home")
