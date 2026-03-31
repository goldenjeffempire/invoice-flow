"""
InvoiceFlow Signals — Auto-create notifications and activity logs on key events.
"""
from __future__ import annotations
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Payment, Invoice, ActivityLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_received_notification(sender, instance, created, **kwargs):
    """
    When a Payment is saved with status=completed, fire a notification
    and log an activity.
    """
    if not (instance.workspace and instance.invoice):
        return

    try:
        if instance.status == Payment.Status.COMPLETED:
            from .services.notification_service import NotificationService
            NotificationService.notify_payment_received(instance, instance.workspace)

            ActivityLog.objects.get_or_create(
                workspace=instance.workspace,
                action="payment_received",
                resource_type="Payment",
                resource_id=str(instance.id),
                defaults={
                    "metadata": {
                        "amount": str(instance.amount),
                        "invoice_number": instance.invoice.invoice_number if instance.invoice else "",
                        "method": instance.payment_method,
                    }
                },
            )
    except Exception as e:
        logger.debug("payment_received_notification signal error: %s", e)


@receiver(post_save, sender=Invoice)
def invoice_status_changed(sender, instance, created, **kwargs):
    """
    Log activity when invoice is created or becomes overdue.
    """
    if not instance.workspace:
        return

    try:
        if created:
            ActivityLog.objects.get_or_create(
                workspace=instance.workspace,
                action="invoice_created",
                resource_type="Invoice",
                resource_id=str(instance.id),
                defaults={
                    "metadata": {
                        "invoice_number": instance.invoice_number,
                        "client": instance.client.name if instance.client else "",
                        "amount": str(instance.total_amount),
                    }
                },
            )
        elif instance.status == "overdue":
            from .services.notification_service import NotificationService
            NotificationService.notify_invoice_overdue(instance, instance.workspace)
    except Exception as e:
        logger.debug("invoice_status_changed signal error: %s", e)
