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

    # Payment Gateway Integration
    paystack_enabled = models.BooleanField(default=False)
    paystack_subaccount_code = models.CharField(max_length=100, blank=True)
    paystack_subaccount_active = models.BooleanField(default=False)
    stripe_enabled = models.BooleanField(default=False)
    stripe_account_id = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    tax_name = models.CharField(max_length=100, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)

    # Notification Preferences
    notify_invoice_created = models.BooleanField(default=True)
    notify_payment_received = models.BooleanField(default=True)
    notify_invoice_viewed = models.BooleanField(default=True)
    notify_invoice_overdue = models.BooleanField(default=True)
    notify_weekly_summary = models.BooleanField(default=True)
    notify_security_alerts = models.BooleanField(default=True)
    notify_password_changes = models.BooleanField(default=True)
    
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


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        PART_PAID = "part_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        WRITE_OFF = "write_off", "Write-off"

    class SourceType(models.TextChoices):
        MANUAL = "manual", "Manual"
        ESTIMATE = "estimate", "From Estimate"
        RECURRING = "recurring", "From Recurring"
        DUPLICATE = "duplicate", "Duplicated"
        API = "api", "API Created"

    class TaxMode(models.TextChoices):
        EXCLUSIVE = "exclusive", "Tax Exclusive (added on top)"
        INCLUSIVE = "inclusive", "Tax Inclusive (included in price)"

    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FLAT = "flat", "Fixed Amount"

    CURRENCY_CHOICES = [
        ("NGN", "₦ - Nigerian Naira"),
        ("USD", "$ - US Dollar"),
        ("EUR", "€ - Euro"),
        ("GBP", "£ - British Pound"),
        ("ZAR", "R - South African Rand"),
        ("GHS", "₵ - Ghanaian Cedi"),
        ("KES", "KSh - Kenyan Shilling"),
        ("CAD", "$ - Canadian Dollar"),
        ("AUD", "$ - Australian Dollar"),
        ("INR", "₹ - Indian Rupee"),
    ]

    CURRENCY_SYMBOLS = {
        "NGN": "₦", "USD": "$", "EUR": "€", "GBP": "£",
        "ZAR": "R", "GHS": "₵", "KES": "KSh", "CAD": "$",
        "AUD": "$", "INR": "₹",
    }

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="invoices")
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name="invoices")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_invoices")
    invoice_number = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.MANUAL)
    source_id = models.IntegerField(null=True, blank=True)
    parent_invoice = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_invoices')

    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    sent_at = models.DateTimeField(null=True, blank=True)
    first_viewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="NGN")
    base_currency = models.CharField(max_length=3, default="NGN")
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=Decimal('1.000000'))
    exchange_rate_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    tax_mode = models.CharField(max_length=20, choices=TaxMode.choices, default=TaxMode.EXCLUSIVE)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.FLAT)
    global_discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    global_discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    client_memo = models.TextField(blank=True, help_text="Visible to client on invoice")
    internal_notes = models.TextField(blank=True, help_text="Private notes, not visible to client")
    terms_conditions = models.TextField(blank=True)
    footer_note = models.TextField(blank=True)
    payment_instructions = models.TextField(blank=True)

    public_token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe, db_index=True)
    view_count = models.IntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    last_viewed_ip = models.GenericIPAddressField(null=True, blank=True)

    is_recurring = models.BooleanField(default=False)
    recurring_schedule = models.JSONField(default=dict, blank=True)

    reminder_enabled = models.BooleanField(default=True)
    reminder_days_before = models.IntegerField(default=3)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.IntegerField(default=0)

    delivery_email_sent = models.BooleanField(default=False)
    delivery_email_opened = models.BooleanField(default=False)
    delivery_whatsapp_sent = models.BooleanField(default=False)

    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workspace', 'invoice_number')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['workspace', 'due_date']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['public_token']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, self.currency)

    @property
    def is_overdue(self):
        if self.status in [self.Status.PAID, self.Status.VOID, self.Status.WRITE_OFF]:
            return False
        return self.due_date < timezone.now().date() and self.amount_due > 0

    @property
    def days_until_due(self):
        return (self.due_date - timezone.now().date()).days

    @property
    def days_overdue(self):
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days

    @property
    def payment_progress(self):
        if self.total_amount == 0:
            return 0
        return int((self.amount_paid / self.total_amount) * 100)

    @property
    def can_edit(self):
        return self.status == self.Status.DRAFT

    @property
    def can_send(self):
        return self.status in [self.Status.DRAFT, self.Status.SENT, self.Status.VIEWED]

    @property
    def can_void(self):
        return self.status not in [self.Status.VOID, self.Status.WRITE_OFF, self.Status.PAID]

    @property
    def can_record_payment(self):
        return self.status not in [self.Status.VOID, self.Status.WRITE_OFF, self.Status.PAID] and self.amount_due > 0

    def get_public_url(self):
        from django.urls import reverse
        return reverse('invoices:public_invoice', kwargs={'token': self.public_token})

    def regenerate_token(self):
        self.public_token = secrets.token_urlsafe(32)
        self.save(update_fields=['public_token'])


