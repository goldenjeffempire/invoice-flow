"""
Production-Grade Authentication Services
Handles user registration, login, email verification, password reset,
MFA, session management, and security event logging.
"""
import hashlib
import logging
import re
import secrets
import urllib.request
import urllib.error
from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Any

import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import (
    UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken,
    LoginAttempt, KnownDevice, WorkspaceInvitation
)

logger = logging.getLogger(__name__)
User = get_user_model()


class SecurityEventType:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_SUSPICIOUS = "login_suspicious"
    LOGOUT = "logout"
    SIGNUP = "signup"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFIED = "email_verified"
    EMAIL_VERIFICATION_SENT = "email_verification_sent"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_VERIFIED = "mfa_verified"
    MFA_FAILED = "mfa_failed"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    INVITATION_ACCEPTED = "invitation_accepted"


class PasswordValidator:
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    COMMON_PASSWORDS = {
        'password', 'password123', '123456', 'qwerty', 'letmein',
        'welcome', 'admin', 'login', 'abc123', 'monkey', '12345678',
        'iloveyou', 'sunshine', 'princess', 'dragon', 'master',
        'football', 'baseball', 'access', 'shadow', 'michael',
    }
    HIBP_API_URL = "https://api.pwnedpasswords.com/range/"
    CACHE_PREFIX = "hibp_"
    CACHE_DURATION = 86400

    @classmethod
    def validate(cls, password: str, check_breach: bool = True) -> Tuple[bool, List[str]]:
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be at most {cls.MAX_LENGTH} characters long")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append("This password is too common")

        if check_breach and not errors:
            is_breached, count = cls.check_breach(password)
            if is_breached:
                errors.append(f"This password has appeared in data breaches ({count:,} times). Please choose a different password.")

        return len(errors) == 0, errors

    @classmethod
    def check_breach(cls, password: str) -> Tuple[bool, int]:
        try:
            sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]

            cache_key = f"{cls.CACHE_PREFIX}{prefix}"
            cached_result = cache.get(cache_key)

            if cached_result is None:
                req = urllib.request.Request(
                    f"{cls.HIBP_API_URL}{prefix}",
                    headers={"User-Agent": "InvoiceFlow-Security-Check"}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    cached_result = response.read().decode('utf-8')
                    cache.set(cache_key, cached_result, cls.CACHE_DURATION)

            for line in cached_result.splitlines():
                parts = line.split(':')
                if len(parts) == 2 and parts[0] == suffix:
                    return True, int(parts[1])

            return False, 0
        except Exception as e:
            logger.warning(f"HIBP check failed: {e}")
            return False, 0


class SecurityService:
    @classmethod
    def get_client_ip(cls, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    @classmethod
    def get_user_agent(cls, request) -> str:
        return request.META.get('HTTP_USER_AGENT', '')[:500]

    @classmethod
    def generate_fingerprint(cls, request) -> str:
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
        ]
        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:32]

    @classmethod
    def parse_user_agent(cls, user_agent: str) -> Dict[str, str]:
        info = {'browser': 'Unknown', 'os': 'Unknown', 'device_type': 'desktop'}
        ua_lower = user_agent.lower()

        if 'chrome' in ua_lower and 'edg' not in ua_lower:
            info['browser'] = 'Chrome'
        elif 'firefox' in ua_lower:
            info['browser'] = 'Firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            info['browser'] = 'Safari'
        elif 'edg' in ua_lower:
            info['browser'] = 'Edge'
        elif 'opera' in ua_lower or 'opr' in ua_lower:
            info['browser'] = 'Opera'

        if 'windows' in ua_lower:
            info['os'] = 'Windows'
        elif 'mac os' in ua_lower or 'macos' in ua_lower:
            info['os'] = 'macOS'
        elif 'linux' in ua_lower and 'android' not in ua_lower:
            info['os'] = 'Linux'
        elif 'android' in ua_lower:
            info['os'] = 'Android'
            info['device_type'] = 'mobile'
        elif 'iphone' in ua_lower:
            info['os'] = 'iOS'
            info['device_type'] = 'mobile'
        elif 'ipad' in ua_lower:
            info['os'] = 'iOS'
            info['device_type'] = 'tablet'

        if 'mobile' in ua_lower:
            info['device_type'] = 'mobile'

        return info

    @classmethod
    def log_event(cls, user, event_type: str, request=None, details: Dict = None, severity: str = "info"):
        ip_address = cls.get_client_ip(request) if request else None
        user_agent = cls.get_user_agent(request) if request else ""

        try:
            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
                severity=severity
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    @classmethod
    def log_login_attempt(cls, username: str, request, success: bool, failure_reason: str = ""):
        ip_address = cls.get_client_ip(request)
        user_agent = cls.get_user_agent(request)

        LoginAttempt.objects.create(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )

    @classmethod
    def is_ip_rate_limited(cls, ip_address: str) -> bool:
        cache_key = f"login_attempts_{ip_address}"
        attempts = cache.get(cache_key, 0)
        return attempts >= 10

    @classmethod
    def increment_ip_attempts(cls, ip_address: str):
        cache_key = f"login_attempts_{ip_address}"
        attempts = cache.get(cache_key, 0)
        cache.set(cache_key, attempts + 1, 3600)

    @classmethod
    def reset_ip_attempts(cls, ip_address: str):
        cache_key = f"login_attempts_{ip_address}"
        cache.delete(cache_key)

    @classmethod
    def check_suspicious_login(cls, user, request) -> Tuple[bool, List[str]]:
        reasons = []
        fingerprint = cls.generate_fingerprint(request)
        ip_address = cls.get_client_ip(request)

        if not KnownDevice.objects.filter(user=user, fingerprint=fingerprint, is_trusted=True).exists():
            reasons.append("new_device")

        thirty_days_ago = timezone.now() - timedelta(days=30)
        if not UserSession.objects.filter(user=user, ip_address=ip_address, created_at__gte=thirty_days_ago).exists():
            reasons.append("new_location")

        current_hour = timezone.localtime().hour
        if 2 <= current_hour < 5:
            reasons.append("unusual_time")

        one_hour_ago = timezone.now() - timedelta(hours=1)
        failed_count = LoginAttempt.objects.filter(
            username=user.username,
            success=False,
            created_at__gte=one_hour_ago
        ).count()
        if failed_count >= 3:
            reasons.append("multiple_failed_attempts")

        return len(reasons) >= 2, reasons

    @classmethod
    def register_device(cls, user, request, device_name: str = "") -> KnownDevice:
        fingerprint = cls.generate_fingerprint(request)
        user_agent = cls.get_user_agent(request)
        device_info = cls.parse_user_agent(user_agent)
        ip_address = cls.get_client_ip(request)

        device, _ = KnownDevice.objects.update_or_create(
            user=user,
            fingerprint=fingerprint,
            defaults={
                'device_name': device_name or f"{device_info['browser']} on {device_info['os']}",
                'user_agent': user_agent,
                'ip_address': ip_address,
                'browser': device_info['browser'],
                'os': device_info['os'],
                'device_type': device_info['device_type'],
                'is_trusted': True,
                'last_used': timezone.now(),
            }
        )
        return device


