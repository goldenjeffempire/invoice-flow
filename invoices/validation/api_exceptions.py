"""
Django REST Framework Exception Handler

Provides consistent error format for all API endpoints.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
    Throttled,
)
from rest_framework.response import Response

from .errors import (
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    FieldError,
    format_validation_errors,
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None
    if not request_id:
        request_id = str(uuid.uuid4())
    
    response = exception_handler(exc, context)
    
    if response is not None:
        error_response = _convert_to_standard_format(exc, response, request_id)
        return Response(error_response.to_dict(), status=response.status_code)
    
    return response


def _convert_to_standard_format(
    exc: Exception,
    response: Response,
    request_id: str,
) -> ErrorResponse:
    status = response.status_code
    
    if isinstance(exc, NotAuthenticated):
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.AUTHENTICATION_REQUIRED.value,
                message="Authentication required. Please log in.",
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, AuthenticationFailed):
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.AUTHENTICATION_FAILED.value,
                message=str(exc.detail) if exc.detail else "Authentication failed.",
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, PermissionDenied):
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.PERMISSION_DENIED.value,
                message=str(exc.detail) if exc.detail else "You do not have permission to perform this action.",
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, NotFound):
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.RESOURCE_NOT_FOUND.value,
                message=str(exc.detail) if exc.detail else "Resource not found.",
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, Throttled):
        wait = exc.wait
        message = f"Too many requests. Please try again in {int(wait)} seconds." if wait else "Too many requests. Please try again later."
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.RATE_LIMITED.value,
                message=message,
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, DRFValidationError):
        field_errors = _extract_field_errors(exc.detail)
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR.value,
                message="Validation failed. Please check your input.",
                fields=field_errors,
            ),
            request_id=request_id,
        )
    
    if isinstance(exc, APIException):
        return ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=str(exc.detail) if exc.detail else "An error occurred.",
            ),
            request_id=request_id,
        )
    
    return ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="An unexpected error occurred.",
        ),
        request_id=request_id,
    )


def _extract_field_errors(detail: Any, prefix: str = "") -> list[FieldError]:
    errors = []
    
    if isinstance(detail, dict):
        for field_name, field_errors in detail.items():
            full_field = f"{prefix}{field_name}" if prefix else field_name
            
            if isinstance(field_errors, list):
                for error in field_errors:
                    if hasattr(error, "code"):
                        code = _map_drf_code(error.code)
                        message = str(error)
                    else:
                        code = ErrorCode.FIELD_INVALID.value
                        message = str(error)
                    
                    errors.append(FieldError(
                        field=full_field,
                        code=code,
                        message=message,
                    ))
            elif isinstance(field_errors, dict):
                errors.extend(_extract_field_errors(field_errors, f"{full_field}."))
            else:
                errors.append(FieldError(
                    field=full_field,
                    code=ErrorCode.FIELD_INVALID.value,
                    message=str(field_errors),
                ))
    
    elif isinstance(detail, list):
        for error in detail:
            if hasattr(error, "code"):
                code = _map_drf_code(error.code)
                message = str(error)
            else:
                code = ErrorCode.FIELD_INVALID.value
                message = str(error)
            
            errors.append(FieldError(
                field="__all__",
                code=code,
                message=message,
            ))
    
    else:
        errors.append(FieldError(
            field="__all__",
            code=ErrorCode.FIELD_INVALID.value,
            message=str(detail),
        ))
    
    return errors


def _map_drf_code(code: str) -> str:
    code_mapping = {
        "required": ErrorCode.FIELD_REQUIRED.value,
        "blank": ErrorCode.FIELD_REQUIRED.value,
        "null": ErrorCode.FIELD_REQUIRED.value,
        "invalid": ErrorCode.FIELD_INVALID.value,
        "max_length": ErrorCode.FIELD_TOO_LONG.value,
        "min_length": ErrorCode.FIELD_TOO_SHORT.value,
        "max_value": ErrorCode.FIELD_OUT_OF_RANGE.value,
        "min_value": ErrorCode.FIELD_OUT_OF_RANGE.value,
        "invalid_choice": ErrorCode.FIELD_INVALID.value,
        "does_not_exist": ErrorCode.RESOURCE_NOT_FOUND.value,
        "unique": ErrorCode.RESOURCE_ALREADY_EXISTS.value,
    }
    
    return code_mapping.get(code, ErrorCode.FIELD_INVALID.value)
