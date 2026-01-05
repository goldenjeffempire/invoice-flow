from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, LineItem
from django.core.validators import MinValueValidator
from decimal import Decimal

class EnterpriseInvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "business_name", "business_email", "business_phone", "business_address",
            "client_name", "client_email", "client_phone", "client_address",
            "invoice_date", "due_date", "currency", "tax_rate", "discount",
            "automated_reminders_enabled", "notes",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "enterprise-input", "placeholder": "Business Name"}),
            "business_email": forms.EmailInput(attrs={"class": "enterprise-input", "placeholder": "email@business.com"}),
            "business_phone": forms.TextInput(attrs={"class": "enterprise-input", "placeholder": "Business Phone"}),
            "business_address": forms.Textarea(attrs={"class": "enterprise-input", "rows": 2, "placeholder": "Business Address"}),
            "client_name": forms.TextInput(attrs={"class": "enterprise-input", "placeholder": "Client Name"}),
            "client_email": forms.EmailInput(attrs={"class": "enterprise-input", "placeholder": "client@example.com"}),
            "client_phone": forms.TextInput(attrs={"class": "enterprise-input", "placeholder": "Client Phone"}),
            "client_address": forms.Textarea(attrs={"class": "enterprise-input", "rows": 2, "placeholder": "Client Address"}),
            "invoice_date": forms.DateInput(attrs={"class": "enterprise-input", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "enterprise-input", "type": "date"}),
            "currency": forms.Select(attrs={"class": "enterprise-select"}),
            "tax_rate": forms.NumberInput(attrs={"class": "enterprise-input", "step": "0.01", "min": "0"}),
            "discount": forms.NumberInput(attrs={"class": "enterprise-input", "step": "0.01", "min": "0", "max": "100"}),
            "automated_reminders_enabled": forms.CheckboxInput(attrs={"class": "enterprise-checkbox"}),
            "notes": forms.Textarea(attrs={"class": "enterprise-input", "rows": 3, "placeholder": "Terms and conditions..."}),
        }

    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount and (discount < 0 or discount > 100):
            raise forms.ValidationError("Discount must be between 0 and 100%")
        return discount

class EnterpriseLineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "enterprise-input", "placeholder": "Item description"}),
            "quantity": forms.NumberInput(attrs={"class": "enterprise-input", "step": "0.01", "min": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "enterprise-input", "step": "0.01", "min": "0"}),
        }

EnterpriseLineItemFormSet = inlineformset_factory(
    Invoice, LineItem, form=EnterpriseLineItemForm,
    extra=1, can_delete=True, min_num=1, validate_min=True
)
