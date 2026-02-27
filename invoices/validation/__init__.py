"""
Centralized Validation Module

This module provides domain-specific validation schemas and rules.
Server is authoritative; client mirrors constraints for UX.

Domains:
- Invoice: Invoice creation and updates
- Client: Client information validation
- Payment: Payment processing validation
- Recurring: Recurring invoice configuration
"""

from .schemas import (
    InvoiceSchema,
    ClientSchema,
    PaymentSchema,
    RecurringSchema,
    LineItemSchema,
)
from .errors import (
    ValidationError,
    APIError,
    ErrorCode,
    ErrorResponse,
    format_validation_errors,
)

__all__ = [
    "InvoiceSchema",
    "ClientSchema",
    "PaymentSchema",
    "RecurringSchema",
    "LineItemSchema",
    "ValidationError",
    "APIError",
    "ErrorCode",
    "ErrorResponse",
    "format_validation_errors",
]
