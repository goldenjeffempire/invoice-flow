"""
InvoiceFlow – Authentication Forms
Production-grade forms with strong validation and accessibility.
"""
from __future__ import annotations

import re
from django import forms
from django.contrib.auth.models import User


# ---------------------------------------------------------------------------
# Shared Mixin
# ---------------------------------------------------------------------------

class _AccessibleFieldsMixin:
    """Marks invalid fields with ARIA attributes after validation."""

    def _mark_invalid_fields(self) -> None:
        for name, field in self.fields.items():
            if name in self.errors:
                attrs = field.widget.attrs
                existing = attrs.get("class", "")
                if "input-error" not in existing:
                    attrs["class"] = existing + " input-error"
                attrs["aria-invalid"] = "true"
                attrs["aria-describedby"] = f"{name}-error"

    def is_valid(self):
        result = super().is_valid()
        self._mark_invalid_fields()
        return result


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

_INPUT_BASE = (
    "auth-input block w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-gray-900 placeholder-gray-400 shadow-sm transition-all duration-150 "
    "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 "
    "disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500"
)


class LoginForm(_AccessibleFieldsMixin, forms.Form):
    username_or_email = forms.CharField(
        label="Email or Username",
        max_length=254,
        widget=forms.TextInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "you@example.com or username",
            "autocomplete": "username",
            "autofocus": True,
            "id": "id_username_or_email",
            "aria-label": "Email or Username",
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Enter your password",
            "autocomplete": "current-password",
            "id": "id_password",
            "aria-label": "Password",
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Keep me signed in for 2 weeks",
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500",
            "id": "id_remember_me",
        }),
    )

    def clean_username_or_email(self):
        return self.cleaned_data["username_or_email"].strip()


# ---------------------------------------------------------------------------
# Sign Up
# ---------------------------------------------------------------------------

class SignUpForm(_AccessibleFieldsMixin, forms.Form):
    full_name = forms.CharField(
        label="Full name",
        min_length=2,
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Jane Smith",
            "autocomplete": "name",
            "autofocus": True,
            "id": "id_full_name",
            "aria-label": "Full name",
        }),
    )
    username = forms.CharField(
        label="Username",
        min_length=3,
        max_length=30,
        widget=forms.TextInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "janesmith",
            "autocomplete": "username",
            "id": "id_username",
            "aria-label": "Username",
            "aria-describedby": "username-hint",
            "pattern": "[a-zA-Z0-9_]+",
        }),
        help_text="3–30 characters. Letters, numbers, underscores only.",
    )
    email = forms.EmailField(
        label="Work email",
        widget=forms.EmailInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "you@company.com",
            "autocomplete": "email",
            "id": "id_email",
            "aria-label": "Work email",
        }),
    )
    password = forms.CharField(
        label="Password",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Create a strong password",
            "autocomplete": "new-password",
            "id": "id_password",
            "aria-label": "Password",
            "aria-describedby": "password-hint",
        }),
        help_text="8+ chars with uppercase, lowercase, number, and special character.",
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Confirm your password",
            "autocomplete": "new-password",
            "id": "id_confirm_password",
            "aria-label": "Confirm password",
        }),
    )
    agree_terms = forms.BooleanField(
        required=True,
        label="",
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500",
            "id": "id_agree_terms",
        }),
        error_messages={"required": "You must accept the Terms of Service and Privacy Policy to continue."},
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise forms.ValidationError("Username may only contain letters, numbers, and underscores.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        issues: list[str] = []
        if len(password) < 8:
            issues.append("at least 8 characters")
        if not re.search(r"[A-Z]", password):
            issues.append("one uppercase letter")
        if not re.search(r"[a-z]", password):
            issues.append("one lowercase letter")
        if not re.search(r"\d", password):
            issues.append("one number")
        if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/`~\'"\\]', password):
            issues.append("one special character")
        if issues:
            raise forms.ValidationError(f"Password must include: {', '.join(issues)}.")
        return password

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned


# ---------------------------------------------------------------------------
# Password Reset – Request
# ---------------------------------------------------------------------------

class PasswordResetRequestForm(_AccessibleFieldsMixin, forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "you@example.com",
            "autocomplete": "email",
            "autofocus": True,
            "id": "id_email",
            "aria-label": "Email address",
        }),
    )

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


# ---------------------------------------------------------------------------
# Password Reset – Confirm
# ---------------------------------------------------------------------------

class PasswordResetConfirmForm(_AccessibleFieldsMixin, forms.Form):
    password = forms.CharField(
        label="New password",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Create a strong new password",
            "autocomplete": "new-password",
            "id": "id_password",
            "aria-label": "New password",
            "aria-describedby": "password-hint",
            "autofocus": True,
        }),
        help_text="8+ chars with uppercase, lowercase, number, and special character.",
    )
    confirm_password = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Confirm your new password",
            "autocomplete": "new-password",
            "id": "id_confirm_password",
            "aria-label": "Confirm new password",
        }),
    )

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        issues: list[str] = []
        if len(password) < 8:
            issues.append("at least 8 characters")
        if not re.search(r"[A-Z]", password):
            issues.append("one uppercase letter")
        if not re.search(r"[a-z]", password):
            issues.append("one lowercase letter")
        if not re.search(r"\d", password):
            issues.append("one number")
        if not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/`~\'"\\]', password):
            issues.append("one special character")
        if issues:
            raise forms.ValidationError(f"Password must include: {', '.join(issues)}.")
        return password

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned


