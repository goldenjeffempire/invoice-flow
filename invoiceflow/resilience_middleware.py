"""
Resilience Middleware - Handles database errors and broken redirects gracefully.
"""
import logging
import time
from django.db import connection, OperationalError, InterfaceError
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse, NoReverseMatch

logger = logging.getLogger(__name__)

class DatabaseResilienceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_retries = 3

    def __call__(self, request):
        for attempt in range(self.max_retries):
            try:
                connection.ensure_connection()
                return self.get_response(request)
            except (OperationalError, InterfaceError) as e:
                if attempt < self.max_retries - 1:
                    delay = 0.5 * (2 ** attempt)
                    logger.warning(f"DB retry {attempt + 1}: {e}")
                    time.sleep(delay)
                    try:
                        connection.close()
                    except:
                        pass
                else:
                    logger.error(f"DB failed: {e}")
                    return JsonResponse({"error": "Service Unavailable"}, status=503) if request.headers.get('Accept') == 'application/json' else HttpResponse("Service Unavailable", status=503)
        return self.get_response(request)

class SafeRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_redirects = 5

    def __call__(self, request):
        redirect_count = request.session.get('_redirect_count', 0) if hasattr(request, 'session') else 0
        if redirect_count > self.max_redirects:
            logger.warning(f"Redirect loop: {request.path}")
            if hasattr(request, 'session'): request.session['_redirect_count'] = 0
            return HttpResponseRedirect('/')

        try:
            response = self.get_response(request)
            if isinstance(response, HttpResponseRedirect) and hasattr(request, 'session'):
                request.session['_redirect_count'] = redirect_count + 1
            elif hasattr(request, 'session'):
                request.session['_redirect_count'] = 0
            return response
        except (NoReverseMatch, Exception) as e:
            logger.error(f"Redirect error: {e}")
            return HttpResponseRedirect('/')

class SessionResilienceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
            if 'session' in str(e).lower():
                logger.warning(f"Session recovery: {e}")
                if hasattr(request, 'session'):
                    try: request.session.flush()
                    except: pass
                return self.get_response(request)
            raise
