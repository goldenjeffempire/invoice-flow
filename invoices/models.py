from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

# ============================================================================
# AUTH & ACCOUNT MODELS
# ============================================================================

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, blank=True)
    company_logo = models.FileField(upload_to="company_logos/", null=True, blank=True)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)
    default_currency = models.CharField(max_length=3, default="USD")
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    invoice_prefix = models.CharField(max_length=10, default="INV")
    timezone = models.CharField(max_length=63, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    CURRENCY_CHOICES = [
        ("USD", "$ - US Dollar"),
        ("EUR", "€ - Euro"),
        ("GBP", "£ - British Pound"),
        ("NGN", "₦ - Nigerian Naira"),
    ]

    def __str__(self):
        return f"{self.user.username}'s Profile"

class MFAProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_profile")
    secret = models.CharField(max_length=32, blank=True)
    is_enabled = models.BooleanField(default=False)
    recovery_codes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SecurityEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    severity = models.CharField(max_length=20, default="info")
    created_at = models.DateTimeField(auto_now_add=True)

class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_sessions")
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

class EmailToken(models.Model):
    class TokenType(models.TextChoices):
        VERIFY = "verify", "Verification"
        RESET = "reset", "Password Reset"
        INVITE = "invite", "Workspace Invitation"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_tokens")
    token = models.CharField(max_length=64, unique=True)
    token_type = models.CharField(max_length=20, choices=TokenType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def create_token(cls, user, token_type, hours=24):
        expires_at = timezone.now() + timedelta(hours=hours)
        return cls.objects.create(user=user, token=secrets.token_urlsafe(32), token_type=token_type, expires_at=expires_at)

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

# ============================================================================
# APP MODELS
# ============================================================================

class InvoiceTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    business_name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, default="USD")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PAID = "paid", "Paid"
        UNPAID = "unpaid", "Unpaid"

    CURRENCY_CHOICES = [
        ("USD", "USD - US Dollar"),
        ("EUR", "EUR - Euro"),
        ("GBP", "GBP - British Pound"),
        ("NGN", "NGN - Nigerian Naira"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    invoice_id = models.CharField(max_length=32, unique=True)
    client_name = models.CharField(max_length=200)
    business_name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

class InvoiceHistory(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reference = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

class WorkspaceInvitation(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

class RecurringInvoice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=200)
    frequency = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

class Waitlist(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

class ContactSubmission(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=50)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

class ReminderRule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    days_delta = models.IntegerField()
    trigger_type = models.CharField(max_length=20)

class SocialAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)
    uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentSettings(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
