import time
import logging
from django.http import HttpResponseForbidden

logger = logging.getLogger("invoiceflow")

class CoreSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()

        # Block suspicious methods
        if request.method not in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            return HttpResponseForbidden("Method not allowed")

        response = self.get_response(request)

        duration = time.time() - start

        logger.info(
            "%s %s %s %sms",
            request.method,
            request.path,
            response.status_code,
            int(duration * 1000)
        )

        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "strict-origin"

        return response
