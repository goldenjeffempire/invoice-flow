"""
Security Service for InvoiceFlow
Handles suspicious login detection, password breach checking, device management,
and security event logging.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class SecurityEventType:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGIN_SUSPICIOUS = "login_suspicious"
    LOGIN_NEW_DEVICE = "login_new_device"
    LOGIN_NEW_LOCATION = "login_new_location"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFIED = "email_verified"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_VERIFIED = "mfa_verified"
    MFA_FAILED = "mfa_failed"
    SESSION_REVOKED = "session_revoked"
    ALL_SESSIONS_REVOKED = "all_sessions_revoked"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SuspiciousLoginReason:
    NEW_DEVICE = "new_device"
    NEW_LOCATION = "new_location"
    UNUSUAL_TIME = "unusual_time"
    RAPID_LOCATION_CHANGE = "rapid_location_change"
    MULTIPLE_FAILED_ATTEMPTS = "multiple_failed_attempts"
    BREACHED_PASSWORD = "breached_password"


class PasswordBreachService:
    """Check passwords against HaveIBeenPwned using k-anonymity."""
    
    HIBP_API_URL = "https://api.pwnedpasswords.com/range/"
    CACHE_PREFIX = "hibp_prefix_"
    CACHE_DURATION = 86400  # 24 hours
    
    @classmethod
    def check_password_breach(cls, password: str) -> tuple[bool, int]:
        """
        Check if password has been exposed in known data breaches.
        Uses k-anonymity: only first 5 chars of SHA1 hash are sent to API.
        Returns (is_breached, breach_count).
        """
        import urllib.request
        import urllib.error
        
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        cache_key = f"{cls.CACHE_PREFIX}{prefix}"
        cached_result = cache.get(cache_key)
        
        if cached_result is None:
            try:
                req = urllib.request.Request(
                    f"{cls.HIBP_API_URL}{prefix}",
                    headers={"User-Agent": "InvoiceFlow-Security-Check"}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    cached_result = response.read().decode('utf-8')
                    cache.set(cache_key, cached_result, cls.CACHE_DURATION)
            except (urllib.error.URLError, TimeoutError) as e:
                logger.warning(f"HIBP API request failed: {e}")
                return False, 0
        
        for line in cached_result.splitlines():
            parts = line.split(':')
            if len(parts) == 2 and parts[0] == suffix:
                try:
                    return True, int(parts[1])
                except ValueError:
                    return True, 1
        
        return False, 0
    
    @classmethod
    def is_password_weak(cls, password: str) -> tuple[bool, list[str]]:
        """Check if password meets security requirements."""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        if len(password) > 128:
            issues.append("Password must be at most 128 characters long")
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one number")
        
        common_passwords = {
            'password', 'password123', '123456', 'qwerty', 'letmein',
            'welcome', 'admin', 'login', 'abc123', 'monkey',
        }
        if password.lower() in common_passwords:
            issues.append("This password is too common")
        
        return len(issues) > 0, issues


class DeviceFingerprintService:
    """Generate and verify device fingerprints for known device tracking."""
    
    @staticmethod
    def generate_fingerprint(request: HttpRequest) -> str:
        """Generate a device fingerprint from request headers."""
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
        ]
        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:32]
    
    @staticmethod
    def parse_user_agent(user_agent: str) -> dict[str, str]:
        """Parse user agent string into device info."""
        info = {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device_type': 'desktop',
        }
        
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
        elif 'linux' in ua_lower:
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


class SuspiciousLoginDetector:
    """Detect suspicious login patterns and behaviors."""
    
    UNUSUAL_HOUR_START = 2  # 2 AM
    UNUSUAL_HOUR_END = 5    # 5 AM
    RAPID_LOCATION_THRESHOLD_HOURS = 1
    MAX_DISTANCE_PER_HOUR_KM = 800  # Roughly max commercial flight speed
    
    @classmethod
    def analyze_login(
        cls,
        request: HttpRequest,
        user: User,
    ) -> tuple[bool, list[str]]:
        """
        Analyze a login attempt for suspicious patterns.
        Returns (is_suspicious, list of reasons).
        """
        from .models import LoginAttempt, UserSession
        
        reasons = []
        client_ip = cls._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        fingerprint = DeviceFingerprintService.generate_fingerprint(request)
        
        if cls._is_new_device(user, fingerprint):
            reasons.append(SuspiciousLoginReason.NEW_DEVICE)
        
        if cls._is_new_ip(user, client_ip):
            reasons.append(SuspiciousLoginReason.NEW_LOCATION)
        
        if cls._is_unusual_time(user):
            reasons.append(SuspiciousLoginReason.UNUSUAL_TIME)
        
        if cls._has_recent_failed_attempts(user.username, client_ip):
            reasons.append(SuspiciousLoginReason.MULTIPLE_FAILED_ATTEMPTS)
        
        is_suspicious = len(reasons) >= 2 or SuspiciousLoginReason.RAPID_LOCATION_CHANGE in reasons
        
        return is_suspicious, reasons
    
    @classmethod
    def _get_client_ip(cls, request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    @classmethod
    def _is_new_device(cls, user: User, fingerprint: str) -> bool:
        """Check if this is a new device for the user."""
        from .models import KnownDevice
        try:
            return not KnownDevice.objects.filter(
                user=user,
                fingerprint=fingerprint,
                is_trusted=True,
            ).exists()
        except Exception:
            return True
    
    @classmethod
    def _is_new_ip(cls, user: User, ip_address: str) -> bool:
        """Check if this is a new IP address for the user."""
        from .models import UserSession
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return not UserSession.objects.filter(
            user=user,
            ip_address=ip_address,
            created_at__gte=thirty_days_ago,
        ).exists()
    
    @classmethod
    def _is_unusual_time(cls, user: User) -> bool:
        """Check if login is at an unusual time."""
        current_hour = timezone.localtime().hour
        return cls.UNUSUAL_HOUR_START <= current_hour < cls.UNUSUAL_HOUR_END
    
    @classmethod
    def _has_recent_failed_attempts(cls, username: str, ip_address: str) -> bool:
        """Check for recent failed login attempts."""
        from .models import LoginAttempt
        
        one_hour_ago = timezone.now() - timedelta(hours=1)
        failed_count = LoginAttempt.objects.filter(
            models.Q(username__iexact=username) | models.Q(ip_address=ip_address),
            success=False,
            created_at__gte=one_hour_ago,
        ).count()
        
        return failed_count >= 3


class SecurityEventService:
    """Log and manage security events for audit trail."""
    
    @classmethod
    def log_event(
        cls,
        user: Optional[User],
        event_type: str,
        ip_address: str = "",
        user_agent: str = "",
        details: Optional[dict] = None,
        severity: str = "info",
    ) -> None:
        """Log a security event."""
        from .models import SecurityEvent
        
        try:
            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                ip_address=ip_address or None,
                user_agent=user_agent[:500] if user_agent else "",
                details=details or {},
                severity=severity,
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    @classmethod
    def get_user_security_events(
        cls,
        user: User,
        days: int = 30,
        event_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Get recent security events for a user."""
        from .models import SecurityEvent
        
        cutoff = timezone.now() - timedelta(days=days)
        query = SecurityEvent.objects.filter(user=user, created_at__gte=cutoff)
        
        if event_types:
            query = query.filter(event_type__in=event_types)
        
        events = []
        for event in query.order_by('-created_at')[:100]:
            events.append({
                'id': event.id,
                'event_type': event.event_type,
                'event_display': event.get_event_display(),
                'ip_address': event.ip_address or 'Unknown',
                'created_at': event.created_at,
                'severity': event.severity,
                'details': event.details,
            })
        
        return events


