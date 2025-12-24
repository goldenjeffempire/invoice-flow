"""
Utility functions for InvoiceFlow.
Modern, type-hinted helpers for common operations.
"""

from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Union
from datetime import datetime, timedelta

T = TypeVar('T')


class APIResponse:
    """Standardized API response builder for consistent JSON responses."""

    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200) -> Dict[str, Any]:
        """Build a successful API response."""
        return {
            "status": "success",
            "code": status_code,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def error(error_code: str, message: str, status_code: int = 400, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Build an error API response."""
        response = {
            "status": "error",
            "code": status_code,
            "error_code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if details:
            response["details"] = details
        return response

    @staticmethod
    def paginated(items: list, total: int, page: int, page_size: int) -> Dict[str, Any]:
        """Build a paginated API response."""
        total_pages = (total + page_size - 1) // page_size
        return {
            "status": "success",
            "data": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class DateHelper:
    """Date/time utilities for invoice operations."""

    @staticmethod
    def add_days(date: datetime, days: int) -> datetime:
        """Add days to a date."""
        return date + timedelta(days=days)

    @staticmethod
    def is_overdue(due_date: datetime, current_date: Optional[datetime] = None) -> bool:
        """Check if invoice is overdue."""
        current = current_date or datetime.now()
        return current > due_date

    @staticmethod
    def days_until_due(due_date: datetime, current_date: Optional[datetime] = None) -> int:
        """Get days remaining until due date."""
        current = current_date or datetime.now()
        delta = due_date - current
        return max(0, delta.days)


class CurrencyHelper:
    """Currency and decimal formatting utilities."""

    CURRENCY_SYMBOLS: Dict[str, str] = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "NGN": "₦",
        "CAD": "C$",
        "AUD": "A$",
    }

    @staticmethod
    def format_amount(amount: Union[Decimal, float, int], currency: str = "USD") -> str:
        """Format amount with currency symbol."""
        symbol = CurrencyHelper.CURRENCY_SYMBOLS.get(currency, currency)
        decimal_amount = Decimal(str(amount))
        return f"{symbol}{decimal_amount:,.2f}"

    @staticmethod
    def validate_amount(amount: Any) -> Optional[Decimal]:
        """Validate and convert to Decimal."""
        try:
            return Decimal(str(amount)).quantize(Decimal("0.01"))
        except (ValueError, TypeError, InvalidOperation) as e:
            import logging
            logging.getLogger(__name__).warning(f"Invalid amount: {e}")
            return None


class ValidationHelper:
    """Data validation utilities."""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Basic phone validation (international format)."""
        import re
        pattern = r"^\+?1?\d{7,15}$"
        return re.match(pattern.replace(" ", ""), phone.replace(" ", "")) is not None

    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        sanitized = str(value).strip()
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized
