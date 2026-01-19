from __future__ import annotations

import secrets
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Type, Callable, Union
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.apps import apps

from .validators import (
    InvoiceBusinessRules,
    validate_payment_reference,
    validate_positive_decimal,
    validate_tax_rate,
)


# ============================================================================
# WAITLIST
# ============================================================================

class Waitlist(models.Model):
    class Feature(models.TextChoices):
        TEMPLATES = "templates", "Invoice Templates"
        API = "api", "API Access"
        GENERAL = "general", "General Updates"

    email = models.EmailField(unique=True)
    feature = models.CharField(
        max_length=20, choices=Feature.choices, default=Feature.GENERAL
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    
    objects = models.Manager()

    class Meta:
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["feature", "is_notified"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.get_feature_display()})"  # type: ignore[attr-defined]


# ============================================================================
# CONTACT FORM
# ============================================================================

class ContactSubmission(models.Model):
    class Subject(models.TextChoices):
        SALES = "sales", "Sales Inquiry"
        SUPPORT = "support", "Technical Support"
        BILLING = "billing", "Billing Question"
        FEATURE = "feature", "Feature Request"
        BUG = "bug", "Bug Report"
        GENERAL = "general", "General Inquiry"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=50, choices=Subject.choices)
    message = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "-submitted_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} – {self.get_subject_display()}"  # type: ignore[attr-defined]


# ============================================================================
# USER PROFILE
# ============================================================================

class UserProfile(models.Model):
    CURRENCY_CHOICES = [
        ("USD", "$ - US Dollar"),
        ("EUR", "€ - Euro"),
        ("GBP", "£ - British Pound"),
        ("NGN", "₦ - Nigerian Naira"),
        ("CAD", "C$ - Canadian Dollar"),
        ("AUD", "A$ - Australian Dollar"),
        ("INR", "₹ - Indian Rupee"),
        ("JPY", "¥ - Japanese Yen"),
        ("ZAR", "R - South African Rand"),
        ("KES", "KSh - Kenyan Shilling"),
        ("GHS", "GH₵ - Ghanaian Cedi"),
        ("BTC", "₿ - Bitcoin"),
        ("ETH", "Ξ - Ethereum"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    company_name = models.CharField(max_length=200, blank=True)
    company_logo = models.FileField(upload_to="company_logos/", null=True, blank=True)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)

    default_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    invoice_prefix = models.CharField(max_length=10, default="INV")
    timezone = models.CharField(max_length=63, default="UTC")

    notify_invoice_created = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_invoice_viewed = models.BooleanField(default=True)
    notify_invoice_overdue = models.BooleanField(default=True)
    notify_weekly_summary = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    notify_password_changes = models.BooleanField(default=True)

    email_verified = models.BooleanField(default=False)
    
    objects = models.Manager()

    # Payment Gateways (Stripe/Paystack)
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_enabled = models.BooleanField(default=False)
    paystack_enabled = models.BooleanField(default=False)
    paystack_subaccount_code = models.CharField(max_length=100, blank=True, null=True)
    paystack_subaccount_active = models.BooleanField(default=False)

    # Tax Settings
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    tax_name = models.CharField(max_length=50, default="VAT")
    
    # Webhook Secrets (Encrypted or just stored)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def has_payment_setup(self) -> bool:
        return bool((self.paystack_subaccount_code and self.paystack_subaccount_active) or (self.stripe_account_id and self.stripe_enabled))

    def __str__(self) -> str:
        return f"{self.user} Profile"


# ============================================================================
# INVOICE TEMPLATE
# ============================================================================

class InvoiceTemplate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoice_templates",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField()

    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)

    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # type: ignore[assignment]

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_default"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_default:
            # type: ignore[attr-defined]
            self.__class__._default_manager.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.name)


# ============================================================================
# INVOICE
# ============================================================================