# ---------------------------------------------------------------------------
# Change Password (authenticated user)
# ---------------------------------------------------------------------------

class ChangePasswordForm(_AccessibleFieldsMixin, forms.Form):
    current_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Your current password",
            "autocomplete": "current-password",
            "id": "id_current_password",
        }),
    )
    new_password = forms.CharField(
        label="New password",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "New password",
            "autocomplete": "new-password",
            "id": "id_new_password",
        }),
    )
    confirm_new_password = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Confirm new password",
            "autocomplete": "new-password",
            "id": "id_confirm_new_password",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("new_password")
        cpw = cleaned.get("confirm_new_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_new_password", "Passwords do not match.")
        return cleaned


# ---------------------------------------------------------------------------
# Stubs – preserving imports used elsewhere
# ---------------------------------------------------------------------------

class MFAVerifyForm(_AccessibleFieldsMixin, forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=10,
        widget=forms.TextInput(attrs={
            "class": _INPUT_BASE + " text-center text-2xl tracking-widest",
            "placeholder": "000000",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "autofocus": True,
        }),
        label="Verification Code",
    )

    def clean_code(self):
        return re.sub(r"[^0-9A-Za-z]", "", self.cleaned_data.get("code", "")).upper()


class MFASetupVerifyForm(_AccessibleFieldsMixin, forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            "class": _INPUT_BASE + " text-center text-2xl tracking-widest",
            "placeholder": "000000",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "autofocus": True,
        }),
        label="Verification Code",
    )

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if not code.isdigit() or len(code) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit code.")
        return code


class MFADisableForm(_AccessibleFieldsMixin, forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Enter your password to confirm",
            "autocomplete": "current-password",
        }),
        label="Confirm Password",
    )


class ResendVerificationForm(_AccessibleFieldsMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": _INPUT_BASE,
            "placeholder": "Enter your email address",
            "autocomplete": "email",
        }),
    )


class InvoiceForm(forms.Form):
    pass


class LineItemForm(forms.Form):
    pass


class InvoiceTemplateForm(forms.Form):
    pass


class NewsletterSubscribeForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address",
            "autocomplete": "email",
            "id": "id_newsletter_email",
            "aria-label": "Email address",
        }),
    )
    first_name = forms.CharField(
        label="First name",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "First name (optional)",
            "autocomplete": "given-name",
            "id": "id_newsletter_first_name",
            "aria-label": "First name",
        }),
    )

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()
