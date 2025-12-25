"""
Unified Settings Views for InvoiceFlow.
Handles all user settings: profile, business, payments, security, notifications, billing.
"""

import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import (
    UserDetailsForm,
    UserProfileForm,
    PaymentSettingsForm,
    NotificationPreferencesForm,
)
from .models import UserProfile, PaymentSettings, UserSession

logger = logging.getLogger(__name__)


@login_required
@require_GET
def settings_dashboard(request):
    """Main settings dashboard - redirect to profile settings."""
    return redirect("invoices:settings_profile")


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_profile(request):
    """Profile settings: personal information and account details."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        user_form = UserDetailsForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("invoices:settings_profile")
    else:
        user_form = UserDetailsForm(instance=request.user)
        profile_form = UserProfileForm(instance=user_profile)
    
    context = {
        "section": "profile",
        "user_form": user_form,
        "profile_form": profile_form,
        "profile": user_profile,
    }
    return render(request, "pages/settings-profile.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_business(request):
    """Business settings: company details, invoice preferences."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Business settings updated successfully.")
            return redirect("invoices:settings_business")
    else:
        form = UserProfileForm(instance=user_profile)
    
    context = {
        "section": "business",
        "form": form,
        "profile": user_profile,
    }
    return render(request, "pages/settings-business.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_payments(request):
    """Payment settings: payment methods, payouts, recipients."""
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = PaymentSettingsForm(request.POST, instance=payment_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment settings updated successfully.")
            return redirect("invoices:settings_payments")
    else:
        form = PaymentSettingsForm(instance=payment_settings)
    
    context = {
        "section": "payments",
        "form": form,
        "payment_settings": payment_settings,
        "profile": user_profile,
    }
    return render(request, "pages/settings-payments.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_security(request):
    """Security settings: password, MFA, sessions, login activity."""
    from django.contrib.auth import update_session_auth_hash
    
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        # Handle password change
        if "current_password" in request.POST:
            current_password = request.POST.get("current_password", "").strip()
            new_password = request.POST.get("new_password", "").strip()
            confirm_password = request.POST.get("confirm_password", "").strip()
            
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif len(new_password) < 12:
                messages.error(request, "Password must be at least 12 characters long.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password changed successfully.")
                logger.info(f"Password changed for user: {request.user.username}")
        
        # Handle logout all sessions
        if request.POST.get("logout_all") == "true":
            current_session = request.session.session_key
            sessions_to_revoke = UserSession.objects.filter(user=request.user).exclude(
                session_key=current_session
            )
            sessions_to_revoke.delete()
            messages.success(request, "Logged out from all other devices.")
        
        # Handle logout single session
        if "logout_session_id" in request.POST:
            session_id = request.POST.get("logout_session_id")
            try:
                session = UserSession.objects.get(id=session_id, user=request.user)
                session.delete()
                messages.success(request, "Session terminated.")
            except UserSession.DoesNotExist:
                messages.error(request, "Session not found.")
    
    sessions = UserSession.objects.filter(user=request.user).order_by("-created_at")[:10]
    current_session_key = request.session.session_key
    
    # Mark current session
    for session in sessions:
        session.is_current = session.session_key == current_session_key
    
    context = {
        "section": "security",
        "profile": user_profile,
        "sessions": sessions,
    }
    return render(request, "pages/settings-security.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_notifications(request):
    """Notification settings: email preferences, alert configuration."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = NotificationPreferencesForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated successfully.")
            return redirect("invoices:settings_notifications")
    else:
        form = NotificationPreferencesForm(instance=user_profile)
    
    context = {
        "section": "notifications",
        "form": form,
        "profile": user_profile,
    }
    return render(request, "pages/settings-notifications.html", context)


@login_required
@require_GET
def settings_billing(request):
    """Billing settings: subscription, invoices, payment history."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        "section": "billing",
        "profile": user_profile,
    }
    return render(request, "pages/settings-billing.html", context)


@login_required
@require_POST
@ratelimit(key="user", rate="5/h", method="POST", block=True)
def revoke_session(request, session_id):
    """Revoke a user session (sign out from another device)."""
    session = get_object_or_404(UserSession, id=session_id, user=request.user)
    session.revoke()
    messages.success(request, "Session revoked successfully.")
    return redirect("invoices:settings_security")


@login_required
@require_POST
@ratelimit(key="user", rate="5/h", method="POST", block=True)
def revoke_all_sessions(request):
    """Revoke all sessions except current one."""
    current_session = request.session.session_key
    sessions = UserSession.objects.filter(user=request.user).exclude(session_key=current_session)
    
    for session in sessions:
        session.revoke()
    
    messages.success(request, "All other sessions have been revoked.")
    return redirect("invoices:settings_security")


@login_required
def profile(request):
    """User profile management - redirects to settings profile."""
    return redirect("invoices:settings_profile")
