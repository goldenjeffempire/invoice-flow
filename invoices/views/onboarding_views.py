"""
Production-Grade Onboarding Views
Stepper-based onboarding with validation, progress tracking, and smart defaults.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse

from ..services.onboarding_service import OnboardingService, ONBOARDING_STEPS
from ..models import UserProfile


@login_required
def onboarding_router(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if not profile.email_verified:
            messages.warning(request, "Please verify your email to continue.")
            return redirect('invoices:verification_sent')
        
        if profile.onboarding_completed:
            return redirect('invoices:dashboard')
        
        current_step = profile.onboarding_step
        step_url = OnboardingService.get_step_url(current_step)
        return redirect(step_url)
        
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:home')


@login_required
@csrf_protect
def onboarding_welcome(request):
    try:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'region': request.POST.get('region', 'ng'),
                'business_type': request.POST.get('business_type', 'freelancer'),
            }
            
            success, message = OnboardingService.save_welcome_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_business')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/welcome.html', {
            'state': state,
            'profile': profile,
            'regions': UserProfile.REGION_CHOICES,
            'business_types': UserProfile.BUSINESS_TYPE_CHOICES,
        })
        
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_business(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        defaults = OnboardingService.get_smart_defaults(request.user)
        
        if request.method == 'POST':
            data = {
                'company_name': request.POST.get('company_name', ''),
                'business_email': request.POST.get('business_email', request.user.email),
                'business_phone': request.POST.get('business_phone', ''),
                'business_address': request.POST.get('business_address', ''),
                'business_city': request.POST.get('business_city', ''),
                'business_state': request.POST.get('business_state', ''),
                'business_country': request.POST.get('business_country', ''),
                'business_postal_code': request.POST.get('business_postal_code', ''),
                'business_website': request.POST.get('business_website', ''),
            }
            
            success, message = OnboardingService.save_business_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_branding')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/business.html', {
            'state': state,
            'profile': profile,
            'defaults': defaults,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_branding(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'primary_color': request.POST.get('primary_color', '#6366f1'),
                'secondary_color': request.POST.get('secondary_color', '#8b5cf6'),
                'accent_color': request.POST.get('accent_color', '#10b981'),
                'invoice_style': request.POST.get('invoice_style', 'modern'),
            }
            
            success, message = OnboardingService.save_branding_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_tax')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/branding.html', {
            'state': state,
            'profile': profile,
            'styles': UserProfile.INVOICE_STYLE_CHOICES,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_tax(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'tax_id_number': request.POST.get('tax_id_number', ''),
                'tax_id_type': request.POST.get('tax_id_type', ''),
                'vat_registered': request.POST.get('vat_registered') == 'on',
                'vat_number': request.POST.get('vat_number', ''),
                'vat_rate': request.POST.get('vat_rate', '0'),
                'wht_applicable': request.POST.get('wht_applicable') == 'on',
                'wht_rate': request.POST.get('wht_rate', '0'),
            }
            
            success, message = OnboardingService.save_tax_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_payments')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/tax.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_payments(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'bank_name': request.POST.get('bank_name', ''),
                'bank_account_name': request.POST.get('bank_account_name', ''),
                'bank_account_number': request.POST.get('bank_account_number', ''),
                'bank_routing_number': request.POST.get('bank_routing_number', ''),
                'bank_swift_code': request.POST.get('bank_swift_code', ''),
                'accept_card_payments': request.POST.get('accept_card_payments') == 'on',
                'accept_bank_transfers': request.POST.get('accept_bank_transfers', 'on') == 'on',
                'accept_mobile_money': request.POST.get('accept_mobile_money') == 'on',
                'payment_instructions': request.POST.get('payment_instructions', ''),
            }
            
            success, message = OnboardingService.save_payments_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_import')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/payments.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_import(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'skip_import': request.POST.get('skip_import') == 'on',
            }
            
            success, message = OnboardingService.save_import_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_templates')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/import.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_templates(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'invoice_prefix': request.POST.get('invoice_prefix', 'INV'),
                'invoice_start_number': request.POST.get('invoice_start_number', '1'),
                'invoice_numbering_format': request.POST.get('invoice_numbering_format', '{prefix}-{year}-{number:04d}'),
            }
            
            success, message = OnboardingService.save_templates_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_team')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/templates.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_team(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            data = {
                'skip_team': request.POST.get('skip_team') == 'on',
            }
            
            success, message = OnboardingService.save_team_step(request.user, data)
            
            if success:
                return redirect('invoices:onboarding_complete')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/team.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@csrf_protect
def onboarding_complete(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        state = OnboardingService.get_onboarding_state(request.user)
        
        if request.method == 'POST':
            success, message = OnboardingService.complete_onboarding(request.user)
            
            if success:
                messages.success(request, message)
                return redirect('invoices:dashboard')
            else:
                messages.error(request, message)
        
        return render(request, 'pages/onboarding/complete.html', {
            'state': state,
            'profile': profile,
        })
        
    except UserProfile.DoesNotExist:
        return redirect('invoices:onboarding_router')
    except Exception as e:
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('invoices:onboarding_router')


@login_required
@require_POST
@csrf_protect
def onboarding_skip_step(request):
    try:
        success, message, new_step = OnboardingService.skip_step(request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success, 'message': message, 'new_step': new_step})
        
        step_url = OnboardingService.get_step_url(new_step)
        return redirect(step_url)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Failed to skip step.'})
        return redirect('invoices:onboarding_router')


@login_required
@require_POST
@csrf_protect
def onboarding_go_back(request):
    try:
        success, message, new_step = OnboardingService.go_back(request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success, 'message': message, 'new_step': new_step})
        
        step_url = OnboardingService.get_step_url(new_step)
        return redirect(step_url)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Failed to go back.'})
        return redirect('invoices:onboarding_router')
