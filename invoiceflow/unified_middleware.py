"""
Unified Middleware for InvoiceFlow.
Combines request timing, security headers, and rate limiting.
"""

import logging
import time
from collections import defaultdict
from threading import Lock

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse

logger = logging.getLogger("invoiceflow")


class UnifiedMiddleware:
    """
    Unified middleware that handles:
    - Request timing and logging
    - Security headers
    - Basic request validation
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extremely fast path for static files, service worker, and webhooks
        if (request.path.startswith(settings.STATIC_URL) or 
            request.path == "/sw.js" or 
            "webhook" in request.path):
            return self.get_response(request)

        start = time.time()

        if request.method not in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            return HttpResponseForbidden("Method not allowed")

        response = self.get_response(request)

        duration = time.time() - start

        if duration > 1.0:
            logger.warning(
                "SLOW_REQ: %s %s %s %sms",
                request.method,
                request.path,
                response.status_code,
                int(duration * 1000),
            )
        else:
            logger.debug(
                "%s %s %s %sms",
                request.method,
                request.path,
                response.status_code,
                int(duration * 1000),
            )

        # Force fresh content in development to avoid 304/stale state
        if settings.DEBUG:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, proxy-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            if "ETag" in response:
                del response["ETag"]
            if "Last-Modified" in response:
                del response["Last-Modified"]
            # Force status code 200 for cached responses in development
            if response.status_code == 304:
                response.status_code = 200
        else:
            response["X-Content-Type-Options"] = "nosniff"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
            # Production: Use sensible defaults or let downstream handle
            if "Cache-Control" not in response:
                response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

        return response


class OptimizedRateLimitMiddleware:
    """
    Simple in-memory rate limiting middleware.
    Uses a sliding window approach for rate limiting.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = defaultdict(list)
        self.lock = Lock()
        self.rate_limit = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
        self.window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        self.enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self.exempt_paths = getattr(settings, "RATE_LIMIT_EXEMPT_PATHS", [
            "/health/",
            "/health/ready/",
            "/health/live/",
            "/static/",
            "/media/",
        ])

    def _get_client_ip(self, request):
        """Get client IP from request, handling proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _is_exempt(self, path):
        """Check if path is exempt from rate limiting."""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False

    def _is_rate_limited(self, client_ip):
        """Check if client is rate limited."""
        current_time = time.time()
        window_start = current_time - self.window

        with self.lock:
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if t > window_start
            ]

            if len(self.requests[client_ip]) >= self.rate_limit:
                return True

            self.requests[client_ip].append(current_time)
            return False

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)

        if self._is_exempt(request.path):
            return self.get_response(request)

        client_ip = self._get_client_ip(request)

        if self._is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded for IP: %s", client_ip)
            return JsonResponse(
                {"error": "Rate limit exceeded. Please try again later."},
                status=429,
            )

        return self.get_response(request)
