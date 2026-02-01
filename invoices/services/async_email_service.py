"""
Fully Async Email Service - Completely Isolates External Email Services from Request Flow.

This service ensures that:
1. Email sending NEVER blocks HTTP requests
2. SendGrid failures/timeouts NEVER cause 500 errors
3. All email operations are fire-and-forget with proper logging
4. Email queue with retry logic for reliability
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from invoices.models import Invoice, Payment

logger = logging.getLogger(__name__)


class EmailType(Enum):
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    WELCOME = "welcome"
    INVOICE_READY = "invoice_ready"
    INVOICE_PAID = "invoice_paid"
    PAYMENT_REMINDER = "payment_reminder"


@dataclass
class EmailTask:
    """Represents an email task to be processed asynchronously."""
    email_type: EmailType
    recipient: str
    data: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 2
    created_at: float = field(default_factory=time.time)


class AsyncEmailService:
    """
    Thread-safe async email service with:
    - Background worker thread for email processing
    - Non-blocking queue for email tasks
    - Automatic retry with exponential backoff
    - Complete isolation from request flow
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._email_queue: queue.Queue[EmailTask] = queue.Queue(maxsize=1000)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email_worker")
        self._shutdown = False
        self._worker_started = False
        self._initialized = True
        
        self._start_worker()
    
    def _start_worker(self):
        """Start background worker thread for processing emails."""
        if self._worker_started:
            return
            
        def worker():
            while not self._shutdown:
                try:
                    task = self._email_queue.get(timeout=1.0)
                    if task is None:
                        continue
                    self._process_task(task)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Email worker error: {e}")
        
        worker_thread = threading.Thread(target=worker, daemon=True, name="email_queue_worker")
        worker_thread.start()
        self._worker_started = True
        logger.info("Async email worker started")
    
    def _process_task(self, task: EmailTask):
        """Process a single email task with retry logic."""
        try:
            success = self._send_email(task)
            if not success and task.retry_count < task.max_retries:
                task.retry_count += 1
                backoff = 2 ** task.retry_count
                time.sleep(min(backoff, 10))
                self._email_queue.put(task)
                logger.debug(f"Email retry {task.retry_count} queued for {task.email_type.value}")
            elif not success:
                logger.warning(f"Email failed after {task.max_retries} retries: {task.email_type.value} to {task.recipient}")
            else:
                logger.debug(f"Email sent successfully: {task.email_type.value} to {task.recipient}")
        except Exception as e:
            logger.error(f"Email task processing failed: {e}")
    
    def _send_email(self, task: EmailTask) -> bool:
        """Actually send the email using SendGrid service."""
        try:
            from invoices.sendgrid_service import SendGridEmailService
            service = SendGridEmailService()
            
            if task.email_type == EmailType.VERIFICATION:
                result = service.send_verification_email(
                    user=task.data.get("user"),
                    verification_token=task.data.get("token")
                )
            elif task.email_type == EmailType.PASSWORD_RESET:
                result = service.send_password_reset_email(
                    user=task.data.get("user"),
                    reset_token=task.data.get("token")
                )
            elif task.email_type == EmailType.WELCOME:
                result = service.send_welcome_email(user=task.data.get("user"))
            elif task.email_type == EmailType.INVOICE_READY:
                result = service.send_invoice_ready(
                    invoice=task.data.get("invoice"),
                    recipient_email=task.recipient
                )
            elif task.email_type == EmailType.INVOICE_PAID:
                result = service.send_invoice_paid(
                    invoice=task.data.get("invoice"),
                    recipient_email=task.recipient
                )
            elif task.email_type == EmailType.PAYMENT_REMINDER:
                result = service.send_payment_reminder(
                    invoice=task.data.get("invoice"),
                    recipient_email=task.recipient
                )
            else:
                logger.warning(f"Unknown email type: {task.email_type}")
                return False
            
            if isinstance(result, dict):
                return result.get("status") == "sent"
            return bool(result)
            
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False
    
    def queue_email(self, task: EmailTask) -> bool:
        """
        Queue an email for async sending. Returns immediately.
        Returns True if queued successfully, False if queue is full.
        """
        try:
            self._email_queue.put_nowait(task)
            return True
        except queue.Full:
            logger.warning("Email queue full, dropping email")
            return False
    
    def send_verification_email_async(self, user, token: str) -> bool:
        """Queue verification email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.VERIFICATION,
            recipient=user.email,
            data={"user": user, "token": token}
        )
        return self.queue_email(task)
    
    def send_password_reset_async(self, user, token: str) -> bool:
        """Queue password reset email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.PASSWORD_RESET,
            recipient=user.email,
            data={"user": user, "token": token}
        )
        return self.queue_email(task)
    
    def send_welcome_async(self, user) -> bool:
        """Queue welcome email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.WELCOME,
            recipient=user.email,
            data={"user": user}
        )
        return self.queue_email(task)
    
    def send_invoice_ready_async(self, invoice, recipient: str) -> bool:
        """Queue invoice ready email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.INVOICE_READY,
            recipient=recipient,
            data={"invoice": invoice}
        )
        return self.queue_email(task)
    
    def send_invoice_paid_async(self, invoice, recipient: str) -> bool:
        """Queue invoice paid email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.INVOICE_PAID,
            recipient=recipient,
            data={"invoice": invoice}
        )
        return self.queue_email(task)
    
    def send_reminder_async(self, invoice, recipient: str) -> bool:
        """Queue payment reminder email - returns immediately."""
        task = EmailTask(
            email_type=EmailType.PAYMENT_REMINDER,
            recipient=recipient,
            data={"invoice": invoice}
        )
        return self.queue_email(task)


def get_async_email_service() -> AsyncEmailService:
    """Get the singleton async email service instance."""
    return AsyncEmailService()
