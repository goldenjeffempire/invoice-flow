import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ..models import UserProfile
from ..services.onboarding_service import OnboardingService

logger = logging.getLogger(__name__)


def get_common_context(request):
    profile = request.user.profile
    return {
        "user": request.user,
        "profile": profile,
        "onboarding_status": OnboardingService.get_onboarding_status(request.user),
        "step_title": "Setup",
    }


@login_required
def onboarding_router(request):
    profile = request.user.profile
    if profile.onboarding_completed:
        return redirect("invoices:dashboard")
    
    step = profile.onboarding_step
    step_routes = {
        1: "invoices:onboarding_welcome",
        2: "invoices:onboarding_business",
        3: "invoices:onboarding_branding",
        4: "invoices:onboarding_tax",
        5: "invoices:onboarding_payments",
        6: "invoices:onboarding_import",
        7: "invoices:onboarding_templates",
        8: "invoices:onboarding_team",
    }
    
    route = step_routes.get(step, "invoices:onboarding_welcome")
    return redirect(route)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_welcome(request):
    OnboardingService.start_onboarding(request.user)
    
    if request.method == "POST":
        data = {
            "region": request.POST.get("region", ""),
        }
        success, message, errors = OnboardingService.save_welcome_step(request.user, data)
        if success:
            return redirect("invoices:onboarding_business")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Welcome",
        "regions": UserProfile.REGION_CHOICES,
    })
    return render(request, "pages/onboarding/welcome.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_business(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "company_name": request.POST.get("company_name", ""),
            "business_type": request.POST.get("business_type", ""),
            "business_email": request.POST.get("business_email", ""),
            "business_phone": request.POST.get("business_phone", ""),
            "business_address": request.POST.get("business_address", ""),
            "business_city": request.POST.get("business_city", ""),
            "business_state": request.POST.get("business_state", ""),
            "business_country": request.POST.get("business_country", ""),
            "business_postal_code": request.POST.get("business_postal_code", ""),
            "business_website": request.POST.get("business_website", ""),
            "region": request.POST.get("region", ""),
        }
        success, message, errors = OnboardingService.save_business_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_branding")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Business Profile",
        "regions": UserProfile.REGION_CHOICES,
        "business_types": UserProfile.BUSINESS_TYPE_CHOICES,
        "errors": errors,
    })
    return render(request, "pages/onboarding/business_profile.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_branding(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "primary_color": request.POST.get("primary_color", ""),
            "secondary_color": request.POST.get("secondary_color", ""),
            "accent_color": request.POST.get("accent_color", ""),
            "invoice_style": request.POST.get("invoice_style", ""),
        }
        logo_file = request.FILES.get("company_logo")
        success, message, errors = OnboardingService.save_branding_step(request.user, data, logo_file)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_tax")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Branding",
        "invoice_styles": UserProfile.INVOICE_STYLE_CHOICES,
        "errors": errors,
    })
    return render(request, "pages/onboarding/branding.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_tax(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "tax_id_type": request.POST.get("tax_id_type", ""),
            "tax_id_number": request.POST.get("tax_id_number", ""),
            "vat_registered": request.POST.get("vat_registered"),
            "vat_number": request.POST.get("vat_number", ""),
            "vat_rate": request.POST.get("vat_rate", "0"),
            "wht_applicable": request.POST.get("wht_applicable"),
            "wht_rate": request.POST.get("wht_rate", "0"),
            "default_tax_rate": request.POST.get("default_tax_rate", "0"),
        }
        success, message, errors = OnboardingService.save_tax_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_payments")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Tax & Compliance",
        "errors": errors,
    })
    return render(request, "pages/onboarding/tax_compliance.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_payments(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "accept_bank_transfers": request.POST.get("accept_bank_transfers"),
            "accept_card_payments": request.POST.get("accept_card_payments"),
            "accept_mobile_money": request.POST.get("accept_mobile_money"),
            "bank_name": request.POST.get("bank_name", ""),
            "bank_account_name": request.POST.get("bank_account_name", ""),
            "bank_account_number": request.POST.get("bank_account_number", ""),
            "bank_routing_number": request.POST.get("bank_routing_number", ""),
            "bank_swift_code": request.POST.get("bank_swift_code", ""),
            "payment_instructions": request.POST.get("payment_instructions", ""),
        }
        success, message, errors = OnboardingService.save_payments_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_import")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Payments",
        "errors": errors,
    })
    return render(request, "pages/onboarding/payments.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_import(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "skip_import": request.POST.get("skip_import"),
            "import_customers": request.POST.get("import_customers"),
            "import_products": request.POST.get("import_products"),
            "import_invoices": request.POST.get("import_invoices"),
        }
        success, message, errors = OnboardingService.save_import_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_templates")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Data Import",
        "errors": errors,
    })
    return render(request, "pages/onboarding/data_import.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_templates(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "invoice_style": request.POST.get("invoice_style", ""),
            "invoice_prefix": request.POST.get("invoice_prefix", ""),
            "invoice_start_number": request.POST.get("invoice_start_number", "1"),
            "default_currency": request.POST.get("default_currency", ""),
            "date_format": request.POST.get("date_format", ""),
        }
        success, message, errors = OnboardingService.save_templates_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_team")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Templates",
        "invoice_styles": UserProfile.INVOICE_STYLE_CHOICES,
        "currencies": UserProfile.CURRENCY_CHOICES,
        "current_year": datetime.now().year,
        "errors": errors,
    })
    return render(request, "pages/onboarding/template_selection.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def onboarding_team(request):
    errors = {}
    
    if request.method == "POST":
        data = {
            "skip_invites": request.POST.get("skip_invites"),
            "team_emails": request.POST.get("team_emails", ""),
        }
        success, message, errors = OnboardingService.save_team_step(request.user, data)
        if success:
            messages.success(request, message)
            return redirect("invoices:onboarding_complete")
    
    context = get_common_context(request)
    context.update({
        "step_title": "Team",
        "errors": errors,
    })
    return render(request, "pages/onboarding/team_invites.html", context)


@login_required
def onboarding_complete(request):
    profile = request.user.profile
    
    time_to_setup = None
    if profile.onboarding_started_at and profile.onboarding_completed_at:
        delta = profile.onboarding_completed_at - profile.onboarding_started_at
        time_to_setup = int(delta.total_seconds() / 60)
    
    return render(request, "pages/onboarding/complete.html", {
        "user": request.user,
        "profile": profile,
        "time_to_setup": time_to_setup,
    })


@login_required
def onboarding_status_api(request):
    status = OnboardingService.get_onboarding_status(request.user)
    checklist = OnboardingService.get_checklist(request.user)
    return JsonResponse({
        "status": status,
        "checklist": checklist,
    })
