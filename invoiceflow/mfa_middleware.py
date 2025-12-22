"""
MFA Enforcement Middleware for InvoiceFlow.
Ensures users with MFA enabled complete verification before accessing protected resources.
"""

import logging
from typing import Callable

from django.conf import settings
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import resolve, Resolver404

logger = logging.getLogger(__name__)


class MFAEnforcementMiddleware:
    """
    Enforces MFA verification for authenticated users.
    - Browser → redirect
    - API → JSON 403
    """

    EXEMPT_URL_NAMES = {
        "mfa_setup",
        "mfa_verify",
        "login",
        "logout",
        "signup",
        "password_reset",
        "password_reset_done",
        "password_reset_confirm",
        "password_reset_complete",
        "health_check",
        "readiness_check",
        "liveness_check",
        "home",
        "verify_email",
        "verification_sent",
        "resend_verification",
    }

    EXEMPT_PATH_PREFIXES = (
        "/static/",
        "/media/",
        "/health/",
        "/api/consent/",
    )

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, "MFA_ENABLED", False):
            return self.get_response(request)

        user = request.user

        if not user.is_authenticated:
            return self.get_response(request)

        # Staff / superusers may bypass MFA if desired
        if user.is_staff or user.is_superuser:
            return self.get_response(request)

        if self._is_exempt_path(request.path):
            return self.get_response(request)

        if self._is_exempt_url(request):
            return self.get_response(request)

        if request.session.get("mfa_verified", False):
            return self.get_response(request)

        try:
            from invoices.models import MFAProfile

            mfa_profile = MFAProfile.objects.get(user=user)

            if mfa_profile.is_enabled:
                logger.warning(
                    "MFA required: user=%s path=%s",
                    user.username,
                    request.path,
                )

                if self._is_api_request(request):
                    return JsonResponse(
                        {"detail": "MFA verification required."},
                        status=403,
                    )

                return redirect("mfa_verify")

        except MFAProfile.DoesNotExist:
            pass

        return self.get_response(request)

    @staticmethod
    def _is_api_request(request: HttpRequest) -> bool:
        return request.path.startswith("/api/") or request.headers.get(
            "Accept"
        ) == "application/json"

    def _is_exempt_path(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.EXEMPT_PATH_PREFIXES)

    def _is_exempt_url(self, request: HttpRequest) -> bool:
        try:
            match = resolve(request.path)
            return match.url_name in self.EXEMPT_URL_NAMES
        except Resolver404:
            return False