class EmailService:
    @classmethod
    def send_verification_email(cls, user, token: EmailToken) -> bool:
        try:
            from .sendgrid_service import SendGridEmailService
            return SendGridEmailService().send_verification_email(user, token.token)
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False

    @classmethod
    def send_password_reset_email(cls, user, token: EmailToken) -> bool:
        try:
            from .sendgrid_service import SendGridEmailService
            return SendGridEmailService().send_password_reset_email(user, token.token)
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False


class AuthService:
    @classmethod
    @transaction.atomic
    def register_user(cls, username: str, email: str, password: str, request=None) -> Tuple[Optional[Any], str]:
        email_lower = email.lower().strip()
        username_clean = username.strip()

        if User.objects.filter(email__iexact=email_lower).exists():
            return None, "An account with this email already exists."

        if User.objects.filter(username__iexact=username_clean).exists():
            return None, "This username is already taken."

        is_valid, errors = PasswordValidator.validate(password)
        if not is_valid:
            return None, errors[0]

        user = User.objects.create_user(
            username=username_clean,
            email=email_lower,
            password=password,
            is_active=False
        )

        profile = UserProfile.objects.create(user=user, last_password_change=timezone.now())

        token = EmailToken.create_token(user, EmailToken.TokenType.VERIFY, hours=24)

        EmailService.send_verification_email(user, token)

        if request:
            SecurityService.log_event(user, SecurityEventType.SIGNUP, request)
            SecurityService.log_event(user, SecurityEventType.EMAIL_VERIFICATION_SENT, request)

        return user, "Account created! Please check your email to verify your account."

    @classmethod
    def authenticate_user(cls, request, username_or_email: str, password: str) -> Tuple[Optional[Any], str, bool]:
        ip_address = SecurityService.get_client_ip(request)

        if SecurityService.is_ip_rate_limited(ip_address):
            return None, "Too many login attempts. Please try again later.", False

        user = None
        if '@' in username_or_email:
            try:
                user = User.objects.get(email__iexact=username_or_email)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username__iexact=username_or_email)
            except User.DoesNotExist:
                pass

        if user is None:
            SecurityService.increment_ip_attempts(ip_address)
            SecurityService.log_login_attempt(username_or_email, request, False, "user_not_found")
            return None, "Invalid username/email or password.", False

        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        if profile.is_locked():
            remaining = (profile.locked_until - timezone.now()).seconds // 60
            SecurityService.log_login_attempt(username_or_email, request, False, "account_locked")
            return None, f"Account is locked. Please try again in {remaining} minutes.", False

        if not user.check_password(password):
            profile.increment_failed_attempts()
            SecurityService.increment_ip_attempts(ip_address)
            SecurityService.log_login_attempt(username_or_email, request, False, "invalid_password")

            if profile.is_locked():
                SecurityService.log_event(user, SecurityEventType.ACCOUNT_LOCKED, request, severity="warning")
                return None, "Account locked due to too many failed attempts. Please try again later.", False

            return None, "Invalid username/email or password.", False

        if not user.is_active:
            SecurityService.log_login_attempt(username_or_email, request, False, "account_inactive")
            return None, "Please verify your email before logging in.", False

        if not profile.email_verified:
            return None, "Please verify your email before logging in.", False

        requires_mfa = MFAService.is_mfa_enabled(user)

        profile.reset_failed_attempts()
        SecurityService.reset_ip_attempts(ip_address)

        return user, "Login successful.", requires_mfa

    @classmethod
    def complete_login(cls, request, user, mfa_verified: bool = False):
        login(request, user)

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        ip_address = SecurityService.get_client_ip(request)
        user_agent = SecurityService.get_user_agent(request)
        fingerprint = SecurityService.generate_fingerprint(request)
        device_info = SecurityService.parse_user_agent(user_agent)

        UserSession.objects.filter(user=user, is_current=True).update(is_current=False)

        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'device_fingerprint': fingerprint,
                'browser': device_info['browser'],
                'os': device_info['os'],
                'device_type': device_info['device_type'],
                'is_current': True,
                'is_active': True,
            }
        )

        SecurityService.register_device(user, request)

        is_suspicious, reasons = SecurityService.check_suspicious_login(user, request)
        if is_suspicious:
            SecurityService.log_event(
                user, SecurityEventType.LOGIN_SUSPICIOUS, request,
                details={'reasons': reasons}, severity="warning"
            )
        else:
            SecurityService.log_event(user, SecurityEventType.LOGIN_SUCCESS, request)

        if mfa_verified:
            request.session['mfa_verified'] = True

    @classmethod
    def logout_user(cls, request):
        user = request.user
        session_key = request.session.session_key

        if user.is_authenticated:
            SecurityService.log_event(user, SecurityEventType.LOGOUT, request)
            UserSession.objects.filter(session_key=session_key).update(is_active=False)

        logout(request)

    @classmethod
    def verify_email(cls, token_str: str, request=None) -> Tuple[bool, str]:
        try:
            token = EmailToken.objects.get(
                token=token_str,
                token_type=EmailToken.TokenType.VERIFY,
                used_at__isnull=True
            )

            if token.is_expired:
                return False, "This verification link has expired. Please request a new one."

            token.mark_used()
            token.user.is_active = True
            token.user.save()

            profile, _ = UserProfile.objects.get_or_create(user=token.user)
            profile.email_verified = True
            profile.save()

            if request:
                SecurityService.log_event(token.user, SecurityEventType.EMAIL_VERIFIED, request)

            return True, "Email verified successfully! You can now log in."

        except EmailToken.DoesNotExist:
            return False, "Invalid verification link."

    @classmethod
    def resend_verification(cls, email: str, request=None) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email__iexact=email, is_active=False)

            recent_token = EmailToken.objects.filter(
                user=user,
                token_type=EmailToken.TokenType.VERIFY,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).exists()

            if recent_token:
                return False, "A verification email was sent recently. Please check your inbox or wait a few minutes."

            token = EmailToken.create_token(user, EmailToken.TokenType.VERIFY, hours=24)
            EmailService.send_verification_email(user, token)

            if request:
                SecurityService.log_event(user, SecurityEventType.EMAIL_VERIFICATION_SENT, request)

            return True, "Verification email sent! Please check your inbox."

        except User.DoesNotExist:
            return True, "If an account exists with this email, a verification email has been sent."

    @classmethod
    def initiate_password_reset(cls, email: str, request=None) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email__iexact=email)

            if not user.is_active:
                return True, "If an account exists with this email, password reset instructions have been sent."

            recent_token = EmailToken.objects.filter(
                user=user,
                token_type=EmailToken.TokenType.RESET,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).exists()

            if recent_token:
                return True, "If an account exists with this email, password reset instructions have been sent."

            token = EmailToken.create_token(user, EmailToken.TokenType.RESET, hours=1)
            EmailService.send_password_reset_email(user, token)

            if request:
                SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_REQUESTED, request)

            return True, "If an account exists with this email, password reset instructions have been sent."

        except User.DoesNotExist:
            return True, "If an account exists with this email, password reset instructions have been sent."

    @classmethod
    def validate_reset_token(cls, token_str: str) -> Tuple[bool, Optional[EmailToken], str]:
        try:
            token = EmailToken.objects.get(
                token=token_str,
                token_type=EmailToken.TokenType.RESET,
                used_at__isnull=True
            )

            if token.is_expired:
                return False, None, "This password reset link has expired. Please request a new one."

            return True, token, ""

        except EmailToken.DoesNotExist:
            return False, None, "Invalid password reset link."

    @classmethod
    @transaction.atomic
    def complete_password_reset(cls, token_str: str, new_password: str, request=None) -> Tuple[bool, str]:
        is_valid, token, error = cls.validate_reset_token(token_str)
        if not is_valid:
            return False, error

        is_valid_password, errors = PasswordValidator.validate(new_password)
        if not is_valid_password:
            return False, errors[0]

        user = token.user
        user.set_password(new_password)
        user.save()

        token.mark_used()

        try:
            profile = user.profile
            profile.last_password_change = timezone.now()
            profile.password_reset_required = False
            profile.reset_failed_attempts()
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        UserSession.objects.filter(user=user).update(is_active=False)

        if request:
            SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_COMPLETED, request)
            SecurityService.log_event(user, SecurityEventType.ALL_SESSIONS_REVOKED, request)

        return True, "Password reset successfully! You can now log in with your new password."

    @classmethod
    @transaction.atomic
    def change_password(cls, user, current_password: str, new_password: str, request=None) -> Tuple[bool, str]:
        if not user.check_password(current_password):
            return False, "Current password is incorrect."

        is_valid, errors = PasswordValidator.validate(new_password)
        if not is_valid:
            return False, errors[0]

        user.set_password(new_password)
        user.save()

        try:
            profile = user.profile
            profile.last_password_change = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        if request:
            current_session = request.session.session_key
            UserSession.objects.filter(user=user).exclude(session_key=current_session).update(is_active=False)
            SecurityService.log_event(user, SecurityEventType.PASSWORD_CHANGED, request)

        return True, "Password changed successfully."