class ClientPortalToken(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name="portal_tokens")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class ClientPortalSession(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name="portal_sessions")
    session_key = models.CharField(max_length=128, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    device_info = models.JSONField(default=dict, blank=True)

    @property
    def is_valid(self):
        return self.is_active and self.expires_at > timezone.now()


class Estimate(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        INVOICED = "invoiced", "Invoiced"
        VOID = "void", "Void"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="estimates")
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name="estimates")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_estimates")
    estimate_number = models.CharField(max_length=50, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    
    issue_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    
    currency = models.CharField(max_length=3, choices=Invoice.CURRENCY_CHOICES, default="NGN")
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    client_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    public_token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe, db_index=True)
    version = models.IntegerField(default=1)
    parent_estimate = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='revisions')
    
    converted_invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_estimate')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workspace', 'estimate_number')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.estimate_number} - {self.client.name}"

    def get_public_url(self):
        from django.urls import reverse
        return reverse('invoices:public_estimate', kwargs={'token': self.public_token})


class EstimateItem(models.Model):
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1.0000'))
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    sort_order = models.IntegerField(default=0)


class EstimateActivity(models.Model):
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
        DISPUTED = "disputed", "Disputed"
        VOID = "void", "Void"

    class Method(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        PAYSTACK = "paystack", "Paystack"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"
        OTHER = "other", "Other"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Invoice.CURRENCY_CHOICES, default="USD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_method = models.CharField(max_length=20, choices=Method.choices, default="other")
    
    transaction_id = models.CharField(max_length=255, blank=True, db_index=True)
    provider_reference = models.CharField(max_length=255, blank=True)
    
    fee_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    payment_date = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment {self.id} for Invoice {self.invoice.invoice_number}"


class Transaction(models.Model):
    class Type(models.TextChoices):
        PAYMENT = "payment", "Payment"
        REFUND = "refund", "Refund"
        CHARGEBACK = "chargeback", "Chargeback"
        PAYOUT = "payout", "Payout"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="transactions")
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=Type.choices, default="payment")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Invoice.CURRENCY_CHOICES, default="USD")
    
    status = models.CharField(max_length=20, default="succeeded")
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class PaymentAuditLog(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def calculate_totals(self, tax_mode='exclusive'):
        line_subtotal = self.quantity * self.unit_price

        if self.discount_type == 'percentage':
            self.discount_amount = (line_subtotal * self.discount_value) / Decimal('100')
        else:
            self.discount_amount = self.discount_value

        after_discount = line_subtotal - self.discount_amount

        if tax_mode == 'inclusive':
            base_amount = after_discount / (1 + self.tax_rate / Decimal('100'))
            self.tax_amount = after_discount - base_amount
            self.subtotal = base_amount
            self.total = after_discount
        else:
            self.tax_amount = (after_discount * self.tax_rate) / Decimal('100')
            self.subtotal = after_discount
            self.total = after_discount + self.tax_amount


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=50, default="service")
    product_id_ref = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=500)
    long_description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default="unit")
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1.0000'))
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_type = models.CharField(max_length=20, default="flat")
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']


