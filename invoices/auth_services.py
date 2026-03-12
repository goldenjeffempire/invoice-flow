"""
InvoiceFlow – Production-Grade Authentication Services
Enterprise SaaS auth: registration, login, session management, password reset.
No email verification flow.
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Any

from django.conf import settings
from django.contrib.auth import login, logout, get_user_model
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


# ---------------------------------------------------------------------------
# Security Event Constants
# ---------------------------------------------------------------------------

class SecurityEventType:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    SIGNUP = "signup"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"
    ACCOUNT_LOCKED = "account_locked"


# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------

class PasswordValidator:
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    COMMON_PASSWORDS = {
        'password', 'password1', 'password123', '12345678', '123456789',
        'qwerty', 'qwerty123', 'letmein', 'welcome', 'admin', 'login',
        'abc123', 'monkey', 'iloveyou', 'sunshine', 'princess', 'dragon',
        'master', 'football', 'baseball', 'access', 'shadow', 'michael',
        'superman', 'batman', 'trustno1', 'hello', 'hunter2',
    }
    HIBP_API_URL = "https://api.pwnedpasswords.com/range/"
    _CACHE_PREFIX = "hibp_"
    _CACHE_TTL = 86400  # 24h

    @classmethod
    def validate(cls, password: str, check_breach: bool = True) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Must be at least {cls.MIN_LENGTH} characters long.")
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Must be at most {cls.MAX_LENGTH} characters long.")
        if not re.search(r'[A-Z]', password):
            errors.append("Must include at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            errors.append("Must include at least one lowercase letter.")
        if not re.search(r'\d', password):
            errors.append("Must include at least one number.")
        if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/`~\'"\\]', password):
            errors.append("Must include at least one special character.")
        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append("This password is too common. Please choose a more unique one.")

        if check_breach and not errors:
            is_breached, count = cls._check_breach(password)
            if is_breached:
                errors.append(
                    f"This password has appeared in known data breaches ({count:,}× exposed). "
                    "Please choose a different password."
                )

        return len(errors) == 0, errors

    @classmethod
    def _check_breach(cls, password: str) -> Tuple[bool, int]:
        if not password:
            return False, 0

        def _fetch(prefix: str) -> str:
            req = urllib.request.Request(
                f"{cls.HIBP_API_URL}{prefix}",
                headers={"User-Agent": "InvoiceFlow-Security-Check/1.0"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.read().decode("utf-8")

        try:
            sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
            prefix, suffix = sha1[:5], sha1[5:]
            cache_key = f"{cls._CACHE_PREFIX}{prefix}"

            data = cache.get(cache_key)
            if data is None:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(_fetch, prefix)
                    try:
                        data = future.result(timeout=1.5)
                        cache.set(cache_key, data, cls._CACHE_TTL)
                    except (FuturesTimeoutError, TimeoutError):
                        return False, 0

            for line in (data or "").splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0] == suffix:
                    return True, int(parts[1])
            return False, 0
        except Exception as exc:
            logger.debug("HIBP check failed (non-fatal): %s", exc)
            return False, 0


# ---------------------------------------------------------------------------
# Security Utilities
# ---------------------------------------------------------------------------

class SecurityService:
    @staticmethod
    def get_client_ip(request) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def get_user_agent(request) -> str:
        return request.META.get("HTTP_USER_AGENT", "")[:500]

    @staticmethod
    def generate_fingerprint(request) -> str:
        parts = [
            request.META.get("HTTP_USER_AGENT", ""),
            request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
            request.META.get("HTTP_ACCEPT_ENCODING", ""),
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

    @staticmethod
    def parse_user_agent(ua: str) -> Dict[str, str]:
        info = {"browser": "Unknown", "os": "Unknown", "device_type": "desktop"}
        ua_l = ua.lower()

        if "edg" in ua_l:
            info["browser"] = "Edge"
        elif "chrome" in ua_l:
            info["browser"] = "Chrome"
        elif "firefox" in ua_l:
            info["browser"] = "Firefox"
        elif "safari" in ua_l:
            info["browser"] = "Safari"
        elif "opera" in ua_l or "opr" in ua_l:
            info["browser"] = "Opera"

        if "android" in ua_l:
            info["os"] = "Android"
            info["device_type"] = "mobile"
        elif "iphone" in ua_l:
            info["os"] = "iOS"
            info["device_type"] = "mobile"
        elif "ipad" in ua_l:
            info["os"] = "iOS"
            info["device_type"] = "tablet"
        elif "windows" in ua_l:
            info["os"] = "Windows"
        elif "mac os" in ua_l:
            info["os"] = "macOS"
        elif "linux" in ua_l:
            info["os"] = "Linux"

        return info

    @classmethod
    def log_event(
        cls,
        user,
        event_type: str,
        request=None,
        severity: str = "info",
        details: dict = None,
    ):
        try:
            ip = cls.get_client_ip(request) if request else None
            ua = cls.get_user_agent(request) if request else ""
            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                ip_address=ip,
                user_agent=ua,
                severity=severity,
                details=details or {},
            )
        except Exception as exc:
            logger.error("Failed to log security event: %s", exc)


# ---------------------------------------------------------------------------
# Core Authentication Service
# ---------------------------------------------------------------------------

class AuthService:
    # ---- Registration -------------------------------------------------------

    @classmethod
    @transaction.atomic
    def register_user(
        cls,
        username: str,
        email: str,
        password: str,
        request=None,
    ) -> Tuple[Optional[Any], str]:
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
                is_active=True,
            )

            profile = UserProfile.objects.create(
                user=user,
                email_verified=True,
                onboarding_step=1,
                onboarding_started_at=timezone.now(),
            )

            MFAProfile.objects.create(user=user)

            workspace = Workspace.objects.create(
                name=f"{username}'s Workspace",
                owner=user,
                slug=secrets.token_urlsafe(8),
            )
            WorkspaceMember.objects.create(workspace=workspace, user=user, role="owner")
            profile.current_workspace = workspace
            profile.save(update_fields=["current_workspace"])

            SecurityService.log_event(user, SecurityEventType.SIGNUP, request)
            return user, "Account created successfully."

        except Exception as exc:
            logger.error("Registration error: %s", exc)
            return None, "Registration failed. Please try again."

    # ---- Authentication -----------------------------------------------------

    @classmethod
    def authenticate_user(
        cls,
        request,
        username_or_email: str,
        password: str,
    ) -> Tuple[Optional[Any], str, bool]:
        """
        Returns (user | None, message, requires_mfa).
        """
        try:
            identifier = username_or_email.strip()

            user = None
            if "@" in identifier:
                try:
                    user = User.objects.get(email__iexact=identifier)
                except User.DoesNotExist:
                    pass
            if user is None:
                try:
                    user = User.objects.get(username__iexact=identifier)
                except User.DoesNotExist:
                    pass

            if user is None:
                cls._record_failed_attempt(identifier, request, "user_not_found")
                return None, "Invalid credentials. Please check your email/username and password.", False

            profile, _ = UserProfile.objects.get_or_create(user=user)

            if profile.is_locked():
                remaining = int((profile.locked_until - timezone.now()).total_seconds() // 60) + 1
                return None, f"Account locked due to too many failed attempts. Try again in {remaining} minute(s).", False

            if not user.check_password(password):
                profile.increment_failed_attempts()
                cls._record_failed_attempt(identifier, request, "invalid_password")
                SecurityService.log_event(user, SecurityEventType.LOGIN_FAILED, request, "warning")
                return None, "Invalid credentials. Please check your email/username and password.", False

            profile.reset_failed_attempts()

            mfa_profile = getattr(user, "mfa_profile", None)
            if mfa_profile and mfa_profile.is_enabled:
                return user, "MFA required", True

            return user, "Login successful", False

        except Exception as exc:
            logger.error("Authentication error: %s", exc)
            return None, "Authentication failed. Please try again.", False

    @classmethod
    def _record_failed_attempt(cls, identifier: str, request, reason: str):
        try:
            LoginAttempt.objects.create(
                username=identifier[:150],
                ip_address=SecurityService.get_client_ip(request),
                user_agent=SecurityService.get_user_agent(request),
                success=False,
                failure_reason=reason,
            )
        except Exception as exc:
            logger.error("Failed to record login attempt: %s", exc)

    @classmethod
    def complete_login(cls, request, user, mfa_verified: bool = False):
        login(request, user)

        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        ip = SecurityService.get_client_ip(request)
        ua = SecurityService.get_user_agent(request)
        ua_info = SecurityService.parse_user_agent(ua)
        fp = SecurityService.generate_fingerprint(request)

        UserSession.objects.filter(user=user).update(is_current=False)
        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                "user": user,
                "ip_address": ip,
                "user_agent": ua,
                "device_fingerprint": fp,
                "browser": ua_info["browser"],
                "os": ua_info["os"],
                "device_type": ua_info["device_type"],
                "is_current": True,
                "is_active": True,
            },
        )

        SecurityService.log_event(
            user,
            SecurityEventType.LOGIN_SUCCESS,
            request,
            details={"mfa_verified": mfa_verified},
        )

    @classmethod
    def logout_user(cls, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            UserSession.objects.filter(session_key=session_key).update(is_active=False)
            SecurityService.log_event(request.user, SecurityEventType.LOGOUT, request)
        logout(request)

    # ---- Password Reset -----------------------------------------------------

    @classmethod
    def request_password_reset(cls, email: str, request=None) -> Tuple[bool, str]:
        """
        Always returns a success-style message to prevent user enumeration.
        """
        safe_msg = (
            "If an account exists with that email address, "
            "we've sent a password reset link. Check your inbox."
        )
        try:
            user = User.objects.get(email__iexact=email.strip())
            # Invalidate any existing unused tokens for this user
            EmailToken.objects.filter(
                user=user,
                token_type=EmailToken.TokenType.RESET,
                used_at__isnull=True,
            ).update(used_at=timezone.now())

            token_obj = EmailToken.create_token(user, EmailToken.TokenType.RESET, hours=1)
            cls._send_reset_email(user, token_obj.token, request)
            SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_REQUESTED, request)
        except User.DoesNotExist:
            pass
        except Exception as exc:
            logger.error("Password reset request error: %s", exc)

        return True, safe_msg

    @classmethod
    def _send_reset_email(cls, user, token: str, request=None):
        try:
            domain = request.get_host() if request else getattr(settings, "SITE_DOMAIN", "localhost:5000")
            scheme = "https" if (not settings.DEBUG or request and request.is_secure()) else "http"
            reset_url = f"{scheme}://{domain}/password-reset/confirm/{token}/"

            subject = "Reset your InvoiceFlow password"
            html_body = render_to_string(
                "emails/password_reset.html",
                {"user": user, "reset_url": reset_url, "expiry_hours": 1},
            )
            plain_body = strip_tags(html_body)

            send_mail(
                subject,
                plain_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_body,
                fail_silently=True,
            )
        except Exception as exc:
            logger.error("Failed to send password reset email: %s", exc)

    @classmethod
    def validate_reset_token(cls, token: str) -> Tuple[bool, Optional[Any], str]:
        try:
            token_obj = EmailToken.objects.get(
                token=token,
                token_type=EmailToken.TokenType.RESET,
            )
            if token_obj.used_at is not None:
                return False, None, "This reset link has already been used. Please request a new one."
            if token_obj.is_expired:
                return False, None, "This reset link has expired. Please request a new one."
            return True, token_obj, ""
        except EmailToken.DoesNotExist:
            return False, None, "Invalid or expired reset link."
        except Exception as exc:
            logger.error("Token validation error: %s", exc)
            return False, None, "Unable to validate reset link. Please try again."

    @classmethod
    def complete_password_reset(cls, token: str, new_password: str, request=None) -> Tuple[bool, str]:
        try:
            is_valid, token_obj, error = cls.validate_reset_token(token)
            if not is_valid:
                return False, error

            is_strong, errors = PasswordValidator.validate(new_password)
            if not is_strong:
                return False, errors[0]

            user = token_obj.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            token_obj.mark_used()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.last_password_change = timezone.now()
            profile.save(update_fields=["last_password_change"])

            # Invalidate all active sessions for this user on password reset
            UserSession.objects.filter(user=user).update(is_active=False)

            SecurityService.log_event(user, SecurityEventType.PASSWORD_RESET_COMPLETED, request)
            return True, "Password reset successfully. You can now sign in with your new password."

        except Exception as exc:
            logger.error("Password reset completion error: %s", exc)
            return False, "Password reset failed. Please try again."

    # ---- Change Password (authenticated) ------------------------------------

    @classmethod
    def change_password(
        cls,
        user,
        current_password: str,
        new_password: str,
        request=None,
    ) -> Tuple[bool, str]:
        try:
            if not user.check_password(current_password):
                return False, "Current password is incorrect."

            is_strong, errors = PasswordValidator.validate(new_password)
            if not is_strong:
                return False, errors[0]

            user.set_password(new_password)
            user.save(update_fields=["password"])

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.last_password_change = timezone.now()
            profile.save(update_fields=["last_password_change"])

            SecurityService.log_event(user, SecurityEventType.PASSWORD_CHANGED, request)
            return True, "Password changed successfully."

        except Exception as exc:
            logger.error("Password change error: %s", exc)
            return False, "Password change failed. Please try again."


# ---------------------------------------------------------------------------
# Session Management Service
# ---------------------------------------------------------------------------

class SessionService:
    @staticmethod
    def get_user_sessions(user) -> list:
        return list(
            UserSession.objects.filter(user=user, is_active=True).order_by("-last_activity")
        )

    @staticmethod
    def revoke_session(user, session_id: int, request=None) -> Tuple[bool, str]:
        try:
            session = UserSession.objects.get(id=session_id, user=user)
            if session.is_current:
                return False, "You cannot revoke your current session here. Use Sign Out instead."
            session.is_active = False
            session.save(update_fields=["is_active"])
            SecurityService.log_event(user, SecurityEventType.SESSION_REVOKED, request)
            return True, "Session revoked successfully."
        except UserSession.DoesNotExist:
            return False, "Session not found."
        except Exception as exc:
            logger.error("Revoke session error: %s", exc)
            return False, "Failed to revoke session."

    @staticmethod
    def revoke_all_other_sessions(user, request=None) -> Tuple[bool, str]:
        try:
            current_key = request.session.session_key if request else None
            qs = UserSession.objects.filter(user=user, is_active=True)
            if current_key:
                qs = qs.exclude(session_key=current_key)
            count = qs.update(is_active=False)
            SecurityService.log_event(user, SecurityEventType.ALL_SESSIONS_REVOKED, request)
            return True, f"{count} other session(s) signed out."
        except Exception as exc:
            logger.error("Revoke all sessions error: %s", exc)
            return False, "Failed to revoke sessions."


# ---------------------------------------------------------------------------
# MFA Service (kept for backward compat with security_settings view)
# ---------------------------------------------------------------------------

class MFAService:
    @staticmethod
    def is_mfa_enabled(user) -> bool:
        try:
            return user.mfa_profile.is_enabled
        except Exception:
            return False

    @staticmethod
    def get_remaining_codes(user) -> int:
        try:
            return user.mfa_profile.get_remaining_codes_count()
        except Exception:
            return 0

    @classmethod
    def generate_setup_data(cls, user):
        import pyotp, qrcode
        from io import BytesIO
        from base64 import b64encode

        secret = pyotp.random_base32()
        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret = secret
        mfa_profile.save(update_fields=["secret"])

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="InvoiceFlow")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        qr_code = b64encode(buf.getvalue()).decode()

        return secret, qr_code, provisioning_uri

    @classmethod
    def verify_mfa(cls, user, code: str, request=None) -> Tuple[bool, str]:
        import pyotp
        try:
            mfa_profile = user.mfa_profile
            totp = pyotp.TOTP(mfa_profile.secret)
            if totp.verify(code, valid_window=1):
                return True, "MFA verified."
            if code.upper() in [c.upper() for c in (mfa_profile.recovery_codes or [])]:
                mfa_profile.recovery_codes = [
                    c for c in mfa_profile.recovery_codes if c.upper() != code.upper()
                ]
                mfa_profile.save(update_fields=["recovery_codes"])
                return True, "Recovery code accepted."
            return False, "Invalid code. Please try again."
        except Exception as exc:
            logger.error("MFA verify error: %s", exc)
            return False, "MFA verification failed."

    @classmethod
    def enable_mfa(cls, user, secret: str, code: str, request=None):
        import pyotp
        try:
            totp = pyotp.TOTP(secret)
            if not totp.verify(code):
                return False, [], "Invalid code. Please try again."
            backup_codes = [secrets.token_hex(5).upper() for _ in range(10)]
            mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
            mfa_profile.secret = secret
            mfa_profile.is_enabled = True
            mfa_profile.recovery_codes = backup_codes
            mfa_profile.save()
            return True, backup_codes, "Two-factor authentication enabled."
        except Exception as exc:
            logger.error("Enable MFA error: %s", exc)
            return False, [], "Failed to enable MFA."

    @classmethod
    def disable_mfa(cls, user, password: str, request=None) -> Tuple[bool, str]:
        try:
            if not user.check_password(password):
                return False, "Incorrect password."
            mfa_profile = user.mfa_profile
            mfa_profile.is_enabled = False
            mfa_profile.secret = ""
            mfa_profile.recovery_codes = []
            mfa_profile.save()
            return True, "Two-factor authentication disabled."
        except Exception as exc:
            logger.error("Disable MFA error: %s", exc)
            return False, "Failed to disable MFA."


# ---------------------------------------------------------------------------
# Invitation Service (stub — workspace invitations used elsewhere)
# ---------------------------------------------------------------------------

class InvitationService:
    @staticmethod
    def validate_invitation(token: str):
        try:
            inv = WorkspaceInvitation.objects.get(token=token)
            if inv.is_expired or inv.accepted_at:
                return False, None, "This invitation is invalid or has expired."
            return True, inv, ""
        except WorkspaceInvitation.DoesNotExist:
            return False, None, "Invitation not found."
        except Exception as exc:
            logger.error("Invitation validation error: %s", exc)
            return False, None, "Unable to validate invitation."

    @staticmethod
    def accept_invitation(token: str, user, request=None) -> Tuple[bool, str]:
        try:
            inv = WorkspaceInvitation.objects.get(token=token)
            if inv.is_expired or inv.accepted_at:
                return False, "This invitation is no longer valid."
            WorkspaceMember.objects.get_or_create(workspace=inv.workspace, user=user, defaults={"role": inv.role})
            inv.accepted_at = timezone.now()
            inv.save(update_fields=["accepted_at"])
            return True, f"You've joined {inv.workspace.name}."
        except WorkspaceInvitation.DoesNotExist:
            return False, "Invitation not found."
        except Exception as exc:
            logger.error("Accept invitation error: %s", exc)
            return False, "Failed to accept invitation."
