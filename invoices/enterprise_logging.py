"""Enterprise-grade structured logging for audit trails and compliance."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
from django.conf import settings
from django.contrib.auth.models import User


class StructuredLogger:
    """Structured JSON logging for enterprise compliance and monitoring."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _build_log(self, level: str, message: str, **context: Any) -> Dict:
        """Build structured log entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "service": "invoiceflow",
            "environment": "production" if settings.DEBUG is False else "development",
            **context
        }
    
    def info(self, message: str, **context: Any) -> None:
        """Log info with context."""
        log_entry = self._build_log("INFO", message, **context)
        self.logger.info(json.dumps(log_entry))
    
    def warning(self, message: str, **context: Any) -> None:
        """Log warning with context."""
        log_entry = self._build_log("WARNING", message, **context)
        self.logger.warning(json.dumps(log_entry))
    
    def error(self, message: str, exception: Optional[Exception] = None, **context: Any) -> None:
        """Log error with exception details."""
        log_entry = self._build_log("ERROR", message, **context)
        if exception:
            log_entry["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
            }
        self.logger.error(json.dumps(log_entry))
    
    def audit(self, action: str, user: Optional[User] = None, resource: Optional[str] = None, **details: Any) -> None:
        """Log audit trail for compliance."""
        log_entry = self._build_log("AUDIT", action,
            user_id=user.id if user else None,
            username=user.username if user else None,
            resource=resource,
            **details
        )
        self.logger.info(json.dumps(log_entry))


class AuditLog:
    """Audit logging decorator for tracking sensitive operations."""
    
    @staticmethod
    def track(action: str, resource_type: str = "resource"):
        """Decorator to track operations for audit trail."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                logger = StructuredLogger("audit")
                
                # Extract user from request if available
                user = None
                request = next((arg for arg in args if hasattr(arg, 'user')), None)
                if request and hasattr(request, 'user'):
                    user = request.user if request.user.is_authenticated else None
                
                try:
                    result = func(*args, **kwargs)
                    logger.audit(
                        action=action,
                        user=user,
                        resource=resource_type,
                        status="success"
                    )
                    return result
                except Exception as e:
                    logger.audit(
                        action=action,
                        user=user,
                        resource=resource_type,
                        status="failed",
                        error=str(e)
                    )
                    raise
            return wrapper
        return decorator


# Initialize enterprise logger
enterprise_logger = StructuredLogger("invoiceflow.enterprise")
