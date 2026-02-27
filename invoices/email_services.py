"""
Email notification service for invoice payment events.
Sends transactional emails for payment failures and success confirmations.
"""

import logging
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class PaymentEmailService:
    """Service for sending payment-related emails."""

    @staticmethod
    def send_payment_failure_notification(
        invoice_id: str,
        client_email: str,
        client_name: str,
        business_name: str,
        amount: str,
        currency: str,
        failure_reason: str,
        reference: str,
        business_email: Optional[str] = None,
    ) -> bool:
        """
        Send email notification when a payment fails.

        Args:
            invoice_id: Invoice ID/number
            client_email: Client's email address
            client_name: Client's name
            business_name: Business/seller name
            amount: Payment amount
            currency: Currency code
            failure_reason: Reason for payment failure
            reference: Payment reference/transaction ID
            business_email: Optional business email for CC

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            context = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "business_name": business_name,
                "amount": amount,
                "currency": currency,
                "failure_reason": failure_reason,
                "reference": reference,
                "support_email": settings.DEFAULT_FROM_EMAIL,
                "dashboard_url": f"{settings.PRODUCTION_URL}/dashboard/",
            }

            subject = f"Payment Failed for Invoice {invoice_id} - {business_name}"

            html_message = render_to_string(
                "invoices/emails/payment_failure.html", context
            )
            plain_message = render_to_string(
                "invoices/emails/payment_failure.txt", context
            )

            recipient_list = [client_email]
            if business_email and business_email != client_email:
                recipient_list.append(business_email)

            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(
                f"Payment failure notification sent for invoice {invoice_id} to {client_email}"
            )
            return result == 1

        except Exception as e:
            logger.error(
                f"Failed to send payment failure email for invoice {invoice_id}: {str(e)}"
            )
            return False

    @staticmethod
    def send_payment_success_notification(
        invoice_id: str,
        client_email: str,
        client_name: str,
        business_name: str,
        amount: str,
        currency: str,
        reference: str,
        business_email: Optional[str] = None,
    ) -> bool:
        """
        Send email confirmation when a payment succeeds.

        Args:
            invoice_id: Invoice ID/number
            client_email: Client's email address
            client_name: Client's name
            business_name: Business/seller name
            amount: Payment amount
            currency: Currency code
            reference: Payment reference/transaction ID
            business_email: Optional business email for CC

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            context = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "business_name": business_name,
                "amount": amount,
                "currency": currency,
                "reference": reference,
                "support_email": settings.DEFAULT_FROM_EMAIL,
            }

            subject = f"Payment Received for Invoice {invoice_id} - {business_name}"

            html_message = render_to_string(
                "invoices/emails/payment_success.html", context
            )
            plain_message = render_to_string(
                "invoices/emails/payment_success.txt", context
            )

            recipient_list = [client_email]
            if business_email and business_email != client_email:
                recipient_list.append(business_email)

            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(
                f"Payment success confirmation sent for invoice {invoice_id} to {client_email}"
            )
            return result == 1

        except Exception as e:
            logger.error(
                f"Failed to send payment success email for invoice {invoice_id}: {str(e)}"
            )
            return False

    @staticmethod
    def send_seller_payment_received(
        invoice_id: str,
        seller_email: str,
        seller_name: str,
        client_name: str,
        amount: str,
        currency: str,
        reference: str,
    ) -> bool:
        """
        Notify seller that payment has been received.

        Args:
            invoice_id: Invoice ID/number
            seller_email: Seller's email address
            seller_name: Seller's name
            client_name: Client who made the payment
            amount: Payment amount
            currency: Currency code
            reference: Payment reference/transaction ID

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            context = {
                "invoice_id": invoice_id,
                "seller_name": seller_name,
                "client_name": client_name,
                "amount": amount,
                "currency": currency,
                "reference": reference,
                "dashboard_url": f"{settings.PRODUCTION_URL}/dashboard/",
            }

            subject = f"Payment Received - Invoice {invoice_id} from {client_name}"

            html_message = render_to_string(
                "invoices/emails/seller_payment_received.html", context
            )
            plain_message = render_to_string(
                "invoices/emails/seller_payment_received.txt", context
            )

            result = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[seller_email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(
                f"Seller payment notification sent for invoice {invoice_id} to {seller_email}"
            )
            return result == 1

        except Exception as e:
            logger.error(
                f"Failed to send seller payment email for invoice {invoice_id}: {str(e)}"
            )
            return False
