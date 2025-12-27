import atexit
import os
import threading
import time
import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class InvoicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[misc]
    name = "invoices"

    def ready(self):
        """
        Application initialization:
        - Register signals
        - Register safe shutdown handlers
        - Warm critical caches (once, non-blocking)
        - Start keep-alive ONLY in production runtime
        """

        # ---------------------------------------------------------------------
        # 1. SIGNAL REGISTRATION (idempotent by Django design)
        # ---------------------------------------------------------------------
        try:
            import invoices.signals  # noqa: F401
        except Exception as exc:
            logger.exception("Failed to import invoices.signals: %s", exc)

        # ---------------------------------------------------------------------
        # 2. SAFE SHUTDOWN HANDLERS
        # ---------------------------------------------------------------------
        try:
            from invoices.async_tasks import shutdown_executor
            from invoices.services import CacheWarmingService

            atexit.register(shutdown_executor)
            atexit.register(CacheWarmingService.shutdown_executor)
        except Exception as exc:
            logger.warning("Failed to register shutdown handlers: %s", exc)

        # ---------------------------------------------------------------------
        # 3. ONE-TIME CACHE WARMUP (PER PROCESS)
        # ---------------------------------------------------------------------
        # Prevent multiple executions in autoreload / gunicorn workers
        run_once_flag = "_invoiceflow_startup_ran"

        if getattr(self.__class__, run_once_flag, False):
            return

        setattr(self.__class__, run_once_flag, True)

        def delayed_cache_warmup():
            """
            Delay execution to allow DB, cache, and migrations to settle.
            Must never crash the process.
            """
            time.sleep(3)

            try:
                from invoices.services import CacheWarmingService

                CacheWarmingService.bump_cache_version()
                CacheWarmingService.warm_active_users_cache()
                logger.info("Startup cache warmup completed")
            except Exception as exc:
                logger.warning("Startup cache warmup failed: %s", exc)

        threading.Thread(
            target=delayed_cache_warmup,
            daemon=True,
            name="invoiceflow-cache-warmup",
        ).start()

        # ---------------------------------------------------------------------
        # 4. KEEP-ALIVE (ONLY FOR PRODUCTION PLATFORM RUNTIME)
        # ---------------------------------------------------------------------
        if os.environ.get("RENDER") and not settings.DEBUG:
            try:
                from invoices.keep_alive import start_keep_alive

                start_keep_alive()
                logger.info("Keep-alive service started")
            except Exception as exc:
                logger.warning("Failed to start keep-alive service: %s", exc)
