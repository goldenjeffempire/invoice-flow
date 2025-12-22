"""
API rate limiting and abuse protection.
Prevents API abuse through request throttling.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class UserBurstThrottle(UserRateThrottle):
    """Allow authenticated users up to 100 requests per hour."""
    scope = 'user_burst'
    THROTTLE_RATES = {
        'user_burst': '100/hour',
    }


class UserSustainedThrottle(UserRateThrottle):
    """Allow authenticated users up to 1000 requests per day."""
    scope = 'user_sustained'
    THROTTLE_RATES = {
        'user_sustained': '1000/day',
    }


class AnonBurstThrottle(AnonRateThrottle):
    """Allow anonymous users up to 20 requests per hour."""
    scope = 'anon_burst'
    THROTTLE_RATES = {
        'anon_burst': '20/hour',
    }


class PaymentThrottle(UserRateThrottle):
    """Allow max 5 payment attempts per hour per user."""
    scope = 'payment'
    THROTTLE_RATES = {
        'payment': '5/hour',
    }


class PublicInvoiceThrottle(AnonRateThrottle):
    """Allow max 30 public invoice views per hour."""
    scope = 'public_invoice'
    THROTTLE_RATES = {
        'public_invoice': '30/hour',
    }
