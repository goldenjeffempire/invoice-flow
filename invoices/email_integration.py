"""
Production-grade email integration for invoice operations.
Handles SendGrid email delivery with comprehensive error handling and logging.
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

if TYPE_CHECKING:
    from invoices.models import Invoice

logger = logging.getLogger(__name__)


class EmailIntegrationError(Exception):
    """Raised when email integration fails."""
    pass


class InvoiceEmailService:
    """
    Service for sending invoice-related emails with SendGrid integration.
    Handles sending invoices to clients, payment reminders, and notifications.
    """

    @staticmethod
    def send_invoice_email(
        invoice: 'Invoice',
        recipient_email: str,
        subject: Optional[str] = None,
        custom_message: Optional[str] = None,
        is_reminder: bool = False
    ) -> Dict[str, Any]:
        """
        Send invoice to recipient via email.

        Args:
            invoice: Invoice instance to send
            recipient_email: Recipient email address
            subject: Custom email subject (optional)
            custom_message: Custom message to include in email
            is_reminder: Whether this is a payment reminder

        Returns:
            dict: Response with status, message, and any errors
        """
        try:
            # Validate email
            if not InvoiceEmailService.validate_email(recipient_email):
                return {
                    'status': 'error',
                    'message': 'Invalid recipient email address',
                    'error': 'invalid_email'
                }

            # Default subject if not provided
            if not subject:
                subject = f"Invoice {invoice.invoice_id}" + \
                          (" - Payment Reminder" if is_reminder else "")

            # Render email template
            context = {
                'invoice': invoice,
                'custom_message': custom_message,
                'is_reminder': is_reminder,
            }

            html_message = render_to_string(
                'invoices/email_invoice.html',
                context
            )
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Invoice {invoice.invoice_id} sent to {recipient_email}")

            return {
                'status': 'success',
                'message': f'Invoice sent to {recipient_email}',
                'email': recipient_email,
                'invoice_id': invoice.invoice_id
            }

        except Exception as e:
            logger.exception(f"Failed to send invoice {invoice.invoice_id}: {str(e)}")
            return {
                'status': 'error',
                'message': 'Failed to send invoice email',
                'error': str(e)
            }

    @staticmethod
    def send_payment_reminder(
        invoice: 'Invoice',
        recipient_email: str,
        days_overdue: int
    ) -> Dict[str, Any]:
        """
        Send payment reminder for overdue invoice.

        Args:
            invoice: Invoice instance
            recipient_email: Recipient email address
            days_overdue: Number of days invoice is overdue

        Returns:
            dict: Response with status and message
        """
        subject = f"Payment Reminder - Invoice {invoice.invoice_id} ({days_overdue} days overdue)"
        custom_message = (
            f"This invoice is {days_overdue} days overdue. "
            f"Please arrange payment at your earliest convenience."
        )

        return InvoiceEmailService.send_invoice_email(
            invoice=invoice,
            recipient_email=recipient_email,
            subject=subject,
            custom_message=custom_message,
            is_reminder=True
        )

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return re.match(pattern, email) is not None

    @staticmethod
    def send_bulk_invoices(
        invoices: list,
        recipient_emails: dict
    ) -> Dict[str, Any]:
        """
        Send multiple invoices to recipients.

        Args:
            invoices: List of Invoice instances
            recipient_emails: Dict mapping invoice.id to email address

        Returns:
            dict: Summary of results
        """
        results = {
            'sent': 0,
            'failed': 0,
            'errors': [],
            'sent_invoices': []
        }

        for invoice in invoices:
            if invoice.id not in recipient_emails:
                results['failed'] += 1
                results['errors'].append(f"No email for invoice {invoice.invoice_id}")
                continue

            recipient = recipient_emails[invoice.id]
            result = InvoiceEmailService.send_invoice_email(invoice, recipient)

            if result['status'] == 'success':
                results['sent'] += 1
                results['sent_invoices'].append(invoice.invoice_id)
            else:
                results['failed'] += 1
                results['errors'].append(f"{invoice.invoice_id}: {result.get('error')}")

        return results
