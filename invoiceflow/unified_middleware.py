"""
Unified Middleware for InvoiceFlow.
Combines request timing, security headers, and rate limiting.
"""
import logging
import time
import re
from collections import defaultdict
from threading import Lock
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse

logger = logging.getLogger("invoiceflow")

class UnifiedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.bot_patterns = [
            re.compile(r'bot|spider|crawl|slurp|libwww|wget|curl|wp-admin|xmlrpc|\.php', re.I)
        ]

    def __call__(self, request):
        # Block bots
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        path = request.path.lower()
        if any(pattern.search(user_agent) or pattern.search(path) for pattern in self.bot_patterns):
            return HttpResponseForbidden("Bot pattern detected", content_type="text/plain")

        # Sanitize dev headers
        if not settings.DEBUG:
            request.META.pop('HTTP_X_FORWARDED_FOR_DEBUG', None)

        # Prevent stale 304s in development
        if settings.DEBUG:
            headers_to_remove = ["HTTP_IF_MODIFIED_SINCE", "HTTP_IF_NONE_MATCH"]
            for header in headers_to_remove:
                request.META.pop(header, None)

        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # Measure/log slow requests
        if duration > 1.0:
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")

        # Inject security headers
        if not settings.DEBUG:
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:;"
            )
        
        # Prevent 304 fallback
        if response.status_code == 304:
            response.status_code = 200

        return response

class OptimizedRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = defaultdict(list)
        self.lock = Lock()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR", "unknown")

    def __call__(self, request):
        enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        if not enabled:
            return self.get_response(request)

        exempt_paths = getattr(settings, 'RATE_LIMIT_EXEMPT_PATHS', ['/static/', '/media/'])
        if any(request.path.startswith(p) for p in exempt_paths):
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)

        current_time = time.time()
        with self.lock:
            # Sliding window filter
            self.requests[client_ip] = [t for t in self.requests[client_ip] if t > current_time - window]
            if len(self.requests[client_ip]) >= limit:
                logger.warning(f"Rate limit exceeded: {client_ip}")
                return JsonResponse({"error": "Rate limit exceeded"}, status=429)
            self.requests[client_ip].append(current_time)

        return self.get_response(request)
