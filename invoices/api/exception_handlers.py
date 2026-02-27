"""
Standardized API exception handling for InvoiceFlow.
Provides consistent error response format across all API endpoints.
"""

import logging
import traceback
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
)
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.exceptions import (
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class APIError:
    """Standardized API error codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVER_ERROR = "SERVER_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    NOT_ACCEPTABLE = "NOT_ACCEPTABLE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    GONE = "GONE"


STATUS_TO_ERROR_CODE: dict[int, str] = {
    400: APIError.BAD_REQUEST,
    401: APIError.AUTHENTICATION_REQUIRED,
    403: APIError.PERMISSION_DENIED,
    404: APIError.NOT_FOUND,
    405: APIError.METHOD_NOT_ALLOWED,
    406: APIError.NOT_ACCEPTABLE,
    409: APIError.CONFLICT,
    410: APIError.GONE,
    415: APIError.UNSUPPORTED_MEDIA_TYPE,
    429: APIError.RATE_LIMIT_EXCEEDED,
    500: APIError.SERVER_ERROR,
}


def _get_error_code_for_status(status_code: int) -> str:
    """Map HTTP status code to appropriate error code."""
    if status_code in STATUS_TO_ERROR_CODE:
        return STATUS_TO_ERROR_CODE[status_code]
    if 400 <= status_code < 500:
        return APIError.BAD_REQUEST
    if status_code >= 500:
        return APIError.SERVER_ERROR
    return APIError.BAD_REQUEST


def create_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    status_code: int = 400,
    request_id: str | None = None,
) -> Response:
    """Create a standardized error response."""
    error_data: dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }

    if details:
        error_data["error"]["details"] = details

    if request_id:
        error_data["error"]["request_id"] = request_id

    return Response(error_data, status=status_code)


def format_validation_errors(detail: Any) -> dict[str, Any]:
    """Format DRF validation errors into a consistent structure."""
    if isinstance(detail, dict):
        formatted = {}
        for field, errors in detail.items():
            if isinstance(errors, list):
                formatted[field] = [str(e) for e in errors]
            else:
                formatted[field] = [str(errors)]
        return formatted
    elif isinstance(detail, list):
        return {"non_field_errors": [str(e) for e in detail]}
    else:
        return {"non_field_errors": [str(detail)]}


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom exception handler for DRF that provides standardized error responses.

    All API errors follow this format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...},  // Optional field-level errors
            "request_id": "abc123"  // For tracing
        }
    }
    """
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None

    response = drf_exception_handler(exc, context)

    if isinstance(exc, ValidationError):
        details = format_validation_errors(exc.detail)
        return create_error_response(
            code=APIError.VALIDATION_ERROR,
            message="Validation failed. Please check the provided data.",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
        )

    if isinstance(exc, NotAuthenticated):
        return create_error_response(
            code=APIError.AUTHENTICATION_REQUIRED,
            message="Authentication credentials were not provided.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id,
        )

    if isinstance(exc, AuthenticationFailed):
        return create_error_response(
            code=APIError.AUTHENTICATION_FAILED,
            message=str(exc.detail) if exc.detail else "Authentication failed.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id,
        )

    if isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
        return create_error_response(
            code=APIError.PERMISSION_DENIED,
            message="You do not have permission to perform this action.",
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id,
        )

    if isinstance(exc, (NotFound, Http404)):
        return create_error_response(
            code=APIError.NOT_FOUND,
            message="The requested resource was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
        )

    if isinstance(exc, MethodNotAllowed):
        method = request.method if request else "Unknown"
        return create_error_response(
            code=APIError.METHOD_NOT_ALLOWED,
            message=f"Method '{method}' is not allowed for this endpoint.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            request_id=request_id,
        )

    if isinstance(exc, Throttled):
        wait_seconds = exc.wait
        message = "Request rate limit exceeded."
        if wait_seconds:
            message = f"Request rate limit exceeded. Try again in {int(wait_seconds)} seconds."
        return create_error_response(
            code=APIError.RATE_LIMIT_EXCEEDED,
            message=message,
            details={"retry_after": wait_seconds} if wait_seconds else None,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            request_id=request_id,
        )

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            details: dict[str, Any] = {
                str(k): [str(m) for m in v] for k, v in exc.message_dict.items()
            }
        else:
            details = {"non_field_errors": [str(m) for m in exc.messages]}
        return create_error_response(
            code=APIError.VALIDATION_ERROR,
            message="Validation failed.",
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
        )

    if isinstance(exc, APIException):
        code = _get_error_code_for_status(exc.status_code)
        return create_error_response(
            code=code,
            message=str(exc.detail) if exc.detail else "An error occurred.",
            status_code=exc.status_code,
            request_id=request_id,
        )

    if response is not None:
        return response

    logger.exception(
        "Unhandled API exception",
        extra={
            "request_id": request_id,
            "path": request.path if request else None,
            "method": request.method if request else None,
            "exception": str(exc),
            "traceback": traceback.format_exc(),
        },
    )

    return create_error_response(
        code=APIError.SERVER_ERROR,
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )


class ServiceError(APIException):
    """Base exception for service layer errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A service error occurred."
    default_code = "service_error"


class InvoiceNotFoundError(ServiceError):
    """Raised when an invoice is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Invoice not found."
    default_code = "invoice_not_found"


class InvoiceValidationError(ServiceError):
    """Raised when invoice data validation fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid invoice data."
    default_code = "invoice_validation_error"


class PaymentProcessingError(ServiceError):
    """Raised when payment processing fails."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Payment processing failed."
    default_code = "payment_error"


class PDFGenerationError(ServiceError):
    """Raised when PDF generation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to generate PDF."
    default_code = "pdf_generation_error"


class EmailDeliveryError(ServiceError):
    """Raised when email delivery fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Failed to send email."
    default_code = "email_delivery_error"
