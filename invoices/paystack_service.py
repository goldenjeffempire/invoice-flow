"""
Paystack Payment Service for InvoiceFlow.
Handles payment processing, verification, and webhook handling.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import requests
from django.conf import settings


class PaystackService:
    """Service for handling Paystack payment operations."""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = os.environ.get("PAYSTACK_SECRET_KEY", "")
        self.public_key = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
        self.is_configured = bool(self.secret_key)
        
    @property
    def headers(self):
        """Get authorization headers for Paystack API."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    def initialize_payment(
        self,
        email: str,
        amount: Decimal,
        currency: str = "NGN",
        reference: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        subaccount_code: Optional[str] = None,
        bearer: str = "subaccount",
    ) -> dict[str, Any]:
        """
        Initialize a payment transaction.
        
        Args:
            email: Customer's email address
            amount: Amount in the currency's base unit (e.g., Naira for NGN)
            currency: Currency code (NGN, USD, GHS, ZAR, KES)
            reference: Unique transaction reference
            callback_url: URL to redirect to after payment
            metadata: Additional data to attach to the transaction
            subaccount_code: Subaccount code for split payments (merchant receives payment directly)
            bearer: Who bears transaction charges - 'account' (platform) or 'subaccount' (merchant)
        
        Returns:
            dict with authorization_url and reference, or error details
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured. Please set PAYSTACK_SECRET_KEY.",
                "configured": False,
            }
        
        amount_kobo = int(amount * 100)
        
        payload: dict[str, Any] = {
            "email": email,
            "amount": amount_kobo,
            "currency": currency,
        }
        
        if reference:
            payload["reference"] = reference
        if callback_url:
            payload["callback_url"] = callback_url
        if metadata:
            payload["metadata"] = metadata
        if subaccount_code:
            payload["subaccount"] = subaccount_code
            payload["bearer"] = bearer
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/initialize",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "authorization_url": data["data"]["authorization_url"],
                    "access_code": data["data"]["access_code"],
                    "reference": data["data"]["reference"],
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to initialize payment"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
            }
    
    def verify_payment(self, reference: str) -> dict[str, Any]:
        """
        Verify a payment transaction.
        
        Args:
            reference: Transaction reference to verify
        
        Returns:
            dict with transaction status and details
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                transaction = data["data"]
                return {
                    "status": "success",
                    "verified": transaction["status"] == "success",
                    "amount": Decimal(transaction["amount"]) / 100,
                    "currency": transaction["currency"],
                    "reference": transaction["reference"],
                    "paid_at": transaction.get("paid_at"),
                    "channel": transaction.get("channel"),
                    "customer_email": transaction.get("customer", {}).get("email"),
                    "metadata": transaction.get("metadata", {}),
                    "raw_data": transaction,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to verify payment"),
                    "verified": False,
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
                "verified": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "verified": False,
            }
    
    def create_payment_link(
        self,
        name: str,
        amount: Decimal,
        description: str = "",
        currency: str = "NGN",
        redirect_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Create a reusable payment link/page.
        
        Args:
            name: Name of the payment page
            amount: Amount in currency's base unit
            description: Description of what customer is paying for
            currency: Currency code
            redirect_url: URL to redirect after payment
            metadata: Additional data
        
        Returns:
            dict with payment link details
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        amount_kobo = int(amount * 100)
        
        payload = {
            "name": name,
            "amount": amount_kobo,
            "currency": currency,
        }
        
        if description:
            payload["description"] = description
        if redirect_url:
            payload["redirect_url"] = redirect_url
        if metadata:
            payload["metadata"] = metadata
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/page",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code in [200, 201] and data.get("status"):
                page = data["data"]
                return {
                    "status": "success",
                    "id": page["id"],
                    "slug": page["slug"],
                    "url": f"https://paystack.com/pay/{page['slug']}",
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to create payment link"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
            }
    
    def list_banks(self, country: str = "nigeria") -> dict[str, Any]:
        """
        Get list of supported banks for transfers.
        
        Args:
            country: Country code (nigeria, ghana, south-africa, kenya)
        
        Returns:
            dict with list of banks
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/bank",
                headers=self.headers,
                params={"country": country},
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "banks": data["data"],
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to fetch banks"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Paystack webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature: X-Paystack-Signature header value
        
        Returns:
            True if signature is valid
        """
        if not self.secret_key:
            return False
        
        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def get_transaction_history(
        self,
        page: int = 1,
        per_page: int = 50,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get transaction history.
        
        Args:
            page: Page number
            per_page: Number of transactions per page
            status: Filter by status (success, failed, abandoned)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        
        Returns:
            dict with transaction list
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        params: dict[str, Any] = {
            "page": page,
            "perPage": per_page,
        }
        
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/transaction",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "transactions": data["data"],
                    "meta": data.get("meta", {}),
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to fetch transactions"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
    
    def create_subaccount(
        self,
        business_name: str,
        bank_code: str,
        account_number: str,
        percentage_charge: Decimal = Decimal("0"),
        primary_contact_email: Optional[str] = None,
        primary_contact_name: Optional[str] = None,
        primary_contact_phone: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Create a Paystack subaccount for direct merchant payments.
        
        Args:
            business_name: Name of the business
            bank_code: Bank code from list_banks
            account_number: Bank account number
            percentage_charge: Platform fee percentage (0-100)
            primary_contact_email: Contact email for the subaccount
            primary_contact_name: Contact name
            primary_contact_phone: Contact phone
            metadata: Additional data
        
        Returns:
            dict with subaccount_code and details, or error
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        payload = {
            "business_name": business_name,
            "bank_code": bank_code,
            "account_number": account_number,
            "percentage_charge": float(percentage_charge),
        }
        
        if primary_contact_email:
            payload["primary_contact_email"] = primary_contact_email
        if primary_contact_name:
            payload["primary_contact_name"] = primary_contact_name
        if primary_contact_phone:
            payload["primary_contact_phone"] = primary_contact_phone
        if metadata:
            payload["metadata"] = metadata
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/subaccount",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code in [200, 201] and data.get("status"):
                subaccount = data["data"]
                return {
                    "status": "success",
                    "subaccount_code": subaccount["subaccount_code"],
                    "business_name": subaccount.get("business_name"),
                    "account_number": subaccount.get("account_number"),
                    "bank": subaccount.get("settlement_bank"),
                    "percentage_charge": subaccount.get("percentage_charge"),
                    "raw_data": subaccount,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to create subaccount"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
    
    def verify_account_number(
        self,
        account_number: str,
        bank_code: str,
    ) -> dict[str, Any]:
        """
        Verify a bank account number and get the account name.
        
        Args:
            account_number: Bank account number
            bank_code: Bank code
        
        Returns:
            dict with account_name and account_number, or error
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/bank/resolve",
                headers=self.headers,
                params={
                    "account_number": account_number,
                    "bank_code": bank_code,
                },
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "account_name": data["data"]["account_name"],
                    "account_number": data["data"]["account_number"],
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to verify account"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
    
    def update_subaccount(
        self,
        subaccount_code: str,
        business_name: Optional[str] = None,
        percentage_charge: Optional[Decimal] = None,
        primary_contact_email: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Update an existing subaccount.
        
        Args:
            subaccount_code: The subaccount code to update
            business_name: New business name
            percentage_charge: New percentage charge
            primary_contact_email: New contact email
            active: Enable/disable the subaccount
        
        Returns:
            dict with updated subaccount details
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        payload: dict[str, Any] = {}
        if business_name:
            payload["business_name"] = business_name
        if percentage_charge is not None:
            payload["percentage_charge"] = float(percentage_charge)
        if primary_contact_email:
            payload["primary_contact_email"] = primary_contact_email
        if active is not None:
            payload["active"] = active
        
        try:
            response = requests.put(
                f"{self.BASE_URL}/subaccount/{subaccount_code}",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "subaccount_code": data["data"]["subaccount_code"],
                    "raw_data": data["data"],
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to update subaccount"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }
    
    def get_subaccount(self, subaccount_code: str) -> dict[str, Any]:
        """
        Get details of a subaccount.
        
        Args:
            subaccount_code: The subaccount code
        
        Returns:
            dict with subaccount details
        """
        if not self.is_configured:
            return {
                "status": "error",
                "message": "Paystack is not configured.",
                "configured": False,
            }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/subaccount/{subaccount_code}",
                headers=self.headers,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "raw_data": data["data"],
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to get subaccount"),
                }
        
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Network error: {str(e)}",
            }


def get_paystack_service():
    """Get Paystack service instance."""
    return PaystackService()


class PaystackTransferService:
    """Service for handling Paystack transfer/payout operations."""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = os.environ.get("PAYSTACK_SECRET_KEY", "")
        self.is_configured = bool(self.secret_key)
        
    @property
    def headers(self):
        """Get authorization headers for Paystack API."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    def create_transfer_recipient(
        self,
        account_name: str,
        account_number: str,
        bank_code: str,
        currency: str = "NGN",
        recipient_type: str = "nuban",
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Create a transfer recipient for payouts.
        
        Args:
            account_name: Name of the account holder
            account_number: Bank account number
            bank_code: Bank code from list_banks
            currency: Currency code
            recipient_type: Type of recipient (nuban, ghipss, basa)
            metadata: Additional data
        
        Returns:
            dict with recipient_code and details
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        payload: dict[str, Any] = {
            "type": recipient_type,
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency,
        }
        
        if metadata:
            payload["metadata"] = metadata
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transferrecipient",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code in [200, 201] and data.get("status"):
                recipient = data["data"]
                return {
                    "status": "success",
                    "recipient_code": recipient["recipient_code"],
                    "name": recipient.get("name"),
                    "bank_name": recipient.get("details", {}).get("bank_name"),
                    "account_number": recipient.get("details", {}).get("account_number"),
                    "raw_data": recipient,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to create recipient"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
    
    def initiate_transfer(
        self,
        amount: Decimal,
        recipient_code: str,
        reason: str = "",
        reference: Optional[str] = None,
        currency: str = "NGN",
    ) -> dict[str, Any]:
        """
        Initiate a transfer/payout to a recipient.
        
        Args:
            amount: Amount to transfer (in base currency unit)
            recipient_code: Recipient code from create_transfer_recipient
            reason: Reason for the transfer
            reference: Unique transfer reference
            currency: Currency code
        
        Returns:
            dict with transfer_code and status
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        amount_kobo = int(amount * 100)
        
        payload = {
            "source": "balance",
            "amount": amount_kobo,
            "recipient": recipient_code,
            "currency": currency,
        }
        
        if reason:
            payload["reason"] = reason
        if reference:
            payload["reference"] = reference
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transfer",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code in [200, 201] and data.get("status"):
                transfer = data["data"]
                return {
                    "status": "success",
                    "transfer_code": transfer["transfer_code"],
                    "reference": transfer.get("reference"),
                    "amount": Decimal(transfer["amount"]) / 100,
                    "currency": transfer.get("currency"),
                    "transfer_status": transfer.get("status"),
                    "raw_data": transfer,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to initiate transfer"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
    
    def verify_transfer(self, reference: str) -> dict[str, Any]:
        """
        Verify the status of a transfer.
        
        Args:
            reference: Transfer reference
        
        Returns:
            dict with transfer status and details
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/transfer/verify/{reference}",
                headers=self.headers,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                transfer = data["data"]
                return {
                    "status": "success",
                    "transfer_status": transfer["status"],
                    "amount": Decimal(transfer["amount"]) / 100,
                    "currency": transfer.get("currency"),
                    "reference": transfer.get("reference"),
                    "transfer_code": transfer.get("transfer_code"),
                    "recipient": transfer.get("recipient", {}),
                    "raw_data": transfer,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to verify transfer"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
    
    def get_balance(self) -> dict[str, Any]:
        """
        Get available Paystack balance for transfers.
        
        Returns:
            dict with balance details
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/balance",
                headers=self.headers,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                balances = data["data"]
                return {
                    "status": "success",
                    "balances": [
                        {
                            "currency": b.get("currency"),
                            "balance": Decimal(b.get("balance", 0)) / 100,
                        }
                        for b in balances
                    ],
                    "raw_data": balances,
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to get balance"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
    
    def list_transfers(
        self,
        page: int = 1,
        per_page: int = 50,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        List transfer history.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status (pending, success, failed)
        
        Returns:
            dict with list of transfers
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        if status:
            params["status"] = status
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/transfer",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "transfers": data["data"],
                    "meta": data.get("meta", {}),
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to list transfers"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}
    
    def finalize_transfer(
        self,
        transfer_code: str,
        otp: str,
    ) -> dict[str, Any]:
        """
        Finalize a transfer that requires OTP.
        
        Args:
            transfer_code: Transfer code
            otp: One-time password
        
        Returns:
            dict with transfer status
        """
        if not self.is_configured:
            return {"status": "error", "message": "Paystack is not configured."}
        
        payload = {
            "transfer_code": transfer_code,
            "otp": otp,
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/transfer/finalize_transfer",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            
            data = response.json()
            
            if response.status_code == 200 and data.get("status"):
                return {
                    "status": "success",
                    "message": data.get("message", "Transfer finalized"),
                    "raw_data": data.get("data", {}),
                }
            else:
                return {
                    "status": "error",
                    "message": data.get("message", "Failed to finalize transfer"),
                }
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Network error: {str(e)}"}


def get_transfer_service():
    """Get Paystack transfer service instance."""
    return PaystackTransferService()
