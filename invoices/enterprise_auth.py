"""Enterprise-grade authentication and API key management."""

import secrets
import hashlib
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings
from typing import Optional, Tuple


class APIKey(models.Model):
    """Securely managed API keys for programmatic access."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=255)
    key_hash = models.CharField(max_length=255, unique=True)  # Hashed for security
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    scopes = models.JSONField(default=list)  # ['invoices:read', 'invoices:write', 'payments:read']
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_active"])]
    
    def __str__(self) -> str:
        return f"API Key: {self.name}"
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure random API key."""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @classmethod
    def create_key(cls, user: settings.AUTH_USER_MODEL, name: str, scopes: list, expires_days: Optional[int] = None):
        """Create a new API key."""
        key = cls.generate_key()
        key_hash = cls.hash_key(key)
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_key = cls.objects.create(
            user=user,
            name=name,
            key_hash=key_hash,
            expires_at=expires_at,
            scopes=scopes
        )
        return key, api_key
    
    @classmethod
    def authenticate(cls, key: str) -> Tuple[Optional[settings.AUTH_USER_MODEL], Optional['APIKey']]:
        """Authenticate with API key."""
        key_hash = cls.hash_key(key)
        try:
            api_key = cls.objects.get(key_hash=key_hash, is_active=True)
            
            # Check expiration
            if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                return None, None
            
            # Update last used
            api_key.last_used = datetime.utcnow()
            api_key.save(update_fields=['last_used'])
            
            return api_key.user, api_key
        except cls.DoesNotExist:
            return None, None
    
    def has_scope(self, scope: str) -> bool:
        """Check if key has required scope."""
        return scope in self.scopes


class SessionToken(models.Model):
    """Secure session tokens for stateless authentication."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="session_tokens")
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_valid = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_valid"])]
    
    @staticmethod
    def generate_token() -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_token(cls, user: settings.AUTH_USER_MODEL, ip_address: str = None, user_agent: str = None, expires_hours: int = 24):
        """Create new session token."""
        token = cls.generate_token()
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[settings.AUTH_USER_MODEL]:
        """Verify session token and return user."""
        try:
            session = cls.objects.get(token=token, is_valid=True)
            
            # Check expiration
            if datetime.utcnow() > session.expires_at:
                session.is_valid = False
                session.save(update_fields=['is_valid'])
                return None
            
            return session.user
        except cls.DoesNotExist:
            return None
    
    def invalidate(self):
        """Invalidate token (logout)."""
        self.is_valid = False
        self.save(update_fields=['is_valid'])


class AuthenticationHelper:
    """Helper methods for authentication."""
    
    @staticmethod
    def authenticate_request(request) -> Tuple[Optional[settings.AUTH_USER_MODEL], Optional[str]]:
        """Extract user from request (JWT, API Key, or Session)."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # API Key authentication
        if auth_header.startswith('Bearer sk_'):
            key = auth_header.replace('Bearer ', '').strip()
            user, api_key = APIKey.authenticate(key)
            if user:
                return user, 'api_key'
        
        # Session token authentication
        elif auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '').strip()
            user = SessionToken.verify_token(token)
            if user:
                return user, 'session_token'
        
        # Default to authenticated user
        if request.user.is_authenticated:
            return request.user, 'session'
        
        return None, None