class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    CURRENCY_CHOICES = [
        ("USD", "USD - US Dollar"),
        ("EUR", "EUR - Euro"),
        ("GBP", "GBP - British Pound"),
        ("NGN", "NGN - Nigerian Naira"),
        ("CAD", "CAD - Canadian Dollar"),
        ("AUD", "AUD - Australian Dollar"),
        ("INR", "INR - Indian Rupee"),
        ("JPY", "JPY - Japanese Yen"),
        ("ZAR", "ZAR - South African Rand"),
        ("KES", "KES - Kenyan Shilling"),
        ("GHS", "GHS - Ghanaian Cedi"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    invoice_id = models.CharField(max_length=32, unique=True, editable=False)

    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)

    client_name = models.CharField(max_length=200, db_index=True)
    client_email = models.EmailField(db_index=True)
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    invoice_date = models.DateField(default=timezone.now, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)

    currency = models.CharField(max_length=3, default="USD", db_index=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    automated_reminders_enabled = models.BooleanField(default=True)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UNPAID, db_index=True
    )
    
    objects = models.Manager()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        errors = {}
        try:
            validate_tax_rate(self.tax_rate)
        except ValidationError as exc:
            errors["tax_rate"] = exc.messages

        try:
            discount_value = Decimal(str(self.discount))
        except (InvalidOperation, ValueError):
            errors["discount"] = ["Discount must be a valid number."]
        else:
            if discount_value < 0 or discount_value > 100:
                errors["discount"] = ["Discount must be between 0 and 100 percent."]

        try:
            InvoiceBusinessRules.validate_due_date(self.invoice_date, self.due_date)
        except ValidationError as exc:
            errors["due_date"] = exc.messages

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.business_email and getattr(self, "user", None):
            self.business_email = self.user.email or ""
        self.full_clean()
        if not self.invoice_id:
            self.invoice_id = self._generate_invoice_id()
        super().save(*args, **kwargs)

    def _generate_invoice_id(self) -> str:
        try:
            prefix = self.user.profile.invoice_prefix  # type: ignore[attr-defined]
        except (AttributeError, UserProfile.DoesNotExist):  # type: ignore[attr-defined]
            prefix = "INV"
        while True:
            code = f"{prefix}-{secrets.token_hex(4).upper()}"
            if not Invoice.objects.filter(invoice_id=code).exists():  # type: ignore[attr-defined]
                return code

    @property
    def subtotal(self) -> Decimal:
        return sum((item.total for item in self.line_items.all()), Decimal("0"))

    @property
    def discount_amount(self) -> Decimal:
        """Calculates the absolute discount value."""
        return (self.subtotal * Decimal(str(self.discount))) / Decimal("100")

    @property
    def tax_amount(self) -> Decimal:
        """Calculates the tax amount based on subtotal minus discount."""
        return ((self.subtotal - self.discount_amount) * Decimal(str(self.tax_rate))) / Decimal("100")

    @property
    def total(self) -> Decimal:
        """Calculates the grand total of the invoice."""
        # Ensure discount is applied to subtotal before tax calculation
        # Most tax jurisdictions apply tax after discounts
        discountable_amount = self.subtotal - self.discount_amount
        taxable_amount = discountable_amount
        tax_total = (taxable_amount * Decimal(str(self.tax_rate))) / Decimal("100")
        
        total = discountable_amount + tax_total
        return total.quantize(Decimal("0.01"))

    @transaction.atomic
    def mark_as_paid(self) -> None:
        """Updates the invoice status to PAID and handles associated business logic."""
        if self.status == self.Status.PAID:
            return

        self.status = self.Status.PAID
        self.save(update_fields=["status", "updated_at"])

        # Update associated payments
        self.payments.filter(status="pending").update(
            status="success", 
            paid_at=timezone.now(),
            updated_at=timezone.now()
        )

        # Integration point for analytics/notification services
        from .services import AnalyticsService, EmailService
        
        AnalyticsService.invalidate_user_cache(self.user_id)
        try:
            # Send receipt for the latest successful payment
            successful_payment = self.payments.filter(status="success").order_by('-paid_at').first()
            if successful_payment:
                EmailService.send_receipt(successful_payment)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send payment confirmation: {e}")

    def mark_as_overdue(self) -> None:
        """Updates the invoice status to OVERDUE."""
        if self.status == self.Status.UNPAID:
            self.status = self.Status.OVERDUE
            self.save(update_fields=["status", "updated_at"])


# ============================================================================
# LINE ITEMS
# ============================================================================

class LineItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )

    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self) -> None:
        errors = {}
        try:
            validate_positive_decimal(self.quantity)
        except ValidationError as exc:
            errors["quantity"] = exc.messages

        try:
            validate_positive_decimal(self.unit_price)
        except ValidationError as exc:
            errors["unit_price"] = exc.messages

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total(self) -> Decimal:
        return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))

    def __str__(self) -> str:
        return str(self.description)


