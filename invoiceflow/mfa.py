"""
MFA (Multi-Factor Authentication) Views and Utilities for InvoiceFlow.
Provides TOTP-based two-factor authentication.
"""

import base64
import io
import secrets
import logging

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from invoices.models import MFAProfile

logger = logging.getLogger(__name__)


def require_mfa(user):
    """
    Enforce MFA at service / business-logic level.
    """
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")

    mfa_profile = getattr(user, "mfa_profile", None)

    if not mfa_profile or not mfa_profile.is_enabled:
        raise PermissionDenied("Multi-factor authentication required")


def generate_secret():
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def generate_qr_code(user, secret):
    """Generate a QR code for TOTP setup."""
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="InvoiceFlow"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_recovery_codes(count=10):
    """Generate recovery codes for MFA backup."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def verify_totp(secret, code):
    """Verify a TOTP code against the secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


@login_required
def mfa_setup(request):
    """
    MFA setup view - GET shows QR code, POST enables MFA.
    """
    mfa_profile, created = MFAProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        secret = request.session.get("mfa_setup_secret")
        
        if not secret:
            messages.error(request, "Session expired. Please start MFA setup again.")
            return redirect("mfa_setup")
        
        if verify_totp(secret, code):
            recovery_codes = generate_recovery_codes()
            mfa_profile.secret = secret
            mfa_profile.is_enabled = True
            mfa_profile.recovery_codes = recovery_codes
            mfa_profile.save()
            
            del request.session["mfa_setup_secret"]
            
            messages.success(request, "Two-factor authentication has been enabled.")
            
            return render(request, "mfa/setup_complete.html", {
                "recovery_codes": recovery_codes
            })
        else:
            messages.error(request, "Invalid verification code. Please try again.")
            return redirect("mfa_setup")
    
    secret = generate_secret()
    request.session["mfa_setup_secret"] = secret
    qr_code = generate_qr_code(request.user, secret)
    
    return render(request, "mfa/setup.html", {
        "qr_code": qr_code,
        "secret": secret,
        "is_enabled": mfa_profile.is_enabled,
    })


@login_required
@require_POST
def mfa_verify(request):
    """
    Verify MFA code during login or sensitive operations.
    """
    code = request.POST.get("code", "").strip()
    
    try:
        mfa_profile = MFAProfile.objects.get(user=request.user)
    except MFAProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "MFA not configured"}, status=400)
    
    if not mfa_profile.is_enabled:
        return JsonResponse({"success": False, "error": "MFA not enabled"}, status=400)
    
    if verify_totp(mfa_profile.secret, code):
        request.session["mfa_verified"] = True
        return JsonResponse({"success": True})
    
    if mfa_profile.recovery_codes and code.upper() in [c.upper() for c in mfa_profile.recovery_codes]:
        mfa_profile.recovery_codes.remove(code.upper())
        mfa_profile.save()
        request.session["mfa_verified"] = True
        return JsonResponse({"success": True, "used_recovery": True})
    
    return JsonResponse({"success": False, "error": "Invalid code"}, status=400)


@login_required
@require_POST
def mfa_disable(request):
    """
    Disable MFA for the current user.
    """
    code = request.POST.get("code", "").strip()
    
    try:
        mfa_profile = MFAProfile.objects.get(user=request.user)
    except MFAProfile.DoesNotExist:
        messages.error(request, "MFA is not configured.")
        return redirect("settings_security")
    
    if not mfa_profile.is_enabled:
        messages.info(request, "MFA is already disabled.")
        return redirect("settings_security")
    
    if verify_totp(mfa_profile.secret, code):
        mfa_profile.is_enabled = False
        mfa_profile.secret = ""
        mfa_profile.recovery_codes = []
        mfa_profile.save()
        
        messages.success(request, "Two-factor authentication has been disabled.")
        return redirect("settings_security")
    
    messages.error(request, "Invalid verification code.")
    return redirect("settings_security")


@login_required
@require_POST
def mfa_regenerate_recovery(request):
    """
    Regenerate recovery codes for MFA.
    """
    code = request.POST.get("code", "").strip()
    
    try:
        mfa_profile = MFAProfile.objects.get(user=request.user)
    except MFAProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "MFA not configured"}, status=400)
    
    if not mfa_profile.is_enabled:
        return JsonResponse({"success": False, "error": "MFA not enabled"}, status=400)
    
    if verify_totp(mfa_profile.secret, code):
        recovery_codes = generate_recovery_codes()
        mfa_profile.recovery_codes = recovery_codes
        mfa_profile.save()
        
        return JsonResponse({
            "success": True,
            "recovery_codes": recovery_codes
        })
    
    return JsonResponse({"success": False, "error": "Invalid code"}, status=400)
