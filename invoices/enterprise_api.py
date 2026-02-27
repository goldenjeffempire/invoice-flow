"""Enterprise API utilities with versioning, validation, and standardization."""

from typing import Any, Callable, Dict
from functools import wraps
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .enterprise_errors import EnterpriseError, ErrorHandler


class APIVersions:
    """API version constants."""
    V1 = "v1"
    V2 = "v2"
    CURRENT = V1


class EnterpriseAPIView:
    """Base class for enterprise API views with standardized response format."""
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> Response:
        """Standardized success response."""
        return Response({
            "status": "success",
            "code": status_code,
            "message": message,
            "data": data,
            "api_version": APIVersions.CURRENT,
        }, status=status_code)
    
    @staticmethod
    def error_response(error_code: str, message: str, status_code: int = 400, details: Dict = None) -> Response:
        """Standardized error response."""
        response = {
            "status": "error",
            "code": status_code,
            "error_code": error_code,
            "message": message,
            "api_version": APIVersions.CURRENT,
        }
        if details:
            response["details"] = details
        return Response(response, status=status_code)
    
    @staticmethod
    def paginated_response(items: list, total: int, page: int, page_size: int) -> Response:
        """Standardized paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return Response({
            "status": "success",
            "data": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "api_version": APIVersions.CURRENT,
        })


def enterprise_api_endpoint(required_auth: bool = True, rate_limit: int = 100):
    """Decorator for enterprise API endpoints with validation and error handling."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            try:
                request = args[0] if args else kwargs.get('request')
                
                # Check authentication
                if required_auth and (not request or not request.user.is_authenticated):
                    return EnterpriseAPIView.error_response(
                        "UNAUTHORIZED",
                        "Authentication required",
                        status.HTTP_401_UNAUTHORIZED
                    )
                
                # Execute endpoint
                result = func(*args, **kwargs)
                return result if isinstance(result, Response) else EnterpriseAPIView.success_response(result)
            
            except EnterpriseError as e:
                return Response(e.to_response(), status=e.http_status)
            except Exception as e:
                return ErrorHandler.handle_error(e)
        
        return wrapper
    return decorator


class APIRequestValidator:
    """Validate API requests against schema."""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: list) -> bool:
        """Check that required fields are present and not empty."""
        from .enterprise_errors import ValidationError
        missing = [f for f in required_fields if f not in data or data[f] is None]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
        return True
    
    @staticmethod
    def validate_field_type(value: Any, expected_type: type) -> bool:
        """Validate field type."""
        from .enterprise_errors import ValidationError
        if not isinstance(value, expected_type):
            raise ValidationError(f"Expected {expected_type.__name__}, got {type(value).__name__}")
        return True
    
    @staticmethod
    def validate_field_length(value: str, min_length: int = 0, max_length: int = None) -> bool:
        """Validate string field length."""
        from .enterprise_errors import ValidationError
        if len(value) < min_length:
            raise ValidationError(f"Field too short (minimum {min_length} characters)")
        if max_length and len(value) > max_length:
            raise ValidationError(f"Field too long (maximum {max_length} characters)")
        return True
