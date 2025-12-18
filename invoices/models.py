from __future__ import annotations

import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    pass


class Waitlist(models.Model):
    """Email waitlist for upcoming features (Templates, API, etc)."""

    objects: "models.Manager[Waitlist]"

    FEATURE_CHOICES = [
        ("templates", "Invoice Templates"),
        ("api", "API Access"),
        ("general", "General Updates"),
    ]

    email = models.EmailField(unique=True)
    feature = models.CharField(max_length=20, choices=FEATURE_CHOICES, default="general")
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-subscribed_at"]
        verbose_name_plural = "Waitlist entries"
        indexes = [
            models.Index(fields=["feature", "is_notified"], name="idx_waitlist_feature"),
        ]

    def __str__(self) -> str:
        return f"{self.email} - {self.get_feature_display()}"


class ContactSubmission(models.Model):
    """Store contact form submissions for follow-up and audit."""

    objects: "models.Manager[ContactSubmission]"

    SUBJECT_CHOICES = [
        ("sales", "Sales Inquiry"),
        ("support", "Technical Support"),
        ("billing", "Billing Question"),
        ("feature", "Feature Request"),
        ("bug", "Bug Report"),
        ("general", "General Inquiry"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="general")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name_plural = "Contact submissions"
        indexes = [
            models.Index(fields=["status", "-submitted_at"], name="idx_contact_status"),
            models.Index(fields=["email"], name="idx_contact_email"),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.get_subject_display()} ({self.status})"


class UserProfile(models.Model):
    """Extended user profile with business preferences and settings."""

    objects: "models.Manager[UserProfile]"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    company_name = models.CharField(max_length=200, blank=True)
    company_logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)
    default_currency = models.CharField(
        max_length=3,
        choices=[
            ("USD", "US Dollar"),
            ("EUR", "Euro"),
            ("GBP", "British Pound"),
            ("NGN", "Nigerian Naira"),
            ("CAD", "Canadian Dollar"),
            ("AUD", "Australian Dollar"),
        ],
        default="USD",
    )
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_prefix = models.CharField(max_length=10, default="INV")
    timezone = models.CharField(max_length=63, default="UTC")

    notify_invoice_created = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_invoice_viewed = models.BooleanField(default=True)
    notify_invoice_overdue = models.BooleanField(default=True)
    notify_weekly_summary = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    notify_password_changes = models.BooleanField(default=True)

    paystack_subaccount_code = models.CharField(max_length=100, blank=True, null=True, help_text="Paystack subaccount code for receiving direct payments")
    paystack_bank_code = models.CharField(max_length=20, blank=True, null=True, help_text="Bank code for the settlement account")
    paystack_account_number = models.CharField(max_length=20, blank=True, null=True, help_text="Account number for receiving payments")
    paystack_account_name = models.CharField(max_length=200, blank=True, null=True, help_text="Account holder name (verified)")
    paystack_settlement_bank = models.CharField(max_length=200, blank=True, null=True, help_text="Bank name for display")
    paystack_percentage_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Platform fee percentage (0-100)")
    paystack_subaccount_active = models.BooleanField(default=False, help_text="Whether direct payments are enabled")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def has_payment_setup(self) -> bool:
        """Check if user has configured direct payment receiving."""
        return bool(self.paystack_subaccount_code and self.paystack_subaccount_active)

    def __str__(self) -> str:
        return f"{self.user.username}'s Profile"


class InvoiceTemplate(models.Model):
    """Reusable invoice templates for quick invoice creation."""

    objects: "models.Manager[InvoiceTemplate]"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoice_templates"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField()
    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_default"], name="idx_template_user_default"),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.user.username}"


class RecurringInvoice(models.Model):
    """Recurring invoice configuration for automated invoicing."""

    objects: "models.Manager[RecurringInvoice]"

    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("ended", "Ended"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_invoices"
    )
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField()

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="monthly")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()
    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    last_generated = models.DateTimeField(null=True, blank=True)
    next_generation = models.DateField()

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_recurring_user_status"),
            models.Index(fields=["status", "next_generation"], name="idx_recurring_schedule"),
        ]

    def __str__(self) -> str:
        return f"Recurring - {self.client_name} ({self.frequency})"

    def generate_next_invoice_date(self) -> date:
        """Calculate next invoice generation date based on frequency."""
        from dateutil.relativedelta import relativedelta

        current_date: date = self.next_generation
        if self.frequency == "weekly":
            return current_date + timedelta(weeks=1)
        elif self.frequency == "biweekly":
            return current_date + timedelta(weeks=2)
        elif self.frequency == "monthly":
            return current_date + relativedelta(months=1)
        elif self.frequency == "quarterly":
            return current_date + relativedelta(months=3)
        elif self.frequency == "yearly":
            return current_date + relativedelta(years=1)
        return current_date


