"""
Async task processing for InvoiceFlow platform.
Uses ThreadPoolExecutor for background task execution without Redis/Celery dependency.

Features:
- Task tracking with status and metadata
- Retry logic with exponential backoff
- Task statistics for monitoring
- Proper database connection management
- Batch processing for heavy operations
"""

import functools
import logging
import time
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = Lock()
MAX_WORKERS = 4


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    """Result of an async task execution."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None


@dataclass
class TaskStats:
    """Statistics for async task processing."""

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    avg_duration_ms: float = 0.0
    recent_tasks: deque = field(default_factory=lambda: deque(maxlen=100))


class TaskTracker:
    """Thread-safe tracker for async task status and statistics."""

    _instance: Optional["TaskTracker"] = None
    _class_lock = Lock()

    _stats: TaskStats
    _tasks: Dict[str, TaskResult]
    _tasks_lock: Lock
    _initialized: bool

    def __new__(cls):
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._stats = TaskStats()
                    instance._tasks = {}
                    instance._tasks_lock = Lock()
                    instance._initialized = True
                    cls._instance = instance
        return cls._instance

    def register_task(self, task_id: str, task_name: str) -> TaskResult:
        """Register a new task and return its result object."""
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING, started_at=datetime.now())
        with self._tasks_lock:
            self._tasks[task_id] = result
            self._stats.total_submitted += 1
        return result

    def update_task_status(
        self, task_id: str, status: TaskStatus, result: Any = None, error: Optional[str] = None
    ) -> None:
        """Update task status."""
        with self._tasks_lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                task.result = result
                task.error = error

                if status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.now()
                    if task.started_at:
                        task.duration_ms = (
                            task.completed_at - task.started_at
                        ).total_seconds() * 1000
                    self._stats.total_completed += 1
                    self._update_avg_duration(task.duration_ms)
                    self._stats.recent_tasks.append(
                        {
                            "task_id": task_id,
                            "status": "completed",
                            "duration_ms": task.duration_ms,
                            "timestamp": task.completed_at.isoformat(),
                        }
                    )
                elif status == TaskStatus.FAILED:
                    task.completed_at = datetime.now()
                    self._stats.total_failed += 1
                    self._stats.recent_tasks.append(
                        {
                            "task_id": task_id,
                            "status": "failed",
                            "error": error,
                            "timestamp": task.completed_at.isoformat(),
                        }
                    )
                elif status == TaskStatus.RETRYING:
                    task.attempts += 1
                    self._stats.total_retried += 1

    def _update_avg_duration(self, duration_ms: Optional[float]) -> None:
        """Update rolling average duration."""
        if duration_ms is None:
            return
        completed = self._stats.total_completed
        if completed == 1:
            self._stats.avg_duration_ms = duration_ms
        else:
            self._stats.avg_duration_ms = (
                self._stats.avg_duration_ms * (completed - 1) + duration_ms
            ) / completed

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get current task statistics."""
        with self._tasks_lock:
            return {
                "total_submitted": self._stats.total_submitted,
                "total_completed": self._stats.total_completed,
                "total_failed": self._stats.total_failed,
                "total_retried": self._stats.total_retried,
                "success_rate": (
                    self._stats.total_completed / self._stats.total_submitted * 100
                    if self._stats.total_submitted > 0
                    else 0
                ),
                "avg_duration_ms": round(self._stats.avg_duration_ms, 2),
                "pending_tasks": self._stats.total_submitted
                - self._stats.total_completed
                - self._stats.total_failed,
                "recent_tasks": list(self._stats.recent_tasks)[-10:],
            }

    def cleanup_old_tasks(self, max_age_seconds: int = 3600) -> int:
        """Remove completed tasks older than max_age_seconds."""
        now = datetime.now()
        cleaned = 0
        with self._tasks_lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    if (
                        task.completed_at
                        and (now - task.completed_at).total_seconds() > max_age_seconds
                    ):
                        to_remove.append(task_id)
            for task_id in to_remove:
                del self._tasks[task_id]
                cleaned += 1
        return cleaned