class InvoiceAttachment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="invoice_attachments/")
    created_at = models.DateTimeField(auto_now_add=True)


# Legacy Payment Model (Deprecated)
class InvoicePayment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="invoice_payments")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)


class InvoiceActivity(models.Model):
    class ActionType(models.TextChoices):
        CREATED = "created", "Invoice Created"
        UPDATED = "updated", "Invoice Updated"
        SENT = "sent", "Invoice Sent"
        VIEWED = "viewed", "Invoice Viewed"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        STATUS_CHANGED = "status_changed", "Status Changed"
        REMINDER_SENT = "reminder_sent", "Reminder Sent"
        VOIDED = "voided", "Invoice Voided"
        WRITTEN_OFF = "written_off", "Invoice Written Off"
        DUPLICATED = "duplicated", "Invoice Duplicated"
        ATTACHMENT_ADDED = "attachment_added", "Attachment Added"
        ATTACHMENT_REMOVED = "attachment_removed", "Attachment Removed"
        COMMENT_ADDED = "comment_added", "Comment Added"
        DOWNLOADED = "downloaded", "PDF Downloaded"
        SHARED = "shared", "Link Shared"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ActionType.choices)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Invoice activities"


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

class Client(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Billing Address
    billing_address = models.TextField(blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    billing_zip = models.CharField(max_length=20, blank=True)
    
    # Shipping Address
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)
    shipping_zip = models.CharField(max_length=20, blank=True)
    
    # Settings
    currency = models.CharField(max_length=3, default="USD")
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True) # comma separated
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ClientNote(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="client_notes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class CommunicationLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="comms_logs")
    subject = models.CharField(max_length=255)
    medium = models.CharField(max_length=50) # email, sms, manual
    sent_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField(blank=True)


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

class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    arrival_date = models.DateField(null=True, blank=True)
    provider_payout_id = models.CharField(max_length=255, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Dispute(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="disputes")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="disputes")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    reason = models.CharField(max_length=255)
    provider_dispute_id = models.CharField(max_length=255, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PaymentSettings(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class RecurringSchedule(models.Model):
    class IntervalType(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Every 2 Weeks"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"
        CUSTOM = "custom", "Custom Interval"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed (Retry Exhausted)"

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name="recurring_schedules")
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name="recurring_schedules")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_schedules")

    description = models.CharField(max_length=255, help_text="Brief description of recurring charge")
    interval_type = models.CharField(max_length=20, choices=IntervalType.choices, default=IntervalType.MONTHLY)
    custom_interval_days = models.PositiveIntegerField(null=True, blank=True, help_text="Days between invoices for custom interval")
    
    start_date = models.DateField(help_text="When to start generating invoices")
    end_date = models.DateField(null=True, blank=True, help_text="Optional end date for the schedule")
    next_run_date = models.DateField(db_index=True, help_text="Next scheduled invoice generation date")
    last_run_date = models.DateField(null=True, blank=True)
    
    timezone = models.CharField(max_length=50, default="UTC", help_text="Timezone for schedule execution")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    proration_enabled = models.BooleanField(default=False, help_text="Prorate partial periods")
    anchor_day = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Day of month to anchor billing (1-31)")

    currency = models.CharField(max_length=3, default="USD")
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Base invoice amount before tax")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    line_items_template = models.JSONField(default=list, blank=True, help_text="Template line items for generated invoices")
    invoice_terms = models.TextField(blank=True, help_text="Terms to include on generated invoices")
    invoice_notes = models.TextField(blank=True, help_text="Notes to include on generated invoices")
    payment_terms_days = models.PositiveIntegerField(default=30, help_text="Days until due date from issue")
    
    auto_send = models.BooleanField(default=True, help_text="Automatically send invoice to client")
    
    retry_enabled = models.BooleanField(default=True)
    max_retry_attempts = models.PositiveSmallIntegerField(default=3, help_text="Max payment retry attempts")
    retry_interval_hours = models.PositiveIntegerField(default=24, help_text="Hours between retry attempts")
    retry_backoff_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('2.0'), help_text="Backoff multiplier for retries")
    current_retry_count = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    failure_notification_sent = models.BooleanField(default=False)
    
    idempotency_key = models.CharField(max_length=64, unique=True, db_index=True)
    total_invoices_generated = models.PositiveIntegerField(default=0)
    total_amount_billed = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_run_date']),
            models.Index(fields=['workspace', 'status']),
        ]

    def __str__(self):
        return f"Schedule #{self.id} - {self.client.name} ({self.interval_type})"

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            self.idempotency_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def calculate_next_run_date(self, from_date=None):
        from dateutil.relativedelta import relativedelta
        base = from_date or self.next_run_date or self.start_date
        if self.interval_type == self.IntervalType.WEEKLY:
            return base + timedelta(days=7)
        elif self.interval_type == self.IntervalType.BIWEEKLY:
            return base + timedelta(days=14)
        elif self.interval_type == self.IntervalType.MONTHLY:
            next_date = base + relativedelta(months=1)
            if self.anchor_day:
                try:
                    next_date = next_date.replace(day=min(self.anchor_day, 28))
                except ValueError:
                    pass
            return next_date
        elif self.interval_type == self.IntervalType.QUARTERLY:
            return base + relativedelta(months=3)
        elif self.interval_type == self.IntervalType.YEARLY:
            return base + relativedelta(years=1)
        elif self.interval_type == self.IntervalType.CUSTOM and self.custom_interval_days:
            return base + timedelta(days=self.custom_interval_days)
        return base + timedelta(days=30)

    def get_retry_delay_hours(self):
        base_delay = self.retry_interval_hours
        return int(base_delay * (float(self.retry_backoff_multiplier) ** self.current_retry_count))

    @property
    def can_retry(self):
        return self.retry_enabled and self.current_retry_count < self.max_retry_attempts

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def days_until_next_run(self):
        if self.next_run_date:
            delta = self.next_run_date - timezone.now().date()
            return delta.days
        return None


class ScheduleExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    schedule = models.ForeignKey(RecurringSchedule, on_delete=models.CASCADE, related_name="executions")
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name="schedule_executions")
    
    period_start = models.DateField(help_text="Start of billing period")
    period_end = models.DateField(help_text="End of billing period")
    
    scheduled_date = models.DateField(help_text="When this execution was scheduled to run")
    executed_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    amount_generated = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prorated_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Prorated amount if applicable")
    
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    
    idempotency_key = models.CharField(max_length=64, unique=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['schedule', 'status']),
            models.Index(fields=['scheduled_date']),
        ]

    def __str__(self):
        return f"Execution #{self.id} for Schedule #{self.schedule_id}"

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            self.idempotency_key = f"{self.schedule_id}-{self.scheduled_date.isoformat()}-{secrets.token_urlsafe(8)}"
        super().save(*args, **kwargs)


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    execution = models.ForeignKey(ScheduleExecution, on_delete=models.CASCADE, related_name="payment_attempts")
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, related_name="recurring_payment_attempts")
    
    attempt_number = models.PositiveSmallIntegerField(default=1)
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    
    payment_method = models.CharField(max_length=50, blank=True)
    provider = models.CharField(max_length=50, blank=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['execution', 'status']),
        ]

    def __str__(self):
        return f"Attempt #{self.attempt_number} for Execution #{self.execution_id}"


class RecurringScheduleAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Schedule Created"
        UPDATED = "updated", "Schedule Updated"
        PAUSED = "paused", "Schedule Paused"
        RESUMED = "resumed", "Schedule Resumed"
        CANCELLED = "cancelled", "Schedule Cancelled"
        INVOICE_GENERATED = "invoice_generated", "Invoice Generated"
        PAYMENT_ATTEMPTED = "payment_attempted", "Payment Attempted"
        PAYMENT_SUCCESS = "payment_success", "Payment Successful"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        RETRY_SCHEDULED = "retry_scheduled", "Retry Scheduled"
        RETRY_EXHAUSTED = "retry_exhausted", "Retry Attempts Exhausted"
        NOTIFICATION_SENT = "notification_sent", "Notification Sent"

    schedule = models.ForeignKey(RecurringSchedule, on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    action = models.CharField(max_length=50, choices=Action.choices)
    description = models.TextField(blank=True)
    
    related_invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    related_execution = models.ForeignKey(ScheduleExecution, on_delete=models.SET_NULL, null=True, blank=True)
    related_attempt = models.ForeignKey(PaymentAttempt, on_delete=models.SET_NULL, null=True, blank=True)
    
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['schedule', 'action']),
        ]

    def __str__(self):
        return f"{self.action} on Schedule #{self.schedule_id} at {self.timestamp}"


