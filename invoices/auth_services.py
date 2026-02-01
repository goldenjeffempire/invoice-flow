"""
Production-Grade Authentication Services
Enterprise-level security with comprehensive validation, rate limiting, and audit logging.
"""
import hashlib
import logging
import re
import secrets
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import timedelta
from decimal import Decimal
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
    LoginAttempt, KnownDevice, WorkspaceInvitation, Workspace, WorkspaceMember
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
    DEVICE_TRUSTED = "device_trusted"
    DEVICE_REMOVED = "device_removed"


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
        if not password:
            return False, 0
            
        def _fetch_hibp(prefix: str) -> str:
            req = urllib.request.Request(
                f"{cls.HIBP_API_URL}{prefix}",
                headers={"User-Agent": "InvoiceFlow-Security-Check"}
            )
            with urllib.request.urlopen(req, timeout=1.0) as response:
                return response.read().decode('utf-8')
        
        try:
            sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]

            cache_key = f"{cls.CACHE_PREFIX}{prefix}"
            cached_result = cache.get(cache_key)

            if cached_result is None:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_fetch_hibp, prefix)
                    try:
                        cached_result = future.result(timeout=1.0)
                        cache.set(cache_key, cached_result, cls.CACHE_DURATION)
                    except (FuturesTimeoutError, TimeoutError):
                        return False, 0

            if cached_result:
                for line in cached_result.splitlines():
                    parts = line.split(':')
                    if len(parts) == 2 and parts[0] == suffix:
                        return True, int(parts[1])

            return False, 0
        except Exception as e:
            logger.debug(f"HIBP check failed (non-fatal): {e}")
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
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            info['os'] = 'iOS'
            info['device_type'] = 'mobile' if 'iphone' in ua_lower else 'tablet'

        if 'mobile' in ua_lower:
            info['device_type'] = 'mobile'
        elif 'tablet' in ua_lower:
            info['device_type'] = 'tablet'

        return info

    @classmethod
    def log_event(cls, user, event_type: str, request=None, severity: str = 'info', details: dict = None):
        try:
            ip_address = None
            user_agent = ''
            if request:
                ip_address = cls.get_client_ip(request)
                user_agent = cls.get_user_agent(request)

            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                severity=severity,
                details=details or {}
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


