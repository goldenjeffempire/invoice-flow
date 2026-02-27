"""Enterprise models for audit trails, compliance, and system monitoring."""

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import json


class AuditTrail(models.Model):
    """Complete audit trail for compliance and forensics."""
    
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        VIEW = "view", "View"
        EXPORT = "export", "Export"
        SEND_EMAIL = "send_email", "Send Email"
        PROCESS_PAYMENT = "process_payment", "Process Payment"
        VERIFY_EMAIL = "verify_email", "Verify Email"
        ENABLE_MFA = "enable_mfa", "Enable MFA"
        GENERATE_TOKEN = "generate_token", "Generate Token"
    
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=Action.choices)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255, null=True, blank=True)
    
    changes = models.JSONField(default=dict)  # {field: {old: value, new: value}}
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[("success", "Success"), ("failure", "Failure")], default="success")
    error_message = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["resource_type", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.get_action_display()} - {self.resource_type}"


class SystemEvent(models.Model):
    """System-level events for monitoring and alerting."""
    
    class EventType(models.TextChoices):
        INVOICE_CREATED = "invoice_created", "Invoice Created"
        INVOICE_SENT = "invoice_sent", "Invoice Sent"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        EMAIL_SENT = "email_sent", "Email Sent"
        EMAIL_FAILED = "email_failed", "Email Failed"
        WEBHOOK_DELIVERED = "webhook_delivered", "Webhook Delivered"
        WEBHOOK_FAILED = "webhook_failed", "Webhook Failed"
        SECURITY_ALERT = "security_alert", "Security Alert"
        SYSTEM_ERROR = "system_error", "System Error"
    
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"
    
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    metadata = models.JSONField(default=dict)
    
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_events")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["severity", "-created_at"]),
            models.Index(fields=["acknowledged", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"[{self.get_severity_display()}] {self.title}"
    
    def acknowledge(self, user: settings.AUTH_USER_MODEL) -> None:
        """Mark event as acknowledged."""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()


class SystemMetric(models.Model):
    """System performance metrics for monitoring."""
    
    class MetricType(models.TextChoices):
        API_RESPONSE_TIME = "api_response_time", "API Response Time"
        DATABASE_QUERY_TIME = "db_query_time", "Database Query Time"
        CACHE_HIT_RATE = "cache_hit_rate", "Cache Hit Rate"
        ACTIVE_USERS = "active_users", "Active Users"
        INVOICES_CREATED = "invoices_created", "Invoices Created"
        PAYMENTS_PROCESSED = "payments_processed", "Payments Processed"
        ERROR_RATE = "error_rate", "Error Rate"
        UPTIME = "uptime", "Uptime"
    
    metric_type = models.CharField(max_length=50, choices=MetricType.choices)
    value = models.FloatField()
    unit = models.CharField(max_length=50)
    tags = models.JSONField(default=dict)  # {env: production, region: us-east}
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["metric_type", "-timestamp"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_metric_type_display()}: {self.value}{self.unit}"


class ComplianceLog(models.Model):
    """Log for regulatory compliance (GDPR, PCI-DSS, etc)."""
    
    class ComplianceType(models.TextChoices):
        DATA_REQUEST = "data_request", "Data Request (GDPR)"
        DATA_DELETION = "data_deletion", "Data Deletion (Right to be Forgotten)"
        CONSENT_CHANGE = "consent_change", "Consent Change"
        DATA_BREACH = "data_breach", "Data Breach Notification"
        RETENTION_CLEANUP = "retention_cleanup", "Automated Retention Cleanup"
    
    compliance_type = models.CharField(max_length=50, choices=ComplianceType.choices)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["compliance_type", "-timestamp"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_compliance_type_display()} - {self.timestamp.date()}"
