"""
Resilience Middleware - Handles database errors and broken redirects gracefully.

Ensures the application never returns 500 errors for recoverable situations:
1. Database connection issues - retries and graceful degradation
2. Broken redirects - catches and handles redirect loops/errors
3. Session errors - recovers gracefully without crashing
"""

import logging
import time
from functools import wraps

from django.conf import settings
from django.db import connection, OperationalError, InterfaceError
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse, NoReverseMatch

logger = logging.getLogger(__name__)


class DatabaseResilienceMiddleware:
    """
    Middleware that handles database connection issues gracefully.
    - Retries failed queries with exponential backoff
    - Closes stale connections
    - Prevents 500 errors from transient DB issues
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_retries = 2
        self.base_delay = 0.1

    def __call__(self, request):
        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_connection()
                response = self.get_response(request)
                return response
            except (OperationalError, InterfaceError) as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"DB connection error (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    time.sleep(delay)
                    self._reset_connection()
                else:
                    logger.error(f"DB connection failed after {self.max_retries + 1} attempts: {e}")
                    return self._database_error_response(request)
        
        return self.get_response(request)

    def _ensure_connection(self):
        """Ensure database connection is healthy."""
        try:
            connection.ensure_connection()
        except Exception:
            self._reset_connection()
            connection.ensure_connection()

    def _reset_connection(self):
        """Close and reset the database connection."""
        try:
            connection.close()
        except Exception:
            pass

    def _database_error_response(self, request):
        """Return a user-friendly error page for database issues."""
        if request.headers.get('Accept', '').find('application/json') != -1:
            from django.http import JsonResponse
            return JsonResponse(
                {"error": "Service temporarily unavailable. Please try again."},
                status=503
            )
        
        try:
            return render(request, "errors/503.html", status=503)
        except Exception:
            return HttpResponse(
                "<h1>Service Temporarily Unavailable</h1>"
                "<p>We're experiencing technical difficulties. Please try again in a moment.</p>",
                status=503,
                content_type="text/html"
            )


class SafeRedirectMiddleware:
    """
    Middleware that catches and handles broken redirects gracefully.
    - Prevents redirect loops
    - Handles missing URL patterns
    - Ensures redirects never cause 500 errors
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.redirect_count_key = '_redirect_count'
        self.max_redirects = 5

    def __call__(self, request):
        redirect_count = request.session.get(self.redirect_count_key, 0) if hasattr(request, 'session') else 0
        
        if redirect_count > self.max_redirects:
            logger.warning(f"Redirect loop detected for path: {request.path}")
            if hasattr(request, 'session'):
                request.session[self.redirect_count_key] = 0
            return self._redirect_loop_response(request)
        
        try:
            response = self.get_response(request)
            
            if isinstance(response, HttpResponseRedirect):
                if hasattr(request, 'session'):
                    request.session[self.redirect_count_key] = redirect_count + 1
            else:
                if hasattr(request, 'session') and redirect_count > 0:
                    request.session[self.redirect_count_key] = 0
            
            return response
            
        except NoReverseMatch as e:
            logger.error(f"Broken redirect - URL pattern not found: {e}")
            return self._safe_redirect_home(request)
        except Exception as e:
            logger.error(f"Redirect error: {e}")
            return self._safe_redirect_home(request)

    def _redirect_loop_response(self, request):
        """Handle redirect loop by showing an error or going to home."""
        try:
            home_url = reverse('invoices:home')
            return HttpResponseRedirect(home_url)
        except NoReverseMatch:
            return HttpResponse(
                "<h1>Navigation Error</h1>"
                "<p>Please <a href='/'>return to the home page</a>.</p>",
                status=200,
                content_type="text/html"
            )

    def _safe_redirect_home(self, request):
        """Safely redirect to home page."""
        try:
            home_url = reverse('invoices:home')
            return HttpResponseRedirect(home_url)
        except NoReverseMatch:
            return HttpResponseRedirect('/')


class SessionResilienceMiddleware:
    """
    Middleware that handles session errors gracefully.
    - Recovers from corrupt session data
    - Handles session backend failures
    - Ensures session issues never cause 500 errors
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            if 'session' in str(e).lower():
                logger.warning(f"Session error, attempting recovery: {e}")
                return self._recover_from_session_error(request)
            raise

    def _recover_from_session_error(self, request):
        """Attempt to recover from session errors."""
        try:
            if hasattr(request, 'session'):
                request.session.flush()
        except Exception:
            pass
        
        try:
            return self.get_response(request)
        except Exception as e:
            logger.error(f"Session recovery failed: {e}")
            return HttpResponseRedirect('/')
