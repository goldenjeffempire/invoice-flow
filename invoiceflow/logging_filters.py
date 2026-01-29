import uuid
import logging

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        # In a real app, this would get the ID from thread-local storage or middleware
        record.request_id = getattr(record, 'request_id', 'no-id')
        return True
