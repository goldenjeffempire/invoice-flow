"""
Production-grade Settings views with comprehensive error handling and security.
"""

import logging
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.decorators import ratelimit
from django.db import transaction

from .models import UserProfile, PaymentSettings, UserSession, MFAProfile
from .settings_forms import (
    ProfileDetailsForm,
    BusinessProfileForm,
    NotificationPreferencesForm,
    PasswordChangeForm,
    PaymentSettingsForm,
)

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
def settings_dashboard(request):
    """Main settings dashboard."""
    return redirect('invoices:settings_profile')


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
@csrf_protect
def settings_profile(request):
    """User profile and personal information settings."""
    try:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            profile_form = ProfileDetailsForm(request.POST, instance=request.user)
            
            if profile_form.is_valid():
                with transaction.atomic():
                    user = profile_form.save()
                    logger.info(f'User {user.username} updated profile')
                    messages.success(request, 'Profile updated successfully.')
                return redirect('invoices:settings_profile')
            else:
                for field, errors in profile_form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            profile_form = ProfileDetailsForm(instance=request.user)

        context = {
            'active_tab': 'profile',
            'form': profile_form,
            'profile': user_profile,
        }
        return render(request, 'settings/settings_profile.html', context)
    
    except Exception as e:
        logger.exception(f'Error in settings_profile for user {request.user.username}')
        messages.error(request, 'An error occurred while loading settings.')
        return redirect('invoices:dashboard')


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
@csrf_protect
def settings_business(request):
    """Business information settings."""
    try:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            form = BusinessProfileForm(request.POST, request.FILES, instance=user_profile)
            
            if form.is_valid():
                with transaction.atomic():
                    form.save()
                    logger.info(f'User {request.user.username} updated business info')
                    messages.success(request, 'Business information updated successfully.')
                return redirect('invoices:settings_business')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = BusinessProfileForm(instance=user_profile)

        context = {
            'active_tab': 'business',
            'form': form,
            'profile': user_profile,
        }
        return render(request, 'settings/settings_business.html', context)
    
    except Exception as e:
        logger.exception(f'Error in settings_business for user {request.user.username}')
        messages.error(request, 'An error occurred while updating business settings.')
        return redirect('invoices:dashboard')


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
@csrf_protect
def settings_security(request):
    """Security settings including password change and session management."""
    try:
        mfa_profile, _ = MFAProfile.objects.get_or_create(user=request.user)
        sessions = UserSession.objects.filter(
            user=request.user,
            is_revoked=False
        ).order_by('-last_seen')[:10]
        
        # Mark current session
        for session in sessions:
            session.is_current = session.session_key == request.session.session_key
        
        password_form = None
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'change_password':
                password_form = PasswordChangeForm(request.POST)
                
                if password_form.is_valid():
                    # Verify current password
                    if not request.user.check_password(password_form.cleaned_data['current_password']):
                        messages.error(request, 'Current password is incorrect.')
                    else:
                        with transaction.atomic():
                            request.user.set_password(password_form.cleaned_data['new_password'])
                            request.user.save()
                            update_session_auth_hash(request, request.user)
                            logger.info(f'User {request.user.username} changed password')
                            messages.success(request, 'Password changed successfully.')
                        return redirect('invoices:settings_security')
                else:
                    for field, errors in password_form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
            
            elif action == 'revoke_all':
                # Revoke all other sessions
                UserSession.objects.filter(
                    user=request.user
                ).exclude(session_key=request.session.session_key).update(is_revoked=True)
                logger.info(f'User {request.user.username} revoked all sessions')
                messages.success(request, 'All other sessions have been revoked.')
                return redirect('invoices:settings_security')
        
        if not password_form:
            password_form = PasswordChangeForm()

        context = {
            'active_tab': 'security',
            'password_form': password_form,
            'mfa_profile': mfa_profile,
            'sessions': sessions,
            'session_count': sessions.count(),
        }
        return render(request, 'settings/settings_security.html', context)
    
    except Exception as e:
        logger.exception(f'Error in settings_security for user {request.user.username}')
        messages.error(request, 'An error occurred while updating security settings.')
        return redirect('invoices:dashboard')


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
@csrf_protect
def settings_notifications(request):
    """Notification preferences settings."""
    try:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            form = NotificationPreferencesForm(request.POST, instance=user_profile)
            
            if form.is_valid():
                with transaction.atomic():
                    form.save()
                    logger.info(f'User {request.user.username} updated notifications')
                    messages.success(request, 'Notification preferences updated successfully.')
                return redirect('invoices:settings_notifications')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = NotificationPreferencesForm(instance=user_profile)

        context = {
            'active_tab': 'notifications',
            'form': form,
        }
        return render(request, 'settings/settings_notifications.html', context)
    
    except Exception as e:
        logger.exception(f'Error in settings_notifications for user {request.user.username}')
        messages.error(request, 'An error occurred while updating notification settings.')
        return redirect('invoices:dashboard')


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="30/h", method="POST", block=True)
@csrf_protect
def settings_payments(request):
    """Payment settings."""
    try:
        payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            form = PaymentSettingsForm(request.POST, instance=payment_settings)
            
            if form.is_valid():
                with transaction.atomic():
                    form.save()
                    logger.info(f'User {request.user.username} updated payment settings')
                    messages.success(request, 'Payment settings updated successfully.')
                return redirect('invoices:settings_payments')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = PaymentSettingsForm(instance=payment_settings)

        context = {
            'active_tab': 'payments',
            'form': form,
            'payment_settings': payment_settings,
        }
        return render(request, 'settings/settings_payments.html', context)
    
    except Exception as e:
        logger.exception(f'Error in settings_payments for user {request.user.username}')
        messages.error(request, 'An error occurred while updating payment settings.')
        return redirect('invoices:dashboard')


@login_required
@require_POST
@ratelimit(key="user", rate="20/m", method="POST", block=True)
@csrf_protect
def revoke_session(request, session_id):
    """Revoke a specific session."""
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
        
        # Prevent revoking current session
        if session.session_key == request.session.session_key:
            messages.error(request, 'You cannot revoke your current session.')
            return redirect('invoices:settings_security')
        
        with transaction.atomic():
            session.is_revoked = True
            session.save()
            logger.info(f'User {request.user.username} revoked session {session_id}')
            messages.success(request, 'Session revoked successfully.')
        
        return redirect('invoices:settings_security')
    
    except UserSession.DoesNotExist:
        messages.error(request, 'Session not found.')
        return redirect('invoices:settings_security')
    except Exception as e:
        logger.exception(f'Error revoking session {session_id}')
        messages.error(request, 'An error occurred while revoking the session.')
        return redirect('invoices:settings_security')


# Backward compatibility redirects
@login_required
def settings_unified(request, tab="profile"):
    """Redirect to tab-specific views for backward compatibility."""
    tab_views = {
        'profile': 'invoices:settings_profile',
        'business': 'invoices:settings_business',
        'security': 'invoices:settings_security',
        'notifications': 'invoices:settings_notifications',
        'payments': 'invoices:settings_payments',
    }
    
    target = tab_views.get(tab, 'invoices:settings_profile')
    return redirect(target)
