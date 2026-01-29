from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import (
    EmailVerificationToken,
    LoginAttempt,
    MFAProfile,
    UserProfile,
    UserSession,
)

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class EmailNotVerifiedError(Exception):
    """Raised when a user's email is not verified."""
    pass


class MFANotVerifiedError(Exception):
    """Raised when MFA verification is required but not completed."""
    pass


def require_verified_email(user: User) -> None:
    """
    Check if the user has a verified email address.
    Raises EmailNotVerifiedError if not verified.
    Required for all payment and sensitive operations.
    """
    if not user.is_authenticated:
        raise EmailNotVerifiedError("Authentication required.")
    
    if not user.is_active:
        raise EmailNotVerifiedError("Please verify your email address to continue.")
    
    try:
        profile = UserProfile.objects.get(user=user)
        if not profile.email_verified:
            raise EmailNotVerifiedError("Please verify your email address to continue.")
    except UserProfile.DoesNotExist:
        raise EmailNotVerifiedError("User profile not found. Please contact support.")


def require_mfa_verified(request) -> None:
    """
    Check if MFA has been completed in current session.
    Raises MFANotVerifiedError if not verified.
    Required for payments and sensitive operations.
    """
    if not request.session.get("mfa_verified", False):
        raise MFANotVerifiedError("MFA verification required for this operation.")


class AuthenticationService:
    """Core authentication service handling login, logout, and session management."""

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip

    @classmethod
    def check_rate_limit(cls, request: HttpRequest, username: str) -> tuple[bool, str]:
        """Check if login is rate limited. Returns (is_locked, message)."""
        client_ip = cls.get_client_ip(request)
        lockout_threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 5)
        lockout_duration = getattr(settings, "ACCOUNT_LOCKOUT_DURATION", 900)

        ip_cache_key = f"login_attempt:ip:{client_ip}"
        user_cache_key = f"login_attempt:user:{username.lower()}" if username else None

        ip_attempts = cache.get(ip_cache_key, 0)
        user_attempts = cache.get(user_cache_key, 0) if user_cache_key else 0

        if ip_attempts >= lockout_threshold:
            return True, "Too many login attempts from this location. Please try again in 15 minutes."

        if user_attempts >= lockout_threshold:
            return True, "This account is temporarily locked due to too many failed attempts. Please try again in 15 minutes."

        return False, ""

    @classmethod
    def record_login_attempt(
        cls,
        request: HttpRequest,
        username: str,
        success: bool,
        failure_reason: str = "",
    ) -> None:
        """Record a login attempt for security tracking."""
        client_ip = cls.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        LoginAttempt.objects.create(
            username=username or "unknown",
            ip_address=client_ip,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
        )

        if not success:
            lockout_duration = getattr(settings, "ACCOUNT_LOCKOUT_DURATION", 900)
            ip_cache_key = f"login_attempt:ip:{client_ip}"
            user_cache_key = f"login_attempt:user:{username.lower()}" if username else None

            ip_attempts = cache.get(ip_cache_key, 0)
            cache.set(ip_cache_key, ip_attempts + 1, lockout_duration)

            if user_cache_key:
                user_attempts = cache.get(user_cache_key, 0)
                cache.set(user_cache_key, user_attempts + 1, lockout_duration)
        else:
            ip_cache_key = f"login_attempt:ip:{client_ip}"
            user_cache_key = f"login_attempt:user:{username.lower()}" if username else None
            cache.delete(ip_cache_key)
            if user_cache_key:
                cache.delete(user_cache_key)

    @classmethod
    def authenticate_user(
        cls,
        request: HttpRequest,
        username: str,
        password: str,
    ) -> tuple[User | None, str]:
        """Authenticate user credentials. Returns (user, error_message)."""
        is_locked, lock_message = cls.check_rate_limit(request, username)
        if is_locked:
            return None, lock_message

        user = authenticate(request, username=username, password=password)

        if user is None:
            cls.record_login_attempt(request, username, success=False, failure_reason="Invalid credentials")
            return None, "Invalid username or password."

        if not user.is_active:
            cls.record_login_attempt(request, username, success=False, failure_reason="Account inactive")
            return None, "This account is inactive. Please verify your email."

        cls.record_login_attempt(request, username, success=True)
        return user, ""

    @classmethod
    def login_user(cls, request: HttpRequest, user: User) -> dict[str, Any]:
        """Complete login process with session rotation and tracking."""
        # Ensure email is verified before login if required
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.email_verified and not user.is_staff:
             return {
                "success": False,
                "error": "Please verify your email address to continue.",
                "email_verified": False
            }

        # Invalidate old sessions for this user (session fixation prevention)
        try:
            UserSession.objects.filter(user=user).delete()
        except Exception as e:
            logger.warning(f"Failed to delete old sessions: {e}")

        # Create fresh session
        login(request, user)
        request.session.cycle_key() # Explicit rotation

        client_ip = cls.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Track new session
        try:
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or "",
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning(f"Failed to create user session: {e}")

        # Check email verification status
        email_verified = False
        try:
            profile = UserProfile.objects.get(user=user)
            email_verified = profile.email_verified
        except UserProfile.DoesNotExist:
            email_verified = False

        # Check MFA status
        mfa_required = False
        if getattr(settings, "MFA_ENABLED", False):
            try:
                mfa_profile = MFAProfile.objects.get(user=user)
                if mfa_profile.is_enabled:
                    request.session["mfa_verified"] = False
                    mfa_required = True
            except MFAProfile.DoesNotExist:
                pass

        if not mfa_required:
            request.session["mfa_verified"] = True

        return {
            "success": True,
            "mfa_required": mfa_required,
            "email_verified": email_verified,
            "user": user,
        }

    @classmethod
    def logout_user(cls, request: HttpRequest) -> None:
        """Complete logout process with session cleanup."""
        if request.user.is_authenticated and request.session.session_key:
            try:
                UserSession.objects.filter(
                    user=request.user,
                    session_key=request.session.session_key,
                ).delete()
            except Exception as e:
                logger.warning(f"Failed to delete user session: {e}")

        request.session.pop("mfa_verified", None)
        logout(request)


