"""
MFA Enforcement Middleware for InvoiceFlow.
"""
import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import resolve, Resolver404

logger = logging.getLogger(__name__)

class MFAEnforcementMiddleware:
    EXEMPT_URLS = {'login', 'logout', 'signup', 'mfa_verify', 'mfa_setup', 'home'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "MFA_ENABLED", False) or not request.user.is_authenticated:
            return self.get_response(request)

        if request.user.is_staff or request.user.is_superuser:
            return self.get_response(request)

        path = request.path
        if any(path.startswith(p) for p in ['/static/', '/media/', '/health/']):
            return self.get_response(request)

        try:
            if resolve(path).url_name in self.EXEMPT_URLS:
                return self.get_response(request)
        except Resolver404:
            pass

        if request.session.get("mfa_verified", False):
            return self.get_response(request)

        from django.apps import apps
        try:
            MFAProfile = apps.get_model('invoices', 'MFAProfile')
            if MFAProfile.objects.filter(user=request.user, is_enabled=True).exists():
                if request.headers.get('Accept') == 'application/json' or path.startswith('/api/'):
                    return JsonResponse({"error": "MFA required"}, status=403)
                return redirect("invoices:mfa_verify")
        except:
            pass

        return self.get_response(request)