# ============================================================================
# PAYMENTS (SINGLE SOURCE OF TRUTH)
# ============================================================================

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.BigAutoField(primary_key=True)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    reference = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    customer_email = models.EmailField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def clean(self) -> None:
        errors = {}
        try:
            validate_payment_reference(self.reference)
        except ValidationError as exc:
            errors["reference"] = exc.messages

        try:
            validate_positive_decimal(self.amount)
        except ValidationError as exc:
            errors["amount"] = exc.messages

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_successful(self) -> bool:
        return self.status == self.Status.SUCCESS

    @transaction.atomic
    def mark_as_success(self, paid_at: Optional[datetime] = None) -> None:
        """Atomically mark payment as successful and update invoice."""
        if self.status == self.Status.SUCCESS:
            return
            
        self.status = self.Status.SUCCESS
        self.paid_at = paid_at or timezone.now()
        self.save(update_fields=["status", "paid_at", "updated_at"])
        
        # Update invoice status
        if self.invoice.status != Invoice.Status.PAID:
            self.invoice.status = Invoice.Status.PAID
            self.invoice.save(update_fields=["status", "updated_at"])

    def __str__(self) -> str:
        return f"{self.reference} ({self.status})"


# ============================================================================
# WEBHOOK DEDUPLICATION
# ============================================================================

class ProcessedWebhook(models.Model):
    """Tracks processed payment webhooks to prevent replay handling."""

    event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique event identifier from payment provider",
    )
    provider = models.CharField(
        max_length=50,
        default="paystack",
        help_text="Payment provider (paystack, stripe, etc)",
    )
    event_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Event type (charge.success, etc)",
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Transaction reference",
    )
    payload_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 hash of payload for integrity verification",
    )
    processed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["provider", "event_id"]),
            models.Index(fields=["-processed_at"]),
        ]
        verbose_name = "Processed Webhook"
        verbose_name_plural = "Processed Webhooks"

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id}"


# ============================================================================
# AUTOMATED REMINDERS (NEW SYSTEM)
# ============================================================================

class ReminderRule(models.Model):
    """Defines rules for when automated reminders should be sent."""
    class TriggerType(models.TextChoices):
        BEFORE_DUE = "before_due", "Days Before Due Date"
        ON_DUE = "on_due", "On Due Date"
        AFTER_DUE = "after_due", "Days After Due Date"
        UPON_CREATION = "upon_creation", "Immediately Upon Creation"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminder_rules")
    name = models.CharField(max_length=100)
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.AFTER_DUE)
    days_delta = models.IntegerField(default=0)
    channel = models.CharField(max_length=20, choices=[('email', 'Email'), ('in_app', 'In-App'), ('sms', 'SMS')], default='email')
    exclude_weekends = models.BooleanField(default=False)
    retry_on_failure = models.BooleanField(default=True)
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=300)
    subject_template = models.CharField(max_length=255, blank=True)
    body_template = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Advanced Settings
    custom_sender_name = models.CharField(max_length=100, blank=True)
    reply_to_email = models.EmailField(blank=True)
    attach_pdf = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["trigger_type", "days_delta"]
        unique_together = ["user", "trigger_type", "days_delta"]

