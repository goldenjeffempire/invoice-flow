"""
Production-grade forms for Create Invoice workflow.
Comprehensive validation, security, and user experience.
"""

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Invoice, LineItem


class InvoiceDetailsForm(forms.Form):
    """Main invoice details and metadata."""
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('NGN', 'Nigerian Naira (NGN)'),
        ('ZAR', 'South African Rand (ZAR)'),
        ('KES', 'Kenyan Shilling (KES)'),
    ]

    invoice_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Auto-generated if empty',
            'aria-label': 'Invoice Number',
        })
    )
    
    invoice_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'aria-label': 'Invoice Date',
        }),
        initial=timezone.now().date()
    )
    
    due_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'aria-label': 'Due Date',
        })
    )
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'aria-label': 'Currency',
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Add notes or terms...',
            'rows': 3,
            'aria-label': 'Invoice Description',
        })
    )

    def clean(self):
        """Validate invoice dates."""
        cleaned_data = super().clean()
        invoice_date = cleaned_data.get('invoice_date')
        due_date = cleaned_data.get('due_date')
        
        if invoice_date and due_date:
            if due_date < invoice_date:
                raise ValidationError('Due date cannot be before invoice date.')
        
        return cleaned_data


class ClientDetailsForm(forms.Form):
    """Client/customer information."""
    
    client_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Client name',
            'aria-label': 'Client Name',
        })
    )
    
    client_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'client@example.com',
            'aria-label': 'Client Email',
        })
    )
    
    client_phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+1234567890',
            'aria-label': 'Client Phone',
        })
    )
    
    client_address = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Client address',
            'rows': 3,
            'aria-label': 'Client Address',
        })
    )


class LineItemForm(forms.Form):
    """Individual line item in invoice."""
    
    description = forms.CharField(
        max_length=500,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input line-item-description',
            'placeholder': 'Item description',
            'aria-label': 'Item Description',
        })
    )
    
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input line-item-qty',
            'placeholder': '1',
            'step': '0.01',
            'aria-label': 'Quantity',
        })
    )
    
    unit_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input line-item-price',
            'placeholder': '0.00',
            'step': '0.01',
            'aria-label': 'Unit Price',
        })
    )

    def clean_quantity(self):
        """Validate quantity is positive."""
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return quantity

    def clean_unit_price(self):
        """Validate unit price is non-negative."""
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is not None and unit_price < 0:
            raise ValidationError('Price cannot be negative.')
        return unit_price


class TaxesDiscountsForm(forms.Form):
    """Tax and discount configuration."""
    
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        initial=Decimal('0.00'),
        min_value=Decimal('0.00'),
        max_value=Decimal('100.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '0.00',
            'step': '0.01',
            'aria-label': 'Tax Rate (%)',
        })
    )
    
    discount_type = forms.ChoiceField(
        choices=[
            ('none', 'No Discount'),
            ('percentage', 'Percentage (%)'),
            ('fixed', 'Fixed Amount'),
        ],
        required=False,
        initial='none',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'aria-label': 'Discount Type',
        })
    )
    
    discount_value = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=Decimal('0.00'),
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': '0.00',
            'step': '0.01',
            'aria-label': 'Discount Value',
        })
    )

    def clean(self):
        """Validate tax and discount values."""
        cleaned_data = super().clean()
        tax_rate = cleaned_data.get('tax_rate') or Decimal('0.00')
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value') or Decimal('0.00')
        
        if tax_rate < 0 or tax_rate > 100:
            raise ValidationError('Tax rate must be between 0 and 100%.')
        
        if discount_type != 'none' and discount_value < 0:
            raise ValidationError('Discount value cannot be negative.')
        
        return cleaned_data


class InvoicePreviewForm(forms.Form):
    """Final review form before submission."""
    
    payment_terms = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., Payment due within 30 days',
            'aria-label': 'Payment Terms',
        })
    )
    
    notes = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Additional notes for client',
            'rows': 4,
            'aria-label': 'Additional Notes',
        })
    )
    
    send_invoice = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'aria-label': 'Send invoice to client',
        })
    )
    
    save_as_draft = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'aria-label': 'Save as draft',
        })
    )
