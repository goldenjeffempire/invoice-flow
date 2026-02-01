from __future__ import annotations

import secrets
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class UserProfile(models.Model):
    BUSINESS_TYPE_CHOICES = [
        ("freelancer", "Freelancer / Sole Proprietor"),
        ("agency", "Agency / Studio"),
        ("consulting", "Consulting Firm"),
        ("ecommerce", "E-commerce / Retail"),
        ("saas", "SaaS / Software"),
        ("services", "Professional Services"),
        ("construction", "Construction / Trades"),
        ("healthcare", "Healthcare / Medical"),
        ("other", "Other"),
    ]
    
    REGION_CHOICES = [
        ("ng", "Nigeria"),
        ("us", "United States"),
        ("gb", "United Kingdom"),
        ("eu", "European Union"),
        ("za", "South Africa"),
        ("gh", "Ghana"),
        ("ke", "Kenya"),
        ("other", "Other"),
    ]
    
    INVOICE_STYLE_CHOICES = [
        ("modern", "Modern"),
        ("classic", "Classic"),
        ("minimal", "Minimal"),
        ("professional", "Professional"),
        ("bold", "Bold"),
    ]
    
    CURRENCY_CHOICES = [
        ("NGN", "₦ - Nigerian Naira"),
        ("USD", "$ - US Dollar"),
        ("EUR", "€ - Euro"),
        ("GBP", "£ - British Pound"),
        ("ZAR", "R - South African Rand"),
        ("GHS", "₵ - Ghanaian Cedi"),
        ("KES", "KSh - Kenyan Shilling"),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    
    # Onboarding State (8 steps: Welcome, Business, Branding, Tax, Payments, Import, Templates, Team)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.IntegerField(default=1)
    onboarding_started_at = models.DateTimeField(null=True, blank=True)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    first_invoice_created_at = models.DateTimeField(null=True, blank=True)
    onboarding_data = models.JSONField(default=dict, blank=True)
    
    # Business Details
    company_name = models.CharField(max_length=255, blank=True)
    company_logo = models.FileField(upload_to="company_logos/", null=True, blank=True)
    business_type = models.CharField(max_length=100, blank=True, choices=BUSINESS_TYPE_CHOICES)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)
    business_city = models.CharField(max_length=100, blank=True)
    business_state = models.CharField(max_length=100, blank=True)
    business_country = models.CharField(max_length=100, blank=True)
    business_postal_code = models.CharField(max_length=20, blank=True)
    business_website = models.URLField(blank=True)
    region = models.CharField(max_length=10, blank=True, choices=REGION_CHOICES)
    
    # Branding
    primary_color = models.CharField(max_length=7, default="#6366f1")
    secondary_color = models.CharField(max_length=7, default="#8b5cf6")
    accent_color = models.CharField(max_length=7, default="#10b981")
    invoice_style = models.CharField(max_length=50, default="modern", choices=INVOICE_STYLE_CHOICES)
    
    # Tax & Compliance
    tax_id_number = models.CharField(max_length=50, blank=True)
    tax_id_type = models.CharField(max_length=20, blank=True)
    vat_registered = models.BooleanField(default=False)
    vat_number = models.CharField(max_length=50, blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    wht_applicable = models.BooleanField(default=False)
    wht_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    # Payment Settings
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_name = models.CharField(max_length=255, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_routing_number = models.CharField(max_length=50, blank=True)
    bank_swift_code = models.CharField(max_length=20, blank=True)
    accept_card_payments = models.BooleanField(default=False)
    accept_bank_transfers = models.BooleanField(default=True)
    accept_mobile_money = models.BooleanField(default=False)
    payment_instructions = models.TextField(blank=True)
    
    # Data Import Status
    customers_imported = models.BooleanField(default=False)
    customers_import_count = models.IntegerField(default=0)
    products_imported = models.BooleanField(default=False)
    products_import_count = models.IntegerField(default=0)
    invoices_imported = models.BooleanField(default=False)
    invoices_import_count = models.IntegerField(default=0)
    
    # Preferences
    default_currency = models.CharField(max_length=3, default="NGN", choices=CURRENCY_CHOICES)
    invoice_prefix = models.CharField(max_length=10, default="INV")
    invoice_start_number = models.IntegerField(default=1)
    invoice_numbering_format = models.CharField(max_length=50, default="{prefix}-{year}-{number:04d}")
    date_format = models.CharField(max_length=20, default="DD/MM/YYYY")
    timezone = models.CharField(max_length=63, default="Africa/Lagos")
    locale = models.CharField(max_length=10, default="en-NG")
    
    # Team Settings
    team_invites_sent = models.IntegerField(default=0)
    
    # Workspace Context
    current_workspace = models.ForeignKey('Workspace', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Security/System
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    password_reset_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def increment_failed_attempts(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= getattr(settings, 'ACCOUNT_LOCKOUT_THRESHOLD', 5):
            lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 900)
            self.locked_until = timezone.now() + timedelta(seconds=lockout_duration)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class MFAProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_profile")
    secret = models.CharField(max_length=64, blank=True)
    is_enabled = models.BooleanField(default=False)
    recovery_codes = models.JSONField(default=list)
    recovery_codes_viewed = models.BooleanField(default=False)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_remaining_codes_count(self):
        return len(self.recovery_codes) if self.recovery_codes else 0


class SecurityEvent(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="security_events")
    event_type = models.CharField(max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, db_index=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type', '-created_at']),
        ]

    def get_event_display(self):
        event_displays = {
            'login_success': 'Successful login',
            'login_failed': 'Failed login attempt',
            'login_suspicious': 'Suspicious login detected',
            'logout': 'Logged out',
            'password_changed': 'Password changed',
            'password_reset_requested': 'Password reset requested',
            'password_reset_completed': 'Password reset completed',
            'email_verified': 'Email verified',
            'email_verification_sent': 'Verification email sent',
            'mfa_enabled': '2FA enabled',
            'mfa_disabled': '2FA disabled',
            'mfa_verified': '2FA verified',
            'mfa_failed': '2FA verification failed',
            'session_revoked': 'Session revoked',
            'all_sessions_revoked': 'All sessions revoked',
            'account_locked': 'Account locked',
            'account_unlocked': 'Account unlocked',
            'signup': 'Account created',
            'invitation_accepted': 'Workspace invitation accepted',
        }
        return event_displays.get(self.event_type, self.event_type.replace('_', ' ').title())


class UserSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_sessions")
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    device_type = models.CharField(max_length=20, default='desktop')
    location = models.CharField(max_length=100, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']


class EmailToken(models.Model):
    class TokenType(models.TextChoices):
        VERIFY = "verify", "Email Verification"
        RESET = "reset", "Password Reset"
        INVITE = "invite", "Workspace Invitation"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, choices=TokenType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def create_token(cls, user, token_type, hours=24):
        cls.objects.filter(user=user, token_type=token_type, used_at__isnull=True).update(used_at=timezone.now())
        expires_at = timezone.now() + timedelta(hours=hours)
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            token_type=token_type,
            expires_at=expires_at
        )

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['username', '-created_at']),
        ]


class KnownDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="known_devices")
    fingerprint = models.CharField(max_length=64, db_index=True)
    device_name = models.CharField(max_length=100, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    device_type = models.CharField(max_length=20, default='desktop')
    is_trusted = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'fingerprint']
        ordering = ['-last_used']


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
    email = models.EmailField(db_index=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
    role = models.CharField(max_length=50, default="member")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="accepted_invitations")
    is_revoked = models.BooleanField(default=False)

    @classmethod
    def create_invitation(cls, inviter, email, role="member", expires_days=7):
        cls.objects.filter(email=email.lower(), accepted_at__isnull=True, is_revoked=False).update(is_revoked=True)
        return cls.objects.create(
            inviter=inviter,
            email=email.lower(),
            token=secrets.token_urlsafe(32),
            role=role,
            expires_at=timezone.now() + timedelta(days=expires_days)
        )

    @property
    def is_valid(self):
        return not self.is_revoked and self.accepted_at is None and self.expires_at > timezone.now()

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    @property
    def is_accepted(self):
        return self.accepted_at is not None


