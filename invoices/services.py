"""
InvoiceFlow Services - Compatibility Layer

This module re-exports all services from the new modular services/ directory.
For new code, import directly from invoices.services instead.

Example:
    from invoices.services import InvoiceService, ReportsService
"""

from .services import (
    InvoiceService,
    UserService,
    ProfileService,
    NotificationService,
    PaymentSettingsService,
    PaymentService,
    ReportsService,
    EmailService,
    PDFService,
)

__all__ = [
    "InvoiceService",
    "UserService",
    "ProfileService",
    "NotificationService",
    "PaymentSettingsService",
    "PaymentService",
    "ReportsService",
    "EmailService",
    "PDFService",
]
