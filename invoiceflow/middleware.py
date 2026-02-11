import uuid
import logging

logger = logging.getLogger(__name__)

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', 'no-id')
        return True

class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.request_id = request_id
        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response
