"""
Payment Service - Business logic for payment processing.

Responsibilities:
- Payment processing and recording
- Webhook handling with deduplication
- Payment status management
- Reconciliation
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:
    from invoices.models import Invoice, Payment

logger = logging.getLogger(__name__)


class PaymentService:
    """Centralized service for payment processing and reconciliation."""

    @staticmethod
    @transaction.atomic
    def process_payment(
        invoice: "Invoice",
        amount: Decimal,
        reference: str,
        provider: str = "paystack",
        customer_email: str = "",
    ) -> Tuple["Payment", bool]:
        """
        Record a payment and update invoice status if successful.
        
        Args:
            invoice: The invoice being paid
            amount: Payment amount
            reference: Unique payment reference
            provider: Payment provider name
            customer_email: Customer's email
            
        Returns:
            Tuple of (payment, created)
        """
        from invoices.models import Payment
        from .analytics_service import AnalyticsService

        payment, created = Payment.objects.get_or_create(
            reference=reference,
            defaults={
                "invoice": invoice,
                "user": invoice.user,
                "amount": amount,
                "customer_email": customer_email or invoice.client_email,
                "status": Payment.Status.PENDING,
            },
        )

        if created:
            logger.info(f"Payment {reference} created for invoice {invoice.invoice_id}")

        payment.mark_as_success()
        AnalyticsService.invalidate_user_cache(invoice.user_id)
        return payment, created

    @staticmethod
    def verify_webhook_signature(
        provider: str,
        signature: str,
        raw_payload: bytes,
    ) -> bool:
        """
        Verify webhook signature from payment provider.
        
        Args:
            provider: Payment provider name
            signature: Signature from webhook header
            raw_payload: Raw request body
            
        Returns:
            True if signature is valid
        """
        if provider == "paystack":
            secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
            if not secret:
                logger.error("PAYSTACK_SECRET_KEY not configured")
                return False

            hash_obj = hmac.new(
                secret.encode("utf-8"),
                raw_payload,
                hashlib.sha512,
            )
            return hmac.compare_digest(hash_obj.hexdigest(), signature)

        return False

    @staticmethod
    @transaction.atomic
    def handle_webhook(
        payload: Dict[str, Any],
        provider: str,
        *,
        signature: str = "",
        raw_payload: Optional[bytes] = None,
    ) -> bool:
        """
        Process incoming webhooks with deduplication and signature validation.
        
        Args:
            payload: Parsed webhook payload
            provider: Payment provider name
            signature: Webhook signature
            raw_payload: Raw request body for signature verification
            
        Returns:
            True if webhook was processed successfully
        """
        from invoices.models import Payment, ProcessedWebhook

        if provider == "paystack":
            if not raw_payload or not signature:
                logger.warning("Missing Paystack webhook signature or payload.")
                return False

            if not PaymentService.verify_webhook_signature(
                provider, signature, raw_payload
            ):
                logger.warning("Invalid Paystack webhook signature.")
                return False

        event_id = payload.get("id") or payload.get("event_id")
        if not event_id:
            logger.warning("Webhook missing event_id")
            return False

        if ProcessedWebhook.objects.filter(event_id=event_id, provider=provider).exists():
            logger.info(f"Duplicate webhook received: {provider}:{event_id}")
            return True

        event_type = payload.get("event", "unknown")
        data = payload.get("data", {})
        reference = data.get("reference", "")

        if event_type == "charge.success":
            amount = Decimal(str(data.get("amount", 0))) / 100

            try:
                payment = Payment.objects.get(reference=reference)
                payment.mark_as_success()
                logger.info(f"Payment {reference} marked as success via webhook")
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for reference: {reference}")
                return False

        ProcessedWebhook.objects.create(
            event_id=event_id,
            provider=provider,
            event_type=event_type,
            reference=reference,
            payload_hash=hashlib.sha256(
                (raw_payload or b"")
            ).hexdigest() if raw_payload else "",
        )

        return True

    @staticmethod
    def get_payment_by_reference(reference: str) -> Optional["Payment"]:
        """Get a payment by its reference."""
        from invoices.models import Payment

        try:
            return Payment.objects.select_related("invoice").get(reference=reference)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_user_payments(user, limit: Optional[int] = None):
        """Get payments for a user's invoices."""
        from invoices.models import Payment

        queryset = (
            Payment.objects.filter(invoice__user=user)
            .select_related("invoice")
            .order_by("-created_at")
        )

        if limit:
            queryset = queryset[:limit]

        return list(queryset)