class AuthService:
    @classmethod
    @transaction.atomic
    def register_user(cls, username: str, email: str, password: str, request=None) -> Tuple[Optional[Any], str]:
        try:
            email = email.lower().strip()
            username = username.strip()

            if User.objects.filter(username__iexact=username).exists():
                return None, "This username is already taken."
            if User.objects.filter(email__iexact=email).exists():
                return None, "An account with this email already exists."

            is_valid, errors = PasswordValidator.validate(password)
            if not is_valid:
                return None, errors[0]

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=True
            )

            profile = UserProfile.objects.create(
                user=user,
                email_verified=False,
                onboarding_step=1,
                onboarding_started_at=timezone.now()
            )

            MFAProfile.objects.create(user=user)

            workspace = Workspace.objects.create(
                name=f"{username}'s Workspace",
                owner=user,
                slug=secrets.token_urlsafe(8)
            )
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=user,
                role='owner'
            )
            profile.current_workspace = workspace
            profile.save(update_fields=['current_workspace'])

            SecurityService.log_event(user, SecurityEventType.SIGNUP, request)

            token = EmailToken.create_token(user, EmailToken.TokenType.VERIFY, hours=24)
            cls._send_verification_email(user, token.token, request)

            return user, "Account created! Please check your email to verify your account."

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None, "Registration failed. Please try again."

    @classmethod
    def _send_verification_email(cls, user, token: str, request=None):
        try:
            from django.urls import reverse
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:5000')
            protocol = 'https' if not settings.DEBUG else 'http'
            verify_url = f"{protocol}://{domain}/verify-email/{token}/"
            
            subject = "Verify your InvoiceFlow account"
            html_message = render_to_string('emails/verify_email.html', {
                'user': user,
                'verify_url': verify_url,
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=True
            )
            
            SecurityService.log_event(user, SecurityEventType.EMAIL_VERIFICATION_SENT, request)
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")

    @classmethod
    def authenticate_user(cls, request, username_or_email: str, password: str) -> Tuple[Optional[Any], str, bool]:
        try:
            username_or_email = username_or_email.strip()
            
            user = None
            if '@' in username_or_email:
                try:
                    user = User.objects.get(email__iexact=username_or_email)
                except User.DoesNotExist:
                    pass
            
            if not user:
                try:
                    user = User.objects.get(username__iexact=username_or_email)
                except User.DoesNotExist:
                    pass
            
            if not user:
                cls._log_failed_attempt(username_or_email, request, "user_not_found")
                return None, "Invalid credentials. Please check your username/email and password.", False

            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            if profile.is_locked():
                return None, "Account is temporarily locked. Please try again later.", False

            if not user.check_password(password):
                profile.increment_failed_attempts()
                cls._log_failed_attempt(username_or_email, request, "invalid_password")
                SecurityService.log_event(user, SecurityEventType.LOGIN_FAILED, request, 'warning')
                return None, "Invalid credentials. Please check your username/email and password.", False

            if not profile.email_verified:
                return None, "Please verify your email before logging in. Check your inbox for the verification link.", False

            profile.reset_failed_attempts()

            mfa_profile = getattr(user, 'mfa_profile', None)
            if mfa_profile and mfa_profile.is_enabled:
                return user, "MFA required", True

            return user, "Login successful", False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None, "Authentication failed. Please try again.", False

    @classmethod
    def _log_failed_attempt(cls, username: str, request, reason: str):
        try:
            LoginAttempt.objects.create(
                username=username,
                ip_address=SecurityService.get_client_ip(request),
                user_agent=SecurityService.get_user_agent(request),
                success=False,
                failure_reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to log attempt: {e}")

    @classmethod
    def complete_login(cls, request, user):
        login(request, user)
        
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        ip_address = SecurityService.get_client_ip(request)
        user_agent = SecurityService.get_user_agent(request)
        ua_info = SecurityService.parse_user_agent(user_agent)
        fingerprint = SecurityService.generate_fingerprint(request)

        UserSession.objects.filter(user=user).update(is_current=False)

        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'device_fingerprint': fingerprint,
                'browser': ua_info['browser'],
                'os': ua_info['os'],
                'device_type': ua_info['device_type'],
                'is_current': True,
                'is_active': True
            }
        )

        SecurityService.log_event(user, SecurityEventType.LOGIN_SUCCESS, request)

    @classmethod
    def logout_user(cls, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            UserSession.objects.filter(session_key=session_key).update(is_active=False)
            SecurityService.log_event(request.user, SecurityEventType.LOGOUT, request)
        logout(request)

    @classmethod
    def verify_email(cls, token: str, request=None) -> Tuple[bool, str]:
        try:
            email_token = EmailToken.objects.get(
                token=token,
                token_type=EmailToken.TokenType.VERIFY
            )

            if email_token.is_expired:
                return False, "This verification link has expired. Please request a new one."
            if email_token.used_at:
                return False, "This verification link has already been used."

            user = email_token.user
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])

            email_token.mark_used()

            SecurityService.log_event(user, SecurityEventType.EMAIL_VERIFIED, request)

            return True, "Email verified successfully!"

        except EmailToken.DoesNotExist:
            return False, "Invalid verification link."
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return False, "Verification failed. Please try again."

    @classmethod
    def resend_verification(cls, email: str, request=None) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email__iexact=email.strip())
            profile = getattr(user, 'profile', None)
            
            if profile and profile.email_verified:
                return False, "This email is already verified."

            token = EmailToken.create_token(user, EmailToken.TokenType.VERIFY, hours=24)
            cls._send_verification_email(user, token.token, request)

            return True, "Verification email sent! Please check your inbox."

        except User.DoesNotExist:
            return True, "If an account exists with this email, you will receive a verification link."
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            return False, "Failed to send verification email. Please try again."

    @classmethod
    def request_password_reset(cls, email: str, request=None) -> Tuple[bool, str]:
        try:
            user = User.objects.get(email__iexact=email.strip())
            
            token = EmailToken.create_token(user, EmailToken.TokenType.RESET, hours=1)
            cls._send_password_reset_email(user, token.token, request)
            
            SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_REQUESTED, request)

            return True, "If an account exists with this email, you will receive a password reset link."

        except User.DoesNotExist:
            return True, "If an account exists with this email, you will receive a password reset link."
        except Exception as e:
            logger.error(f"Password reset request error: {e}")
            return False, "Failed to send reset email. Please try again."

    @classmethod
    def _send_password_reset_email(cls, user, token: str, request=None):
        try:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:5000')
            protocol = 'https' if not settings.DEBUG else 'http'
            reset_url = f"{protocol}://{domain}/password-reset/confirm/{token}/"
            
            subject = "Reset your InvoiceFlow password"
            html_message = render_to_string('emails/password_reset.html', {
                'user': user,
                'reset_url': reset_url,
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")

    @classmethod
    def confirm_password_reset(cls, token: str, new_password: str, request=None) -> Tuple[bool, str]:
        try:
            email_token = EmailToken.objects.get(
                token=token,
                token_type=EmailToken.TokenType.RESET
            )

            if email_token.is_expired:
                return False, "This reset link has expired. Please request a new one."
            if email_token.used_at:
                return False, "This reset link has already been used."

            is_valid, errors = PasswordValidator.validate(new_password)
            if not is_valid:
                return False, errors[0]

            user = email_token.user
            user.set_password(new_password)
            user.save()

            email_token.mark_used()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.last_password_change = timezone.now()
            profile.save(update_fields=['last_password_change'])

            SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_COMPLETED, request)

            return True, "Password reset successfully! You can now log in with your new password."

        except EmailToken.DoesNotExist:
            return False, "Invalid or expired reset link."
        except Exception as e:
            logger.error(f"Password reset error: {e}")
            return False, "Password reset failed. Please try again."

    @classmethod
    def change_password(cls, user, current_password: str, new_password: str, request=None) -> Tuple[bool, str]:
        try:
            if not user.check_password(current_password):
                return False, "Current password is incorrect."

            is_valid, errors = PasswordValidator.validate(new_password)
            if not is_valid:
                return False, errors[0]

            user.set_password(new_password)
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.last_password_change = timezone.now()
            profile.save(update_fields=['last_password_change'])

            SecurityService.log_event(user, SecurityEventType.PASSWORD_CHANGED, request)

            return True, "Password changed successfully!"

        except Exception as e:
            logger.error(f"Password change error: {e}")
            return False, "Password change failed. Please try again."


class MFAService:
    @classmethod
    def generate_setup(cls, user) -> Dict[str, str]:
        secret = pyotp.random_base32()
        
        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret = secret
        mfa_profile.save(update_fields=['secret'])
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="InvoiceFlow"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = b64encode(buffer.getvalue()).decode()
        
        return {
            'secret': secret,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'provisioning_uri': provisioning_uri
        }

    @classmethod
    def verify_and_enable(cls, user, code: str, request=None) -> Tuple[bool, str, List[str]]:
        try:
            mfa_profile = MFAProfile.objects.get(user=user)
            
            if not mfa_profile.secret:
                return False, "Please generate a new setup code first.", []

            totp = pyotp.TOTP(mfa_profile.secret)
            if not totp.verify(code, valid_window=1):
                return False, "Invalid verification code. Please try again.", []

            recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            
            mfa_profile.is_enabled = True
            mfa_profile.recovery_codes = recovery_codes
            mfa_profile.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.two_factor_enabled = True
            profile.save(update_fields=['two_factor_enabled'])

            SecurityService.log_event(user, SecurityEventType.MFA_ENABLED, request)

            return True, "Two-factor authentication enabled successfully!", recovery_codes

        except MFAProfile.DoesNotExist:
            return False, "MFA profile not found.", []
        except Exception as e:
            logger.error(f"MFA enable error: {e}")
            return False, "Failed to enable 2FA. Please try again.", []

    @classmethod
    def verify_code(cls, user, code: str, request=None) -> Tuple[bool, str]:
        try:
            mfa_profile = MFAProfile.objects.get(user=user)
            
            if not mfa_profile.is_enabled or not mfa_profile.secret:
                return False, "2FA is not enabled for this account."

            totp = pyotp.TOTP(mfa_profile.secret)
            if totp.verify(code, valid_window=1):
                mfa_profile.last_used = timezone.now()
                mfa_profile.save(update_fields=['last_used'])
                SecurityService.log_event(user, SecurityEventType.MFA_VERIFIED, request)
                return True, "Code verified successfully."

            if mfa_profile.recovery_codes:
                code_upper = code.upper().replace('-', '')
                for i, recovery_code in enumerate(mfa_profile.recovery_codes):
                    if recovery_code.replace('-', '') == code_upper:
                        mfa_profile.recovery_codes.pop(i)
                        mfa_profile.save(update_fields=['recovery_codes'])
                        SecurityService.log_event(user, SecurityEventType.MFA_VERIFIED, request, 
                                                  details={'method': 'recovery_code'})
                        return True, "Recovery code accepted."

            SecurityService.log_event(user, SecurityEventType.MFA_FAILED, request, 'warning')
            return False, "Invalid code. Please try again."

        except MFAProfile.DoesNotExist:
            return False, "2FA is not configured for this account."
        except Exception as e:
            logger.error(f"MFA verify error: {e}")
            return False, "Verification failed. Please try again."

    @classmethod
    def disable(cls, user, password: str, request=None) -> Tuple[bool, str]:
        try:
            if not user.check_password(password):
                return False, "Incorrect password."

            mfa_profile = MFAProfile.objects.get(user=user)
            mfa_profile.is_enabled = False
            mfa_profile.secret = ''
            mfa_profile.recovery_codes = []
            mfa_profile.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.two_factor_enabled = False
            profile.save(update_fields=['two_factor_enabled'])

            SecurityService.log_event(user, SecurityEventType.MFA_DISABLED, request)

            return True, "Two-factor authentication disabled."

        except MFAProfile.DoesNotExist:
            return False, "2FA is not configured for this account."
        except Exception as e:
            logger.error(f"MFA disable error: {e}")
            return False, "Failed to disable 2FA. Please try again."

    @classmethod
    def regenerate_recovery_codes(cls, user, password: str, request=None) -> Tuple[bool, str, List[str]]:
        try:
            if not user.check_password(password):
                return False, "Incorrect password.", []

            mfa_profile = MFAProfile.objects.get(user=user)
            
            if not mfa_profile.is_enabled:
                return False, "2FA is not enabled.", []

            recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            mfa_profile.recovery_codes = recovery_codes
            mfa_profile.save(update_fields=['recovery_codes'])

            return True, "New recovery codes generated.", recovery_codes

        except MFAProfile.DoesNotExist:
            return False, "2FA is not configured for this account.", []
        except Exception as e:
            logger.error(f"Recovery code regeneration error: {e}")
            return False, "Failed to regenerate codes. Please try again.", []


class SessionService:
    @classmethod
    def get_user_sessions(cls, user) -> List[Dict]:
        sessions = UserSession.objects.filter(user=user, is_active=True).order_by('-last_activity')
        return [
            {
                'id': s.id,
                'session_key': s.session_key,
                'browser': s.browser,
                'os': s.os,
                'device_type': s.device_type,
                'ip_address': s.ip_address,
                'location': s.location or 'Unknown',
                'is_current': s.is_current,
                'last_activity': s.last_activity,
                'created_at': s.created_at
            }
            for s in sessions
        ]

    @classmethod
    def revoke_session(cls, user, session_id: int, request=None) -> Tuple[bool, str]:
        try:
            session = UserSession.objects.get(id=session_id, user=user)
            
            if session.is_current:
                return False, "Cannot revoke current session."

            session.is_active = False
            session.save(update_fields=['is_active'])

            from django.contrib.sessions.models import Session
            try:
                Session.objects.filter(session_key=session.session_key).delete()
            except Exception:
                pass

            SecurityService.log_event(user, SecurityEventType.SESSION_REVOKED, request,
                                      details={'revoked_session': session_id})

            return True, "Session revoked successfully."

        except UserSession.DoesNotExist:
            return False, "Session not found."
        except Exception as e:
            logger.error(f"Session revoke error: {e}")
            return False, "Failed to revoke session."

    @classmethod
    def revoke_all_other_sessions(cls, user, request=None) -> Tuple[bool, str]:
        try:
            current_session_key = request.session.session_key if request else None
            
            other_sessions = UserSession.objects.filter(user=user, is_active=True)
            if current_session_key:
                other_sessions = other_sessions.exclude(session_key=current_session_key)
            
            session_keys = list(other_sessions.values_list('session_key', flat=True))
            other_sessions.update(is_active=False)

            from django.contrib.sessions.models import Session
            try:
                Session.objects.filter(session_key__in=session_keys).delete()
            except Exception:
                pass

            SecurityService.log_event(user, SecurityEventType.ALL_SESSIONS_REVOKED, request,
                                      details={'count': len(session_keys)})

            return True, f"Signed out of {len(session_keys)} other session(s)."

        except Exception as e:
            logger.error(f"Revoke all sessions error: {e}")
            return False, "Failed to sign out of other sessions."


class DeviceService:
    @classmethod
    def get_user_devices(cls, user) -> List[Dict]:
        devices = KnownDevice.objects.filter(user=user, is_trusted=True).order_by('-last_used')
        return [
            {
                'id': d.id,
                'fingerprint': d.fingerprint,
                'device_name': d.device_name or f"{d.browser} on {d.os}",
                'browser': d.browser,
                'os': d.os,
                'device_type': d.device_type,
                'ip_address': d.ip_address,
                'last_used': d.last_used,
                'created_at': d.created_at
            }
            for d in devices
        ]

    @classmethod
    def trust_device(cls, user, request) -> Tuple[bool, str]:
        try:
            fingerprint = SecurityService.generate_fingerprint(request)
            user_agent = SecurityService.get_user_agent(request)
            ua_info = SecurityService.parse_user_agent(user_agent)
            ip_address = SecurityService.get_client_ip(request)

            device, created = KnownDevice.objects.update_or_create(
                user=user,
                fingerprint=fingerprint,
                defaults={
                    'user_agent': user_agent,
                    'ip_address': ip_address,
                    'browser': ua_info['browser'],
                    'os': ua_info['os'],
                    'device_type': ua_info['device_type'],
                    'is_trusted': True
                }
            )

            SecurityService.log_event(user, SecurityEventType.DEVICE_TRUSTED, request)

            return True, "Device trusted successfully."

        except Exception as e:
            logger.error(f"Trust device error: {e}")
            return False, "Failed to trust device."

    @classmethod
    def remove_device(cls, user, device_id: int, request=None) -> Tuple[bool, str]:
        try:
            device = KnownDevice.objects.get(id=device_id, user=user)
            device.is_trusted = False
            device.save(update_fields=['is_trusted'])

            SecurityService.log_event(user, SecurityEventType.DEVICE_REMOVED, request,
                                      details={'device_id': device_id})

            return True, "Device removed successfully."

        except KnownDevice.DoesNotExist:
            return False, "Device not found."
        except Exception as e:
            logger.error(f"Remove device error: {e}")
            return False, "Failed to remove device."


class InvitationService:
    @classmethod
    def send_invitation(cls, workspace, email: str, role: str, invited_by, request=None) -> Tuple[bool, str]:
        try:
            email = email.lower().strip()

            if WorkspaceMember.objects.filter(workspace=workspace, user__email__iexact=email).exists():
                return False, "This user is already a member of this workspace."

            pending = WorkspaceInvitation.objects.filter(
                workspace=workspace,
                email__iexact=email,
                status='pending'
            )
            if pending.exists():
                return False, "An invitation has already been sent to this email."

            invitation = WorkspaceInvitation.objects.create(
                workspace=workspace,
                email=email,
                role=role,
                invited_by=invited_by,
                token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timedelta(days=7)
            )

            cls._send_invitation_email(invitation, request)

            profile = getattr(invited_by, 'profile', None)
            if profile:
                profile.team_invites_sent = (profile.team_invites_sent or 0) + 1
                profile.save(update_fields=['team_invites_sent'])

            return True, "Invitation sent successfully!"

        except Exception as e:
            logger.error(f"Send invitation error: {e}")
            return False, "Failed to send invitation."

    @classmethod
    def _send_invitation_email(cls, invitation, request=None):
        try:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:5000')
            protocol = 'https' if not settings.DEBUG else 'http'
            invite_url = f"{protocol}://{domain}/invite/{invitation.token}/"
            
            subject = f"You're invited to join {invitation.workspace.name} on InvoiceFlow"
            html_message = render_to_string('emails/workspace_invitation.html', {
                'invitation': invitation,
                'invite_url': invite_url,
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [invitation.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")

    @classmethod
    def accept_invitation(cls, token: str, user, request=None) -> Tuple[bool, str]:
        try:
            invitation = WorkspaceInvitation.objects.get(
                token=token,
                status='pending'
            )

            if invitation.is_expired:
                invitation.status = 'expired'
                invitation.save(update_fields=['status'])
                return False, "This invitation has expired."

            if invitation.email.lower() != user.email.lower():
                return False, "This invitation was sent to a different email address."

            WorkspaceMember.objects.create(
                workspace=invitation.workspace,
                user=user,
                role=invitation.role
            )

            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=['status', 'accepted_at'])

            SecurityService.log_event(user, SecurityEventType.INVITATION_ACCEPTED, request,
                                      details={'workspace_id': invitation.workspace.id})

            return True, f"Welcome to {invitation.workspace.name}!"

        except WorkspaceInvitation.DoesNotExist:
            return False, "Invalid invitation link."
        except Exception as e:
            logger.error(f"Accept invitation error: {e}")
            return False, "Failed to accept invitation."

    @classmethod
    def revoke_invitation(cls, invitation_id: int, user) -> Tuple[bool, str]:
        try:
            invitation = WorkspaceInvitation.objects.get(id=invitation_id)
            
            member = WorkspaceMember.objects.filter(
                workspace=invitation.workspace,
                user=user,
                role__in=['owner', 'admin']
            ).first()
            
            if not member:
                return False, "You don't have permission to revoke this invitation."

            invitation.status = 'revoked'
            invitation.save(update_fields=['status'])

            return True, "Invitation revoked."

        except WorkspaceInvitation.DoesNotExist:
            return False, "Invitation not found."
        except Exception as e:
            logger.error(f"Revoke invitation error: {e}")
            return False, "Failed to revoke invitation."