class RegistrationService:
    """Handle user registration, email verification, and account activation."""

    @classmethod
    @transaction.atomic
    def create_user(
        cls,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        require_email_verification: bool = True,
    ) -> tuple[User | None, str, EmailVerificationToken | None]:
        """Create a new user account. Returns (user, error_message, token)."""
        if User.objects.filter(username__iexact=username).exists():
            return None, "This username is already taken.", None

        if User.objects.filter(email__iexact=email).exists():
            return None, "An account with this email already exists.", None

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=not require_email_verification,
        )

        UserProfile.objects.create(user=user)
        token = None

        if require_email_verification:
            token = EmailVerificationToken.create_verification_token(
                user=user,
                email=email,
                token_type="signup",
                expires_hours=24,
            )

        # Redact email in logs
        logger.info(f"New user registered: {username} (email redacted)")
        return user, "", token

    @classmethod
    def verify_email(cls, token: str) -> tuple[bool, str]:
        """Verify email using token. Returns (success, message)."""
        try:
            email_token = EmailVerificationToken.objects.get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return False, "Invalid or expired verification link."

        if not email_token.is_valid:
            return False, "This verification link has expired or already been used."

        user = email_token.user
        user.is_active = True
        user.save(update_fields=["is_active"])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])

        email_token.mark_used()

        logger.info(f"Email verified for user: {user.username}")
        return True, "Your email has been verified. You can now log in."

    @classmethod
    def resend_verification_email(
        cls,
        email: str,
    ) -> tuple[bool, str, EmailVerificationToken | None]:
        """Resend verification email. Returns (success, message, token)."""
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
        except User.DoesNotExist:
            return False, "No pending verification found for this email.", None

        token = EmailVerificationToken.create_verification_token(
            user=user,
            email=email,
            token_type="signup",
            expires_hours=24,
        )

        return True, "Verification email has been resent.", token


class PasswordService:
    """Handle password reset and change operations."""

    @classmethod
    def request_password_reset(cls, email: str) -> tuple[bool, str, EmailVerificationToken | None]:
        """Request password reset. Returns (success, message, token)."""
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return True, "If an account exists with this email, you will receive a password reset link.", None

        token = EmailVerificationToken.create_verification_token(
            user=user,
            email=email,
            token_type="password_reset",
            expires_hours=1,
        )

        logger.info(f"Password reset requested for: {user.username}")
        return True, "If an account exists with this email, you will receive a password reset link.", token

    @classmethod
    def validate_reset_token(cls, token: str) -> tuple[bool, User | None, str]:
        """Validate password reset token. Returns (is_valid, user, message)."""
        try:
            email_token = EmailVerificationToken.objects.get(
                token=token,
                token_type="password_reset",
            )
        except EmailVerificationToken.DoesNotExist:
            return False, None, "Invalid or expired reset link."

        if not email_token.is_valid:
            return False, None, "This reset link has expired or already been used."

        return True, email_token.user, ""

    @classmethod
    def reset_password(cls, token: str, new_password: str) -> tuple[bool, str]:
        """Reset password using token. Returns (success, message)."""
        is_valid, user, error_msg = cls.validate_reset_token(token)
        if not is_valid or user is None:
            return False, error_msg

        user.set_password(new_password)
        user.save(update_fields=["password"])

        try:
            email_token = EmailVerificationToken.objects.get(token=token)
            email_token.mark_used()
        except EmailVerificationToken.DoesNotExist:
            pass

        UserSession.objects.filter(user=user).delete()

        logger.info(f"Password reset completed for: {user.username}")
        return True, "Your password has been reset. Please log in with your new password."

    @classmethod
    def change_password(
        cls,
        user: User,
        current_password: str,
        new_password: str,
    ) -> tuple[bool, str]:
        """Change password for authenticated user. Returns (success, message)."""
        if not user.check_password(current_password):
            return False, "Current password is incorrect."

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info(f"Password changed for: {user.username}")
        return True, "Your password has been changed successfully."


