"""
Permission classes and decorators for API access control.
Implements role-based and object-level permissions.
"""
from rest_framework import permissions
from rest_framework.decorators import permission_classes


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission: User can only access their own invoices."""
    
    def has_object_permission(self, request, view, obj):
        if not request or not hasattr(request, 'user'):
            return False
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return obj.user == request.user


class IsAuthenticated(permissions.IsAuthenticated):
    """Permission: User must be authenticated."""
    pass


class IsInvoiceOwnerOrAdmin(permissions.BasePermission):
    """Permission: Only invoice owner or admin can access."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.user == request.user


class CanViewPublicInvoice(permissions.BasePermission):
    """Permission: Public invoice access with valid token."""
    
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            return obj.user == request.user
        
        token = request.query_params.get('token')
        if token and hasattr(obj, 'public_token'):
            return obj.public_token.is_valid()
        return False


class CanInitializePayment(permissions.BasePermission):
    """Permission: Only invoice owner can initialize payment."""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class HasEmailVerification(permissions.BasePermission):
    """Permission: User must have verified email for sensitive operations."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, 'userprofile', None)
        return profile and profile.email_verified if profile else False


class HasMFAVerification(permissions.BasePermission):
    """Permission: User must have completed MFA verification."""
    
    def has_permission(self, request, view):
        return request.session.get('mfa_verified', False)


class RateLimitByUser(permissions.BasePermission):
    """Permission: Apply rate limiting based on user."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        from django.core.cache import cache
        cache_key = f"user_rate_limit:{request.user.id}"
        request_count = cache.get(cache_key, 0)
        if request_count >= 100:
            return False
        cache.set(cache_key, request_count + 1, 3600)
        return True