class ExpenseCategory(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6366f1', help_text='Hex color code')
    icon = models.CharField(max_length=50, blank=True, help_text='Icon name/class')
    is_active = models.BooleanField(default=True)
    is_tax_deductible = models.BooleanField(default=False, help_text='Whether expenses in this category are tax deductible')
    gl_account_code = models.CharField(max_length=20, blank=True, help_text='General ledger account code')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = ['workspace', 'name']
        verbose_name_plural = 'Expense categories'

    def __str__(self):
        return self.name


class Vendor(models.Model):
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='vendors')
    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text='Vendor tax ID/VAT number')
    payment_terms = models.CharField(max_length=100, blank=True, help_text='e.g., Net 30, Due on receipt')
    default_category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    expense_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['workspace', 'name']

    def __str__(self):
        return self.name

    def update_totals(self):
        from django.db.models import Sum, Count
        aggregates = self.expenses.filter(status='approved').aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        self.total_expenses = aggregates['total'] or Decimal('0.00')
        self.expense_count = aggregates['count'] or 0
        self.save(update_fields=['total_expenses', 'expense_count'])


class Expense(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        REIMBURSED = 'reimbursed', 'Reimbursed'
        BILLED = 'billed', 'Billed to Client'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Cash'
        CREDIT_CARD = 'credit_card', 'Credit Card'
        DEBIT_CARD = 'debit_card', 'Debit Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CHECK = 'check', 'Check'
        PETTY_CASH = 'petty_cash', 'Petty Cash'
        COMPANY_CARD = 'company_card', 'Company Card'
        OTHER = 'other', 'Other'

    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='expenses')
    expense_number = models.CharField(max_length=50, db_index=True)
    description = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    expense_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text='Pre-tax amount')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, help_text='Amount including tax')
    currency = models.CharField(max_length=3, default='USD', choices=Invoice.CURRENCY_CHOICES)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('1.000000'), help_text='Exchange rate to base currency')
    base_currency_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text='Amount in workspace base currency')
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.OTHER)
    reference_number = models.CharField(max_length=100, blank=True, help_text='Receipt/invoice number from vendor')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_billable = models.BooleanField(default=False, help_text='Whether this expense can be billed to a client')
    is_billed = models.BooleanField(default=False)
    markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text='Markup percentage when billing to client')
    billable_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text='Amount to bill client (including markup)')
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses', help_text='Client to bill for this expense')
    project_name = models.CharField(max_length=255, blank=True, help_text='Optional project or job reference')
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='billed_expenses', help_text='Invoice where this expense was billed')
    billed_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True, help_text='List of tags for filtering')
    is_recurring = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True)
    reimbursed_at = models.DateTimeField(null=True, blank=True)
    reimbursement_reference = models.CharField(max_length=100, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_expenses')
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_expenses')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['workspace', 'expense_date']),
            models.Index(fields=['workspace', 'category']),
            models.Index(fields=['workspace', 'is_billable', 'is_billed']),
            models.Index(fields=['client', 'is_billed']),
        ]

    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        if not self.expense_number:
            self.expense_number = self.generate_expense_number()
        self.calculate_totals()
        super().save(*args, **kwargs)

    def generate_expense_number(self):
        import secrets
        prefix = "EXP"
        today = timezone.now().strftime('%Y%m')
        random_suffix = secrets.token_hex(3).upper()
        return f"{prefix}-{today}-{random_suffix}"

    def calculate_totals(self):
        self.tax_amount = (self.amount * self.tax_rate / Decimal('100')).quantize(Decimal('0.01'))
        self.total_amount = self.amount + self.tax_amount
        self.base_currency_amount = (self.total_amount * self.exchange_rate).quantize(Decimal('0.01'))
        if self.is_billable:
            markup = (self.total_amount * self.markup_percent / Decimal('100')).quantize(Decimal('0.01'))
            self.billable_amount = self.total_amount + markup
        else:
            self.billable_amount = Decimal('0.00')