class ScheduledReminder(models.Model):
    """A specific reminder instance scheduled for an invoice."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        RETRYING = "retrying", "Retrying"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="scheduled_reminders")
    rule = models.ForeignKey(ReminderRule, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_for = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True)
    delivery_metadata = models.JSONField(default=dict, blank=True) # Store provider IDs, open rates, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for"]
        indexes = [models.Index(fields=["status", "scheduled_for"])]

class ReminderLog(models.Model):
    """Audit trail for all sent reminders."""
    scheduled_reminder = models.OneToOneField(ScheduledReminder, on_delete=models.SET_NULL, null=True, related_name="log")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=True)
    
    objects = models.Manager()


class InAppNotification(models.Model):
    """Internal notifications for users within the platform dashboard."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="in_app_notifications")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    
    objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self) -> str:
        return f"{self.title} for {self.user}"

# ============================================================================
# PROCESSED PAYSTACK WEBHOOKS
# ============================================================================


# ============================================================================
# EMAIL VERIFICATION TOKEN
# ============================================================================

class EmailVerificationToken(models.Model):
    class TokenType(models.TextChoices):
        SIGNUP = "signup", "Account Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"
        EMAIL_CHANGE = "email_change", "Email Change"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_tokens",
    )

    token = models.CharField(max_length=64, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, choices=TokenType.choices)
    email = models.EmailField()

    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > timezone.now()

    def mark_used(self) -> None:
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])

    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(48)

    @classmethod
    def create_verification_token(
        cls,
        user: settings.AUTH_USER_MODEL,
        email: str,
        token_type: str,
        expires_hours: int = 24,
    ) -> "EmailVerificationToken":
        cls.objects.filter(
            user=user,
            token_type=token_type,
            is_used=False,
        ).update(is_used=True, used_at=timezone.now())

        token = cls.generate_token()
        expires_at = timezone.now() + timedelta(hours=expires_hours)
        return cls.objects.create(
            user=user,
            email=email,
            token=token,
            token_type=token_type,
            expires_at=expires_at,
        )


# ============================================================================
# LOGIN ATTEMPT (SECURITY TRACKING)
# ============================================================================

class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username", "-created_at"]),
            models.Index(fields=["ip_address", "-created_at"]),
        ]

    def __str__(self) -> str:
        status = "success" if self.success else "failed"
        return f"{self.username} - {status} at {self.created_at}"


# ============================================================================
# MFA PROFILE
# ============================================================================

class MFAProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_profile",
    )
    secret_key = models.CharField(max_length=32, blank=True)
    recovery_codes = models.JSONField(default=list, blank=True)
    is_enabled = models.BooleanField(default=False)
    backup_phone = models.CharField(max_length=20, blank=True, null=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        username = getattr(self.user, 'username', 'Unknown')
        status_val = "enabled" if self.is_enabled else "disabled"
        return f"MFA for {username} ({status_val})"  # type: ignore[attr-defined, name-defined]


# ============================================================================
# USER SESSION
# ============================================================================

class UserSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_sessions",
    )
    session_key = models.CharField(max_length=40)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen"]
        indexes = [
            models.Index(fields=["user", "-last_seen"]),
            models.Index(fields=["session_key"]),
        ]

    def __str__(self) -> str:
        return f"Session for {getattr(self.user, 'username', 'Unknown')}"

    def revoke(self) -> None:
        self.is_revoked = True
        self.save(update_fields=["is_revoked"])

    @classmethod
    def create_session(
        cls,
        user: settings.AUTH_USER_MODEL,
        session_key: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> "UserSession":
        return cls.objects.create(
            user=user,
            session_key=session_key,
            ip_address=ip_address or None,
            user_agent=user_agent or "",
        )


# ============================================================================
# SOCIAL ACCOUNT (OAUTH)
# ============================================================================

class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        GITHUB = "github", "GitHub"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_id = models.CharField(max_length=255, default="", db_index=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_scopes = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{getattr(self.user, 'username', 'Unknown')} - {self.get_provider_display()}"  # type: ignore[attr-defined]


# ============================================================================
# RECURRING INVOICE
# ============================================================================

class RecurringInvoice(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_invoices",
    )
    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()

    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField(blank=True)

    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # type: ignore[assignment]

    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_generation = models.DateField(null=True, blank=True)
    last_generated = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["next_generation"]),
        ]

    def __str__(self) -> str:
        return f"Recurring: {self.client_name} ({self.get_frequency_display()})"  # type: ignore[attr-defined]