class KnownDeviceService:
    """Manage known/trusted devices for users."""
    
    @classmethod
    def register_device(
        cls,
        user: User,
        request: HttpRequest,
        device_name: str = "",
    ) -> Any:
        """Register a new known device."""
        from .models import KnownDevice
        
        fingerprint = DeviceFingerprintService.generate_fingerprint(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_info = DeviceFingerprintService.parse_user_agent(user_agent)
        
        ip_address = SuspiciousLoginDetector._get_client_ip(request)
        
        device, created = KnownDevice.objects.update_or_create(
            user=user,
            fingerprint=fingerprint,
            defaults={
                'device_name': device_name or f"{device_info['browser']} on {device_info['os']}",
                'user_agent': user_agent[:500],
                'ip_address': ip_address,
                'browser': device_info['browser'],
                'os': device_info['os'],
                'device_type': device_info['device_type'],
                'is_trusted': True,
                'last_used': timezone.now(),
            }
        )
        
        return device
    
    @classmethod
    def get_user_devices(cls, user: User) -> list[dict]:
        """Get all known devices for a user."""
        from .models import KnownDevice
        
        devices = []
        for device in KnownDevice.objects.filter(user=user).order_by('-last_used'):
            devices.append({
                'id': device.id,
                'device_name': device.device_name,
                'browser': device.browser,
                'os': device.os,
                'device_type': device.device_type,
                'ip_address': device.ip_address or 'Unknown',
                'is_trusted': device.is_trusted,
                'last_used': device.last_used,
                'created_at': device.created_at,
            })
        
        return devices
    
    @classmethod
    def revoke_device(cls, user: User, device_id: int) -> bool:
        """Revoke trust from a device."""
        from .models import KnownDevice
        
        try:
            device = KnownDevice.objects.get(id=device_id, user=user)
            device.is_trusted = False
            device.save(update_fields=['is_trusted'])
            return True
        except KnownDevice.DoesNotExist:
            return False


class WorkspaceInvitationService:
    """Handle workspace/team invitations."""
    
    TOKEN_LENGTH = 32
    DEFAULT_EXPIRY_DAYS = 7
    
    @classmethod
    def create_invitation(
        cls,
        inviter: User,
        email: str,
        role: str = "member",
        expires_days: int = DEFAULT_EXPIRY_DAYS,
    ) -> Any:
        """Create a new workspace invitation."""
        from .models import WorkspaceInvitation
        
        token = secrets.token_urlsafe(cls.TOKEN_LENGTH)
        expires_at = timezone.now() + timedelta(days=expires_days)
        
        invitation = WorkspaceInvitation.objects.create(
            inviter=inviter,
            email=email.lower(),
            token=token,
            role=role,
            expires_at=expires_at,
        )
        
        return invitation
    
    @classmethod
    def validate_invitation(cls, token: str) -> tuple[bool, Optional[Any], str]:
        """
        Validate an invitation token.
        Returns (is_valid, invitation, error_message).
        """
        from .models import WorkspaceInvitation
        
        try:
            invitation = WorkspaceInvitation.objects.get(token=token)
        except WorkspaceInvitation.DoesNotExist:
            return False, None, "Invalid invitation link."
        
        if invitation.is_accepted:
            return False, invitation, "This invitation has already been accepted."
        
        if invitation.is_revoked:
            return False, invitation, "This invitation has been revoked."
        
        if invitation.expires_at < timezone.now():
            return False, invitation, "This invitation has expired."
        
        return True, invitation, ""
    
    @classmethod
    @transaction.atomic
    def accept_invitation(cls, token: str, user: User) -> tuple[bool, str]:
        """
        Accept a workspace invitation.
        Returns (success, message).
        """
        is_valid, invitation, error_message = cls.validate_invitation(token)
        if not is_valid:
            return False, error_message
        
        if invitation.email.lower() != user.email.lower():
            return False, "This invitation was sent to a different email address."
        
        invitation.is_accepted = True
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save()
        
        return True, f"Welcome to the team! You've joined as a {invitation.role}."
    
    @classmethod
    def revoke_invitation(cls, invitation_id: int, user: User) -> bool:
        """Revoke an invitation (only inviter can revoke)."""
        from .models import WorkspaceInvitation
        
        try:
            invitation = WorkspaceInvitation.objects.get(
                id=invitation_id,
                inviter=user,
                is_accepted=False,
            )
            invitation.is_revoked = True
            invitation.save(update_fields=['is_revoked'])
            return True
        except WorkspaceInvitation.DoesNotExist:
            return False
    
    @classmethod
    def get_pending_invitations(cls, user: User) -> list[dict]:
        """Get invitations sent by the user that are still pending."""
        from .models import WorkspaceInvitation
        
        invitations = []
        for inv in WorkspaceInvitation.objects.filter(
            inviter=user,
            is_accepted=False,
            is_revoked=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at'):
            invitations.append({
                'id': inv.id,
                'email': inv.email,
                'role': inv.role,
                'created_at': inv.created_at,
                'expires_at': inv.expires_at,
            })
        
        return invitations
