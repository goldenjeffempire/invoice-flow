from typing import Any, Dict, Optional

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    ContactSubmission,
    Invoice,
    InvoiceTemplate,
    PaymentRecipient,
    PaymentSettings,
    RecurringInvoice,
    UserProfile,
    Waitlist,
)
from .validators import (
    InvoiceBusinessRules,
    validate_email_domain,
    validate_invoice_date,
    validate_phone_number,
    validate_tax_rate,
)

try:
    import pytz

    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.common_timezones]
except ImportError:
    from zoneinfo import available_timezones

    TIMEZONE_CHOICES = [(tz, tz) for tz in sorted(available_timezones())]


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        validators=[validate_email_domain],
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "your.email@example.com",
                "autocomplete": "email",
            }
        ),
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "First Name",
                "autocomplete": "given-name",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "Last Name",
                "autocomplete": "family-name",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "Username",
                    "autocomplete": "username",
                }
            ),
        }

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    def clean_email(self) -> str:
        email: Optional[str] = self.cleaned_data.get("email")
        if email is None:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(forms.Form):
    """Modern login form with remember me option and enhanced validation."""

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "auth-form-input",
                "placeholder": "Email or Username",
                "autocomplete": "username",
                "autofocus": True,
                "aria-label": "Email or Username",
            }
        ),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-form-input",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
                "aria-label": "Password",
            }
        )
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "auth-checkbox-input",
            }
        ),
        label="Remember me for 30 days",
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username', '').strip()
        password = cleaned_data.get('password', '')
        
        if not username:
            self.add_error('username', 'Email or username is required.')
        if not password:
            self.add_error('password', 'Password is required.')
        
        return cleaned_data