class RecurringInvoiceLineItem(models.Model):
    recurring_invoice = models.ForeignKey(
        RecurringInvoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self) -> Decimal:
        return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))

    def __str__(self) -> str:
        return str(self.description)


# ============================================================================
# PAYMENT SETTINGS
# ============================================================================

class PaymentSettings(models.Model):
    class PayoutSchedule(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        MANUAL = "manual", "Manual"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_settings",
    )

    enable_card_payments = models.BooleanField(default=True)  # type: ignore[assignment]
    enable_bank_transfers = models.BooleanField(default=True)  # type: ignore[assignment]
    enable_mobile_money = models.BooleanField(default=False)  # type: ignore[assignment]
    enable_ussd = models.BooleanField(default=False)  # type: ignore[assignment]
    preferred_currency = models.CharField(max_length=3, default="USD")
    auto_payout = models.BooleanField(default=True)  # type: ignore[assignment]
    payout_schedule = models.CharField(
        max_length=20, choices=PayoutSchedule.choices, default=PayoutSchedule.DAILY
    )
    payout_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    send_payment_receipt = models.BooleanField(default=True)  # type: ignore[assignment]
    send_payout_notification = models.BooleanField(default=True)  # type: ignore[assignment]
    payment_instructions = models.TextField(blank=True)

    paystack_public_key = models.CharField(max_length=255, blank=True)
    paystack_secret_key = models.CharField(max_length=255, blank=True)
    paystack_webhook_secret = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=255, blank=True)
    account_number_encrypted = models.CharField(max_length=255, blank=True)
    account_name = models.CharField(max_length=255, blank=True)

    webhook_secret = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        username = getattr(self.user, 'username', 'Unknown')
        return f"Payment Settings for {username}"  # type: ignore[attr-defined]


# ============================================================================
# PROCESSED PAYSTACK WEBHOOKS
# ============================================================================


class PaymentRecipient(models.Model):
    class AccountType(models.TextChoices):
        PERSONAL = "personal", "Personal"
        BUSINESS = "business", "Business"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_recipients",
    )

    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.PERSONAL)
    bank_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=30)
    account_name = models.CharField(max_length=200, blank=True)
    currency = models.CharField(max_length=3, default="NGN")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    is_primary = models.BooleanField(default=False)  # type: ignore[assignment]
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # type: ignore[assignment]

    recipient_code = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.account_number}"


# ============================================================================
# PAYMENT CARD
# ============================================================================

class PaymentCard(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_cards",
    )

    brand = models.CharField(max_length=50)
    last4 = models.CharField(max_length=4)
    exp_month = models.PositiveIntegerField()
    exp_year = models.PositiveIntegerField()

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)  # type: ignore[assignment]
    is_primary = models.BooleanField(default=False)  # type: ignore[assignment]
    
    authorization_code = models.CharField(max_length=255, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    card_type = models.CharField(max_length=50, blank=True)
    bank = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    reusable = models.BooleanField(default=False)  # type: ignore[assignment]
    nickname = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.brand} **** {self.last4}"


# ============================================================================
# PAYMENT PAYOUT
# ============================================================================

class PaymentPayout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_payouts",
    )
    recipient = models.ForeignKey(
        PaymentRecipient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    reference = models.CharField(max_length=255, unique=True)
    paystack_transfer_code = models.CharField(max_length=255, blank=True)
    failure_message = models.TextField(blank=True)

    attempted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self) -> str:
        return f"Payout {self.reference} ({self.status})"


# ============================================================================
# IDEMPOTENCY KEY (PAYMENT SAFETY)
# ============================================================================

