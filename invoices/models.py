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
    def can_record_payment(self, payment_id):
        return self.status not in [self.Status.VOID, self.Status.WRITE_OFF, self.Status.PAID] and self.amount_due > 0

    def get_public_url(self):
        from django.urls import reverse
        return reverse('invoices:public_invoice', kwargs={'token': self.public_token})

    def regenerate_token(self):
        self.public_token = secrets.token_urlsafe(32)
        self.save(update_fields=['public_token'])


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

class LineItem(models.Model):
    class ItemType(models.TextChoices):
        SERVICE = "service", "Service"
        PRODUCT = "product", "Product"
        EXPENSE = "expense", "Expense"
        DISCOUNT = "discount", "Discount Line"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.SERVICE)
    product_id_ref = models.IntegerField(null=True, blank=True)

    description = models.CharField(max_length=500)
    long_description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, blank=True, default="unit")
    quantity = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1.0000'))
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_type = models.CharField(max_length=20, choices=Invoice.DiscountType.choices, default=Invoice.DiscountType.FLAT)
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def calculate_totals(self, tax_mode='exclusive'):
        line_subtotal = self.quantity * self.unit_price

        if self.discount_type == Invoice.DiscountType.PERCENTAGE:
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


class InvoiceAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        DOCUMENT = "document", "Document"
        IMAGE = "image", "Image"
        CONTRACT = "contract", "Contract"
        RECEIPT = "receipt", "Receipt"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to="invoice_attachments/%Y/%m/")
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=AttachmentType.choices, default=AttachmentType.DOCUMENT)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.IntegerField(default=0)
    description = models.CharField(max_length=255, blank=True)
    is_visible_to_client = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class InvoicePayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CARD = "card", "Card Payment"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        PAYSTACK = "paystack", "Paystack"
        STRIPE = "stripe", "Stripe"
        CHECK = "check", "Check/Cheque"
        OTHER = "other", "Other"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reference = models.CharField(max_length=255, unique=True, db_index=True)
    external_reference = models.CharField(max_length=255, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_partial = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.amount} {self.currency}"


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

class PaymentSettings(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
