"""
Custom validators for enhanced form validation with inline feedback.
Provides real-time validation for invoice forms.
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_positive_decimal(value):
    """
    Validate that a decimal value is positive.

    Args:
        value: Decimal value to validate

    Raises:
        ValidationError: If value is not positive
    """
    try:
        decimal_value = Decimal(str(value))
        if decimal_value <= 0:
            raise ValidationError(
                _("%(value)s must be greater than zero."),
                params={"value": value},
                code="invalid_positive",
            )
    except (ValueError, InvalidOperation):
        raise ValidationError(
            _("%(value)s is not a valid number."), params={"value": value}, code="invalid_decimal"
        )


def validate_phone_number(value):
    """
    Validate phone number format (international format supported).
    Accepts: +1234567890, (123) 456-7890, 123-456-7890, etc.

    Args:
        value: Phone number string

    Raises:
        ValidationError: If phone number format is invalid
    """
    if not value:
        return  # Optional field

    # Remove common separators and spaces
    cleaned = re.sub(r"[\s\-\(\)\.]", "", value)

    # Check if it's a valid phone number (10-15 digits, optionally starting with +)
    pattern = r"^\+?[1-9]\d{9,14}$"

    if not re.match(pattern, cleaned):
        raise ValidationError(
            _("Enter a valid phone number (e.g., +1234567890 or (123) 456-7890)."),
            code="invalid_phone",
        )


def validate_tax_rate(value):
    """
    Validate tax rate is within acceptable range (0-100%).

    Args:
        value: Tax rate as decimal

    Raises:
        ValidationError: If tax rate is out of range
    """
    try:
        decimal_value = Decimal(str(value))
        if decimal_value < 0 or decimal_value > 100:
            raise ValidationError(
                _("Tax rate must be between 0 and 100 percent."), code="invalid_tax_rate"
            )
    except (ValueError, InvalidOperation):
        raise ValidationError(_("Tax rate must be a valid number."), code="invalid_decimal")


def validate_invoice_date(value):
    """
    Validate invoice date is not too far in the future.

    Args:
        value: Date object

    Raises:
        ValidationError: If date is more than 1 year in the future
    """
    from datetime import date, timedelta

    if value > date.today() + timedelta(days=365):
        raise ValidationError(
            _("Invoice date cannot be more than 1 year in the future."), code="invalid_future_date"
        )


def validate_bank_account(value):
    """
    Validate bank account number format.
    Basic validation - checks for reasonable length and format.

    Args:
        value: Account number string

    Raises:
        ValidationError: If account number format is invalid
    """
    if not value:
        return  # Optional field

    # Remove spaces and hyphens
    cleaned = re.sub(r"[\s\-]", "", value)

    # Check if it contains only digits and is reasonable length (4-34 chars for IBAN compatibility)
    if not re.match(r"^[A-Z0-9]{4,34}$", cleaned.upper()):
        raise ValidationError(
            _("Enter a valid account number (4-34 alphanumeric characters)."),
            code="invalid_account_number",
        )


def validate_hex_color(value):
    """
    Validate hex color code format (#RRGGBB or #RGB).

    Args:
        value: Hex color string

    Raises:
        ValidationError: If color format is invalid
    """
    if not value:
        return

    pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

    if not re.match(pattern, value):
        raise ValidationError(
            _("Enter a valid hex color code (e.g., #6366f1 or #fff)."), code="invalid_color"
        )


def validate_email_domain(value):
    """
    Enhanced email validation to check for common typos and invalid domains.

    Args:
        value: Email address string

    Raises:
        ValidationError: If email domain appears invalid
    """
    if not value:
        return

    # Common typos in email domains
    common_typos = {
        "gmial.com": "gmail.com",
        "gmai.com": "gmail.com",
        "yahooo.com": "yahoo.com",
        "yaho.com": "yahoo.com",
        "hotmial.com": "hotmail.com",
        "outlok.com": "outlook.com",
    }

    domain = value.split("@")[-1].lower()

    if domain in common_typos:
        raise ValidationError(
            _("Did you mean %(suggestion)s? Please check your email address."),
            params={"suggestion": value.replace(domain, common_typos[domain])},
            code="possible_typo",
        )

    # Check for missing TLD
    if "." not in domain:
        raise ValidationError(
            _("Email address must have a valid domain (e.g., @example.com)."), code="missing_tld"
        )


def validate_payment_reference(value):
    """
    Validate payment reference format.

    Args:
        value: Payment reference string

    Raises:
        ValidationError: If reference is invalid
    """
    if not value:
        raise ValidationError(_("Payment reference is required."), code="missing_reference")

    if len(value) < 3 or len(value) > 255:
        raise ValidationError(
            _("Payment reference must be between 3 and 255 characters."),
            code="invalid_reference_length",
        )

    pattern = r"^[A-Za-z0-9._-]+$"
    if not re.match(pattern, value):
        raise ValidationError(
            _("Payment reference may only contain letters, numbers, dots, underscores, and hyphens."),
            code="invalid_reference_format",
        )


class InvoiceBusinessRules:
    """
    Business rule validators for invoices.
    """

    @staticmethod
    def validate_due_date(invoice_date, due_date):
        """
        Validate due date is after invoice date.

        Args:
            invoice_date: Invoice date
            due_date: Due date

        Raises:
            ValidationError: If due date is before invoice date
        """
        if due_date and invoice_date and due_date < invoice_date:
            raise ValidationError(
                _("Due date must be on or after the invoice date."), code="invalid_due_date"
            )

    @staticmethod
    def validate_line_items(line_items_data):
        """
        Validate line items have required data and valid values.

        Args:
            line_items_data: List of line item dictionaries

        Raises:
            ValidationError: If line items are invalid
        """
        if not line_items_data:
            raise ValidationError(_("At least one line item is required."), code="no_line_items")

        for idx, item in enumerate(line_items_data, 1):
            if not item.get("description"):
                raise ValidationError(
                    _("Line item %(number)d must have a description."),
                    params={"number": idx},
                    code="missing_description",
                )

            try:
                quantity = Decimal(str(item.get("quantity", 0)))
                if quantity <= 0:
                    raise ValidationError(
                        _("Line item %(number)d quantity must be greater than zero."),
                        params={"number": idx},
                        code="invalid_quantity",
                    )
            except (ValueError, InvalidOperation):
                raise ValidationError(
                    _("Line item %(number)d has an invalid quantity."),
                    params={"number": idx},
                    code="invalid_quantity",
                )

            try:
                unit_price = Decimal(str(item.get("unit_price", 0)))
                if unit_price < 0:
                    raise ValidationError(
                        _("Line item %(number)d unit price cannot be negative."),
                        params={"number": idx},
                        code="invalid_price",
                    )
            except (ValueError, InvalidOperation):
                raise ValidationError(
                    _("Line item %(number)d has an invalid unit price."),
                    params={"number": idx},
                    code="invalid_price",
                )
