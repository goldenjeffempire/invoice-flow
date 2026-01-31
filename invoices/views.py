from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django_ratelimit.decorators import ratelimit
from .auth_services import AuthService, MFAService, SecurityService
from .models import UserSession, WorkspaceInvitation

def landing_view(request):
    return render(request, "pages/landing.html")

def favicon_view(request):
    return HttpResponse(status=204)

def robots_txt_view(request):
    return HttpResponse("User-agent: *\nDisallow: /admin/", content_type="text/plain")

def health_check_view(request):
    return HttpResponse("OK")

def custom_404_view(request, exception=None):
    return render(request, "404.html", status=404)

def custom_500_view(request):
    return render(request, "500.html", status=500)

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('invoices:dashboard')
    return render(request, 'pages/auth/signup.html')

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('invoices:dashboard')
    return render(request, 'pages/auth/login.html')

def logout_view(request):
    if request.user.is_authenticated:
        SecurityService.log_event(request.user, "logout", request)
    logout(request)
    return redirect('invoices:home')

@login_required
def dashboard(request):
    return render(request, 'pages/dashboard.html')

@login_required
def security_settings(request):
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    return render(request, 'pages/auth/security_settings.html', {'sessions': sessions})

@login_required
@require_POST
def revoke_session(request, session_id):
    session = get_object_or_404(UserSession, id=session_id, user=request.user)
    session.is_active = False
    session.save()
    messages.success(request, "Session revoked.")
    return redirect('invoices:security_settings')

# Empty views for other routes
def about_view(request): return render(request, "pages/about.html")
def features_view(request): return render(request, "pages/features.html")
def contact_view(request): return render(request, "pages/contact.html")
def faq_view(request): return render(request, "pages/faq.html")
def terms_view(request): return render(request, "pages/terms.html")
def privacy_view(request): return render(request, "pages/privacy.html")
def security_view(request): return render(request, "pages/security.html")
def use_cases_view(request): return render(request, "pages/use_cases.html")
def templates_view(request): return render(request, "pages/templates.html")
def integrations_view(request): return render(request, "pages/integrations.html")
def resources_view(request): return render(request, "pages/resources.html")
def verification_sent(request): return render(request, "pages/auth/verification_sent.html")
def verify_email(request, token): return render(request, "pages/auth/verify_email.html")
def resend_verification(request): return render(request, "pages/auth/resend_verification.html")
def password_reset_request(request): return render(request, "pages/auth/password_reset.html")
def password_reset_done(request): return render(request, "pages/auth/password_reset_done.html")
def password_reset_confirm(request, token): return render(request, "pages/auth/password_reset_confirm.html")
def settings_page(request): return redirect('invoices:security_settings')
def profile_update_ajax(request): return JsonResponse({"success": True})
def security_update_ajax(request): return JsonResponse({"success": True})
def notifications_update_ajax(request): return JsonResponse({"success": True})
def payment_settings_update_ajax(request): return JsonResponse({"success": True})
def reminder_dashboard(request): return render(request, "pages/reminder_settings.html")
def reminder_settings(request): return redirect('invoices:reminder_dashboard')
def track_reminder_click(request, log_id): return redirect('invoices:home')
def track_reminder_open(request, log_id): return HttpResponse(status=200)
def mfa_setup(request): return render(request, "mfa/setup.html")
def mfa_verify(request): return render(request, "mfa/verify.html")
def mfa_disable(request): return redirect('invoices:security_settings')
def mfa_backup_codes(request): return render(request, "mfa/backup_codes.html")
def security_activity(request): return render(request, "pages/auth/security_activity.html")
def accept_invitation(request, token): return render(request, "pages/auth/accept_invitation.html")
def record_engagement(request): return JsonResponse({"success": True})
def submit_feedback(request): return JsonResponse({"success": True})
def faq_api(request): return JsonResponse({"faqs": []})
def invoice_create(request): return render(request, "pages/invoice_create.html")
def invoice_detail(request, invoice_id): return render(request, "pages/invoice_detail.html")
def invoices_list(request): return render(request, "pages/invoices_list.html")
def invoice_edit(request, invoice_id): return render(request, "pages/invoice_create.html")
def invoice_delete(request, invoice_id): return redirect('invoices:invoices_list')
def invoice_pdf(request, invoice_id): return HttpResponse(status=200)
def payment_history(request): return render(request, "pages/payment_history.html")
def payment_detail(request, payment_id): return render(request, "pages/payment_detail.html")
def delete_invoice(request, invoice_id): return redirect('invoices:invoices_list')
def download_invoice_pdf(request, invoice_id): return HttpResponse(status=200)
def send_reminder(request, invoice_id): return redirect('invoices:invoice_detail', invoice_id=invoice_id)
def toggle_invoice_reminders(request, invoice_id): return redirect('invoices:invoice_detail', invoice_id=invoice_id)
def send_manual_reminder(request, invoice_id): return redirect('invoices:invoice_detail', invoice_id=invoice_id)
