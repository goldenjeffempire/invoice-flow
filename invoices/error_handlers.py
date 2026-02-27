"""
Production-grade error handling for invoices app.
Provides comprehensive error handling, logging, and user-friendly error messages.
"""

import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Any

from django.contrib import messages
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist

logger = logging.getLogger(__name__)


class InvoiceError(Exception):
    """Base exception for invoice-related errors."""
    pass


class InvoiceNotFoundError(InvoiceError):
    """Raised when invoice is not found."""
    pass


class InvoicePermissionError(InvoiceError):
    """Raised when user doesn't have permission to access invoice."""
    pass


class InvalidInvoiceDataError(InvoiceError):
    """Raised when invoice data is invalid."""
    pass


def handle_invoice_errors(view_func: Callable) -> Callable:
    """
    Decorator to handle common invoice errors with graceful fallback.
    Provides consistent error responses and logging.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            return view_func(request, *args, **kwargs)
        
        except InvoicePermissionError:
            logger.warning(f"Permission denied for user {request.user.id}")
            messages.error(request, "You don't have permission to access this invoice.")
            return redirect("invoices:invoices_list")
        
        except InvoiceNotFoundError:
            logger.warning(f"Invoice not found for user {request.user.id}")
            messages.error(request, "Invoice not found. It may have been deleted.")
            return redirect("invoices:invoices_list")
        
        except InvalidInvoiceDataError as e:
            logger.error(f"Invalid invoice data: {str(e)}")
            messages.error(request, f"Invalid data: {str(e)}")
            return redirect("invoices:invoices_list")
        
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            messages.error(request, f"Validation error: {str(e)}")
            if request.path.startswith('/api/'):
                return JsonResponse({'error': str(e)}, status=400)
            return redirect("invoices:invoices_list")
        
        except PermissionDenied:
            logger.warning(f"Permission denied for user {request.user.id}")
            messages.error(request, "You don't have permission to perform this action.")
            return redirect("invoices:dashboard")
        
        except ObjectDoesNotExist as e:
            logger.error(f"Object not found: {str(e)}")
            messages.error(request, "The requested resource was not found.")
            return redirect("invoices:invoices_list")
        
        except Exception as e:
            logger.exception(f"Unexpected error in {view_func.__name__}: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please try again later.")
            return redirect("invoices:invoices_list")
    
    return wrapper


def validate_invoice_ownership(view_func: Callable) -> Callable:
    """
    Decorator to ensure user owns the invoice they're trying to access.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        from invoices.models import Invoice
        
        invoice_id = kwargs.get('invoice_id')
        if invoice_id:
            try:
                invoice = Invoice.objects.get(id=invoice_id)
                if invoice.user != request.user:
                    raise InvoicePermissionError("You don't own this invoice.")
            except Invoice.DoesNotExist:
                raise InvoiceNotFoundError("Invoice not found.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def safe_decimal_conversion(value: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely convert value to decimal with error handling.
    Returns (decimal_value, error_message) tuple.
    """
    from decimal import Decimal, InvalidOperation
    
    try:
        decimal_value = Decimal(str(value))
        if decimal_value < 0:
            return None, "Amount cannot be negative."
        return float(decimal_value), None
    except (ValueError, InvalidOperation):
        return None, f"Invalid amount: {value}. Please enter a valid number."


class ErrorResponse:
    """Helper class for building consistent error responses."""
    
    @staticmethod
    def bad_request(message: str) -> JsonResponse:
        """Return 400 Bad Request response."""
        return JsonResponse({'error': message, 'status': 'error'}, status=400)
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> JsonResponse:
        """Return 404 Not Found response."""
        return JsonResponse({'error': message, 'status': 'error'}, status=404)
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> JsonResponse:
        """Return 401 Unauthorized response."""
        return JsonResponse({'error': message, 'status': 'error'}, status=401)
    
    @staticmethod
    def forbidden(message: str = "Forbidden") -> JsonResponse:
        """Return 403 Forbidden response."""
        return JsonResponse({'error': message, 'status': 'error'}, status=403)
    
    @staticmethod
    def server_error(message: str = "Internal server error") -> JsonResponse:
        """Return 500 Internal Server Error response."""
        return JsonResponse({'error': message, 'status': 'error'}, status=500)
    
    @staticmethod
    def success(data: dict = None, message: str = "Success") -> JsonResponse:
        """Return 200 OK response with data."""
        response = {'status': 'success', 'message': message}
        if data:
            response['data'] = data
        return JsonResponse(response)
