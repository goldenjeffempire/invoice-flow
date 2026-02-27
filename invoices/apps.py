import atexit
import os
import threading
import time
import logging
import fcntl

from django.apps import AppConfig
from django.conf import settings

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
