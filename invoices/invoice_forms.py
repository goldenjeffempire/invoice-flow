from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, LineItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "business_name", "business_email", "business_phone", "business_address",
            "client_name", "client_email", "client_phone", "client_address",
            "invoice_date", "due_date", "currency", "tax_rate", "discount",
            "automated_reminders_enabled", "notes",
        ]
        widgets = {
            "business_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your Company Name"}),
            "business_email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "billing@yourcompany.com"}),
            "business_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+1 (555) 000-0000"}),
            "business_address": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Business Address"}),
            "client_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Client Name"}),
            "client_email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "client@example.com"}),
            "client_phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+1 (555) 000-0000"}),
            "client_address": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Client Address"}),
            "invoice_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "due_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "currency": forms.Select(attrs={"class": "form-input"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "discount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "automated_reminders_enabled": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Notes/Terms"}),
        }

class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItem
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-input", "placeholder": "Item description"}),
            "quantity": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
        }

LineItemFormSet = inlineformset_factory(
    Invoice, LineItem, form=LineItemForm,
    extra=1, can_delete=True
)