class RecurringInvoice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=200)
    frequency = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)


class Waitlist(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = "info", "Information"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        INVOICE = "invoice", "Invoice Activity"
        PAYMENT = "payment", "Payment Received"
        TEAM = "team", "Team Invitation"
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]

class ActivityLog(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=50) # invoice, client, etc.
    resource_id = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

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


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    # Business Details
    company_name = models.CharField(max_length=255, blank=True)
    company_logo = models.FileField(upload_to="company_logos/", null=True, blank=True)
    business_type = models.CharField(max_length=100, blank=True, choices=UserProfile.BUSINESS_TYPE_CHOICES)
    business_email = models.EmailField(blank=True)
    business_phone = models.CharField(max_length=50, blank=True)
    business_address = models.TextField(blank=True)
    business_city = models.CharField(max_length=100, blank=True)
    business_state = models.CharField(max_length=100, blank=True)
    business_country = models.CharField(max_length=100, blank=True, choices=UserProfile.REGION_CHOICES)
    business_postal_code = models.CharField(max_length=20, blank=True)
    
    # Branding
    primary_color = models.CharField(max_length=7, default="#6366f1")
    secondary_color = models.CharField(max_length=7, default="#8b5cf6")
    accent_color = models.CharField(max_length=7, default="#10b981")
    invoice_style = models.CharField(max_length=50, default="modern", choices=UserProfile.INVOICE_STYLE_CHOICES)
    
    # Compliance
    tax_id_number = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WorkspaceMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
    
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    
    # Onboarding Persistence
    onboarding_step = models.IntegerField(default=1)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("workspace", "user")

class ImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="import_jobs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resource_type = models.CharField(max_length=50) # customers, products, invoices
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to="imports/")
    error_report = models.FileField(upload_to="import_errors/", null=True, blank=True)
    stats = models.JSONField(default=dict, blank=True) # {total: 100, success: 90, failed: 10}
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentSettings(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
