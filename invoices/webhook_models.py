"""Webhook models and management for event-driven architecture."""

from django.db import models
from django.conf import settings
import hashlib
import hmac
import json


class Webhook(models.Model):
    """Webhook endpoint configuration."""
    
    class Event(models.TextChoices):
        INVOICE_CREATED = "invoice.created", "Invoice Created"
        INVOICE_UPDATED = "invoice.updated", "Invoice Updated"
        INVOICE_DELETED = "invoice.deleted", "Invoice Deleted"
        PAYMENT_RECEIVED = "payment.received", "Payment Received"
        INVOICE_OVERDUE = "invoice.overdue", "Invoice Overdue"
        INVOICE_PAID = "invoice.paid", "Invoice Paid"
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField()
    events = models.JSONField(default=list)  # List of Event choices
    secret = models.CharField(max_length=255, blank=True)  # For signing payloads
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_active"])]
    
    def __str__(self) -> str:
        return f"Webhook for {self.user} - {self.url}"
    
    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()


class WebhookEvent(models.Model):
    """Record of webhook delivery attempts."""
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
    
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, choices=Webhook.Event.choices)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempts = models.IntegerField(default=0)
    next_retry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.event_type} - {self.status}"
