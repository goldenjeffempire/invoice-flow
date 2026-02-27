"""Enterprise middleware for security, logging, and compliance."""

import json
import logging
from typing import Callable
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from .enterprise_logging import StructuredLogger


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all requests for audit trail and monitoring."""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.logger = StructuredLogger("http.request")
    
    def process_request(self, request: HttpRequest) -> None:
        """Log incoming request."""
        request._start_time = logging.Formatter().formatTime(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
        ))
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Log response and timing."""
        # Skip logging for static files and health checks
        if request.path.startswith('/static/') or request.path == '/health/':
            return response
        
        self.logger.info(
            "HTTP Request Completed",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            user_id=request.user.id if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
        )
        return response
    
    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add enterprise security headers."""
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to response."""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cache control for sensitive endpoints
        if request.path.startswith('/api/') or request.path.startswith('/admin/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware for API endpoints."""
    
    def process_request(self, request: HttpRequest):
        """Check rate limits for API endpoints."""
        if not request.path.startswith('/api/'):
            return None
        
        from .monitoring import RateLimitMonitor
        
        user_id = request.user.id if request.user.is_authenticated else self._get_client_ip(request)
        
        if RateLimitMonitor.is_rate_limited(user_id, limit=100, window_seconds=60):
            from django.http import JsonResponse
            return JsonResponse({
                "status": "error",
                "code": 429,
                "message": "Too many requests. Please try again later.",
            }, status=429)
        
        RateLimitMonitor.increment_user_requests(user_id)
        return None
    
    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
