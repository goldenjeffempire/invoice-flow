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

        try:
            response = requests.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Connection error: {str(e)}"}
        except ValueError:
            return {"status": "error", "message": "Invalid response format from Paystack"}

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

    def verify_payment(self, reference: str) -> dict[str, Any]:
        """Alias for verify_transaction for backward compatibility."""
        return self.verify_transaction(reference)

    def verify_bvn(self, bvn: str) -> dict[str, Any]:
        """Verify BVN (Bank Verification Number) for KYC."""
        if not self.is_configured:
            return {"status": "error", "configured": False, "verified": False}

        response = requests.get(
            f"{PAYSTACK_BASE_URL}/bank/resolve",
            params={"account_number": bvn},
            headers=self.headers,
            timeout=30,
        )

        data = response.json()

        if response.status_code == 200 and data.get("status"):
            return {
                "status": "success",
                "verified": True,
                "data": data.get("data", {}),
            }

        return {
            "status": "error",
            "verified": False,
            "message": data.get("message", "BVN verification failed"),
        }

    def list_banks(self, country: str = "nigeria") -> dict[str, Any]:
        """List available banks for the specified country."""
        if not self.is_configured:
            return {"status": "error", "banks": []}

        response = requests.get(
            f"{PAYSTACK_BASE_URL}/bank",
            params={"country": country},
            headers=self.headers,
            timeout=30,
        )

        data = response.json()

        if response.status_code == 200 and data.get("status"):
            return {
                "status": "success",
                "banks": data.get("data", []),
            }

        return {
            "status": "error",
            "banks": [],
            "message": data.get("message", "Failed to fetch banks"),
        }

    def verify_account_number(self, account_number: str, bank_code: str) -> dict[str, Any]:
        """Verify bank account number and get account name."""
        if not self.is_configured:
            return {"status": "error", "verified": False}

        response = requests.get(
            f"{PAYSTACK_BASE_URL}/bank/resolve",
            params={"account_number": account_number, "bank_code": bank_code},
            headers=self.headers,
            timeout=30,
        )

        try:
            data = response.json()
        except Exception:
            return {"status": "error", "verified": False, "message": "Invalid response from Paystack"}

        if response.status_code == 200 and data.get("status"):
            account_data = data.get("data", {})
            return {
                "status": "success",
                "verified": True,
                "account_name": account_data.get("account_name", ""),
                "account_number": account_data.get("account_number", ""),
            }

        return {
            "status": "error",
            "verified": False,
            "message": data.get("message", "Account verification failed"),
        }

    def update_subaccount(self, subaccount_code: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing Paystack subaccount."""
        if not self.is_configured:
            return {"status": "error", "configured": False}

        response = requests.put(
            f"{PAYSTACK_BASE_URL}/subaccount/{subaccount_code}",
            headers=self.headers,
            json=kwargs,
            timeout=30,
        )
        return response.json()

    def create_subaccount(
        self,
        *,
        business_name: str,
        bank_code: str,
        account_number: str,
        percentage_charge: Decimal = Decimal("0"),
        primary_contact_email: str = "",
        primary_contact_phone: str = "",
    ) -> dict[str, Any]:
        """Create a Paystack subaccount for receiving payments directly."""
        if not self.is_configured:
            return {"status": "error", "configured": False}

        payload: dict[str, Any] = {
            "business_name": business_name,
            "bank_code": bank_code,
            "account_number": account_number,
            "percentage_charge": float(percentage_charge),
        }

        if primary_contact_email:
            payload["primary_contact_email"] = primary_contact_email
        if primary_contact_phone:
            payload["primary_contact_phone"] = primary_contact_phone

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/subaccount",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        data = response.json()

        if response.status_code == 201 and data.get("status"):
            subaccount_data = data.get("data", {})
            return {
                "status": "success",
                "subaccount_code": subaccount_data.get("subaccount_code", ""),
                "business_name": subaccount_data.get("business_name", ""),
            }

        return {
            "status": "error",
            "message": data.get("message", "Failed to create subaccount"),
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


def get_transfer_service() -> PaystackService:
    """
    Factory function to get PaystackService for transfers/payouts.
    Alias for get_paystack_service - same instance manages both.
    """
    return PaystackService()
