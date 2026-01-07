from typing import Any, Dict, Optional

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    ContactSubmission,
    Invoice,
    InvoiceTemplate,
    LineItem,
    PaymentSettings,
    RecurringInvoice,
    UserProfile,
    Waitlist,
)

class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "input-modern", "placeholder": "Item description"}),
            "quantity": forms.NumberInput(attrs={"class": "input-modern", "step": "0.01", "placeholder": "1"}),
            "unit_price": forms.NumberInput(attrs={"class": "input-modern", "step": "0.01", "placeholder": "0.00"}),
        }

LineItemFormSet = forms.inlineformset_factory(
    Invoice, LineItem, form=LineItemForm, extra=1, can_delete=True
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
        widget=forms.TextInput(attrs={"class": "input-modern", "placeholder": "+1 (555) 000-0000"}),
    )
    client_phone = forms.CharField(
        max_length=50,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={"class": "input-modern", "placeholder": "+1 (555) 000-0000"}),
    )
    currency = forms.ChoiceField(
        choices=Invoice.CURRENCY_CHOICES,
        initial="USD",
        widget=forms.Select(attrs={"class": "input-modern"}),
    )
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=0,
        validators=[validate_tax_rate],
        widget=forms.NumberInput(attrs={"class": "input-modern", "step": "0.01", "placeholder": "0.00"}),
    )
    invoice_date = forms.DateField(
        validators=[validate_invoice_date],
        widget=forms.DateInput(attrs={"class": "input-modern", "type": "date"}),
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
            "discount",
            "automated_reminders_enabled",
            "notes",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "input-modern", "placeholder": "Your Company Name"}),
            "business_email": forms.EmailInput(attrs={"class": "input-modern", "placeholder": "billing@yourcompany.com"}),
            "business_address": forms.Textarea(attrs={"class": "input-modern", "rows": 2, "placeholder": "Street, City, Country"}),
            "client_name": forms.TextInput(attrs={"class": "input-modern", "placeholder": "Client Business Name"}),
            "client_email": forms.EmailInput(attrs={"class": "input-modern", "placeholder": "client@example.com"}),
            "client_address": forms.Textarea(attrs={"class": "input-modern", "rows": 2, "placeholder": "Client Address"}),
            "due_date": forms.DateInput(attrs={"class": "input-modern", "type": "date"}),
            "discount": forms.NumberInput(attrs={"class": "input-modern", "step": "0.01", "placeholder": "0.00"}),
            "automated_reminders_enabled": forms.CheckboxInput(attrs={"class": "sr-only peer"}),
            "notes": forms.Textarea(attrs={"class": "input-modern", "rows": 3, "placeholder": "Terms and conditions or thank you note"}),
        }

    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount is not None:
            if discount < 0 or discount > 100:
                raise forms.ValidationError("Discount must be between 0 and 100.")
        return discount

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'automated_reminders_enabled':
                current_classes = self.fields[field].widget.attrs.get('class', '')
                if 'input-modern' not in current_classes:
                    self.fields[field].widget.attrs['class'] = f"input-modern {current_classes}".strip()


class UserDetailsForm(forms.ModelForm):
    """Form for editing user profile information (first name, last name, email)."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "First Name",
                    "autocomplete": "given-name",
                    "required": "required",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Last Name",
                    "autocomplete": "family-name",
                    "required": "required",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Email Address",
                    "autocomplete": "email",
                    "required": "required",
                }
            ),
        }

    def clean_email(self) -> str:
        email: Optional[str] = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email


class UserProfileForm(forms.ModelForm):
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    default_currency = forms.ChoiceField(
        choices=UserProfile.CURRENCY_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-input",
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
                    "class": "form-input",
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
                    "class": "form-input",
                    "placeholder": "business@example.com",
                }
            ),
            "business_phone": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "+1 (555) 123-4567",
                }
            ),
            "business_address": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "123 Business Street, City, State, ZIP",
                }
            ),
            "default_currency": forms.Select(
                attrs={
                    "class": "form-input",
                }
            ),
            "default_tax_rate": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
            "invoice_prefix": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "INV-",
                }
            ),
            "tax_id": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Tax ID / VAT Number",
                }
            ),
            "tax_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "e.g. VAT, GST",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False

    def clean_business_email(self):
        email = self.cleaned_data.get('business_email')
        if email:
            validate_email_domain(email)
        return email

    def clean_business_phone(self):
        phone = self.cleaned_data.get('business_phone')
        if phone:
            validate_phone_number(phone)
        return phone

    def clean_default_tax_rate(self):
        rate = self.cleaned_data.get('default_tax_rate')
        if rate is not None:
            validate_tax_rate(rate)
        return rate


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
        self.fields['notify_invoice_created'].label = "Invoice Created"
        self.fields['notify_payment_received'].label = "Payment Received"
        self.fields['notify_invoice_viewed'].label = "Invoice Viewed"
        self.fields['notify_invoice_overdue'].label = "Invoice Overdue"
        self.fields['notify_weekly_summary'].label = "Weekly Summary"
        self.fields['notify_security_alerts'].label = "Security Alerts"
        self.fields['notify_password_changes'].label = "Password Changes"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Current Password",
                "autocomplete": "current-password",
            }
        )
    )
    new_password = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "New Password (min 12 characters)",
                "autocomplete": "new-password",
            }
        ),
        help_text="Password must be at least 12 characters and include a mix of letters and numbers.",
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
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


class ReminderRuleForm(forms.ModelForm):
    class Meta:
        from .models import ReminderRule
        model = ReminderRule
        fields = [
            "name", "trigger_type", "days_delta", "exclude_weekends", 
            "retry_on_failure", "max_retries", "channel", 
            "subject_template", "body_template", "is_active",
            "custom_sender_name", "reply_to_email", "attach_pdf"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g., 3-day overdue notice"}),
            "trigger_type": forms.Select(attrs={"class": "form-input"}),
            "days_delta": forms.NumberInput(attrs={"class": "form-input"}),
            "exclude_weekends": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "retry_on_failure": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "max_retries": forms.NumberInput(attrs={"class": "form-input"}),
            "channel": forms.Select(attrs={"class": "form-input"}),
            "subject_template": forms.TextInput(attrs={"class": "form-input", "placeholder": "Optional subject template"}),
            "body_template": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Optional body template"}),
            "is_active": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "custom_sender_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Leave blank for default"}),
            "reply_to_email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Leave blank for default"}),
            "attach_pdf": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
        }

class UserReminderSettingsForm(forms.Form):
    # This form is deprecated in favor of ReminderRuleForm.
    # Placeholder maintained for backward compatibility in existing views/templates.
    enabled = forms.BooleanField(required=False)

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


class PaymentRecipientForm(forms.Form):
    # This is a placeholder as the real PaymentRecipient model is used
    pass

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
            "payout_schedule",
            "bank_name",
            "account_number_encrypted",
            "account_name",
            "payment_instructions",
        ]
        widgets = {
            "enable_card_payments": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "enable_bank_transfers": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "enable_mobile_money": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "enable_ussd": forms.CheckboxInput(attrs={"class": "w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 transition-all cursor-pointer"}),
            "preferred_currency": forms.Select(attrs={"class": "form-input"}),
            "payout_schedule": forms.Select(attrs={"class": "form-input"}),
            "bank_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. GTBank"}),
            "account_number_encrypted": forms.TextInput(attrs={"class": "form-input", "placeholder": "0123456789"}),
            "account_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "John Doe"}),
            "payment_instructions": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure we don't accidentally require fields that aren't strictly necessary for the form to save
        for field_name in self.fields:
            self.fields[field_name].required = False
