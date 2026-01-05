from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, LineItem

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
            "business_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Your Company Name"}),
            "business_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "billing@yourcompany.com"}),
            "business_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Business Phone"}),
            "business_address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Business Address"}),
            "client_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Client Name"}),
            "client_email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "client@example.com"}),
            "client_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Client Phone"}),
            "client_address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Client Address"}),
            "invoice_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "discount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}),
            "automated_reminders_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Notes/Terms"}),
        }

class EnterpriseLineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Item description"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

EnterpriseLineItemFormSet = inlineformset_factory(
    Invoice, LineItem, form=EnterpriseLineItemForm,
    extra=1, can_delete=True, min_num=1, validate_min=True
)
