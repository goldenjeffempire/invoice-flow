"""
Monitoring and performance tracking for InvoiceFlow.
"""

import logging
import time
from functools import wraps

from django.core.cache import cache
from django.db import connection, reset_queries

logger = logging.getLogger(__name__)


def monitor_performance(view_func):
    """Decorator to monitor view performance"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        reset_queries()

        response = view_func(request, *args, **kwargs)

        duration = time.time() - start_time
        query_count = len(connection.queries)

        # Log performance
        if duration > 1:  # Log slow views (> 1 second)
            logger.warning(
                f"Slow view: {view_func.__name__} took {duration:.2f}s "
                f"with {query_count} queries"
            )

        # Add performance headers
        response["X-Response-Time"] = f"{duration:.3f}"
        response["X-Query-Count"] = str(query_count)

        return response

    return wrapper


def cache_view_response(timeout=300):
    """Decorator to cache view responses"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            cache_key = f"{view_func.__name__}_{request.user.id}_{request.GET.urlencode()}"

            response = cache.get(cache_key)
            if response is None:
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator


class PerformanceMiddleware:
    """Middleware to track request performance"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # Add timing header
        response["Server-Timing"] = f"total;dur={duration*1000:.0f}"

        return response
