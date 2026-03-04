import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class InvoicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "invoices"

    def ready(self):
        # Only import and connect signals when the app is ready to prevent early model loading
        try:
            from . import signals  # noqa
        except ImportError:
            pass