class MFAService:
    ISSUER_NAME = "InvoiceFlow"
    BACKUP_CODE_COUNT = 10

    @classmethod
    def is_mfa_enabled(cls, user) -> bool:
        try:
            return user.mfa_profile.is_enabled
        except (AttributeError, MFAProfile.DoesNotExist):
            return False

    @classmethod
    def generate_setup_data(cls, user) -> Tuple[str, str, str]:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=cls.ISSUER_NAME
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = f"data:image/png;base64,{b64encode(buffer.getvalue()).decode()}"

        return secret, qr_code_base64, provisioning_uri

    @classmethod
    def generate_backup_codes(cls) -> List[str]:
        return [secrets.token_hex(4).upper() for _ in range(cls.BACKUP_CODE_COUNT)]

    @classmethod
    def verify_totp(cls, secret: str, code: str) -> bool:
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code.strip(), valid_window=1)
        except Exception:
            return False

    @classmethod
    @transaction.atomic
    def enable_mfa(cls, user, secret: str, code: str, request=None) -> Tuple[bool, List[str], str]:
        if not cls.verify_totp(secret, code):
            return False, [], "Invalid verification code. Please try again."

        backup_codes = cls.generate_backup_codes()

        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret = secret
        mfa_profile.is_enabled = True
        mfa_profile.recovery_codes = backup_codes
        mfa_profile.recovery_codes_viewed = False
        mfa_profile.last_used = timezone.now()
        mfa_profile.save()

        try:
            profile = user.profile
            profile.two_factor_enabled = True
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        if request:
            SecurityService.log_event(user, SecurityEventType.MFA_ENABLED, request)

        return True, backup_codes, "Two-factor authentication enabled successfully!"

    @classmethod
    @transaction.atomic
    def disable_mfa(cls, user, password: str, request=None) -> Tuple[bool, str]:
        if not user.check_password(password):
            return False, "Incorrect password."

        try:
            mfa_profile = user.mfa_profile
            mfa_profile.is_enabled = False
            mfa_profile.secret = ""
            mfa_profile.recovery_codes = []
            mfa_profile.save()
        except MFAProfile.DoesNotExist:
            pass

        try:
            profile = user.profile
            profile.two_factor_enabled = False
            profile.save()
        except UserProfile.DoesNotExist:
            pass

        if request:
            SecurityService.log_event(user, SecurityEventType.MFA_DISABLED, request)

        return True, "Two-factor authentication disabled."

    @classmethod
    def verify_mfa(cls, user, code: str, request=None) -> Tuple[bool, str]:
        try:
            mfa_profile = user.mfa_profile
        except MFAProfile.DoesNotExist:
            return False, "MFA is not set up for this account."

        if not mfa_profile.is_enabled:
            return False, "MFA is not enabled for this account."

        code_clean = code.strip().upper()

        if cls.verify_totp(mfa_profile.secret, code_clean):
            mfa_profile.last_used = timezone.now()
            mfa_profile.save(update_fields=['last_used'])

            if request:
                SecurityService.log_event(user, SecurityEventType.MFA_VERIFIED, request)

            return True, "Verification successful."

        if code_clean in mfa_profile.recovery_codes:
            codes = mfa_profile.recovery_codes.copy()
            codes.remove(code_clean)
            mfa_profile.recovery_codes = codes
            mfa_profile.last_used = timezone.now()
            mfa_profile.save()

            if request:
                SecurityService.log_event(
                    user, SecurityEventType.MFA_VERIFIED, request,
                    details={'method': 'backup_code', 'remaining_codes': len(codes)}
                )

            return True, f"Backup code used. {len(codes)} codes remaining."

        if request:
            SecurityService.log_event(user, SecurityEventType.MFA_FAILED, request, severity="warning")

        return False, "Invalid verification code."

    @classmethod
    def get_remaining_codes(cls, user) -> int:
        try:
            return len(user.mfa_profile.recovery_codes or [])
        except (AttributeError, MFAProfile.DoesNotExist):
            return 0

    @classmethod
    @transaction.atomic
    def regenerate_backup_codes(cls, user, password: str, request=None) -> Tuple[bool, List[str], str]:
        if not user.check_password(password):
            return False, [], "Incorrect password."

        try:
            mfa_profile = user.mfa_profile
            if not mfa_profile.is_enabled:
                return False, [], "MFA is not enabled."

            new_codes = cls.generate_backup_codes()
            mfa_profile.recovery_codes = new_codes
            mfa_profile.recovery_codes_viewed = False
            mfa_profile.save()

            if request:
                SecurityService.log_event(
                    user, SecurityEventType.MFA_ENABLED, request,
                    details={'action': 'backup_codes_regenerated'}
                )

            return True, new_codes, "Backup codes regenerated successfully."

        except MFAProfile.DoesNotExist:
            return False, [], "MFA is not set up."


