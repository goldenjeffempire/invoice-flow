from __future__ import annotations

import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


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

    class Meta:
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["feature", "is_notified"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.get_feature_display()})"


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
        return f"{self.name} - {self.get_subject_display()}"


# ============================================================================
# USER PROFILE
# ============================================================================

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    company_name = models.CharField(max_length=200, blank=True)
    company_logo = models.ImageField(upload_to="company_logos/", null=True, blank=True)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)

    default_currency = models.CharField(max_length=3, default="USD")
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    invoice_prefix = models.CharField(max_length=10, default="INV")
    timezone = models.CharField(max_length=63, default="UTC")

    notify_invoice_created = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_invoice_overdue = models.BooleanField(default=True)
    notify_security_alerts = models.BooleanField(default=True)

    # Paystack
    paystack_subaccount_code = models.CharField(max_length=100, blank=True, null=True)
    paystack_percentage_charge = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    paystack_subaccount_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def has_payment_setup(self) -> bool:
        return bool(self.paystack_subaccount_code and self.paystack_subaccount_active)

    def __str__(self) -> str:
        return f"{self.user.username} Profile"


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
    business_address = models.TextField()

    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_default"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.is_default:
            InvoiceTemplate.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name}"


# ============================================================================
# INVOICE
# ============================================================================

class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    invoice_id = models.CharField(
        max_length=20, unique=True, editable=False
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

    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UNPAID
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.invoice_id:
            self.invoice_id = self._generate_invoice_id()
        super().save(*args, **kwargs)

    def _generate_invoice_id(self) -> str:
        prefix = "INV"
        while True:
            code = f"{prefix}{secrets.token_hex(3).upper()}"
            if not Invoice.objects.filter(invoice_id=code).exists():
                return code

    @property
    def subtotal(self) -> Decimal:
        return sum((i.total for i in self.line_items.all()), Decimal("0"))

    @property
    def tax_amount(self) -> Decimal:
        return (self.subtotal * self.tax_rate) / Decimal("100")

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax_amount

    def __str__(self) -> str:
        return self.invoice_id


# ============================================================================
# LINE ITEMS
# ============================================================================

class LineItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )

    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_price

    def __str__(self) -> str:
        return self.description


# ============================================================================
# PAYMENTS
# ============================================================================

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    @property
    def is_successful(self) -> bool:
        return self.status == self.Status.SUCCESS

    def __str__(self) -> str:
        return f"{self.reference} ({self.status})"


# ============================================================================
# EMAIL VERIFICATION TOKEN (FINAL, SINGLE SOURCE)
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
    token_type = models.CharField(
        max_length=20, choices=TokenType.choices
    )
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