class SessionService:
    """Handle user session management and device tracking."""

    @classmethod
    def get_user_sessions(cls, user: User, current_session_key: str = "") -> list[dict[str, Any]]:
        """Get all active sessions for a user."""
        sessions = UserSession.objects.filter(user=user).order_by("-last_seen")

        result = []
        for session in sessions:
            result.append({
                "id": session.id,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "last_seen": session.last_seen,
                "created_at": session.created_at,
                "is_current": session.session_key == current_session_key,
                "is_revoked": session.is_revoked,
            })

        return result

    @classmethod
    def revoke_session(cls, user: User, session_id: int) -> tuple[bool, str]:
        """Revoke a specific session. Returns (success, message)."""
        try:
            session = UserSession.objects.get(id=session_id, user=user)
            session.revoke()
            return True, "Session has been revoked."
        except UserSession.DoesNotExist:
            return False, "Session not found."

    @classmethod
    def revoke_all_sessions(cls, user: User, except_session_key: str = "") -> int:
        """Revoke all sessions except the current one. Returns count of revoked sessions."""
        sessions = UserSession.objects.filter(user=user)
        if except_session_key:
            sessions = sessions.exclude(session_key=except_session_key)

        count = sessions.count()
        for session in sessions:
            session.revoke()

        return count


class MFAService:
    """Handle Multi-Factor Authentication setup and verification."""

    @classmethod
    def setup_mfa(cls, user: User) -> tuple[str, str, list[str]]:
        """Setup MFA for a user. Returns (secret_key, qr_uri, recovery_codes)."""
        import base64
        import secrets

        secret = base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")

        issuer = getattr(settings, "MFA_ISSUER_NAME", "InvoiceFlow")
        qr_uri = f"otpauth://totp/{issuer}:{user.email}?secret={secret}&issuer={issuer}"

        recovery_count = getattr(settings, "MFA_RECOVERY_CODES_COUNT", 10)
        recovery_codes = [secrets.token_hex(4).upper() for _ in range(recovery_count)]

        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes]

        mfa_profile, _ = MFAProfile.objects.get_or_create(user=user)
        mfa_profile.secret_key = secret
        mfa_profile.recovery_codes = hashed_codes
        mfa_profile.save()

        return secret, qr_uri, recovery_codes

    @classmethod
    def verify_totp(cls, user: User, code: str) -> tuple[bool, str]:
        """Verify TOTP code. Returns (success, message)."""
        import pyotp

        try:
            mfa_profile = MFAProfile.objects.get(user=user)
        except MFAProfile.DoesNotExist:
            return False, "MFA is not set up for this account."

        if not mfa_profile.secret_key:
            return False, "MFA is not properly configured."

        totp = pyotp.TOTP(mfa_profile.secret_key)
        if totp.verify(code, valid_window=1):
            mfa_profile.last_used = timezone.now()
            mfa_profile.save()
            return True, ""

        return False, "Invalid verification code."

    @classmethod
    def verify_recovery_code(cls, user: User, code: str) -> tuple[bool, str]:
        """Verify recovery code. Returns (success, message)."""
        try:
            mfa_profile = MFAProfile.objects.get(user=user)
        except MFAProfile.DoesNotExist:
            return False, "MFA is not set up for this account."

        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()

        if code_hash in mfa_profile.recovery_codes:
            mfa_profile.recovery_codes.remove(code_hash)
            mfa_profile.last_used = timezone.now()
            mfa_profile.save()
            return True, ""

        return False, "Invalid recovery code."

    @classmethod
    def enable_mfa(cls, user: User, verification_code: str) -> tuple[bool, str]:
        """Enable MFA after initial setup verification. Returns (success, message)."""
        success, error = cls.verify_totp(user, verification_code)
        if not success:
            return False, error

        try:
            mfa_profile = MFAProfile.objects.get(user=user)
            mfa_profile.is_enabled = True
            mfa_profile.save(update_fields=["is_enabled"])
            return True, "MFA has been enabled successfully."
        except MFAProfile.DoesNotExist:
            return False, "MFA setup not found."

    @classmethod
    def disable_mfa(cls, user: User, password: str) -> tuple[bool, str]:
        """Disable MFA for a user. Returns (success, message)."""
        if not user.check_password(password):
            return False, "Incorrect password."

        try:
            mfa_profile = MFAProfile.objects.get(user=user)
            mfa_profile.is_enabled = False
            mfa_profile.secret_key = ""
            mfa_profile.recovery_codes = []
            mfa_profile.save()
            return True, "MFA has been disabled."
        except MFAProfile.DoesNotExist:
            return True, "MFA was not enabled."