def get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool executor."""
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=MAX_WORKERS, thread_name_prefix="async_task"
                )
                logger.info(f"Created ThreadPoolExecutor with {MAX_WORKERS} workers")
    return _executor


def shutdown_executor(wait: bool = True) -> None:
    """Shutdown the executor gracefully."""
    global _executor
    if _executor is not None:
        with _executor_lock:
            if _executor is not None:
                _executor.shutdown(wait=wait)
                _executor = None
                logger.info("ThreadPoolExecutor shutdown complete")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types to retry on
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from django.db import close_old_connections

            task_id = kwargs.pop("_task_id", str(uuid.uuid4())[:8])
            tracker = TaskTracker()

            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    close_old_connections()

                    if attempt > 0:
                        tracker.update_task_status(task_id, TaskStatus.RETRYING)
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        logger.info(
                            f"Retry {attempt}/{max_retries} for task {task_id} after {delay:.1f}s delay"
                        )
                        time.sleep(delay)

                    result = func(*args, **kwargs)
                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Task {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                    else:
                        logger.error(
                            f"Task {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise
                finally:
                    close_old_connections()

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def run_async(func: Callable) -> Callable:
    """Decorator to run a function asynchronously in the thread pool.

    Usage:
        @run_async
        def my_slow_task(arg1, arg2):
            # This runs in background thread
            do_something_slow()

    The decorated function returns a Future that can be used to get the result.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Future:
        executor = get_executor()
        future = executor.submit(func, *args, **kwargs)
        logger.debug(f"Submitted async task: {func.__name__}")
        return future

    return wrapper