class InvoiceForm(forms.ModelForm):
    business_phone = forms.CharField(
        max_length=50,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={"class": "input-field"}),
    )
    client_phone = forms.CharField(
        max_length=50,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={"class": "input-field"}),
    )
    currency = forms.ChoiceField(
        choices=Invoice.CURRENCY_CHOICES,
        initial="USD",
        widget=forms.Select(attrs={"class": "input-field"}),
        help_text="Select the currency for this invoice",
    )
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=0,
        validators=[validate_tax_rate],
        widget=forms.NumberInput(attrs={"class": "input-field", "step": "0.01"}),
    )
    invoice_date = forms.DateField(
        validators=[validate_invoice_date],
        widget=forms.DateInput(attrs={"class": "input-field", "type": "date"}),
    )

    class Meta:
        model = Invoice
        fields = [
            "business_name",
            "business_email",
            "business_phone",
            "business_address",
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "invoice_date",
            "due_date",
            "currency",
            "tax_rate",
            "notes",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "input-field"}),
            "business_email": forms.EmailInput(attrs={"class": "input-field"}),
            "business_address": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
            "client_name": forms.TextInput(attrs={"class": "input-field"}),
            "client_email": forms.EmailInput(attrs={"class": "input-field"}),
            "client_address": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
            "due_date": forms.DateInput(attrs={"class": "input-field", "type": "date"}),
            "currency": forms.Select(attrs={"class": "input-field"}),
            "notes": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
        }

    def clean(self) -> dict:
        cleaned_data = super().clean()
        invoice_date = cleaned_data.get("invoice_date")
        due_date = cleaned_data.get("due_date")
        
        if invoice_date and due_date and due_date < invoice_date:
            self.add_error("due_date", "Due date cannot be earlier than invoice date.")
            
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
            }
        ),
    )

    class Meta:
        model = UserProfile
        fields = [
            "company_name",
            "company_logo",
            "business_email",
            "business_phone",
            "business_address",
            "default_currency",
            "default_tax_rate",
            "invoice_prefix",
            "timezone",
            "tax_id",
            "tax_name",
        ]
        widgets = {
            "company_name": forms.TextInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Your Company Name",
                }
            ),
            "company_logo": forms.FileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                    "id": "id_company_logo"
                }
            ),
            "business_email": forms.EmailInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "business@example.com",
                }
            ),
            "business_phone": forms.TextInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "+1 (555) 123-4567",
                }
            ),
            "business_address": forms.Textarea(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "rows": 3,
                    "placeholder": "123 Business Street, City, State, ZIP",
                }
            ),
            "default_currency": forms.Select(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "default_tax_rate": forms.NumberInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
            "invoice_prefix": forms.TextInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "INV-",
                }
            ),
            "tax_id": forms.TextInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Tax ID / VAT Number",
                }
            ),
            "tax_name": forms.TextInput(
                attrs={
                    "class": "form-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "e.g. VAT, GST",
                }
            ),
        }


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "notify_invoice_created",
            "notify_payment_received",
            "notify_invoice_viewed",
            "notify_invoice_overdue",
            "notify_weekly_summary",
            "notify_security_alerts",
            "notify_password_changes",
        ]
        widgets = {
            "notify_invoice_created": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_payment_received": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_invoice_viewed": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_invoice_overdue": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_weekly_summary": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_security_alerts": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
            "notify_password_changes": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add labels to fields manually if needed, though Meta.fields handles it
        self.fields['notify_invoice_created'].label = "Invoice Created"
        self.fields['notify_payment_received'].label = "Payment Received"
        self.fields['notify_invoice_viewed'].label = "Invoice Viewed"
        self.fields['notify_invoice_overdue'].label = "Invoice Overdue"
        self.fields['notify_weekly_summary'].label = "Weekly Summary"
        self.fields['notify_security_alerts'].label = "Security Alerts"
        self.fields['notify_password_changes'].label = "Password Changes"


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "Current Password",
                "autocomplete": "current-password",
            }
        )
    )
    new_password = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "New Password (min 12 characters)",
                "autocomplete": "new-password",
            }
        ),
        help_text="Password must be at least 12 characters and include a mix of letters and numbers.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "Confirm Password",
                "autocomplete": "new-password",
            }
        )
    )

    def clean_new_password(self) -> str:
        password = self.cleaned_data.get("new_password")
        if password:
            if len(password) < 12:
                raise forms.ValidationError("Password must be at least 12 characters long.")
            if password.isalpha():
                raise forms.ValidationError("Password must contain at least one number.")
            if password.isdigit():
                raise forms.ValidationError("Password must contain at least one letter.")
        return password or ""

    def clean(self) -> Dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data.get("new_password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class InvoiceTemplateForm(forms.ModelForm):
    class Meta:
        model = InvoiceTemplate
        fields = [
            "name",
            "description",
            "business_name",
            "business_email",
            "business_phone",
            "business_address",
            "currency",
            "tax_rate",
            "bank_name",
            "account_name",
            "is_default",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field"}),
            "description": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
            "business_name": forms.TextInput(attrs={"class": "input-field"}),
            "business_email": forms.EmailInput(attrs={"class": "input-field"}),
            "business_phone": forms.TextInput(attrs={"class": "input-field"}),
            "business_address": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
            "currency": forms.Select(attrs={"class": "input-field"}),
            "tax_rate": forms.NumberInput(attrs={"class": "input-field", "step": "0.01"}),
            "bank_name": forms.TextInput(attrs={"class": "input-field"}),
            "account_name": forms.TextInput(attrs={"class": "input-field"}),
        }


class RecurringInvoiceForm(forms.ModelForm):
    class Meta:
        model = RecurringInvoice
        fields = [
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "frequency",
            "start_date",
            "end_date",
            "business_name",
            "business_email",
            "currency",
            "tax_rate",
            "status",
            "next_generation",
            "notes",
        ]
        widgets = {
            "client_name": forms.TextInput(attrs={"class": "input-field"}),
            "client_email": forms.EmailInput(attrs={"class": "input-field"}),
            "client_phone": forms.TextInput(attrs={"class": "input-field"}),
            "client_address": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
            "frequency": forms.Select(attrs={"class": "input-field"}),
            "start_date": forms.DateInput(attrs={"class": "input-field", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "input-field", "type": "date"}),
            "business_name": forms.TextInput(attrs={"class": "input-field"}),
            "business_email": forms.EmailInput(attrs={"class": "input-field"}),
            "currency": forms.Select(attrs={"class": "input-field"}),
            "tax_rate": forms.NumberInput(attrs={"class": "input-field", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "input-field"}),
            "next_generation": forms.DateInput(attrs={"class": "input-field", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "input-field", "rows": 3}),
        }


class InvoiceSearchForm(forms.Form):
    """Advanced search and filter form for invoices."""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "Search by invoice ID, client, or business name...",
                "aria-label": "Search invoices",
            }
        ),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "-- All Statuses --"), ("paid", "Paid"), ("unpaid", "Unpaid")],
        widget=forms.Select(attrs={"class": "input-field", "aria-label": "Filter by status"}),
    )
    currency = forms.ChoiceField(
        required=False,
        choices=[("", "-- All Currencies --")] + list(Invoice.CURRENCY_CHOICES),
        widget=forms.Select(attrs={"class": "input-field", "aria-label": "Filter by currency"}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "input-field", "type": "date", "aria-label": "Invoice date from"}
        ),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"class": "input-field", "type": "date", "aria-label": "Invoice date to"}
        ),
    )
    min_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "input-field",
                "placeholder": "Min Amount",
                "step": "0.01",
                "min": "0",
                "aria-label": "Minimum amount",
            }
        ),
    )
    max_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "input-field",
                "placeholder": "Max Amount",
                "step": "0.01",
                "min": "0",
                "aria-label": "Maximum amount",
            }
        ),
    )

    def clean(self) -> Dict[str, Any]:
        """Validate date range and amount range."""
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        min_amount = cleaned_data.get("min_amount")
        max_amount = cleaned_data.get("max_amount")

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("Start date must be before or equal to end date.")

        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise forms.ValidationError(
                "Minimum amount must be less than or equal to maximum amount."
            )

        return cleaned_data


