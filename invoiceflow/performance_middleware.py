import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('performance')

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            path = request.path
            status = response.status_code
            
            # Log slow requests (> 10s) or errors - increased threshold for cold starts
            if duration > 10.0 or status >= 400:
                logger.warning(f"SLOW_REQ: {request.method} {path} - {status} - {duration:.2f}s")
            else:
                logger.info(f"REQ: {request.method} {path} - {status} - {duration:.2f}s")
        
        return response
