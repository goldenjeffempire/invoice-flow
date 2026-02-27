"""
Standardized Error Handling

Provides consistent error format:
API: { success: false, error: { code, message, fields? }, request_id }
UI: toast + inline field errors + dedicated error pages

HTTP Status Code Standards:
- 200: Success
- 201: Created
- 400: Bad Request (validation errors, malformed input)
- 401: Unauthorized (not authenticated)
- 403: Forbidden (not permitted)
- 404: Not Found
- 409: Conflict (duplicate, state conflict)
- 422: Unprocessable Entity (business rule violation)
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from django.http import JsonResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FIELD_REQUIRED = "FIELD_REQUIRED"
    FIELD_INVALID = "FIELD_INVALID"
    FIELD_TOO_SHORT = "FIELD_TOO_SHORT"
    FIELD_TOO_LONG = "FIELD_TOO_LONG"
    FIELD_OUT_OF_RANGE = "FIELD_OUT_OF_RANGE"
    FIELD_INVALID_FORMAT = "FIELD_INVALID_FORMAT"
    
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    PAYMENT_EXPIRED = "PAYMENT_EXPIRED"
    
    RATE_LIMITED = "RATE_LIMITED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    INVOICE_INVALID = "INVOICE_INVALID"
    INVOICE_ALREADY_PAID = "INVOICE_ALREADY_PAID"
    INVOICE_EXPIRED = "INVOICE_EXPIRED"
    
    CLIENT_INVALID = "CLIENT_INVALID"
    RECURRING_INVALID = "RECURRING_INVALID"


@dataclass
class FieldError:
    field: str
    code: str
    message: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class ErrorDetail:
    code: str
    message: str
    fields: Optional[List[FieldError]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.fields:
            result["fields"] = [f.to_dict() for f in self.fields]
        return result


@dataclass
class ErrorResponse:
    success: bool = False
    error: Optional[ErrorDetail] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error.to_dict() if self.error else None,
            "request_id": self.request_id,
        }
    
    def to_json_response(self, status: int = 400) -> JsonResponse:
        return JsonResponse(self.to_dict(), status=status)


class APIError(Exception):
    def __init__(
        self,
        code: Union[ErrorCode, str],
        message: str,
        status: int = 400,
        fields: Optional[List[FieldError]] = None,
        request_id: Optional[str] = None,
    ):
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.status = status
        self.fields = fields
        self.request_id = request_id or str(uuid.uuid4())
        super().__init__(message)
    
    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=self.code,
                message=self.message,
                fields=self.fields,
            ),
            request_id=self.request_id,
        )
    
    def to_json_response(self) -> JsonResponse:
        return self.to_response().to_json_response(self.status)


class ValidationError(APIError):
    def __init__(
        self,
        message: str = "Validation failed",
        fields: Optional[List[FieldError]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status=400,
            fields=fields,
            request_id=request_id,
        )


class AuthenticationError(APIError):
    def __init__(
        self,
        message: str = "Authentication required",
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.AUTHENTICATION_REQUIRED,
            message=message,
            status=401,
            request_id=request_id,
        )


class PermissionError(APIError):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.PERMISSION_DENIED,
            message=message,
            status=403,
            request_id=request_id,
        )


class NotFoundError(APIError):
    def __init__(
        self,
        message: str = "Resource not found",
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            status=404,
            request_id=request_id,
        )


class ConflictError(APIError):
    def __init__(
        self,
        message: str = "Resource conflict",
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            status=409,
            request_id=request_id,
        )


class BusinessRuleError(APIError):
    def __init__(
        self,
        message: str,
        code: Union[ErrorCode, str] = ErrorCode.BUSINESS_RULE_VIOLATION,
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            status=422,
            request_id=request_id,
        )


class RateLimitError(APIError):
    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        request_id: Optional[str] = None,
    ):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message=message,
            status=429,
            request_id=request_id,
        )


def format_validation_errors(
    errors: Dict[str, Any],
    prefix: str = "",
) -> List[FieldError]:
    field_errors = []
    
    for field_name, error_list in errors.items():
        full_field = f"{prefix}{field_name}" if prefix else field_name
        
        if isinstance(error_list, dict):
            field_errors.extend(format_validation_errors(error_list, f"{full_field}."))
        elif isinstance(error_list, list):
            for error in error_list:
                if isinstance(error, dict):
                    field_errors.extend(format_validation_errors(error, f"{full_field}."))
                else:
                    error_str = str(error)
                    code = _infer_error_code(error_str)
                    field_errors.append(FieldError(
                        field=full_field,
                        code=code,
                        message=error_str,
                    ))
        else:
            field_errors.append(FieldError(
                field=full_field,
                code=ErrorCode.FIELD_INVALID.value,
                message=str(error_list),
            ))
    
    return field_errors


def _infer_error_code(message: str) -> str:
    message_lower = message.lower()
    
    if "required" in message_lower or "blank" in message_lower or "null" in message_lower:
        return ErrorCode.FIELD_REQUIRED.value
    elif "too short" in message_lower or "at least" in message_lower:
        return ErrorCode.FIELD_TOO_SHORT.value
    elif "too long" in message_lower or "at most" in message_lower or "maximum" in message_lower:
        return ErrorCode.FIELD_TOO_LONG.value
    elif "greater than" in message_lower or "less than" in message_lower or "between" in message_lower:
        return ErrorCode.FIELD_OUT_OF_RANGE.value
    elif "format" in message_lower or "valid" in message_lower or "invalid" in message_lower:
        return ErrorCode.FIELD_INVALID_FORMAT.value
    else:
        return ErrorCode.FIELD_INVALID.value


def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    response = {
        "success": True,
        "request_id": request_id or str(uuid.uuid4()),
    }
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response