class IdempotencyKey(models.Model):
    """
    Prevents duplicate payment processing via idempotency keys.
    Critical for payment safety when requests are retried.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    key = models.CharField(max_length=255, unique=True, db_index=True)
    request_hash = models.CharField(max_length=64)
    response_data = models.JSONField(default=dict)
    http_status = models.PositiveIntegerField(default=200)  # type: ignore[assignment]
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["key", "-created_at"]),
        ]

    def is_valid(self) -> bool:
        return self.expires_at > timezone.now()

    def __str__(self) -> str:
        key_str = str(self.key)
        username = getattr(self.user, 'username', 'Unknown')
        return f"IdempotencyKey {key_str[:8]}... ({username})"  # type: ignore[attr-defined, name-defined]


# ============================================================================
# PAYMENT RECONCILIATION (STATE MACHINE FOR PAYMENT TRACKING)
# ============================================================================

class PaymentReconciliation(models.Model):
    """
    Tracks payment state transitions for reconciliation with Paystack.
    Critical for detecting lost/interrupted payments and ensuring no double-charging.
    """
    class ReconciliationStatus(models.TextChoices):
        PENDING = "pending", "Pending Reconciliation"
        IN_PROGRESS = "in_progress", "Reconciliation In Progress"
        VERIFIED = "verified", "Verified with Paystack"
        MISMATCH = "mismatch", "Amount/Status Mismatch"
        RECOVERED = "recovered", "Recovered via Retry"
        FAILED = "failed", "Reconciliation Failed"

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="reconciliation",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_reconciliations",
    )

    status = models.CharField(
        max_length=20,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.PENDING,
    )

    paystack_status = models.CharField(max_length=50, blank=True)
    local_status = models.CharField(max_length=50)

    amount_match = models.BooleanField(default=True)  # type: ignore[assignment]
    currency_match = models.BooleanField(default=True)  # type: ignore[assignment]
    status_match = models.BooleanField(default=True)  # type: ignore[assignment]

    retry_count = models.PositiveIntegerField(default=0)  # type: ignore[assignment]
    last_attempt = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def is_complete(self) -> bool:
        return self.status in [self.ReconciliationStatus.VERIFIED, self.ReconciliationStatus.RECOVERED]

    def __str__(self) -> str:
        reference = getattr(self.payment, 'reference', 'Unknown')
        return f"Reconciliation {reference} ({self.status})"  # type: ignore[attr-defined]


# ============================================================================
# PAYMENT RECOVERY (AUTOMATIC RETRY LOGIC)
# ============================================================================

class PaymentRecovery(models.Model):
    """
    Tracks failed payment recovery attempts.
    Enables automatic retry logic for interrupted or failed payments.
    """
    class RecoveryStrategy(models.TextChoices):
        IMMEDIATE_RETRY = "immediate_retry", "Immediate Retry"
        SCHEDULED_RETRY = "scheduled_retry", "Scheduled Retry (30s)"
        WEBHOOK_RETRY = "webhook_retry", "Webhook Verification"
        MANUAL_VERIFICATION = "manual_verification", "Manual Verification"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="recovery_attempts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_recoveries",
    )

    strategy = models.CharField(
        max_length=30,
        choices=RecoveryStrategy.choices,
        default=RecoveryStrategy.WEBHOOK_RETRY,
    )
    attempt_number = models.PositiveIntegerField(default=1)  # type: ignore[assignment]
    max_attempts = models.PositiveIntegerField(default=3)  # type: ignore[assignment]

    error_reason = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)

    is_successful = models.BooleanField(default=False)  # type: ignore[assignment]
    attempted_at = models.DateTimeField(auto_now_add=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["user", "is_successful"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def should_retry(self) -> bool:
        return not self.is_successful and self.attempt_number < self.max_attempts

    def __str__(self) -> str:
        reference = getattr(self.payment, 'reference', 'Unknown')
        return f"Recovery {reference} (Attempt {self.attempt_number})"  # type: ignore[attr-defined]


# ============================================================================
# IDENTITY VERIFICATION FOR PAYOUTS (KYC)
# ============================================================================

class UserIdentityVerification(models.Model):
    """
    Strong identity verification (KYC) for payout enablement.
    Prevents fraud and ensures compliance before enabling transfers.
    """
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Not Verified"
        PENDING = "pending", "Pending Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Verification Expired"

    class DocumentType(models.TextChoices):
        PASSPORT = "passport", "Passport"
        NATIONAL_ID = "national_id", "National ID"
        DRIVERS_LICENSE = "drivers_license", "Driver's License"
        BVN = "bvn", "Bank Verification Number (BVN)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identity_verification",
    )

    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )

    # Personal Information
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Document Information
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        blank=True,
    )
    document_number = models.CharField(max_length=100, blank=True, unique=True, null=True)
    document_expiry = models.DateField(null=True, blank=True)

    # Verification Details
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=100, blank=True)  # Service used (e.g., Paystack KYC)
    rejection_reason = models.TextField(blank=True)

    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
        ]

    def is_verified(self) -> bool:
        now = timezone.now()
        if self.status != self.VerificationStatus.VERIFIED:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True

    def can_enable_payouts(self) -> bool:
        """Check if user can enable payouts based on identity verification."""
        return self.is_verified()

    def __str__(self) -> str:
        return f"Identity Verification {getattr(self.user, 'email', 'Unknown')} ({str(self.status)})"  # type: ignore[attr-defined]


# ============================================================================
# USER SETTINGS (PERSISTENT, AUDITED)
# ============================================================================

class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings_audit",
    )

    allow_marketing_emails = models.BooleanField(default=False)  # type: ignore[assignment]
    allow_security_alerts = models.BooleanField(default=True)  # type: ignore[assignment]
    invoice_reminders_enabled = models.BooleanField(default=True)  # type: ignore[assignment]
    payment_notifications_enabled = models.BooleanField(default=True)  # type: ignore[assignment]
    
    two_factor_enabled = models.BooleanField(default=False)  # type: ignore[assignment]
    two_factor_method = models.CharField(
        max_length=20,
        choices=[("totp", "TOTP"), ("email", "Email")],
        default="totp",
        blank=True,
    )
    
    preferred_language = models.CharField(max_length=10, default="en")
    preferred_timezone = models.CharField(max_length=63, default="UTC")
    
    theme_preference = models.CharField(
        max_length=20,
        choices=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")],
        default="auto",
    )
    
    data_retention_days = models.PositiveIntegerField(default=365)  # type: ignore[assignment]
    auto_export_enabled = models.BooleanField(default=False)  # type: ignore[assignment]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"
        indexes = [
            models.Index(fields=["user", "updated_at"]),
        ]
    
    def __str__(self) -> str:
        return f"Settings for {getattr(self.user, 'username', 'Unknown')}"  # type: ignore[attr-defined, name-defined]
    
    def validate_settings(self) -> dict:
        errors = {}
        if self.data_retention_days < 30:
            errors["data_retention_days"] = "Minimum 30 days required"
        if self.preferred_timezone not in ["UTC", "Africa/Lagos", "Europe/London", "America/New_York"]:
            try:
                import pytz
                pytz.timezone(str(self.preferred_timezone))
            except Exception:
                errors["preferred_timezone"] = "Invalid timezone"
        return errors


class UserSettingsAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"
        ACCESSED = "accessed", "Accessed"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings_audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{getattr(self.user, 'username', 'Unknown')} - {self.action} on {self.created_at}"


# ============================================================================
# RECURRING INVOICE SAFETY
# ============================================================================

class ExecutionLock(models.Model):
    name = models.CharField(max_length=255, unique=True)
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    process_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["name", "expires_at"]),
        ]
    
    def __str__(self) -> str:
        return f"Lock: {self.name}"


class RecurringInvoiceExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
    
    recurring_invoice = models.ForeignKey(
        RecurringInvoice,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    invoice_generated = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_execution",
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)  # type: ignore[assignment]
    max_retries = models.PositiveIntegerField(default=3)  # type: ignore[assignment]
    
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["recurring_invoice", "status"]),
            models.Index(fields=["idempotency_key"]),
        ]
    
    def __str__(self) -> str:
        return f"Execution {self.id} - {self.recurring_invoice.client_name} ({self.status})"  # type: ignore[attr-defined]


# ============================================================================
# PUBLIC INVOICE SECURITY
# ============================================================================

class PublicInvoiceToken(models.Model):
    invoice = models.OneToOneField(
        Invoice,
        on_delete=models.CASCADE,
        related_name="public_token",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    access_count = models.PositiveIntegerField(default=0)  # type: ignore[assignment]
    max_accesses = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["token", "is_revoked"]),
            models.Index(fields=["invoice", "expires_at"]),
        ]
    
    def is_valid(self) -> bool:
        if self.is_revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.max_accesses and self.access_count >= self.max_accesses:
            return False
        return True
    
    def __str__(self) -> str:
        return f"Token for {getattr(self.invoice, 'invoice_id', 'Unknown')}"


class InvoiceAccessLog(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="access_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.TextField(blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    accessed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_access_logs",
    )
    
    class Meta:
        ordering = ["-accessed_at"]
        indexes = [
            models.Index(fields=["invoice", "-accessed_at"]),
            models.Index(fields=["ip_address", "-accessed_at"]),
        ]
    
    def __str__(self) -> str:
        return f"Access {getattr(self.invoice, 'invoice_id', 'Unknown')} at {self.accessed_at}"


class EngagementMetric(models.Model):
    class MetricType(models.TextChoices):
        PAGE_VIEW = "page_view", "Page View"
        BUTTON_CLICK = "button_click", "Button Click"
        SESSION_DURATION = "session_duration", "Session Duration"
        BOUNCE = "bounce", "Bounce"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="engagement_metrics")
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name="engagement_metrics")
    metric_type = models.CharField(max_length=20, choices=MetricType.choices)
    element_id = models.CharField(max_length=100, blank=True)
    value = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "metric_type", "timestamp"]),
            models.Index(fields=["invoice", "metric_type"]),
        ]

class UserFeedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    page_url = models.URLField(max_length=500)
    user_agent = models.TextField(blank=True)
    is_mobile = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

class EmailDeliveryLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        BOUNCED = "bounced", "Bounced"
        FAILED = "failed", "Failed"
        QUEUED = "queued", "Queued"
    
    class EmailType(models.TextChoices):
        VERIFICATION = "verification", "Email Verification"
        INVOICE_READY = "invoice_ready", "Invoice Ready"
        PAYMENT_REMINDER = "payment_reminder", "Payment Reminder"
        PAYMENT_RECEIPT = "payment_receipt", "Payment Receipt"
        RECURRING_NOTIFICATION = "recurring_notification", "Recurring Notification"
        SECURITY_ALERT = "security_alert", "Security Alert"
        PASSWORD_RESET = "password_reset", "Password Reset"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_logs",
    )
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    email_type = models.CharField(max_length=50, choices=EmailType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    
    message_id = models.CharField(max_length=255, blank=True, db_index=True)
    bounce_type = models.CharField(max_length=50, blank=True)
    bounce_reason = models.TextField(blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    related_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["to_email", "-created_at"]),
            models.Index(fields=["email_type", "status"]),
            models.Index(fields=["message_id"]),
        ]
    
    def __str__(self) -> str:
        return f"Email to {self.to_email} ({self.status})"


class EmailRetryQueue(models.Model):
    class RetryStrategy(models.TextChoices):
        EXPONENTIAL = "exponential", "Exponential Backoff"
        LINEAR = "linear", "Linear Backoff"
        IMMEDIATE = "immediate", "Immediate Retry"
    
    email_log = models.ForeignKey(
        EmailDeliveryLog,
        on_delete=models.CASCADE,
        related_name="retry_queue",
    )
    retry_count = models.PositiveIntegerField(default=0)  # type: ignore[assignment]
    max_retries = models.PositiveIntegerField(default=5)  # type: ignore[assignment]
    retry_strategy = models.CharField(
        max_length=20,
        choices=RetryStrategy.choices,
        default=RetryStrategy.EXPONENTIAL,
    )
    
    next_retry_at = models.DateTimeField()
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)  # type: ignore[assignment]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["next_retry_at"]
        indexes = [
            models.Index(fields=["is_active", "next_retry_at"]),
            models.Index(fields=["email_log", "is_active"]),
        ]
    
    def __str__(self) -> str:
        return f"Retry {self.retry_count}/{self.max_retries} - {getattr(self.email_log, 'to_email', 'Unknown')}"