class AsyncTaskService:
    """Service for managing async background tasks with tracking and monitoring."""

    @staticmethod
    def submit_task(
        func: Callable,
        *args,
        task_name: Optional[str] = None,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        **kwargs,
    ) -> Future:
        """Submit a function to run asynchronously with tracking.

        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            task_name: Optional name for the task (defaults to function name)
            on_complete: Optional callback when task completes
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Future object that can be used to check status or get result
        """
        from django.db import close_old_connections

        executor = get_executor()
        tracker = TaskTracker()

        task_id = str(uuid.uuid4())[:12]
        name = task_name or func.__name__
        tracker.register_task(task_id, name)

        def task_wrapper():
            try:
                close_old_connections()
                tracker.update_task_status(task_id, TaskStatus.RUNNING)

                result = func(*args, **kwargs)

                tracker.update_task_status(task_id, TaskStatus.COMPLETED, result=result)

                if on_complete:
                    try:
                        task_result_obj = tracker.get_task(task_id)
                        if task_result_obj is not None:
                            on_complete(task_result_obj)
                    except Exception as cb_error:
                        logger.warning(f"Task callback failed: {cb_error}")

                return result
            except Exception as e:
                tracker.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
                logger.exception(f"Async task {name} failed: {e}")
                raise
            finally:
                close_old_connections()

        future = executor.submit(task_wrapper)
        logger.debug(f"Submitted task: {name} (id: {task_id})")
        return future

    @staticmethod
    def get_task_stats() -> Dict[str, Any]:
        """Get current task processing statistics."""
        return TaskTracker().get_stats()

    @staticmethod
    def cleanup_completed_tasks(max_age_seconds: int = 3600) -> int:
        """Clean up old completed tasks from tracker."""
        return TaskTracker().cleanup_old_tasks(max_age_seconds)

    @staticmethod
    def submit_task_with_retry(
        func: Callable,
        *args,
        task_name: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        **kwargs,
    ) -> Future:
        """Submit a function to run asynchronously with retry logic and tracking.

        This integrates retry with proper task status tracking, ensuring that
        RETRYING status is correctly recorded in the tracker.

        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            task_name: Optional name for the task
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            on_complete: Optional callback when task completes
            **kwargs: Keyword arguments to pass to the function
        """
        from django.db import close_old_connections

        executor = get_executor()
        tracker = TaskTracker()

        task_id = str(uuid.uuid4())[:12]
        name = task_name or func.__name__
        tracker.register_task(task_id, name)

        def retry_wrapper():
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    close_old_connections()

                    if attempt == 0:
                        tracker.update_task_status(task_id, TaskStatus.RUNNING)
                    else:
                        tracker.update_task_status(task_id, TaskStatus.RETRYING)
                        delay = min(base_delay * (2.0 ** (attempt - 1)), max_delay)
                        logger.info(
                            f"Retry {attempt}/{max_retries} for task {name} (id: {task_id}) after {delay:.1f}s"
                        )
                        time.sleep(delay)

                    result = func(*args, **kwargs)

                    tracker.update_task_status(task_id, TaskStatus.COMPLETED, result=result)

                    if on_complete:
                        try:
                            task_result_obj = tracker.get_task(task_id)
                            if task_result_obj is not None:
                                on_complete(task_result_obj)
                        except Exception as cb_error:
                            logger.warning(f"Task callback failed: {cb_error}")

                    return result

                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Task {name} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                    else:
                        logger.error(f"Task {name} failed after {max_retries + 1} attempts: {e}")
                        tracker.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
                        raise
                finally:
                    close_old_connections()

            if last_exception:
                tracker.update_task_status(task_id, TaskStatus.FAILED, error=str(last_exception))
                raise last_exception

        future = executor.submit(retry_wrapper)
        logger.debug(f"Submitted task with retry: {name} (id: {task_id})")
        return future

    @staticmethod
    def generate_pdf_async(invoice_id: int) -> Future:
        """Generate PDF for an invoice asynchronously with retry.

        Returns a Future that resolves to the PDF bytes.
        """
        from .models import Invoice
        from .services import PDFService

        def _generate():
            invoice = (
                Invoice.objects.select_related().prefetch_related("line_items").get(id=invoice_id)  # type: ignore[union-attr]
            )
            pdf_bytes = PDFService.generate_pdf_bytes(invoice)
            logger.info(f"Generated PDF for invoice #{invoice.invoice_id} ({len(pdf_bytes)} bytes)")
            return pdf_bytes

        return AsyncTaskService.submit_task_with_retry(
            _generate,
            task_name=f"generate_pdf_{invoice_id}",
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0,
        )

    @staticmethod
    def send_invoice_email_async(invoice_id: int, recipient_email: str) -> Future:
        """Send invoice email asynchronously with retry handling.

        Returns a Future that resolves to the send result dict.
        """
        from .models import Invoice
        from .sendgrid_service import SendGridEmailService

        def _send():
            invoice = Invoice.objects.get(id=invoice_id)  # type: ignore[union-attr]
            service = SendGridEmailService()
            result = service.send_invoice_ready(invoice, recipient_email)

            if result.get("status") == "sent":
                logger.info(
                    f"Invoice #{invoice.invoice_id} sent to {recipient_email}",
                    extra={"invoice_id": invoice_id, "recipient": recipient_email},
                )
            elif result.get("configured") is False:
                logger.warning(
                    f"Email delivery disabled for invoice #{invoice.invoice_id}",
                    extra={"invoice_id": invoice_id},
                )
            elif result.get("status") == "error":
                raise Exception(f"Email send failed: {result.get('message')}")

            return result

        return AsyncTaskService.submit_task_with_retry(
            _send,
            task_name=f"send_email_{invoice_id}",
            max_retries=3,
            base_delay=2.0,
            max_delay=30.0,
        )

    @staticmethod
    def send_payment_reminder_async(invoice_id: int, subject: Optional[str] = None, body: Optional[str] = None, max_retries: int = 3, attach_pdf: bool = True, reply_to: Optional[str] = None, sender_name: Optional[str] = None) -> Future:
        """Send payment reminder email asynchronously with retry.

        Returns a Future that resolves to the send result dict.
        """
        from .models import Invoice
        from .sendgrid_service import SendGridEmailService

        def _send():
            invoice = Invoice.objects.get(id=invoice_id)  # type: ignore[union-attr]
            service = SendGridEmailService()
            result = service.send_invoice_email(
                invoice=invoice, 
                subject_override=subject, 
                body_override=body,
                attach_pdf=attach_pdf,
                reply_to=reply_to,
                sender_name=sender_name
            )

            if result.get("status") == "sent":
                logger.info(f"Payment reminder sent for invoice #{invoice.invoice_id}")
            elif result.get("status") == "error":
                raise Exception(f"Reminder failed: {result.get('message')}")

            return result

        return AsyncTaskService.submit_task_with_retry(
            _send,
            task_name=f"payment_reminder_{invoice_id}",
            max_retries=max_retries,
            base_delay=2.0,
            max_delay=60.0,
        )

    @staticmethod
    def generate_and_email_invoice(invoice_id: int, recipient_email: str) -> Future:
        """Generate PDF and send invoice email as a combined async task.

        This is useful when both operations need to happen together.
        """

        def _generate_and_send():
            from .models import Invoice
            from .sendgrid_service import SendGridEmailService
            from .services import PDFService

            try:
                invoice = (
                    Invoice.objects.select_related()  # type: ignore[union-attr]
                    .prefetch_related("line_items")
                    .get(id=invoice_id)
                )

                pdf_bytes = PDFService.generate_pdf_bytes(invoice)
                logger.info(f"Generated PDF for invoice #{invoice.invoice_id}")

                service = SendGridEmailService()
                result = service.send_invoice_ready(invoice, recipient_email)

                if result.get("status") == "sent":
                    logger.info(
                        f"Invoice #{invoice.invoice_id} generated and sent to {recipient_email}"
                    )

                return {"pdf_generated": True, "pdf_size": len(pdf_bytes), "email_result": result}
            except Exception as e:
                logger.exception(f"Failed to generate and send invoice {invoice_id}: {e}")
                return {
                    "pdf_generated": False,
                    "email_result": {"status": "error", "message": str(e)},
                }

        return AsyncTaskService.submit_task(
            _generate_and_send, task_name=f"generate_and_email_{invoice_id}"
        )

    @staticmethod
    def compute_analytics_async(user_id: int) -> Future:
        """Compute analytics for a user asynchronously.

        Useful for pre-computing analytics during off-peak times.
        """

        def _compute():
            from django.contrib.auth import get_user_model

            from .services import ReportsService
            from .services.reports_service import DateRange

            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                workspace = user.profile.current_workspace if hasattr(user, 'profile') else None
                if not workspace:
                    return {"user_id": user_id, "error": "No workspace found"}
                
                date_range = DateRange.from_preset('this_month')
                dashboard_stats = ReportsService.get_reports_home_data(workspace, date_range)

                logger.info(f"Computed analytics for user {user_id}")
                return {
                    "user_id": user_id,
                    "dashboard_stats": dashboard_stats.get('kpis', {}),
                }
            except Exception as e:
                logger.error(f"Analytics computation failed for user {user_id}: {e}")
                return {"user_id": user_id, "error": str(e)}

        return AsyncTaskService.submit_task(_compute, task_name=f"compute_analytics_{user_id}")

    @staticmethod
    def batch_send_reminders(invoice_ids: List[int]) -> Future:
        """Send payment reminders for multiple invoices in batch.

        Useful for scheduled reminder jobs.
        """

        def _batch_send():
            from .models import Invoice
            from .sendgrid_service import SendGridEmailService

            results = []
            service = SendGridEmailService()

            for invoice_id in invoice_ids:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)  # type: ignore[union-attr]
                    result = service.send_payment_reminder(invoice, invoice.client_email)
                    results.append(
                        {
                            "invoice_id": invoice_id,
                            "status": result.get("status"),
                            "success": result.get("status") == "sent",
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "invoice_id": invoice_id,
                            "status": "error",
                            "error": str(e),
                            "success": False,
                        }
                    )

            sent_count = sum(1 for r in results if r.get("success"))
            logger.info(f"Batch reminders: {sent_count}/{len(invoice_ids)} sent successfully")

            return {
                "total": len(invoice_ids),
                "sent": sent_count,
                "failed": len(invoice_ids) - sent_count,
                "results": results,
            }

        return AsyncTaskService.submit_task(
            _batch_send, task_name=f"batch_reminders_{len(invoice_ids)}_invoices"
        )
