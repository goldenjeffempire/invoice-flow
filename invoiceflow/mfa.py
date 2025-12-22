from django.core.exceptions import PermissionDenied


def require_mfa(user):
    """
    Enforce MFA at service / business-logic level.
    """
    if not user.is_authenticated:
        raise PermissionDenied("Authentication required")

    mfa_profile = getattr(user, "mfa_profile", None)

    if not mfa_profile or not mfa_profile.is_enabled:
        raise PermissionDenied("Multi-factor authentication required")
