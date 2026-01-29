"""
Domain-Specific Validation Schemas

Centralized validation rules per domain object.
Server is authoritative; client mirrors constraints for UX.

Each schema provides:
- Field constraints (min/max length, format, required)
- Business rules
- Validation methods that return standardized errors
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from .errors import FieldError, ValidationError, ErrorCode


@dataclass
class FieldConstraints:
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    pattern: Optional[str] = None
    pattern_message: Optional[str] = None
    choices: Optional[List[str]] = None


class BaseSchema:
    FIELDS: Dict[str, FieldConstraints] = {}
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Tuple[bool, List[FieldError]]:
        errors = []
        
        for field_name, constraints in cls.FIELDS.items():
            value = data.get(field_name)
            field_errors = cls._validate_field(field_name, value, constraints)
            errors.extend(field_errors)
        
        business_errors = cls.validate_business_rules(data)
        errors.extend(business_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_field(
        cls,
        field_name: str,
        value: Any,
        constraints: FieldConstraints,
    ) -> List[FieldError]:
        errors = []
        
        if constraints.required and (value is None or value == ""):
            errors.append(FieldError(
                field=field_name,
                code=ErrorCode.FIELD_REQUIRED.value,
                message=f"{cls._humanize(field_name)} is required.",
            ))
            return errors
        
        if value is None or value == "":
            return errors
        
        if isinstance(value, str):
            if constraints.min_length and len(value) < constraints.min_length:
                errors.append(FieldError(
                    field=field_name,
                    code=ErrorCode.FIELD_TOO_SHORT.value,
                    message=f"{cls._humanize(field_name)} must be at least {constraints.min_length} characters.",
                ))
            
            if constraints.max_length and len(value) > constraints.max_length:
                errors.append(FieldError(
                    field=field_name,
                    code=ErrorCode.FIELD_TOO_LONG.value,
                    message=f"{cls._humanize(field_name)} must be at most {constraints.max_length} characters.",
                ))
            
            if constraints.pattern and not re.match(constraints.pattern, value):
                errors.append(FieldError(
                    field=field_name,
                    code=ErrorCode.FIELD_INVALID_FORMAT.value,
                    message=constraints.pattern_message or f"{cls._humanize(field_name)} format is invalid.",
                ))
        
        if constraints.min_value is not None or constraints.max_value is not None:
            try:
                decimal_value = Decimal(str(value))
                
                if constraints.min_value is not None and decimal_value < constraints.min_value:
                    errors.append(FieldError(
                        field=field_name,
                        code=ErrorCode.FIELD_OUT_OF_RANGE.value,
                        message=f"{cls._humanize(field_name)} must be at least {constraints.min_value}.",
                    ))
                
                if constraints.max_value is not None and decimal_value > constraints.max_value:
                    errors.append(FieldError(
                        field=field_name,
                        code=ErrorCode.FIELD_OUT_OF_RANGE.value,
                        message=f"{cls._humanize(field_name)} must be at most {constraints.max_value}.",
                    ))
            except (InvalidOperation, ValueError):
                errors.append(FieldError(
                    field=field_name,
                    code=ErrorCode.FIELD_INVALID.value,
                    message=f"{cls._humanize(field_name)} must be a valid number.",
                ))
        
        if constraints.choices and value not in constraints.choices:
            errors.append(FieldError(
                field=field_name,
                code=ErrorCode.FIELD_INVALID.value,
                message=f"{cls._humanize(field_name)} must be one of: {', '.join(constraints.choices)}.",
            ))
        
        return errors
    
    @classmethod
    def validate_business_rules(cls, data: Dict[str, Any]) -> List[FieldError]:
        return []
    
    @staticmethod
    def _humanize(field_name: str) -> str:
        return field_name.replace("_", " ").title()
    
    @classmethod
    def raise_if_invalid(cls, data: Dict[str, Any]) -> None:
        is_valid, errors = cls.validate(data)
        if not is_valid:
            raise ValidationError(
                message="Validation failed. Please check your input.",
                fields=errors,
            )


class LineItemSchema(BaseSchema):
    FIELDS = {
        "description": FieldConstraints(
            required=True,
            min_length=1,
            max_length=500,
        ),
        "quantity": FieldConstraints(
            required=True,
            min_value=Decimal("0.01"),
            max_value=Decimal("999999.99"),
        ),
        "unit_price": FieldConstraints(
            required=True,
            min_value=Decimal("0"),
            max_value=Decimal("99999999.99"),
        ),
    }


class ClientSchema(BaseSchema):
    FIELDS = {
        "client_name": FieldConstraints(
            required=True,
            min_length=1,
            max_length=200,
        ),
        "client_email": FieldConstraints(
            required=True,
            max_length=254,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            pattern_message="Please enter a valid email address.",
        ),
        "client_phone": FieldConstraints(
            required=False,
            max_length=30,
            pattern=r"^\+?[\d\s\-\(\)]+$",
            pattern_message="Please enter a valid phone number.",
        ),
        "client_address": FieldConstraints(
            required=False,
            max_length=500,
        ),
    }


class InvoiceSchema(BaseSchema):
    CURRENCY_CHOICES = ["USD", "EUR", "GBP", "NGN", "CAD", "AUD", "INR", "JPY", "ZAR", "KES", "GHS"]
    STATUS_CHOICES = ["unpaid", "paid", "overdue"]
    
    FIELDS = {
        "business_name": FieldConstraints(
            required=True,
            min_length=1,
            max_length=200,
        ),
        "business_email": FieldConstraints(
            required=True,
            max_length=254,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            pattern_message="Please enter a valid email address.",
        ),
        "business_phone": FieldConstraints(
            required=False,
            max_length=30,
        ),
        "business_address": FieldConstraints(
            required=False,
            max_length=500,
        ),
        "client_name": FieldConstraints(
            required=True,
            min_length=1,
            max_length=200,
        ),
        "client_email": FieldConstraints(
            required=True,
            max_length=254,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            pattern_message="Please enter a valid email address.",
        ),
        "client_phone": FieldConstraints(
            required=False,
            max_length=30,
        ),
        "client_address": FieldConstraints(
            required=False,
            max_length=500,
        ),
        "tax_rate": FieldConstraints(
            required=False,
            min_value=Decimal("0"),
            max_value=Decimal("100"),
        ),
        "notes": FieldConstraints(
            required=False,
            max_length=2000,
        ),
    }
    
    @classmethod
    def validate_business_rules(cls, data: Dict[str, Any]) -> List[FieldError]:
        errors = []
        
        invoice_date = data.get("invoice_date")
        due_date = data.get("due_date")
        
        if invoice_date and due_date:
            if isinstance(invoice_date, str):
                try:
                    invoice_date = date.fromisoformat(invoice_date)
                except ValueError:
                    pass
            if isinstance(due_date, str):
                try:
                    due_date = date.fromisoformat(due_date)
                except ValueError:
                    pass
            
            if isinstance(invoice_date, date) and isinstance(due_date, date):
                if due_date < invoice_date:
                    errors.append(FieldError(
                        field="due_date",
                        code=ErrorCode.BUSINESS_RULE_VIOLATION.value,
                        message="Due date must be on or after the invoice date.",
                    ))
        
        if invoice_date:
            if isinstance(invoice_date, str):
                try:
                    invoice_date = date.fromisoformat(invoice_date)
                except ValueError:
                    pass
            
            if isinstance(invoice_date, date):
                max_future = date.today() + timedelta(days=365)
                if invoice_date > max_future:
                    errors.append(FieldError(
                        field="invoice_date",
                        code=ErrorCode.BUSINESS_RULE_VIOLATION.value,
                        message="Invoice date cannot be more than 1 year in the future.",
                    ))
        
        line_items = data.get("line_items", [])
        if not line_items:
            errors.append(FieldError(
                field="line_items",
                code=ErrorCode.FIELD_REQUIRED.value,
                message="At least one line item is required.",
            ))
        else:
            for i, item in enumerate(line_items):
                _, item_errors = LineItemSchema.validate(item)
                for error in item_errors:
                    error.field = f"line_items.{i}.{error.field}"
                errors.extend(item_errors)
        
        return errors


class PaymentSchema(BaseSchema):
    PAYMENT_METHOD_CHOICES = ["card", "bank_transfer", "mobile_money", "ussd"]
    STATUS_CHOICES = ["pending", "success", "failed", "refunded"]
    
    FIELDS = {
        "amount": FieldConstraints(
            required=True,
            min_value=Decimal("0.01"),
            max_value=Decimal("99999999.99"),
        ),
        "reference": FieldConstraints(
            required=True,
            min_length=3,
            max_length=255,
            pattern=r"^[A-Za-z0-9._-]+$",
            pattern_message="Reference may only contain letters, numbers, dots, underscores, and hyphens.",
        ),
        "payment_method": FieldConstraints(
            required=False,
            choices=["card", "bank_transfer", "mobile_money", "ussd"],
        ),
    }
    
    @classmethod
    def validate_business_rules(cls, data: Dict[str, Any]) -> List[FieldError]:
        errors = []
        
        invoice_id = data.get("invoice_id")
        if not invoice_id:
            errors.append(FieldError(
                field="invoice_id",
                code=ErrorCode.FIELD_REQUIRED.value,
                message="Invoice ID is required for payment.",
            ))
        
        return errors


class RecurringSchema(BaseSchema):
    FREQUENCY_CHOICES = ["weekly", "biweekly", "monthly", "quarterly", "yearly"]
    
    FIELDS = {
        "frequency": FieldConstraints(
            required=True,
            choices=["weekly", "biweekly", "monthly", "quarterly", "yearly"],
        ),
        "max_occurrences": FieldConstraints(
            required=False,
            min_value=Decimal("1"),
            max_value=Decimal("999"),
        ),
        "days_before_due": FieldConstraints(
            required=False,
            min_value=Decimal("0"),
            max_value=Decimal("90"),
        ),
    }
    
    @classmethod
    def validate_business_rules(cls, data: Dict[str, Any]) -> List[FieldError]:
        errors = []
        
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if start_date and end_date:
            if isinstance(start_date, str):
                try:
                    start_date = date.fromisoformat(start_date)
                except ValueError:
                    pass
            if isinstance(end_date, str):
                try:
                    end_date = date.fromisoformat(end_date)
                except ValueError:
                    pass
            
            if isinstance(start_date, date) and isinstance(end_date, date):
                if end_date < start_date:
                    errors.append(FieldError(
                        field="end_date",
                        code=ErrorCode.BUSINESS_RULE_VIOLATION.value,
                        message="End date must be on or after the start date.",
                    ))
        
        return errors


VALIDATION_CONSTRAINTS = {
    "invoice": {
        "business_name": {"required": True, "max_length": 200},
        "business_email": {"required": True, "max_length": 254, "type": "email"},
        "business_phone": {"required": False, "max_length": 30, "type": "phone"},
        "business_address": {"required": False, "max_length": 500},
        "client_name": {"required": True, "max_length": 200},
        "client_email": {"required": True, "max_length": 254, "type": "email"},
        "client_phone": {"required": False, "max_length": 30, "type": "phone"},
        "client_address": {"required": False, "max_length": 500},
        "tax_rate": {"required": False, "min": 0, "max": 100, "type": "decimal"},
        "notes": {"required": False, "max_length": 2000},
        "currency": {"required": True, "choices": InvoiceSchema.CURRENCY_CHOICES},
    },
    "line_item": {
        "description": {"required": True, "min_length": 1, "max_length": 500},
        "quantity": {"required": True, "min": 0.01, "max": 999999.99, "type": "decimal"},
        "unit_price": {"required": True, "min": 0, "max": 99999999.99, "type": "decimal"},
    },
    "client": {
        "client_name": {"required": True, "max_length": 200},
        "client_email": {"required": True, "max_length": 254, "type": "email"},
        "client_phone": {"required": False, "max_length": 30, "type": "phone"},
        "client_address": {"required": False, "max_length": 500},
    },
    "payment": {
        "amount": {"required": True, "min": 0.01, "type": "decimal"},
        "reference": {"required": True, "min_length": 3, "max_length": 255},
    },
    "recurring": {
        "frequency": {"required": True, "choices": RecurringSchema.FREQUENCY_CHOICES},
        "max_occurrences": {"required": False, "min": 1, "max": 999, "type": "integer"},
        "days_before_due": {"required": False, "min": 0, "max": 90, "type": "integer"},
    },
}


def get_validation_constraints() -> Dict[str, Any]:
    return VALIDATION_CONSTRAINTS
