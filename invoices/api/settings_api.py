"""
REST API endpoints for settings management.
Provides complete CRUD operations for user settings with proper authentication.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer, Serializer, CharField, BooleanField, IntegerField

from ..models import UserProfile, PaymentSettings
from ..payment_settings_views import verify_bank_account


class UserProfileSerializer(ModelSerializer):
    """Serializer for user profile settings."""

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "company_name",
            "business_email",
            "business_phone",
            "business_address",
            "default_currency",
            "default_tax_rate",
            "invoice_prefix",
            "timezone",
            "notify_invoice_created",
            "notify_payment_received",
            "notify_invoice_viewed",
            "notify_invoice_overdue",
            "notify_weekly_summary",
            "notify_security_alerts",
            "notify_password_changes",
            "paystack_subaccount_active",
        ]
        read_only_fields = ["id"]


class PaymentSettingsSerializer(ModelSerializer):
    """Serializer for payment settings."""

    class Meta:
        model = PaymentSettings
        fields = [
            "id",
            "enable_card_payments",
            "enable_bank_transfers",
            "enable_mobile_money",
            "enable_ussd",
            "preferred_currency",
            "auto_payout",
            "payout_schedule",
            "payout_threshold",
            "send_payment_receipt",
            "send_payout_notification",
            "payment_instructions",
        ]
        read_only_fields = ["id"]


class SettingsViewSet(viewsets.ViewSet):
    """
    API endpoints for retrieving and updating user settings.
    Provides profile and payment settings management.
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "put"], url_path="profile")
    def profile_settings(self, request):
        """Get or update user profile settings."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        if request.method == "PUT":
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["get", "put"], url_path="payment")
    def payment_settings(self, request):
        """Get or update user payment settings."""
        payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)

        if request.method == "PUT":
            serializer = PaymentSettingsSerializer(
                payment_settings, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = PaymentSettingsSerializer(payment_settings)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="all")
    def all_settings(self, request):
        """Get all user settings (profile + payment)."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)

        return Response(
            {
                "profile": UserProfileSerializer(profile).data,
                "payment": PaymentSettingsSerializer(payment_settings).data,
            }
        )

    @action(detail=False, methods=["post"], url_path="payment/verify-bank")
    def verify_bank_account_api(self, request):
        """Verify bank account for payment recipient."""
        account_number = request.data.get("account_number", "").strip()
        bank_code = request.data.get("bank_code", "").strip()

        if not account_number or not bank_code:
            return Response(
                {"error": "Account number and bank code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not account_number.isdigit() or len(account_number) != 10:
            return Response(
                {"error": "Invalid account number format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from ..paystack_service import get_paystack_service

        paystack = get_paystack_service()
        if not paystack.is_configured:
            return Response(
                {"error": "Payment gateway not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        result = paystack.verify_account_number(account_number, bank_code)

        if result.get("status") == "success":
            return Response(
                {
                    "status": "success",
                    "account_name": result.get("account_name", ""),
                    "account_number": result.get("account_number", ""),
                }
            )

        return Response(
            {"error": result.get("message", "Could not verify account")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"], url_path="payment/toggle-payout")
    def toggle_auto_payout(self, request):
        """Toggle automatic payout setting."""
        payment_settings, _ = PaymentSettings.objects.get_or_create(user=request.user)

        payment_settings.auto_payout = not payment_settings.auto_payout
        payment_settings.save()

        serializer = PaymentSettingsSerializer(payment_settings)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="notification-preferences")
    def update_notifications(self, request):
        """Update notification preferences."""
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        notification_fields = [
            "notify_invoice_created",
            "notify_payment_received",
            "notify_invoice_viewed",
            "notify_invoice_overdue",
            "notify_weekly_summary",
            "notify_security_alerts",
            "notify_password_changes",
        ]

        for field in notification_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])

        profile.save()

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
