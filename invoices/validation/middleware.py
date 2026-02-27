"""
Error Handling Middleware

Catches exceptions and returns standardized error responses.
Ensures consistent error format across all endpoints.
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

from .errors import (
    APIError,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    FieldError,
    format_validation_errors,
)

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.request_id = str(uuid.uuid4())
        
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            return self.handle_exception(request, e)
    
    def handle_exception(self, request: HttpRequest, exc: Exception) -> HttpResponse:
        request_id = getattr(request, "request_id", str(uuid.uuid4()))
        
        is_api_request = self._is_api_request(request)
        
        if isinstance(exc, APIError):
            exc.request_id = request_id
            if is_api_request:
                return exc.to_json_response()
            return self._render_error_page(request, exc.status, exc.message, request_id)
        
        if isinstance(exc, Http404):
            if is_api_request:
                return self._create_json_error(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    str(exc) or "Resource not found",
                    404,
                    request_id,
                )
            return None
        
        if isinstance(exc, PermissionDenied):
            if is_api_request:
                return self._create_json_error(
                    ErrorCode.PERMISSION_DENIED,
                    str(exc) or "Permission denied",
                    403,
                    request_id,
                )
            return None
        
        if isinstance(exc, DjangoValidationError):
            if is_api_request:
                if hasattr(exc, "message_dict"):
                    field_errors = format_validation_errors(exc.message_dict)
                else:
                    field_errors = [
                        FieldError(field="__all__", code=ErrorCode.VALIDATION_ERROR.value, message=str(exc))
                    ]
                
                return ErrorResponse(
                    error=ErrorDetail(
                        code=ErrorCode.VALIDATION_ERROR.value,
                        message="Validation failed",
                        fields=field_errors,
                    ),
                    request_id=request_id,
                ).to_json_response(400)
            return None
        
        logger.exception(
            f"Unhandled exception [request_id={request_id}]: {exc}",
            extra={"request_id": request_id},
        )
        
        if is_api_request:
            message = "An unexpected error occurred. Please try again later."
            if settings.DEBUG:
                message = f"{type(exc).__name__}: {str(exc)}"
            
            return self._create_json_error(
                ErrorCode.INTERNAL_ERROR,
                message,
                500,
                request_id,
            )
        
        return None
    
    def _is_api_request(self, request: HttpRequest) -> bool:
        if request.path.startswith("/api/"):
            return True
        
        content_type = request.content_type or ""
        if "application/json" in content_type:
            return True
        
        accept = request.headers.get("Accept", "")
        if "application/json" in accept:
            return True
        
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        
        return False
    
    def _create_json_error(
        self,
        code: ErrorCode,
        message: str,
        status: int,
        request_id: str,
    ) -> JsonResponse:
        return ErrorResponse(
            error=ErrorDetail(code=code.value, message=message),
            request_id=request_id,
        ).to_json_response(status)
    
    def _render_error_page(
        self,
        request: HttpRequest,
        status: int,
        message: str,
        request_id: str,
    ) -> HttpResponse:
        from django.shortcuts import render
        
        template_map = {
            400: "errors/400.html",
            401: "errors/401.html",
            403: "errors/403.html",
            404: "errors/404.html",
            500: "errors/500.html",
        }
        
        template = template_map.get(status, "errors/500.html")
        
        try:
            return render(request, template, {
                "message": message,
                "request_id": request_id,
                "status_code": status,
            }, status=status)
        except Exception:
            return render(request, "500.html", {
                "message": message,
                "request_id": request_id,
            }, status=status)
