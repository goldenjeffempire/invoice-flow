"""
Paystack Payment & Transfer Service for InvoiceFlow
Production-safe, stateless, webhook-ready.
"""

import hashlib
import hmac
import json
import os
from decimal import Decimal
from typing import Any, Optional

import requests
from django.utils import timezone

from .models import IdempotencyKey, Payment, ProcessedWebhook


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:
    def __init__(self):
        self.secret_key = os.getenv("PAYSTACK_SECRET_KEY", "")
        self.public_key = os.getenv("PAYSTACK_PUBLIC_KEY", "")
        self.is_configured = bool(self.secret_key)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    # ---------------------------------------------------------------------
    # PAYMENT INITIALIZATION
    # ---------------------------------------------------------------------

    def initialize_payment(
        self,
        *,
        email: str,
        amount: Decimal,
        reference: str,
        currency: str = "NGN",
        callback_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        subaccount_code: Optional[str] = None,
        bearer: str = "subaccount",
    ) -> dict[str, Any]:

        if not self.is_configured:
            return {"status": "error", "configured": False}

        payload: dict[str, Any] = {
            "email": email,
            "amount": int(amount * 100),
            "currency": currency,
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url
        if metadata:
            payload["metadata"] = metadata
        if subaccount_code:
            payload["subaccount"] = subaccount_code
            payload["bearer"] = bearer

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        data = response.json()

        if response.status_code == 200 and data.get("status"):
            return {
                "status": "success",
                "authorization_url": data["data"]["authorization_url"],
                "reference": data["data"]["reference"],
            }

        return {"status": "error", "message": data.get("message")}

    # ---------------------------------------------------------------------
    # PAYMENT VERIFICATION (STATELESS)
    # ---------------------------------------------------------------------

    def verify_transaction(self, reference: str) -> dict[str, Any]:
        if not self.is_configured:
            return {"status": "error", "configured": False}

        response = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=self.headers,
            timeout=30,
        )

        data = response.json()

        if response.status_code != 200 or not data.get("status"):
            return {"status": "error", "verified": False}

        tx = data["data"]

        return {
            "status": "success",
            "verified": tx["status"] == "success",
            "amount": Decimal(tx["amount"]) / 100,
            "currency": tx["currency"],
            "paid_at": tx.get("paid_at"),
            "channel": tx.get("channel"),
            "reference": tx["reference"],
            "customer_email": tx.get("customer", {}).get("email"),
            "metadata": tx.get("metadata", {}),
            "raw": tx,
        }

    # ---------------------------------------------------------------------
    # WEBHOOK SECURITY
    # ---------------------------------------------------------------------

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not self.secret_key:
            return False

        expected = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def is_webhook_processed(self, event_id: str) -> bool:
        return ProcessedWebhook.objects.filter(event_id=event_id).exists()

    def mark_webhook_processed(self, event_id: str) -> None:
        ProcessedWebhook.objects.create(event_id=event_id)

    # -------------------------------------------------------------------------
    # IDEMPOTENCY KEY HANDLING
    # -------------------------------------------------------------------------

    def get_or_create_idempotency_response(
        self,
        user_id: int,
        idempotency_key: str,
        request_data: dict[str, Any],
        response_callback: Any,
    ) -> tuple[dict[str, Any], int, bool]:
        """
        Check if idempotency key exists and return cached response.
        If not, execute callback and cache the response.
        Returns: (response_data, http_status, is_cached)
        """
        try:
            cached = IdempotencyKey.objects.get(
                key=idempotency_key,
                user_id=user_id,
            )
            if cached.is_valid():
                return cached.response_data, cached.http_status, True
            cached.delete()
        except IdempotencyKey.DoesNotExist:
            pass

        response_data, http_status = response_callback()

        request_hash = hashlib.sha256(
            json.dumps(request_data, sort_keys=True).encode()
        ).hexdigest()

        IdempotencyKey.objects.create(
            user_id=user_id,
            key=idempotency_key,
            request_hash=request_hash,
            response_data=response_data,
            http_status=http_status,
            expires_at=timezone.now() + timezone.timedelta(hours=24),
        )

        return response_data, http_status, False


# -------------------------------------------------------------------------
# DOMAIN-LEVEL PAYMENT FINALIZATION
# -------------------------------------------------------------------------

def finalize_payment_from_verification(
    *,
    payment: Payment,
    verification: dict[str, Any],
) -> Payment:
    """
    Apply verified Paystack data to Payment model.
    """

    if verification.get("verified"):
        payment.status = Payment.Status.SUCCESS
        payment.verified = True
        payment.paid_at = timezone.now()
        payment.verified_at = timezone.now()
    else:
        payment.status = Payment.Status.FAILED

    payment.save(update_fields=[
        "status",
        "verified",
        "paid_at",
        "verified_at",
    ])

    return payment


# -------------------------------------------------------------------------
# FACTORY FUNCTION
# -------------------------------------------------------------------------

def get_paystack_service() -> PaystackService:
    """
    Factory function to get a PaystackService instance.
    """
    return PaystackService()
