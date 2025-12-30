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
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[misc]
    name = "invoices"

    def ready(self):
        """
        Application initialization:
        - Register signals
        - Register safe shutdown handlers
        - Warm critical caches (once, cluster-wide)
        - Start keep-alive ONLY in production runtime (once per cluster)
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

        # Per-process flag to prevent re-execution in autoreload
        run_once_flag = "_invoiceflow_startup_ran_per_process"
        if getattr(self.__class__, run_once_flag, False):
            return
        setattr(self.__class__, run_once_flag, True)

        # Only ONE worker in the entire cluster should run these operations
        # Use file-based lock to coordinate across workers
        lock_file = "/tmp/invoiceflow_startup.lock"

        def _acquire_startup_lock():
            """Acquire exclusive lock for startup operations."""
            try:
                lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY, 0o644)
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except (OSError, IOError, BlockingIOError):
                return None

        def delayed_startup_tasks():
            """
            Run startup tasks (cache warmup, keep-alive) exactly ONCE per cluster.
            Delay execution to allow DB, cache, and migrations to settle.
            Must never crash the process.
            """
            time.sleep(3)

            lock_fd = _acquire_startup_lock()
            if lock_fd is None:
                logger.debug("Startup lock held by another worker; skipping startup tasks")
                return

            try:
                # Cache warmup
                try:
                    from invoices.services import CacheWarmingService
                    CacheWarmingService.bump_cache_version()
                    warmed = CacheWarmingService.warm_active_users_cache()
                    logger.info(f"Startup cache warmup completed: {warmed} users")
                except Exception as exc:
                    logger.warning(f"Startup cache warmup failed: {exc}")

                # Keep-alive (production only)
                if os.environ.get("RENDER") and not settings.DEBUG:
                    try:
                        from invoices.keep_alive import start_keep_alive
                        start_keep_alive()
                        logger.info("Keep-alive service started")
                    except Exception as exc:
                        logger.warning(f"Failed to start keep-alive service: {exc}")

            finally:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except Exception:
                    pass

        threading.Thread(
            target=delayed_startup_tasks,
            daemon=True,
            name="invoiceflow-startup",
        ).start()
