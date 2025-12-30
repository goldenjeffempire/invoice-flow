import logging
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit

from .forms import (
    UserDetailsForm,
    UserProfileForm,
    PaymentSettingsForm,
    NotificationPreferencesForm,
    PasswordChangeForm,
)
from .models import UserProfile, PaymentSettings, UserSession

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def settings_unified(request, tab="profile"):
    """Unified settings dashboard handling all user configurations."""
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
    
    # Initialize all forms
    user_form = UserDetailsForm(instance=request.user)
    profile_form = UserProfileForm(instance=user_profile)
    business_form = UserProfileForm(instance=user_profile, prefix="business")
    payment_form = PaymentSettingsForm(instance=payment_settings)
    notification_form = NotificationPreferencesForm(instance=user_profile)
    password_form = PasswordChangeForm()

    if request.method == "POST":
        active_tab = request.POST.get("active_tab", tab)
        
        if active_tab == "profile":
            user_form = UserDetailsForm(request.POST, instance=request.user)
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("invoices:settings_tab", tab="profile")
                
        elif active_tab == "business":
            business_form = UserProfileForm(request.POST, request.FILES, instance=user_profile, prefix="business")
            if business_form.is_valid():
                business_form.save()
                messages.success(request, "Business settings updated successfully.")
                return redirect("invoices:settings_tab", tab="business")
                
        elif active_tab == "security":
            if "current_password" in request.POST:
                password_form = PasswordChangeForm(request.POST)
                if password_form.is_valid():
                    request.user.set_password(password_form.cleaned_data["new_password"])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password changed successfully.")
                    return redirect("invoices:settings_tab", tab="security")
            
            if request.POST.get("revoke_all"):
                UserSession.objects.filter(user=request.user).exclude(
                    session_key=request.session.session_key
                ).delete()
                messages.success(request, "Logged out from all other devices.")
                return redirect("invoices:settings_tab", tab="security")

        elif active_tab == "payments":
            payment_form = PaymentSettingsForm(request.POST, instance=payment_settings)
            if payment_form.is_valid():
                payment_form.save()
                messages.success(request, "Payment settings updated successfully.")
                return redirect("invoices:settings_tab", tab="payments")

        elif active_tab == "notifications":
            notification_form = NotificationPreferencesForm(request.POST, instance=user_profile)
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, "Notification preferences updated.")
                return redirect("invoices:settings_tab", tab="notifications")

    # Fetch sessions for security tab
    sessions = UserSession.objects.filter(user=request.user).order_by("-created_at")[:5]
    for session in sessions:
        session.is_current = session.session_key == request.session.session_key

    context = {
        "active_tab": tab,
        "user_form": user_form,
        "profile_form": profile_form,
        "business_form": business_form,
        "payment_form": payment_form,
        "notification_form": notification_form,
        "password_form": password_form,
        "sessions": sessions,
        "profile": user_profile,
    }
    return render(request, "pages/settings-unified.html", context)

@login_required
def settings_dashboard(request):
    """Main settings dashboard - redirect to profile settings."""
    return redirect("invoices:settings_tab", tab="profile")

@login_required
def profile(request):
    """User profile management - redirects to settings profile."""
    return redirect("invoices:settings_tab", tab="profile")

@login_required
def settings_profile(request):
    return redirect("invoices:settings_tab", tab="profile")

@login_required
def settings_business(request):
    return redirect("invoices:settings_tab", tab="business")

@login_required
def settings_payments(request):
    return redirect("invoices:settings_tab", tab="payments")

@login_required
def settings_security(request):
    return redirect("invoices:settings_tab", tab="security")

@login_required
def settings_notifications(request):
    return redirect("invoices:settings_tab", tab="notifications")

@login_required
def settings_billing(request):
    return redirect("invoices:settings_tab", tab="billing")

@login_required
@require_POST
def revoke_session(request, session_id):
    return redirect("invoices:settings_tab", tab="security")

@login_required
@require_POST
def revoke_all_sessions(request):
    return redirect("invoices:settings_tab", tab="security")