class SessionService:
    @classmethod
    def get_user_sessions(cls, user) -> List[Dict]:
        sessions = []
        for session in UserSession.objects.filter(user=user, is_active=True).order_by('-last_activity'):
            sessions.append({
                'id': session.id,
                'browser': session.browser or 'Unknown',
                'os': session.os or 'Unknown',
                'device_type': session.device_type,
                'ip_address': session.ip_address or 'Unknown',
                'location': session.location or 'Unknown',
                'last_activity': session.last_activity,
                'is_current': session.is_current,
                'created_at': session.created_at,
            })
        return sessions

    @classmethod
    def revoke_session(cls, user, session_id: int, request=None) -> Tuple[bool, str]:
        try:
            session = UserSession.objects.get(id=session_id, user=user)

            if session.is_current:
                return False, "Cannot revoke the current session."

            session.is_active = False
            session.save()

            if request:
                SecurityService.log_event(
                    user, SecurityEventType.SESSION_REVOKED, request,
                    details={'revoked_session_id': session_id}
                )

            return True, "Session revoked successfully."

        except UserSession.DoesNotExist:
            return False, "Session not found."

    @classmethod
    def revoke_all_other_sessions(cls, user, request=None) -> Tuple[bool, str]:
        current_session_key = request.session.session_key if request else None

        count = UserSession.objects.filter(user=user, is_active=True).exclude(
            session_key=current_session_key
        ).update(is_active=False)

        if request:
            SecurityService.log_event(
                user, SecurityEventType.ALL_SESSIONS_REVOKED, request,
                details={'sessions_revoked': count}
            )

        return True, f"Revoked {count} session(s)."


class InvitationService:
    @classmethod
    def validate_invitation(cls, token: str) -> Tuple[bool, Optional[WorkspaceInvitation], str]:
        try:
            invitation = WorkspaceInvitation.objects.get(token=token)

            if invitation.is_revoked:
                return False, None, "This invitation has been revoked."

            if invitation.is_accepted:
                return False, None, "This invitation has already been accepted."

            if invitation.is_expired:
                return False, None, "This invitation has expired."

            return True, invitation, ""

        except WorkspaceInvitation.DoesNotExist:
            return False, None, "Invalid invitation link."

    @classmethod
    @transaction.atomic
    def accept_invitation(cls, token: str, user, request=None) -> Tuple[bool, str]:
        is_valid, invitation, error = cls.validate_invitation(token)
        if not is_valid:
            return False, error

        if invitation.email.lower() != user.email.lower():
            return False, "This invitation was sent to a different email address."

        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save()

        if request:
            SecurityService.log_event(
                user, SecurityEventType.INVITATION_ACCEPTED, request,
                details={'inviter': invitation.inviter.username, 'role': invitation.role}
            )

        return True, f"Welcome! You've joined the workspace as {invitation.role}."
