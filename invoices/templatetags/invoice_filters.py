"""
InvoiceFlow Custom Template Filters
"""
from django import template
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from django.utils import timezone

register = template.Library()


@register.filter(name='dict_get')
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key, 0)
    return 0


@register.filter(name='abs_value')
def abs_value(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value


@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='divide')
def divide(value, arg):
    try:
        divisor = Decimal(str(arg))
        if divisor == 0:
            return 0
        return Decimal(str(value)) / divisor
    except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter(name='subtract')
def subtract(value, arg):
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='add_decimal')
def add_decimal(value, arg):
    try:
        return Decimal(str(value)) + Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='percentage')
def percentage(value, total):
    try:
        total_d = Decimal(str(total))
        if total_d == 0:
            return Decimal('0')
        return round(Decimal(str(value)) / total_d * 100, 1)
    except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter(name='format_currency')
def format_currency(value, symbol=''):
    try:
        val = float(value)
        formatted = f"{val:,.2f}"
        if symbol:
            return f"{symbol}{formatted}"
        return formatted
    except (TypeError, ValueError):
        return f"{symbol}0.00" if symbol else "0.00"


@register.filter(name='currency_format')
def currency_format(value, currency='NGN'):
    symbols = {
        'NGN': '₦', 'USD': '$', 'GBP': '£', 'EUR': '€',
        'GHS': 'GH₵', 'KES': 'KSh', 'ZAR': 'R', 'CAD': 'CA$',
        'AUD': 'A$', 'INR': '₹', 'JPY': '¥', 'CNY': '¥',
    }
    sym = symbols.get(currency, currency + ' ')
    try:
        val = float(value)
        return f"{sym}{val:,.2f}"
    except (TypeError, ValueError):
        return f"{sym}0.00"


@register.filter(name='days_since')
def days_since(value):
    """Returns days since the given date."""
    try:
        if isinstance(value, datetime):
            value = value.date()
        today = timezone.now().date()
        delta = today - value
        return delta.days
    except (TypeError, AttributeError):
        return 0


@register.filter(name='days_until')
def days_until(value):
    """Returns days until the given date (negative if past)."""
    try:
        if isinstance(value, datetime):
            value = value.date()
        today = timezone.now().date()
        delta = value - today
        return delta.days
    except (TypeError, AttributeError):
        return 0


@register.filter(name='is_overdue')
def is_overdue(due_date):
    try:
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        return due_date < timezone.now().date()
    except (TypeError, AttributeError):
        return False


@register.filter(name='status_color')
def status_color(status):
    colors = {
        'draft': 'slate',
        'sent': 'violet',
        'viewed': 'blue',
        'part_paid': 'teal',
        'paid': 'green',
        'overdue': 'red',
        'cancelled': 'slate',
        'void': 'slate',
        'active': 'green',
        'paused': 'yellow',
        'failed': 'red',
        'pending': 'yellow',
        'completed': 'green',
        'approved': 'green',
        'rejected': 'red',
        'expired': 'slate',
    }
    return colors.get(str(status).lower(), 'slate')


@register.filter(name='status_badge_class')
def status_badge_class(status):
    classes = {
        'draft': 'badge-slate',
        'sent': 'badge-violet',
        'viewed': 'badge-blue',
        'part_paid': 'badge-teal',
        'paid': 'badge-green',
        'overdue': 'badge-red',
        'cancelled': 'badge-slate',
        'void': 'badge-slate',
        'active': 'badge-green',
        'paused': 'badge-yellow',
        'failed': 'badge-red',
        'pending': 'badge-yellow',
        'completed': 'badge-green',
        'approved': 'badge-green',
        'rejected': 'badge-red',
        'expired': 'badge-slate',
    }
    return classes.get(str(status).lower(), 'badge-slate')


@register.filter(name='truncate_middle')
def truncate_middle(value, length=20):
    try:
        s = str(value)
        if len(s) <= length:
            return s
        half = (length - 3) // 2
        return f"{s[:half]}...{s[-half:]}"
    except Exception:
        return value


@register.filter(name='split_tags')
def split_tags(value, sep=','):
    if not value:
        return []
    return [t.strip() for t in str(value).split(sep) if t.strip()]


@register.filter(name='phone_format')
def phone_format(value):
    if not value:
        return ''
    digits = ''.join(filter(str.isdigit, str(value)))
    if len(digits) == 11 and digits.startswith('0'):
        return f"+234 {digits[1:4]} {digits[4:7]} {digits[7:]}"
    return str(value)


@register.filter(name='get_item')
def get_item(obj, key):
    try:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)
    except Exception:
        return None


@register.filter(name='replace')
def replace_filter(value, arg):
    """Replace characters: usage {{ value|replace:"old,new" }}"""
    try:
        old, new = arg.split(',', 1)
        return str(value).replace(old, new)
    except Exception:
        return value


@register.filter(name='startswith')
def startswith(value, arg):
    return str(value).startswith(str(arg))


@register.filter(name='endswith')
def endswith(value, arg):
    return str(value).endswith(str(arg))


@register.filter(name='contains')
def contains_filter(value, arg):
    return str(arg) in str(value)


@register.filter(name='nbsp')
def nbsp(value):
    """Replace spaces with non-breaking spaces."""
    return str(value).replace(' ', '\u00a0')


@register.filter(name='intcomma')
def intcomma(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.filter(name='floatcomma')
def floatcomma(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return value


@register.simple_tag
def currency_symbol(currency_code):
    symbols = {
        'NGN': '₦', 'USD': '$', 'GBP': '£', 'EUR': '€',
        'GHS': 'GH₵', 'KES': 'KSh', 'ZAR': 'R', 'CAD': 'CA$',
        'AUD': 'A$', 'INR': '₹', 'JPY': '¥', 'CNY': '¥',
    }
    return symbols.get(currency_code, currency_code)


@register.inclusion_tag('components/status_badge.html', takes_context=False)
def status_badge(status, size='sm'):
    return {'status': status, 'size': size}
