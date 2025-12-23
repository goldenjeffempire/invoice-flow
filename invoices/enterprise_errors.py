"""Enterprise-grade error handling with detailed context and recovery."""

from typing import Any, Dict, Optional
from rest_framework import status
from rest_framework.response import Response


class EnterpriseError(Exception):
    """Base enterprise error with rich context."""
    
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "UNKNOWN_ERROR"
    message = "An error occurred"
    
    def __init__(self, message: Optional[str] = None, **context: Any):
        self.message = message or self.message
        self.context = context
        super().__init__(self.message)
    
    def to_response(self) -> Dict[str, Any]:
        """Convert error to API response."""
        return {
            "status": "error",
            "code": self.http_status,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context if self.context else None,
        }


class ValidationError(EnterpriseError):
    """Input validation error."""
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"
    message = "Invalid input provided"


class AuthenticationError(EnterpriseError):
    """Authentication failure."""
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication required"


class AuthorizationError(EnterpriseError):
    """Insufficient permissions."""
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_FAILED"
    message = "You don't have permission to perform this action"


class ResourceNotFoundError(EnterpriseError):
    """Resource not found."""
    http_status = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    message = "Resource not found"


class ConflictError(EnterpriseError):
    """Resource conflict (duplicate, state mismatch)."""
    http_status = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource conflict"


class RateLimitError(EnterpriseError):
    """Rate limit exceeded."""
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."


class ServiceUnavailableError(EnterpriseError):
    """Service temporarily unavailable."""
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"


class ErrorHandler:
    """Centralized error handling and recovery."""
    
    @staticmethod
    def handle_error(error: Exception) -> Response:
        """Convert any error to API response."""
        if isinstance(error, EnterpriseError):
            return Response(error.to_response(), status=error.http_status)
        
        # Generic error
        return Response({
            "status": "error",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required: list) -> None:
        """Validate that required fields are present."""
        missing = [field for field in required if field not in data or data[field] is None]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
