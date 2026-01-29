"""
Email Service - Business logic for email delivery.

Responsibilities:
- Invoice email delivery
- Payment receipt emails
- Standardized email operations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from invoices.models import Invoice, Payment

logger = logging.getLogger(__name__)


class EmailService:
    """Standardized email delivery service."""

    @staticmethod
    def send_invoice(invoice: "Invoice", recipient: str) -> bool:
        """
        Send invoice email to recipient.
        
        Args:
            invoice: The invoice to send
            recipient: Email address of recipient
            
        Returns:
            True if email was sent successfully
        """
        from invoices.sendgrid_service import SendGridEmailService

        try:
            return SendGridEmailService().send_invoice(invoice, recipient)
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False

    @staticmethod
    def send_receipt(payment: "Payment") -> bool:
        """
        Send payment receipt email.
        
        Args:
            payment: The payment to send receipt for
            
        Returns:
            True if email was sent successfully
        """
        from invoices.sendgrid_service import SendGridEmailService

        try:
            recipient = payment.invoice.client_email
            return SendGridEmailService().send_invoice_paid(payment.invoice, recipient)
        except Exception as e:
            logger.error("Failed to send receipt email")
            return False

    @staticmethod
    def send_reminder(invoice: "Invoice", recipient: str, template: str = "default") -> bool:
        """
        Send payment reminder email.
        
        Args:
            invoice: The invoice to remind about
            recipient: Email address of recipient
            template: Reminder template name
            
        Returns:
            True if email was sent successfully
        """
        from invoices.sendgrid_service import SendGridEmailService

        try:
            return SendGridEmailService().send_payment_reminder(invoice, recipient)
        except Exception as e:
            logger.error(f"Failed to send reminder email: {e}")
            return False

    @staticmethod
    def send_verification_email(user, token: str) -> bool:
        """
        Send email verification email.
        
        Args:
            user: The user to verify
            token: Verification token
            
        Returns:
            True if email was sent successfully
        """
        from invoices.sendgrid_service import SendGridEmailService

        try:
            SendGridEmailService().send_verification_email(user, token)
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False

    @staticmethod
    def send_password_reset_email(user, token: str) -> bool:
        """
        Send password reset email.
        
        Args:
            user: The user requesting password reset
            token: Reset token
            
        Returns:
            True if email was sent successfully
        """
        from invoices.sendgrid_service import SendGridEmailService

        try:
            SendGridEmailService().send_password_reset_email(user, token)
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False
