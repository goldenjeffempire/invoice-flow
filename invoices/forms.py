"""
Production-Grade Authentication Forms
Strong validation, accessibility, and security best practices.
"""
import re
from django import forms
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from .models import UserProfile


class BaseFormMixin:
    def add_error_class(self) -> None:
        fields = getattr(self, 'fields', {})
        errors = getattr(self, 'errors', {})
        for field_name, field in fields.items():
            if field_name in errors:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' border-red-500'
                field.widget.attrs['aria-invalid'] = 'true'


class SignUpForm(forms.Form, BaseFormMixin):
    username = forms.CharField(
        min_length=3,
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
            'aria-describedby': 'username-help',
        }),
        help_text="3-30 characters, letters, numbers, and underscores only"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
            'aria-describedby': 'email-help',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
            'aria-describedby': 'password-help',
        }),
        help_text="At least 8 characters with uppercase, lowercase, number, and special character"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
        }),
        error_messages={'required': 'You must accept the terms and conditions'}
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, and underscores")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        errors = []

        if len(password) < 8:
            errors.append("at least 8 characters")
        if not re.search(r'[A-Z]', password):
            errors.append("one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("one special character")

        if errors:
            raise forms.ValidationError(f"Password must contain: {', '.join(errors)}")

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

        return cleaned_data


class LoginForm(forms.Form, BaseFormMixin):
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Email or username',
            'autocomplete': 'username',
            'autofocus': True,
        }),
        label="Email or Username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
        })
    )


class MFAVerifyForm(forms.Form, BaseFormMixin):
    code = forms.CharField(
        min_length=6,
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-widest',
            'placeholder': '000000',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9A-Za-z]*',
            'autofocus': True,
            'aria-describedby': 'mfa-help',
        }),
        label="Verification Code",
        help_text="Enter the 6-digit code from your authenticator app, or use a backup code"
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        code = re.sub(r'[^0-9A-Z]', '', code)
        return code


class MFASetupVerifyForm(forms.Form, BaseFormMixin):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-widest',
            'placeholder': '000000',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autofocus': True,
        }),
        label="Verification Code"
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Please enter a 6-digit code")
        return code


class MFADisableForm(forms.Form, BaseFormMixin):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your password to confirm',
            'autocomplete': 'current-password',
        }),
        label="Confirm Password"
    )


class PasswordResetRequestForm(forms.Form, BaseFormMixin):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )


class PasswordResetConfirmForm(forms.Form, BaseFormMixin):
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Create a new password',
            'autocomplete': 'new-password',
            'aria-describedby': 'password-help',
        }),
        help_text="At least 8 characters with uppercase, lowercase, number, and special character"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Confirm your new password',
            'autocomplete': 'new-password',
        })
    )

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        errors = []

        if len(password) < 8:
            errors.append("at least 8 characters")
        if not re.search(r'[A-Z]', password):
            errors.append("one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("one special character")

        if errors:
            raise forms.ValidationError(f"Password must contain: {', '.join(errors)}")

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

        return cleaned_data


class ChangePasswordForm(forms.Form, BaseFormMixin):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Current password',
            'autocomplete': 'current-password',
        })
    )
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'New password',
            'autocomplete': 'new-password',
        })
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password and confirm_new_password and new_password != confirm_new_password:
            self.add_error('confirm_new_password', "Passwords do not match")

        return cleaned_data


class ResendVerificationForm(forms.Form, BaseFormMixin):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )


class InvoiceForm(forms.Form):
    pass


class LineItemForm(forms.Form):
    pass


class InvoiceTemplateForm(forms.Form):
    pass
