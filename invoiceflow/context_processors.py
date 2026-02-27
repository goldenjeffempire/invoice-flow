"""
Custom context processors for InvoiceFlow templates.
"""

from django.conf import settings


def assets_config(request):
    """
    Expose asset configuration to templates for production optimization.
    """
    return {
        "USE_MINIFIED_ASSETS": getattr(settings, "USE_MINIFIED_ASSETS", False),
        "DEBUG": settings.DEBUG,
    }
