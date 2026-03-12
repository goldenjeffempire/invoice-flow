"""
InvoiceFlow – Main Views
Rebuilt auth views: Login, Sign-Up, Logout, Password Reset, Session Management.
All other app views (landing, pages, settings, etc.) preserved.
"""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
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

@cache_page(60 * 15)
def landing_view(request):
    if request.user.is_authenticated:
        return redirect("invoices:dashboard")
    return render(request, "pages/landing.html")


def favicon_view(request):
    return HttpResponse(status=204)


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
    User registration. On success → auto-login and redirect to onboarding.
    No email verification required.
    """
    if request.user.is_authenticated:
        return redirect("invoices:onboarding_router")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                # Split full_name into first/last for the User model
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
                    # Persist first/last name
                    user.first_name = first_name
                    user.last_name = last_name
                    user.save(update_fields=["first_name", "last_name"])

                    AuthService.complete_login(request, user)
                    messages.success(request, f"Welcome to InvoiceFlow, {first_name}!")
                    return redirect("invoices:onboarding_router")
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
                    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
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


@login_required
def dashboard(request):
    return render(request, "pages/dashboard.html")


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

    return render(request, "pages/auth/mfa_setup.html", {"form": form, "qr_code": qr_code, "secret": secret})


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
    sessions = SessionService.get_user_sessions(request.user)
    mfa_enabled = MFAService.is_mfa_enabled(request.user)
    remaining_codes = MFAService.get_remaining_codes(request.user) if mfa_enabled else 0

    # Mark current session
    current_key = request.session.session_key
    for s in sessions:
        s.is_current = s.session_key == current_key

    return render(request, "pages/auth/security_settings.html", {
        "sessions": sessions,
        "mfa_enabled": mfa_enabled,
        "remaining_codes": remaining_codes,
    })


@login_required
@require_POST
@csrf_protect
def revoke_session(request, session_id):
    success, message = SessionService.revoke_session(
        user=request.user, session_id=session_id, request=request
    )
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
        messages.error(request, "New passwords don't match.")
        return redirect("invoices:security_settings")

    success, message = AuthService.change_password(
        user=request.user,
        current_password=current,
        new_password=new_pw,
        request=request,
    )
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

def about_view(request):
    return render(request, "pages/about.html")


def features_view(request):
    return render(request, "pages/features.html")


def contact_view(request):
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


def settings_page(request):
    return redirect("invoices:security_settings")


# ============================================================================
# AJAX / API helpers (settings page)
# ============================================================================

@login_required
def profile_update_ajax(request):
    if request.method == "POST":
        try:
            profile = request.user.profile
            full_name = request.POST.get("full_name", "").strip()
            if full_name:
                parts = full_name.split(" ", 1)
                request.user.first_name = parts[0]
                request.user.last_name = parts[1] if len(parts) > 1 else ""
                request.user.save(update_fields=["first_name", "last_name"])

            timezone_val = request.POST.get("timezone")
            locale_val = request.POST.get("locale")
            if timezone_val:
                profile.timezone = timezone_val
            if locale_val:
                profile.locale = locale_val
            profile.save()
            messages.success(request, "Profile updated successfully.")
        except Exception as exc:
            logger.error("Profile update error: %s", exc)
            messages.error(request, "Failed to update profile.")
        return redirect("invoices:settings")
    return JsonResponse({"success": True})


def security_update_ajax(request):
    return JsonResponse({"success": True})


@login_required
def notifications_update_ajax(request):
    if request.method == "POST":
        try:
            profile = request.user.profile
            profile.notify_payment_received = request.POST.get("notify_payment_received") == "on"
            profile.notify_invoice_viewed = request.POST.get("notify_invoice_viewed") == "on"
            profile.notify_invoice_overdue = request.POST.get("notify_invoice_overdue") == "on"
            profile.notify_weekly_summary = request.POST.get("notify_weekly_summary") == "on"
            profile.notify_security_alerts = request.POST.get("notify_security_alerts") == "on"
            profile.save()
            messages.success(request, "Notification preferences updated.")
        except Exception as exc:
            logger.error("Notifications update error: %s", exc)
        return redirect("invoices:settings")
    return JsonResponse({"success": True})


def payment_settings_update_ajax(request):
    return JsonResponse({"success": True})


def reminder_dashboard(request):
    return render(request, "pages/reminder_settings.html")


def reminder_settings(request):
    return redirect("invoices:reminder_dashboard")


def track_reminder_click(request, log_id):
    return redirect("invoices:home")


def track_reminder_open(request, log_id):
    return HttpResponse(status=200)


def record_engagement(request):
    return JsonResponse({"success": True})


def submit_feedback(request):
    return JsonResponse({"success": True})


def faq_api(request):
    return JsonResponse({"faqs": []})


# ============================================================================
# Legacy email verification stubs
# (redirected to login — email verification not required in this system)
# ============================================================================

@require_GET
def verification_sent(request):
    """Kept for URL backward-compat; redirect to login."""
    return redirect("invoices:login")


def verify_email(request, token):
    """Legacy route — redirect to login."""
    return redirect("invoices:login")


@csrf_protect
def resend_verification(request):
    """Legacy route — redirect to login."""
    return redirect("invoices:login")


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
