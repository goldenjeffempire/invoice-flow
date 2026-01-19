"""Background task management for asynchronous operations."""

from django.db import models
from django.conf import settings
from django.utils import timezone
from typing import Any, Dict, Optional, Callable
import json
from datetime import datetime, timedelta


class BackgroundTask(models.Model):
    """Track and manage background tasks."""
    
    class TaskType(models.TextChoices):
        SEND_EMAIL = "send_email", "Send Email"
        PROCESS_PAYMENT = "process_payment", "Process Payment"
        GENERATE_PDF = "generate_pdf", "Generate PDF"
        EXPORT_DATA = "export_data", "Export Data"
        RECONCILE_PAYMENTS = "reconcile_payments", "Reconcile Payments"
        CLEANUP = "cleanup", "Cleanup"
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
    
    task_type = models.CharField(max_length=50, choices=TaskType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="background_tasks", null=True, blank=True)
    
    data = models.JSONField(default=dict)  # Task parameters
    result = models.JSONField(null=True, blank=True)  # Task result
    error_message = models.TextField(blank=True)
    
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_retry = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["task_type", "status"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_task_type_display()} - {self.get_status_display()}"
    
    def start(self):
        """Mark task as started."""
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.attempts += 1
        self.save()
    
    def complete(self, result: Optional[Dict[str, Any]] = None):
        """Mark task as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save()
    
    def fail(self, error: str):
        """Mark task as failed."""
        self.error_message = error
        
        if self.attempts < self.max_attempts:
            # Schedule retry
            self.status = self.Status.RETRYING
            self.next_retry = timezone.now() + timedelta(minutes=5 * self.attempts)
        else:
            self.status = self.Status.FAILED
        
        self.save()
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        if self.status != self.Status.RETRYING:
            return False
        if self.next_retry is None:
            return True
        return timezone.now() >= self.next_retry


class TaskQueue:
    """Queue and manage background tasks."""
    
    @staticmethod
    def enqueue(task_type: str, data: Dict[str, Any] = None, user=None) -> BackgroundTask:
        """Add task to queue."""
        return BackgroundTask.objects.create(
            task_type=task_type,
            data=data or {},
            user=user
        )
    
    @staticmethod
    def get_pending_tasks(limit: int = 10) -> list:
        """Get pending tasks to process."""
        return BackgroundTask.objects.filter(
            status__in=[BackgroundTask.Status.PENDING, BackgroundTask.Status.RETRYING]
        ).order_by('created_at')[:limit]
    
    @staticmethod
    def process_pending_tasks():
        """Process all pending tasks."""
        tasks = TaskQueue.get_pending_tasks()
        for task in tasks:
            TaskQueue.execute_task(task)
    
    @staticmethod
    def execute_task(task: BackgroundTask):
        """Execute a single task."""
        task.start()
        
        try:
            # Route to appropriate handler
            if task.task_type == BackgroundTask.TaskType.SEND_EMAIL:
                TaskQueue._handle_send_email(task)
            elif task.task_type == BackgroundTask.TaskType.GENERATE_PDF:
                TaskQueue._handle_generate_pdf(task)
            elif task.task_type == BackgroundTask.TaskType.EXPORT_DATA:
                TaskQueue._handle_export_data(task)
            
            task.complete()
        except Exception as e:
            task.fail(str(e))
    
    @staticmethod
    def _handle_send_email(task: BackgroundTask):
        """Handle email sending task."""
        from .services import EmailService
        from .models import Invoice
        invoice_id = task.data.get("invoice_id")
        recipient = task.data.get("recipient")
        if invoice_id and recipient:
            invoice = Invoice.objects.get(id=invoice_id)
            EmailService.send_invoice(invoice, recipient)
            task.result = {"status": "sent", "recipient": recipient}
    
    @staticmethod
    def _handle_generate_pdf(task: BackgroundTask):
        """Handle PDF generation task."""
        from .services import PDFService
        from .models import Invoice
        invoice_id = task.data.get("invoice_id")
        if invoice_id:
            invoice = Invoice.objects.get(id=invoice_id)
            pdf_bytes = PDFService.generate_pdf_bytes(invoice)
            task.result = {"status": "generated", "size": len(pdf_bytes)}
    
    @staticmethod
    def _handle_export_data(task: BackgroundTask):
        """Handle data export task."""
        import csv
        import io
        from .models import Invoice
        user_id = task.data.get("user_id")
        if user_id:
            invoices = Invoice.objects.filter(user_id=user_id)
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Invoice ID', 'Client Name', 'Total', 'Status', 'Date'])
            for inv in invoices:
                writer.writerow([inv.invoice_id, inv.client_name, inv.total, inv.status, inv.invoice_date])
            task.result = {"status": "exported", "row_count": invoices.count(), "data": output.getvalue()[:1000]}


class ScheduledTask(models.Model):
    """Scheduled recurring tasks."""
    
    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        HOURLY = "hourly", "Hourly"
    
    name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=50, choices=BackgroundTask.TaskType.choices)
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    
    data = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["next_run"]
    
    def __str__(self) -> str:
        return f"{self.name} - {self.get_frequency_display()}"
    
    def should_run(self) -> bool:
        """Check if task should run."""
        return self.is_active and timezone.now() >= self.next_run
    
    def mark_as_run(self):
        """Mark as run and schedule next run."""
        self.last_run = timezone.now()
        
        if self.frequency == self.Frequency.DAILY:
            self.next_run = self.last_run + timedelta(days=1)
        elif self.frequency == self.Frequency.WEEKLY:
            self.next_run = self.last_run + timedelta(weeks=1)
        elif self.frequency == self.Frequency.MONTHLY:
            self.next_run = self.last_run + timedelta(days=30)
        elif self.frequency == self.Frequency.HOURLY:
            self.next_run = self.last_run + timedelta(hours=1)
        
        self.save()
