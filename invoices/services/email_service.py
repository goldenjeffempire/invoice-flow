"""
Email Service - Business logic for email delivery.

Uses the fully async email service to ensure email operations
NEVER block HTTP requests or cause 500 errors.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from invoices.models import Invoice, Payment

logger = logging.getLogger(__name__)


def _get_async_service():
    """Lazy import to avoid circular imports."""
    from .async_email_service import get_async_email_service
    return get_async_email_service()


class EmailService:
    """
    Standardized email delivery service.
    All operations are fully async and non-blocking.
    """

    @staticmethod
    def send_invoice(invoice: "Invoice", recipient: str) -> bool:
        """Queue invoice email - returns immediately."""
        try:
            return _get_async_service().send_invoice_ready_async(invoice, recipient)
        except Exception as e:
            logger.error(f"Failed to queue invoice email: {e}")
            return False

    @staticmethod
    def send_receipt(payment: "Payment") -> bool:
        """Queue payment receipt email - returns immediately."""
        try:
            recipient = payment.invoice.client_email
            return _get_async_service().send_invoice_paid_async(payment.invoice, recipient)
        except Exception as e:
            logger.error("Failed to queue receipt email")
            return False

    @staticmethod
    def send_reminder(invoice: "Invoice", recipient: str, template: str = "default") -> bool:
        """Queue payment reminder email - returns immediately."""
        try:
            return _get_async_service().send_reminder_async(invoice, recipient)
        except Exception as e:
            logger.error(f"Failed to queue reminder email: {e}")
            return False

    @staticmethod
    def send_verification_email(user, token: str) -> bool:
        """Queue verification email - returns immediately."""
        try:
            return _get_async_service().send_verification_email_async(user, token)
        except Exception as e:
            logger.error(f"Failed to queue verification email: {e}")
            return False

    @staticmethod
    def send_password_reset_email(user, token: str) -> bool:
        """Queue password reset email - returns immediately."""
        try:
            return _get_async_service().send_password_reset_async(user, token)
        except Exception as e:
            logger.error(f"Failed to queue password reset email: {e}")
            return False