class WaitlistForm(forms.ModelForm):
    """Form for email capture from landing page and Coming Soon pages."""

    class Meta:
        model = Waitlist
        fields = ["email", "feature"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "your.email@example.com",
                    "required": True,
                }
            ),
            "feature": forms.Select(
                attrs={
                    "class": "w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
        }

    def clean_email(self) -> str:
        email: Optional[str] = self.cleaned_data.get("email")
        if email is None:
            raise forms.ValidationError("Email is required.")
        if Waitlist.objects.filter(email=email).exists():  # type: ignore[attr-defined]
            raise forms.ValidationError("This email is already on our waitlist!")
        return email


class UserDetailsForm(forms.ModelForm):
    """Form for editing user profile information (first name, last name, email)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "First Name",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Last Name",
                    "autocomplete": "family-name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Email Address",
                    "autocomplete": "email",
                }
            ),
        }

    def clean_email(self) -> str:
        email: Optional[str] = self.cleaned_data.get("email")
        if email is None:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email


class ContactForm(forms.ModelForm):
    """Form for contact page submissions with validation and honeypot."""

    honeypot = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"style": "display:none", "tabindex": "-1", "autocomplete": "off"}
        ),
    )

    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input-field w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Your Name",
                    "autocomplete": "name",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input-field w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "your.email@example.com",
                    "autocomplete": "email",
                    "required": True,
                }
            ),
            "subject": forms.Select(
                attrs={
                    "class": "input-field w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "input-field w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "How can we help you?",
                    "rows": 5,
                    "required": True,
                }
            ),
        }

    def clean_honeypot(self) -> str:
        """Reject form if honeypot field is filled (spam bot detection)."""
        honeypot = self.cleaned_data.get("honeypot", "")
        if honeypot:
            raise forms.ValidationError("Spam detected.")
        return honeypot

    def clean_message(self) -> str:
        """Validate message length and content."""
        message = self.cleaned_data.get("message", "")
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        if len(message) > 5000:
            raise forms.ValidationError("Message must be less than 5000 characters.")
        return message


class PaymentRecipientForm(forms.ModelForm):
    """Form for adding/editing bank account recipients for receiving payments."""

    class Meta:
        model = PaymentRecipient
        fields = [
            "name",
            "account_type",
            "bank_code",
            "bank_name",
            "account_number",
            "account_name",
            "currency",
            "is_primary",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "e.g., My Business Account",
                }
            ),
            "account_type": forms.Select(
                attrs={
                    "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "bank_code": forms.Select(
                attrs={
                    "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "id": "bank-code-select",
                }
            ),
            "bank_name": forms.HiddenInput(),
            "account_number": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "placeholder": "Enter 10-digit account number",
                    "maxlength": "10",
                    "pattern": "[0-9]{10}",
                }
            ),
            "account_name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl bg-gray-50 focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "readonly": "readonly",
                    "placeholder": "Account name will be verified",
                }
            ),
            "currency": forms.Select(
                attrs={
                    "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                },
                choices=[
                    ("NGN", "Nigerian Naira (NGN)"),
                    ("USD", "US Dollar (USD)"),
                    ("GHS", "Ghanaian Cedi (GHS)"),
                    ("ZAR", "South African Rand (ZAR)"),
                    ("KES", "Kenyan Shilling (KES)"),
                ],
            ),
            "is_primary": forms.CheckboxInput(
                attrs={
                    "class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500",
                }
            ),
        }

    def clean_account_number(self) -> str:
        account_number = self.cleaned_data.get("account_number", "")
        if not account_number.isdigit():
            raise forms.ValidationError("Account number must contain only digits.")
        if len(account_number) < 10:
            raise forms.ValidationError("Account number must be at least 10 digits.")
        return account_number


class PaymentSettingsForm(forms.ModelForm):
    """Form for configuring payment preferences and payout settings."""

    class Meta:
        model = PaymentSettings
        fields = [
            "enable_card_payments",
            "enable_bank_transfers",
            "enable_mobile_money",
            "enable_ussd",
            "preferred_currency",
            "auto_payout",
            "payout_schedule",
            "payout_threshold",
            "send_payment_receipt",
            "send_payout_notification",
            "payment_instructions",
            "paystack_public_key",
            "paystack_secret_key",
            "paystack_webhook_secret",
            "bank_name",
            "account_number_encrypted",
            "account_name",
        ]
        widgets = {
            "enable_card_payments": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "enable_bank_transfers": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "enable_mobile_money": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "enable_ussd": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "preferred_currency": forms.Select(
                attrs={
                    "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "auto_payout": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "payout_schedule": forms.Select(
                attrs={
                    "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "payout_threshold": forms.NumberInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "send_payment_receipt": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "send_payout_notification": forms.CheckboxInput(
                attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500"}
            ),
            "payment_instructions": forms.Textarea(
                attrs={
                    "class": "form-light-textarea w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "rows": 4,
                    "placeholder": "Custom payment instructions for your clients (optional)",
                }
            ),
            "paystack_public_key": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "type": "password",
                }
            ),
            "paystack_secret_key": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "type": "password",
                }
            ),
            "paystack_webhook_secret": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                    "type": "password",
                }
            ),
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "account_number_encrypted": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
            "account_name": forms.TextInput(
                attrs={
                    "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                }
            ),
        }


class SubaccountSetupForm(forms.Form):
    """Form for setting up Paystack subaccount to receive payments directly."""

    business_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "Your Business Name",
            }
        ),
    )
    bank_code = forms.CharField(
        max_length=20,
        widget=forms.Select(
            attrs={
                "class": "form-light-select w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "id": "subaccount-bank-select",
            }
        ),
    )
    account_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "10-digit account number",
                "maxlength": "10",
                "pattern": "[0-9]{10}",
            }
        ),
    )
    account_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl bg-gray-50 focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "readonly": "readonly",
                "placeholder": "Account name will be verified",
            }
        ),
    )
    contact_email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "business@example.com",
            }
        ),
    )
    contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-light-input w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-indigo-600/20 focus:border-indigo-600 transition-all",
                "placeholder": "+234 xxx xxx xxxx",
            }
        ),
    )

    def clean_account_number(self) -> str:
        account_number = self.cleaned_data.get("account_number", "")
        if not account_number.isdigit():
            raise forms.ValidationError("Account number must contain only digits.")
        if len(account_number) != 10:
            raise forms.ValidationError("Account number must be exactly 10 digits.")
        return account_number
