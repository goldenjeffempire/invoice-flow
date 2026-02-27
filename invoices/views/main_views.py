"""
Production-Grade Authentication Views
Handles all authentication flows with proper security, validation, and UX.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, JsonResponse
from django_ratelimit.decorators import ratelimit

from ..auth_services import (
    AuthService, MFAService, SessionService, InvitationService,
    SecurityService
)
from ..forms import (
    SignUpForm, LoginForm, MFAVerifyForm, MFASetupVerifyForm, MFADisableForm,
    PasswordResetRequestForm, PasswordResetConfirmForm, ChangePasswordForm,
    ResendVerificationForm
)
from ..models import UserSession, WorkspaceInvitation, MFAProfile


from django.views.decorators.cache import cache_page

@cache_page(60 * 15) # Cache for 15 minutes
def landing_view(request):
    """Fast landing page - cached for 15 minutes."""
    if request.user.is_authenticated:
        return redirect('invoices:dashboard')
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


@csrf_protect
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def signup_view(request):
    """
    Production-grade signup view with:
    - Comprehensive error handling (never returns 500)
    - Graceful degradation on service failures
    - Proper user feedback for all scenarios
    """
    try:
        if request.user.is_authenticated:
            return redirect('invoices:onboarding_router')

        if request.method == 'POST':
            form = SignUpForm(request.POST)
            if form.is_valid():
                try:
                    user, message = AuthService.register_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        request=request
                    )
                    if user:
                        messages.success(request, message)
                        # Ensure absolute redirect to prevent proxy issues
                        return redirect('invoices:verification_sent')
                    else:
                        messages.error(request, message)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Signup error: {e}")
                    messages.error(request, "We couldn't create your account right now. Please try again in a moment.")
        else:
            form = SignUpForm()

        return render(request, 'pages/auth/signup.html', {'form': form})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Critical signup view error: {e}")
        messages.error(request, "Something went wrong. Please try again.")
        return render(request, 'pages/auth/signup.html', {'form': SignUpForm()})


@csrf_protect
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_view(request):
    """
    Production-grade login view with comprehensive error handling.
    """
    try:
        if request.user.is_authenticated:
            return redirect('invoices:onboarding_router')

        if request.method == 'POST':
            form = LoginForm(request.POST)
            if form.is_valid():
                try:
                    user, message, requires_mfa = AuthService.authenticate_user(
                        request=request,
                        username_or_email=form.cleaned_data['username_or_email'],
                        password=form.cleaned_data['password']
                    )

                    if user:
                        if requires_mfa:
                            request.session['pending_user_id'] = user.id
                            request.session['pending_login_remember'] = form.cleaned_data.get('remember_me', False)
                            return redirect('invoices:mfa_verify')
                        else:
                            AuthService.complete_login(request, user)

                            if not form.cleaned_data.get('remember_me'):
                                request.session.set_expiry(0)

                            messages.success(request, "Welcome back!")
                            next_url = request.GET.get('next', 'invoices:dashboard')
                            return redirect(next_url)
                    else:
                        messages.error(request, message)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Login error: {e}")
                    messages.error(request, "Login failed. Please try again.")
        else:
            form = LoginForm()

        return render(request, 'pages/auth/login.html', {'form': form})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Critical login view error: {e}")
        messages.error(request, "Something went wrong. Please try again.")
        return render(request, 'pages/auth/login.html', {'form': LoginForm()})


def logout_view(request):
    if request.user.is_authenticated:
        AuthService.logout_user(request)
    messages.info(request, "You have been logged out.")
    return redirect('invoices:home')


@login_required
def dashboard(request):
    return render(request, 'pages/dashboard.html')


@require_GET
def verification_sent(request):
    return render(request, "pages/auth/verification_sent.html")


@ratelimit(key='ip', rate='5/m', method='GET', block=True)
def verify_email(request, token):
    success, message = AuthService.verify_email(token, request)
    if success:
        from django.contrib.auth import get_user_model
        from ..models import EmailToken
        try:
            email_token = EmailToken.objects.get(token=token)
            user = email_token.user
            # Auto-login after verification for better UX
            AuthService.complete_login(request, user)
            messages.success(request, "Email verified successfully! Welcome to InvoiceFlow.")
            return redirect('invoices:onboarding_router')
        except Exception:
            messages.success(request, message)
            return redirect('invoices:login')
    else:
        return render(request, 'pages/auth/verification_failed.html', {
            'message': message,
            'can_resend': 'expired' in message.lower()
        })


@csrf_protect
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def resend_verification(request):
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            success, message = AuthService.resend_verification(
                email=form.cleaned_data['email'],
                request=request
            )
            messages.success(request, message)
            return redirect('invoices:verification_sent')
    else:
        form = ResendVerificationForm()

    return render(request, "pages/auth/resend_verification.html", {'form': form})


@csrf_protect
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            success, message = AuthService.initiate_password_reset(
                email=form.cleaned_data['email'],
                request=request
            )
            messages.success(request, message)
            return redirect('invoices:password_reset_done')
    else:
        form = PasswordResetRequestForm()

    return render(request, "pages/auth/password_reset.html", {'form': form})


def password_reset_done(request):
    return render(request, "pages/auth/password_reset_done.html")


@csrf_protect
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def password_reset_confirm(request, token):
    is_valid, token_obj, error = AuthService.validate_reset_token(token)

    if not is_valid:
        return render(request, 'pages/auth/password_reset_invalid.html', {'message': error})

    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            success, message = AuthService.complete_password_reset(
                token_str=token,
                new_password=form.cleaned_data['password'],
                request=request
            )
            if success:
                messages.success(request, message)
                return redirect('invoices:login')
            else:
                messages.error(request, message)
    else:
        form = PasswordResetConfirmForm()

    return render(request, "pages/auth/password_reset_confirm.html", {'form': form, 'token': token})


@csrf_protect
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def mfa_verify(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('invoices:login')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=pending_user_id)
    except User.DoesNotExist:
        messages.error(request, "Session expired. Please log in again.")
        return redirect('invoices:login')

    if request.method == 'POST':
        form = MFAVerifyForm(request.POST)
        if form.is_valid():
            success, message = MFAService.verify_mfa(
                user=user,
                code=form.cleaned_data['code'],
                request=request
            )
            if success:
                remember_me = request.session.pop('pending_login_remember', False)
                del request.session['pending_user_id']

                AuthService.complete_login(request, user, mfa_verified=True)

                if not remember_me:
                    request.session.set_expiry(0)

                messages.success(request, "Welcome back!")
                return redirect('invoices:dashboard')
            else:
                messages.error(request, message)
    else:
        form = MFAVerifyForm()

    remaining_codes = MFAService.get_remaining_codes(user)

    return render(request, 'pages/auth/mfa_verify.html', {
        'form': form,
        'remaining_codes': remaining_codes
    })


@login_required
def mfa_setup(request):
    if MFAService.is_mfa_enabled(request.user):
        messages.info(request, "Two-factor authentication is already enabled.")
        return redirect('invoices:security_settings')

    if request.method == 'POST':
        form = MFASetupVerifyForm(request.POST)
        secret = request.session.get('mfa_setup_secret')

        if not secret:
            messages.error(request, "Setup session expired. Please try again.")
            return redirect('invoices:mfa_setup')

        if form.is_valid():
            success, backup_codes, message = MFAService.enable_mfa(
                user=request.user,
                secret=secret,
                code=form.cleaned_data['code'],
                request=request
            )

            if success:
                del request.session['mfa_setup_secret']
                request.session['mfa_backup_codes'] = backup_codes
                messages.success(request, message)
                return redirect('invoices:mfa_backup_codes')
            else:
                messages.error(request, message)
    else:
        form = MFASetupVerifyForm()
        secret, qr_code, provisioning_uri = MFAService.generate_setup_data(request.user)
        request.session['mfa_setup_secret'] = secret

    return render(request, 'pages/auth/mfa_setup.html', {
        'form': form,
        'qr_code': qr_code if request.method == 'GET' else request.session.get('mfa_qr_code'),
        'secret': secret if request.method == 'GET' else request.session.get('mfa_setup_secret'),
    })


@login_required
def mfa_backup_codes(request):
    backup_codes = request.session.get('mfa_backup_codes')
    if not backup_codes:
        try:
            mfa_profile = request.user.mfa_profile
            if mfa_profile.is_enabled and not mfa_profile.recovery_codes_viewed:
                backup_codes = mfa_profile.recovery_codes
        except MFAProfile.DoesNotExist:
            pass

    if not backup_codes:
        messages.info(request, "No backup codes to display.")
        return redirect('invoices:security_settings')

    if 'mfa_backup_codes' in request.session:
        del request.session['mfa_backup_codes']
        try:
            mfa_profile = request.user.mfa_profile
            mfa_profile.recovery_codes_viewed = True
            mfa_profile.save(update_fields=['recovery_codes_viewed'])
        except MFAProfile.DoesNotExist:
            pass

    return render(request, 'pages/auth/mfa_backup_codes.html', {
        'backup_codes': backup_codes
    })


@login_required
@csrf_protect
def mfa_disable(request):
    if not MFAService.is_mfa_enabled(request.user):
        messages.info(request, "Two-factor authentication is not enabled.")
        return redirect('invoices:security_settings')

    if request.method == 'POST':
        form = MFADisableForm(request.POST)
        if form.is_valid():
            success, message = MFAService.disable_mfa(
                user=request.user,
                password=form.cleaned_data['password'],
                request=request
            )
            if success:
                messages.success(request, message)
                return redirect('invoices:security_settings')
            else:
                messages.error(request, message)
    else:
        form = MFADisableForm()

    return render(request, 'pages/auth/mfa_disable.html', {'form': form})


@login_required
def security_settings(request):
    sessions = SessionService.get_user_sessions(request.user)
    mfa_enabled = MFAService.is_mfa_enabled(request.user)
    remaining_codes = MFAService.get_remaining_codes(request.user) if mfa_enabled else 0

    return render(request, 'pages/auth/security_settings.html', {
        'sessions': sessions,
        'mfa_enabled': mfa_enabled,
        'remaining_codes': remaining_codes,
    })


@login_required
@require_POST
@csrf_protect
def revoke_session(request, session_id):
    success, message = SessionService.revoke_session(
        user=request.user,
        session_id=session_id,
        request=request
    )
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('invoices:security_settings')


@login_required
@require_POST
@csrf_protect
def revoke_all_sessions(request):
    success, message = SessionService.revoke_all_other_sessions(
        user=request.user,
        request=request
    )
    messages.success(request, message)
    return redirect('invoices:security_settings')


@login_required
@require_POST
@csrf_protect
def change_password(request):
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    
    if new_password != confirm_password:
        messages.error(request, "New passwords don't match.")
        return redirect('invoices:settings')
    
    if not request.user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
        return redirect('invoices:settings')
    
    success, message = AuthService.change_password(
        user=request.user,
        current_password=current_password,
        new_password=new_password,
        request=request
    )
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('invoices:settings')


@login_required
def security_activity(request):
    from ..models import SecurityEvent
    events = SecurityEvent.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'pages/auth/security_activity.html', {'events': events})


def accept_invitation(request, token):
    is_valid, invitation, error = InvitationService.validate_invitation(token)

    if not is_valid:
        return render(request, 'pages/auth/invitation_invalid.html', {'message': error})

    if not request.user.is_authenticated:
        request.session['pending_invitation'] = token
        messages.info(request, "Please log in or create an account to accept this invitation.")
        return redirect('invoices:login')

    if request.method == 'POST':
        success, message = InvitationService.accept_invitation(
            token=token,
            user=request.user,
            request=request
        )
        if success:
            messages.success(request, message)
            return redirect('invoices:dashboard')
        else:
            messages.error(request, message)

    return render(request, 'pages/auth/accept_invitation.html', {
        'invitation': invitation
    })


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
    return redirect('invoices:security_settings')


def profile_update_ajax(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.user.first_name = request.POST.get('full_name', '').split(' ')[0]
        profile.user.last_name = ' '.join(request.POST.get('full_name', '').split(' ')[1:])
        profile.user.save()
        
        profile.timezone = request.POST.get('timezone')
        profile.locale = request.POST.get('locale')
        profile.save()
        
        messages.success(request, "Profile updated successfully.")
        return redirect('invoices:settings')
    return JsonResponse({"success": True})


def security_update_ajax(request):
    return JsonResponse({"success": True})


def notifications_update_ajax(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.notify_payment_received = request.POST.get('notify_payment_received') == 'on'
        profile.notify_invoice_viewed = request.POST.get('notify_invoice_viewed') == 'on'
        profile.notify_invoice_overdue = request.POST.get('notify_invoice_overdue') == 'on'
        profile.notify_weekly_summary = request.POST.get('notify_weekly_summary') == 'on'
        profile.notify_security_alerts = request.POST.get('notify_security_alerts') == 'on'
        profile.save()
        
        messages.success(request, "Notification preferences updated.")
        return redirect('invoices:settings')
    return JsonResponse({"success": True})


def payment_settings_update_ajax(request):
    return JsonResponse({"success": True})


def reminder_dashboard(request):
    return render(request, "pages/reminder_settings.html")


def reminder_settings(request):
    return redirect('invoices:reminder_dashboard')


def track_reminder_click(request, log_id):
    return redirect('invoices:home')


def track_reminder_open(request, log_id):
    return HttpResponse(status=200)


def invoice_create(request):
    return render(request, "pages/invoice_create.html")


def invoice_detail(request, invoice_id):
    return render(request, "pages/invoice_detail.html")


def invoices_list(request):
    return render(request, "pages/invoices_list.html")


def invoice_edit(request, invoice_id):
    return render(request, "pages/invoice_create.html")


def invoice_delete(request, invoice_id):
    return redirect('invoices:invoices_list')


def invoice_pdf(request, invoice_id):
    return HttpResponse(status=200)


def payment_history(request):
    return render(request, "pages/payment_history.html")


def payment_detail(request, payment_id):
    return render(request, "pages/payment_detail.html")


def record_engagement(request):
    return JsonResponse({"success": True})


def submit_feedback(request):
    return JsonResponse({"success": True})


def faq_api(request):
    return JsonResponse({"faqs": []})