class ExpenseAttachment(models.Model):
    class FileType(models.TextChoices):
        RECEIPT = 'receipt', 'Receipt'
        INVOICE = 'invoice', 'Invoice'
        CONTRACT = 'contract', 'Contract'
        OTHER = 'other', 'Other'

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255)
    original_file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, help_text='Storage path or URL')
    file_type = models.CharField(max_length=20, choices=FileType.choices, default=FileType.RECEIPT)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, help_text='Primary receipt image')
    thumbnail_path = models.CharField(max_length=500, blank=True)
    ocr_text = models.TextField(blank=True, help_text='OCR extracted text from receipt')
    ocr_processed = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.original_file_name} for {self.expense.expense_number}"


class ExpenseAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Expense Created'
        UPDATED = 'updated', 'Expense Updated'
        SUBMITTED = 'submitted', 'Expense Submitted'
        APPROVED = 'approved', 'Expense Approved'
        REJECTED = 'rejected', 'Expense Rejected'
        REIMBURSED = 'reimbursed', 'Expense Reimbursed'
        BILLED = 'billed', 'Expense Billed to Client'
        ATTACHMENT_ADDED = 'attachment_added', 'Attachment Added'
        ATTACHMENT_REMOVED = 'attachment_removed', 'Attachment Removed'
        DELETED = 'deleted', 'Expense Deleted'

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=Action.choices)
    description = models.TextField(blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    related_invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['expense', 'action']),
        ]

    def __str__(self):
        return f"{self.action} on {self.expense.expense_number} at {self.timestamp}"

class SharedReportLink(models.Model):
    """Shareable report links with permissions and audit logging."""
    
    class ReportType(models.TextChoices):
        REVENUE = "revenue", "Revenue Report"
        AGING = "aging", "A/R Aging Report"
        CASHFLOW = "cashflow", "Cash Flow Report"
        PROFITABILITY = "profitability", "Client Profitability"
        TAX = "tax", "Tax Summary"
        EXPENSE = "expense", "Expense Report"
        CUSTOM = "custom", "Custom Report"
    
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='shared_reports')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_shared_reports')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    report_type = models.CharField(max_length=50, choices=ReportType.choices)
    report_params = models.JSONField(default=dict, blank=True, help_text="Report parameters like date range, filters")
    name = models.CharField(max_length=255, blank=True, help_text="Optional name for the shared report")
    
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    password_hash = models.CharField(max_length=64, blank=True, null=True, help_text="SHA256 hash of password if protected")
    
    view_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['workspace', 'is_active']),
        ]
    
    def __str__(self):
        return f"Shared {self.report_type} report - {self.token[:8]}..."
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_accessible(self):
        return self.is_active and not self.is_expired
    
    def increment_view_count(self):
        self.view_count += 1
        self.last_viewed_at = timezone.now()
        self.save(update_fields=['view_count', 'last_viewed_at'])


class ReportAccessLog(models.Model):
    """Audit log for shared report accesses."""
    
    shared_link = models.ForeignKey(SharedReportLink, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['shared_link', '-accessed_at']),
        ]
    
    def __str__(self):
        return f"Access to {self.shared_link.token[:8]} at {self.accessed_at}"


class ReportExport(models.Model):
    """Track report exports for audit purposes."""
    
    class ExportFormat(models.TextChoices):
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"
        EXCEL = "excel", "Excel"
    
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='report_exports')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    report_type = models.CharField(max_length=50)
    report_params = models.JSONField(default=dict, blank=True)
    export_format = models.CharField(max_length=10, choices=ExportFormat.choices)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    row_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} export by {self.user} at {self.created_at}"
