"""
User Service - Business logic for user management.

Responsibilities:
- Profile management
- Notification preferences
- Payment settings
- Security settings
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from django.db import transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import UserProfile, PaymentSettings

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing user profiles."""

    @staticmethod
    def get_or_create_profile(user: "User") -> "UserProfile":
        """Get or create a user profile with safe defaults for all fields."""
        from invoices.models import UserProfile
        from decimal import Decimal
        from django.utils import timezone

        # Define comprehensive defaults for deterministic profile creation
        defaults = {
            "email_verified": False,
            "two_factor_enabled": False,
            "onboarding_completed": False,
            "onboarding_step": 1,
            "onboarding_data": {},
            "primary_color": "#6366f1",
            "secondary_color": "#8b5cf6",
            "accent_color": "#10b981",
            "invoice_style": "modern",
            "vat_registered": False,
            "vat_rate": Decimal('0.00'),
            "wht_applicable": False,
            "wht_rate": Decimal('0.00'),
            "default_tax_rate": Decimal('0.00'),
            "accept_card_payments": False,
            "accept_bank_transfers": True,
            "accept_mobile_money": False,
            "paystack_enabled": False,
            "paystack_subaccount_code": "",
            "paystack_subaccount_active": False,
            "stripe_enabled": False,
            "stripe_account_id": "",
            "tax_id": "",
            "tax_name": "",
            "webhook_secret": "",
            "customers_imported": False,
            "customers_import_count": 0,
            "products_imported": False,
            "products_import_count": 0,
            "invoices_imported": False,
            "invoices_import_count": 0,
            "default_currency": "NGN",
            "invoice_prefix": "INV",
            "invoice_start_number": 1,
            "invoice_numbering_format": "{prefix}-{year}-{number:04d}",
            "date_format": "DD/MM/YYYY",
            "timezone": "Africa/Lagos",
            "locale": "en-NG",
            "team_invites_sent": 0,
            "notify_invoice_created": True,
            "notify_payment_received": True,
            "notify_invoice_viewed": True,
            "notify_invoice_overdue": True,
            "notify_weekly_summary": True,
            "notify_security_alerts": True,
            "notify_password_changes": True,
            "failed_login_attempts": 0,
            "password_reset_required": False,
            "last_password_change": timezone.now(),
        }

        profile, created = UserProfile.objects.get_or_create(user=user, defaults=defaults)
        if created:
            logger.info(f"Created profile for user {user.id}")
        return profile

    @staticmethod
    @transaction.atomic
    def update_profile(
        user: "User",
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional["UserProfile"]]:
        """
        Update user profile with provided data.
        
        Args:
            user: The user whose profile to update
            data: Dictionary of profile field values
            
        Returns:
            Tuple of (success, message, profile)
        """
        from invoices.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=user)

        profile.company_name = data.get("company_name", profile.company_name)
        profile.business_email = data.get("business_email", profile.business_email)
        profile.business_phone = data.get("business_phone", profile.business_phone)
        profile.business_address = data.get("business_address", profile.business_address)
        profile.default_currency = data.get("default_currency", profile.default_currency)
        profile.invoice_prefix = data.get("invoice_prefix", profile.invoice_prefix)

        if "default_tax_rate" in data:
            try:
                profile.default_tax_rate = Decimal(str(data.get("default_tax_rate")))
            except (InvalidOperation, ValueError):
                return False, "Invalid tax rate.", None

        profile.save()
        logger.info(f"Profile updated for user {user.id}")
        return True, "Profile updated.", profile


class NotificationService:
    """Service for managing notification preferences."""

    NOTIFICATION_FIELDS = [
        "notify_invoice_created",
        "notify_payment_received",
        "notify_invoice_viewed",
        "notify_invoice_overdue",
        "notify_weekly_summary",
        "notify_security_alerts",
        "notify_password_changes",
    ]

    @staticmethod
    @transaction.atomic
    def update_preferences(
        user: "User",
        preferences: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Update notification preferences.
        
        Args:
            user: The user whose preferences to update
            preferences: Dictionary of preference values
            
        Returns:
            Tuple of (success, message)
        """
        from invoices.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=user)

        for field in NotificationService.NOTIFICATION_FIELDS:
            if field in preferences:
                value = str(preferences[field]).lower() in {"1", "true", "yes", "on"}
                setattr(profile, field, value)

        profile.save()
        logger.info(f"Notification preferences updated for user {user.id}")
        return True, "Notification preferences updated."


class PaymentSettingsService:
    """Service for managing payment settings."""

    BOOL_FIELDS = [
        "enable_card_payments",
        "enable_bank_transfers",
        "enable_mobile_money",
        "enable_ussd",
        "auto_payout",
        "send_payment_receipt",
        "send_payout_notification",
    ]

    STRING_FIELDS = [
        "preferred_currency",
        "payout_schedule",
        "payment_instructions",
        "paystack_public_key",
        "paystack_secret_key",
        "paystack_webhook_secret",
        "bank_name",
        "account_number_encrypted",
        "account_name",
        "webhook_secret",
    ]

    @staticmethod
    @transaction.atomic
    def update_settings(
        user: "User",
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional["PaymentSettings"]]:
        """
        Update payment settings.
        
        Args:
            user: The user whose settings to update
            data: Dictionary of setting values
            
        Returns:
            Tuple of (success, message, settings)
        """
        from invoices.models import PaymentSettings

        settings, _ = PaymentSettings.objects.get_or_create(user=user)

        for field in PaymentSettingsService.BOOL_FIELDS:
            if field in data:
                value = str(data[field]).lower() in {"1", "true", "yes", "on"}
                setattr(settings, field, value)

        for field in PaymentSettingsService.STRING_FIELDS:
            if field in data:
                setattr(settings, field, data.get(field, getattr(settings, field)))

        if "payout_threshold" in data:
            try:
                settings.payout_threshold = Decimal(str(data.get("payout_threshold")))
            except (InvalidOperation, ValueError):
                return False, "Invalid payout threshold.", None

        settings.save()
        logger.info(f"Payment settings updated for user {user.id}")
        return True, "Payment settings updated.", settings


class UserService:
    """Facade for user-related services."""

    profile = ProfileService
    notifications = NotificationService
    payment_settings = PaymentSettingsService

    @staticmethod
    def get_user_context(user: "User") -> Dict[str, Any]:
        """
        Get complete user context for views.
        
        Args:
            user: The user
            
        Returns:
            Dictionary with profile and settings
        """
        from invoices.models import UserProfile, PaymentSettings

        profile, _ = UserProfile.objects.get_or_create(user=user)
        payment_settings, _ = PaymentSettings.objects.get_or_create(user=user)

        return {
            "profile": profile,
            "payment_settings": payment_settings,
            "user": user,
        }
