"""
Production-grade Settings forms with comprehensive validation.
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import UserProfile, PaymentSettings, MFAProfile, UserSession


class ProfileDetailsForm(forms.ModelForm):
    """User account details form with validation."""
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First Name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last Name',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email Address',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['email'].initial = self.instance.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already in use.')
        return email

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if not name:
            raise ValidationError('First name cannot be empty.')
        if len(name) < 2:
            raise ValidationError('First name must be at least 2 characters.')
        if not re.match(r"^[a-zA-Z\s'-]+$", name):
            raise ValidationError('First name contains invalid characters.')
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if not name:
            raise ValidationError('Last name cannot be empty.')
        if len(name) < 2:
            raise ValidationError('Last name must be at least 2 characters.')
        if not re.match(r"^[a-zA-Z\s'-]+$", name):
            raise ValidationError('Last name contains invalid characters.')
        return name


class BusinessProfileForm(forms.ModelForm):
    """Business information form with validation."""

    class Meta:
        model = UserProfile
        fields = [
            'company_name',
            'company_logo',
            'business_email',
            'business_phone',
            'business_address',
            'default_currency',
            'invoice_prefix',
            'timezone',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Company Name',
                'maxlength': '200',
            }),
            'company_logo': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
            'business_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'business@example.com',
            }),
            'business_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 000-0000',
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': '123 Business St, City, State, ZIP',
            }),
            'default_currency': forms.Select(attrs={
                'class': 'form-select',
            }),
            'invoice_prefix': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'INV',
                'maxlength': '10',
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def clean_company_logo(self):
        logo = self.cleaned_data.get('company_logo')
        if logo:
            if logo.size > 5 * 1024 * 1024:
                raise ValidationError('Logo file size must not exceed 5MB.')
            if not logo.content_type.startswith('image/'):
                raise ValidationError('Please upload a valid image file.')
        return logo

    def clean_invoice_prefix(self):
        prefix = self.cleaned_data.get('invoice_prefix', '').strip().upper()
        if not prefix:
            prefix = 'INV'
        if len(prefix) > 10:
            raise ValidationError('Prefix must not exceed 10 characters.')
        if not re.match(r'^[A-Z0-9\-_]+$', prefix):
            raise ValidationError('Prefix can only contain letters, numbers, hyphens, and underscores.')
        return prefix


class NotificationPreferencesForm(forms.ModelForm):
    """Email notification preferences form."""

    class Meta:
        model = UserProfile
        fields = [
            'notify_invoice_created',
            'notify_payment_received',
            'notify_invoice_viewed',
            'notify_invoice_overdue',
            'notify_weekly_summary',
            'notify_security_alerts',
            'notify_password_changes',
        ]
        widgets = {
            'notify_invoice_created': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_payment_received': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_invoice_viewed': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_invoice_overdue': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_weekly_summary': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_security_alerts': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'notify_password_changes': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }


class PasswordChangeForm(forms.Form):
    """Secure password change form with validation."""

    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current Password',
            'autocomplete': 'current-password',
        }),
        required=True,
    )
    new_password = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New Password (min 12 characters)',
            'autocomplete': 'new-password',
        }),
        required=True,
        help_text='At least 12 characters with letters, numbers, and symbols.',
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm Password',
            'autocomplete': 'new-password',
        }),
        required=True,
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password', '')
        if len(password) < 12:
            raise ValidationError('Password must be at least 12 characters long.')
        if password.isalpha():
            raise ValidationError('Password must contain numbers.')
        if password.isdigit():
            raise ValidationError('Password must contain letters.')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            raise ValidationError('Password should contain special characters for better security.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if new_password and confirm and new_password != confirm:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data


class PaymentSettingsForm(forms.ModelForm):
    """Payment configuration form."""

    class Meta:
        model = PaymentSettings
        fields = [
            'accept_cards',
            'accept_bank_transfers',
            'enable_mobile_money',
            'minimum_payment_amount',
            'auto_reconcile',
            'send_payment_receipt',
            'payment_instructions',
        ]
        widgets = {
            'accept_cards': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'accept_bank_transfers': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'enable_mobile_money': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'minimum_payment_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'auto_reconcile': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'send_payment_receipt': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
            'payment_instructions': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Add payment instructions visible to clients',
            }),
        }

    def clean_minimum_payment_amount(self):
        amount = self.cleaned_data.get('minimum_payment_amount')
        if amount and amount < 0:
            raise ValidationError('Minimum payment amount cannot be negative.')
        return amount
