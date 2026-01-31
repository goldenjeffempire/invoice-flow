import logging
import secrets
import pyotp
from typing import Optional, Tuple
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from .models import UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken, WorkspaceInvitation

logger = logging.getLogger(__name__)

class SecurityService:
    @staticmethod
    def log_event(user, event_type, request, details=None, severity="info"):
        ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')
        SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            ip_address=ip,
            user_agent=ua,
            details=details or {},
            severity=severity
        )

class AuthService:
    @staticmethod
    def register_user(username, email, password):
        if User.objects.filter(email=email).exists():
            return None, "An account with this email already exists."
        
        user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
        UserProfile.objects.create(user=user)
        token = EmailToken.create_token(user, EmailToken.TokenType.VERIFY)
        return user, "Registration successful. Please check your email for verification."

    @staticmethod
    def verify_email(token_str):
        try:
            token = EmailToken.objects.get(token=token_str, token_type=EmailToken.TokenType.VERIFY, used_at__isnull=True)
            if not token.is_valid:
                return False, "Verification link has expired."
            
            token.used_at = timezone.now()
            token.save()
            token.user.is_active = True
            token.user.save()
            
            profile = token.user.profile
            profile.email_verified = True
            profile.save()
            return True, "Email verified successfully. You can now login."
        except EmailToken.DoesNotExist:
            return False, "Invalid verification link."

    @staticmethod
    def initiate_password_reset(email):
        try:
            user = User.objects.get(email=email, is_active=True)
            token = EmailToken.create_token(user, EmailToken.TokenType.RESET, hours=1)
            return True, "Password reset instructions sent."
        except User.DoesNotExist:
            return True, "Password reset instructions sent." # Security: don't reveal existence

class MFAService:
    @staticmethod
    def setup_totp(user):
        profile, _ = MFAProfile.objects.get_or_create(user=user)
        if profile.is_enabled:
            return None, "MFA already enabled"
        
        secret = pyotp.random_base32()
        profile.secret = secret
        profile.save()
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="InvoiceFlow")
        return secret, provisioning_uri

    @staticmethod
    def verify_and_enable(user, code):
        profile = user.mfa_profile
        totp = pyotp.TOTP(profile.secret)
        if totp.verify(code):
            profile.is_enabled = True
            profile.recovery_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            profile.save()
            user.profile.two_factor_enabled = True
            user.profile.save()
            return True, profile.recovery_codes
        return False, "Invalid code"
