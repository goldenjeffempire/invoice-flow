"""
Signal handlers for InvoiceFlow:
- Emails
- Cache invalidation
- Cache warming
"""

import logging
from typing import Any, Type

from django.contrib.auth import user_logged_in
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# USER SIGNALS
# =============================================================================

@receiver(post_save, sender='auth.User')
def send_welcome_email_on_signup(sender, instance, created: bool, **kwargs):
    if not created or instance.is_staff or instance.is_superuser or not instance.email:
        return
    try:
        from .sendgrid_service import SendGridEmailService
        service = SendGridEmailService()
        service.send_welcome_email(instance)
    except Exception as exc:
        logger.exception("Welcome email signal failed: %s", exc)

@receiver(user_logged_in)
def warm_cache_on_login(sender, request, user, **kwargs):
    try:
        from .services import CacheWarmingService
        CacheWarmingService.warm_user_cache_async(user)
    except Exception as exc:
        logger.warning("Cache warming failed on login: %s", exc)

# =============================================================================
# INVOICE SIGNALS
# =============================================================================

@receiver(pre_save, sender='invoices.Invoice')
def track_invoice_status_change(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        Invoice = apps.get_model('invoices', 'Invoice')
        previous = Invoice.objects.only("status").get(pk=instance.pk)
        instance._previous_status = previous.status
    except Exception:
        instance._previous_status = None

@receiver(post_save, sender='invoices.Invoice')
def handle_invoice_save(sender, instance, created: bool, **kwargs):
    from .reminder_service import ReminderSchedulingService
    ReminderSchedulingService.schedule_reminders_for_invoice(instance)

@receiver(post_save, sender='invoices.Invoice')
def handle_invoice_paid(sender, instance, created: bool, **kwargs):
    if created or getattr(instance, "_previous_status", None) == instance.status or instance.status != "paid" or not instance.client_email:
        return
    try:
        from .sendgrid_service import SendGridEmailService
        service = SendGridEmailService()
        service.send_invoice_paid(instance, instance.client_email)
    except Exception as exc:
        logger.exception("Invoice paid email handler failed: %s", exc)

# =============================================================================
# CACHE INVALIDATION
# =============================================================================

@receiver(post_delete, sender='invoices.Invoice')
def invalidate_cache_on_invoice_delete(sender, instance, **kwargs):
    try:
        from .services import ReportsService
        ReportsService.invalidate_workspace_cache(instance.workspace_id)
    except Exception as exc:
        logger.warning("Cache invalidation failed (invoice delete): %s", exc)

@receiver(post_delete, sender='invoices.LineItem')
def invalidate_cache_on_lineitem_delete(sender, instance, **kwargs):
    try:
        if instance.invoice_id and instance.invoice.workspace_id:
            from .services import ReportsService
            ReportsService.invalidate_workspace_cache(instance.invoice.workspace_id)
    except Exception as exc:
        logger.warning("Cache invalidation failed (line item delete): %s", exc)