class Invoice(models.Model):
    """Invoice model for storing invoice data and metadata."""

    objects: "models.Manager[Invoice]"

    CURRENCY_CHOICES = [
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
        ("NGN", "Nigerian Naira"),
        ("CAD", "Canadian Dollar"),
        ("AUD", "Australian Dollar"),
    ]

    STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices"
    )
    invoice_id = models.CharField(max_length=20, unique=True, editable=False)
    recurring_invoice = models.ForeignKey(
        RecurringInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_invoices",
    )
    template = models.ForeignKey(
        InvoiceTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    business_name = models.CharField(max_length=200)
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField()

    client_name = models.CharField(max_length=200)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=50, blank=True)
    client_address = models.TextField()

    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    brand_name = models.CharField(max_length=100, blank=True)
    brand_color = models.CharField(max_length=7, default="#6366f1")
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)

    bank_name = models.CharField(max_length=200, blank=True)
    account_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unpaid")
    payment_reference = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to auto-generate invoice_id if not set."""
        if not self.invoice_id:
            self.invoice_id = self.generate_invoice_id()
        super().save(*args, **kwargs)

    def generate_invoice_id(self) -> str:
        """Generate a unique invoice ID with prefix and random hex suffix."""
        prefix = "INV"
        random_part = secrets.token_hex(3).upper()
        invoice_id = f"{prefix}{random_part}"

        while Invoice.objects.filter(invoice_id=invoice_id).exists():
            random_part = secrets.token_hex(3).upper()
            invoice_id = f"{prefix}{random_part}"

        return invoice_id

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal from all line items."""
        return sum((item.total for item in self.line_items.all()), Decimal("0"))

    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax amount based on subtotal and tax rate."""
        tax_rate_decimal = Decimal(str(self.tax_rate))
        return (self.subtotal * tax_rate_decimal) / Decimal("100")

    @property
    def total(self) -> Decimal:
        """Calculate total amount including tax."""
        return self.subtotal + self.tax_amount

    def __str__(self) -> str:
        return f"{self.invoice_id} - {self.client_name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_user_status"),
            models.Index(fields=["user", "-created_at"], name="idx_user_created"),
            models.Index(fields=["user", "invoice_date"], name="idx_user_date"),
            models.Index(fields=["invoice_id"], name="idx_invoice_id"),
            models.Index(fields=["user", "client_email"], name="idx_user_client"),
        ]


class LineItem(models.Model):
    """Line item model for invoice line items."""

    objects: "models.Manager[LineItem]"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self) -> Decimal:
        """Calculate total for this line item."""
        return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))

    def __str__(self) -> str:
        return f"{self.description} - {self.invoice.invoice_id}"


class MFAProfile(models.Model):
    """Multi-Factor Authentication profile for enhanced security."""

    objects: "models.Manager[MFAProfile]"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_profile"
    )
    is_enabled = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=64, blank=True)
    recovery_codes = models.JSONField(default=list, blank=True)
    backup_phone = models.CharField(max_length=20, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MFA Profile"
        verbose_name_plural = "MFA Profiles"

    def __str__(self) -> str:
        status = "enabled" if self.is_enabled else "disabled"
        return f"{self.user.username}'s MFA ({status})"

    @property
    def recovery_codes_remaining(self) -> int:
        """Return count of remaining recovery codes."""
        return len(self.recovery_codes) if self.recovery_codes else 0


class LoginAttempt(models.Model):
    """Track login attempts for security and rate limiting."""

    objects: "models.Manager[LoginAttempt]"

    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username", "created_at"], name="idx_login_user_time"),
            models.Index(fields=["ip_address", "created_at"], name="idx_login_ip_time"),
        ]

    def __str__(self) -> str:
        status = "success" if self.success else "failed"
        return f"{self.username} - {self.ip_address} ({status})"


class EmailVerificationToken(models.Model):
    """Secure email verification tokens for account activation and email changes."""

    objects: "models.Manager[EmailVerificationToken]"

    TOKEN_TYPE_CHOICES = [
        ("signup", "Account Verification"),
        ("email_change", "Email Change Verification"),
        ("password_reset", "Password Reset"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_tokens"
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES, default="signup")
    email = models.EmailField(help_text="Email address this token was sent to")
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"], name="idx_email_token"),
            models.Index(fields=["user", "token_type"], name="idx_user_token_type"),
            models.Index(fields=["expires_at"], name="idx_token_expires"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.get_token_type_display()} ({self.email})"

    @classmethod
    def generate_token(cls) -> str:
        """Generate a cryptographically secure token."""
        return secrets.token_urlsafe(48)

    @classmethod
    def create_verification_token(
        cls,
        user: Any,
        email: str,
        token_type: str = "signup",
        expires_hours: int = 24,
    ) -> "EmailVerificationToken":
        """Create a new verification token for a user."""
        cls.objects.filter(user=user, token_type=token_type, is_used=False).update(is_used=True)

        token = cls.generate_token()
        expires_at = timezone.now() + timedelta(hours=expires_hours)

        return cls.objects.create(
            user=user,
            token=token,
            token_type=token_type,
            email=email,
            expires_at=expires_at,
        )

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not used and not expired)."""
        return not self.is_used and self.expires_at > timezone.now()

    def mark_used(self) -> None:
        """Mark the token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])


class UserSession(models.Model):
    """Track user sessions for device management and security monitoring."""

    objects: "models.Manager[UserSession]"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_sessions"
    )
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_current = models.BooleanField(default=False)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_activity"]
        indexes = [
            models.Index(fields=["user", "-last_activity"], name="idx_user_session_activity"),
            models.Index(fields=["session_key"], name="idx_session_key"),
        ]

    def __str__(self) -> str:
        device = self.device_type or "Unknown device"
        return f"{self.user.username} - {device} ({self.ip_address})"

    @classmethod
    def create_session(
        cls,
        user: Any,
        session_key: str,
        ip_address: str,
        user_agent: str = "",
    ) -> "UserSession":
        """Create a new user session with parsed device info."""
        device_info = cls.parse_user_agent(user_agent)

        return cls.objects.create(
            user=user,
            session_key=session_key,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_info.get("device_type", ""),
            browser=device_info.get("browser", ""),
            os=device_info.get("os", ""),
        )

    @staticmethod
    def parse_user_agent(user_agent: str) -> dict[str, str]:
        """Parse user agent string to extract device info."""
        result: dict[str, str] = {
            "device_type": "Desktop",
            "browser": "Unknown",
            "os": "Unknown",
        }

        ua_lower = user_agent.lower()

        if "mobile" in ua_lower or "android" in ua_lower:
            result["device_type"] = "Mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            result["device_type"] = "Tablet"

        if "chrome" in ua_lower and "edg" not in ua_lower:
            result["browser"] = "Chrome"
        elif "firefox" in ua_lower:
            result["browser"] = "Firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            result["browser"] = "Safari"
        elif "edg" in ua_lower:
            result["browser"] = "Edge"

        if "windows" in ua_lower:
            result["os"] = "Windows"
        elif "mac os" in ua_lower or "macos" in ua_lower:
            result["os"] = "macOS"
        elif "linux" in ua_lower:
            result["os"] = "Linux"
        elif "android" in ua_lower:
            result["os"] = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            result["os"] = "iOS"

        return result

    def revoke(self) -> None:
        """Revoke this session by deleting the Django session."""
        from django.contrib.sessions.models import Session

        try:
            Session.objects.filter(session_key=self.session_key).delete()
        except Exception:
            pass
        self.delete()


class SocialAccount(models.Model):
    """Link social OAuth accounts (Google, GitHub) to user accounts."""

    objects: "models.Manager[SocialAccount]"

    PROVIDER_CHOICES = [
        ("google", "Google"),
        ("github", "GitHub"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_accounts"
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=255, db_index=True)
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires = models.DateTimeField(null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "provider_id")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "provider_id"], name="idx_social_provider"),
            models.Index(fields=["user", "provider"], name="idx_social_user_provider"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.get_provider_display()} ({self.email})"


class Payment(models.Model):
    """Track individual payment transactions for invoices with full lifecycle support."""

    objects: "models.Manager[Payment]"

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    ]

    CHANNEL_CHOICES = [
        ("card", "Card Payment"),
        ("bank_transfer", "Bank Transfer"),
        ("ussd", "USSD"),
        ("qr", "QR Code"),
        ("mobile_money", "Mobile Money"),
        ("direct_debit", "Direct Debit"),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    external_reference = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, blank=True, null=True)
    gateway = models.CharField(max_length=50, default="paystack")
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=200, blank=True)
    authorization_code = models.CharField(max_length=100, blank=True, null=True)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_exp_month = models.CharField(max_length=2, blank=True, null=True)
    card_exp_year = models.CharField(max_length=4, blank=True, null=True)
    card_bank = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    account_name = models.CharField(max_length=200, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subaccount_code = models.CharField(max_length=100, blank=True, null=True)
    split_code = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    gateway_response = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_payment_user_created"),
            models.Index(fields=["invoice", "status"], name="idx_payment_invoice_status"),
            models.Index(fields=["reference"], name="idx_payment_reference"),
            models.Index(fields=["status", "-created_at"], name="idx_payment_status_date"),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.amount} {self.currency} ({self.status})"

    @property
    def is_successful(self) -> bool:
        return self.status == "success"


class PaymentRecipient(models.Model):
    """Store recipient/bank account details for receiving payments and payouts."""

    objects: "models.Manager[PaymentRecipient]"

    ACCOUNT_TYPE_CHOICES = [
        ("bank", "Bank Account"),
        ("mobile_money", "Mobile Money"),
        ("nuban", "NUBAN"),
        ("ghipss", "GHIPSS"),
        ("basa", "BASA"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_recipients"
    )
    name = models.CharField(max_length=200, help_text="Friendly name for this account")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default="bank")
    bank_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=30)
    account_name = models.CharField(max_length=200, help_text="Verified account holder name")
    currency = models.CharField(max_length=3, default="NGN")
    recipient_code = models.CharField(max_length=100, blank=True, null=True, help_text="Payment gateway recipient code")
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"], name="idx_recipient_user_active"),
            models.Index(fields=["user", "is_primary"], name="idx_recipient_user_primary"),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.bank_name} ({self.account_number[-4:]})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_primary:
            PaymentRecipient.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class PaymentPayout(models.Model):
    """Track payout/transfer requests to recipients."""

    objects: "models.Manager[PaymentPayout]"

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("reversed", "Reversed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts"
    )
    recipient = models.ForeignKey(
        PaymentRecipient, on_delete=models.SET_NULL, null=True, related_name="payouts"
    )
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    transfer_code = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reason = models.CharField(max_length=200, blank=True, help_text="Reason for transfer")
    gateway_response = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_payout_user_created"),
            models.Index(fields=["status", "-created_at"], name="idx_payout_status_date"),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.amount} {self.currency} ({self.status})"


class PaymentCard(models.Model):
    """Store tokenized card information for saved payment methods."""

    objects: "models.Manager[PaymentCard]"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_cards"
    )
    authorization_code = models.CharField(max_length=100)
    card_type = models.CharField(max_length=50)
    last4 = models.CharField(max_length=4)
    exp_month = models.CharField(max_length=2)
    exp_year = models.CharField(max_length=4)
    bank = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=50, blank=True)
    country_code = models.CharField(max_length=3, blank=True)
    reusable = models.BooleanField(default=True)
    signature = models.CharField(max_length=100, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    nickname = models.CharField(max_length=50, blank=True, help_text="Friendly name for this card")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"], name="idx_card_user_active"),
        ]

    def __str__(self) -> str:
        name = self.nickname or f"{self.card_type} *{self.last4}"
        return f"{name} ({self.exp_month}/{self.exp_year})"

    @property
    def display_name(self) -> str:
        if self.nickname:
            return f"{self.nickname} (*{self.last4})"
        return f"{self.card_type} *{self.last4}"

    @property
    def is_expired(self) -> bool:
        from datetime import datetime
        current_year = datetime.now().year
        current_month = datetime.now().month
        try:
            exp_year = int(self.exp_year)
            exp_month = int(self.exp_month)
            if exp_year < current_year:
                return True
            if exp_year == current_year and exp_month < current_month:
                return True
            return False
        except (ValueError, TypeError):
            return True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_primary:
            PaymentCard.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class PaymentSettings(models.Model):
    """User payment settings and preferences for receiving payments."""

    objects: "models.Manager[PaymentSettings]"

    PAYOUT_SCHEDULE_CHOICES = [
        ("auto", "Automatic (Next Business Day)"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("manual", "Manual Withdrawal"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_settings"
    )
    enable_card_payments = models.BooleanField(default=True)
    enable_bank_transfers = models.BooleanField(default=True)
    enable_mobile_money = models.BooleanField(default=False)
    enable_ussd = models.BooleanField(default=False)
    preferred_currency = models.CharField(max_length=3, default="NGN")
    auto_payout = models.BooleanField(default=False, help_text="Automatically transfer funds to default recipient")
    payout_schedule = models.CharField(max_length=20, choices=PAYOUT_SCHEDULE_CHOICES, default="auto")
    payout_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum amount before auto-payout")
    send_payment_receipt = models.BooleanField(default=True)
    send_payout_notification = models.BooleanField(default=True)
    payment_instructions = models.TextField(blank=True, help_text="Custom payment instructions for clients")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Settings"
        verbose_name_plural = "Payment Settings"

    def __str__(self) -> str:
        return f"Payment Settings for {self.user.username}"


class GDPRRequest(models.Model):
    """Persistent GDPR compliance request tracking for audit and fulfillment."""

    objects: "models.Manager[GDPRRequest]"

    REQUEST_TYPE_CHOICES = [
        ("data_export", "Data Export (Article 20)"),
        ("data_deletion", "Data Deletion (Article 17)"),
        ("subject_access", "Subject Access Request (Article 15)"),
        ("rectification", "Rectification (Article 16)"),
        ("restriction", "Restriction (Article 18)"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="gdpr_requests",
    )
    user_email = models.EmailField(help_text="Preserved in case user is deleted")
    user_username = models.CharField(max_length=150, help_text="Preserved in case user is deleted")
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    details = models.TextField(blank=True, help_text="Additional request details from user")
    admin_notes = models.TextField(blank=True, help_text="Internal notes for processing")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)
    email_error = models.TextField(blank=True, help_text="Error message if email delivery failed")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gdpr_requests_processed",
    )

    class Meta:
        ordering = ["-requested_at"]
        verbose_name = "GDPR Request"
        verbose_name_plural = "GDPR Requests"
        indexes = [
            models.Index(fields=["status", "-requested_at"], name="idx_gdpr_status"),
            models.Index(fields=["request_type", "-requested_at"], name="idx_gdpr_type"),
            models.Index(fields=["user_email"], name="idx_gdpr_email"),
        ]

    def __str__(self) -> str:
        return f"{self.user_email} - {self.get_request_type_display()} ({self.status})"


class ProcessedWebhook(models.Model):
    """Track processed webhooks to prevent replay attacks."""

    objects: "models.Manager[ProcessedWebhook]"

    event_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique event identifier from payment provider")
    provider = models.CharField(max_length=50, default="paystack", help_text="Payment provider (paystack, stripe, etc)")
    event_type = models.CharField(max_length=100, help_text="Event type (charge.success, etc)")
    reference = models.CharField(max_length=100, blank=True, db_index=True, help_text="Transaction reference")
    payload_hash = models.CharField(max_length=64, help_text="SHA256 hash of payload for integrity verification")
    processed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-processed_at"]
        verbose_name = "Processed Webhook"
        verbose_name_plural = "Processed Webhooks"
        indexes = [
            models.Index(fields=["provider", "event_id"], name="idx_webhook_provider_event"),
            models.Index(fields=["-processed_at"], name="idx_webhook_processed"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type} - {self.event_id}"

    @classmethod
    def is_duplicate(cls, event_id: str, provider: str = "paystack") -> bool:
        """Check if this webhook has already been processed."""
        return cls.objects.filter(event_id=event_id, provider=provider).exists()

    @classmethod
    def record_webhook(
        cls,
        event_id: str,
        event_type: str,
        reference: str,
        payload_hash: str,
        provider: str = "paystack",
        ip_address: str | None = None,
    ) -> "ProcessedWebhook":
        """Record a processed webhook to prevent replay."""
        return cls.objects.create(
            event_id=event_id,
            provider=provider,
            event_type=event_type,
            reference=reference,
            payload_hash=payload_hash,
            ip_address=ip_address,
        )

    @classmethod
    def cleanup_old_webhooks(cls, days: int = 30) -> int:
        """Remove webhook records older than specified days."""
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = cls.objects.filter(processed_at__lt=cutoff).delete()
        return deleted
