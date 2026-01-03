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

logger = logging.getLogger(__name__)

def get_models():
    Invoice = apps.get_model('invoices', 'Invoice')
    LineItem = apps.get_model('invoices', 'LineItem')
    User = apps.get_model('auth', 'User')
    return Invoice, LineItem, User

# =============================================================================
# USER SIGNALS
# =============================================================================

@receiver(post_save, sender='auth.User')
def send_welcome_email_on_signup(sender, instance, created: bool, **kwargs):
    """
    Send welcome email only once for real user signups.
    """
    if not created:
        return

    if instance.is_staff or instance.is_superuser:
        return

    if not instance.email:
        return

    try:
        from .sendgrid_service import SendGridEmailService
        service = SendGridEmailService()
        result = service.send_welcome_email(instance)

        if result.get("status") == "sent":
            logger.info("Welcome email sent to %s", instance.email)
        elif result.get("configured") is False:
            logger.info("Email disabled; welcome email skipped")
        else:
            logger.error("Welcome email failed: %s", result.get("message"))

    except Exception as exc:
        logger.exception("Welcome email signal failed: %s", exc)


@receiver(user_logged_in)
def warm_cache_on_login(sender, request, user, **kwargs):
    """
    Pre-warm analytics cache after successful login.
    Must NEVER block authentication.
    """
    try:
        from .services import CacheWarmingService

        CacheWarmingService.warm_user_cache_async(user)
        logger.debug("Cache warming triggered for user %s", user.id)

    except Exception as exc:
        logger.warning("Cache warming failed on login: %s", exc)


# =============================================================================
# INVOICE SIGNALS
# =============================================================================

@receiver(pre_save, sender='invoices.Invoice')
def track_invoice_status_change(sender, instance, **kwargs):
    """
    Store previous status to detect state transitions.
    """
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
    """Trigger reminder scheduling whenever an invoice is created or updated."""
    from .reminder_service import ReminderSchedulingService
    ReminderSchedulingService.schedule_reminders_for_invoice(instance)


@receiver(post_save, sender='invoices.Invoice')
def handle_invoice_paid(sender, instance, created: bool, **kwargs):
    """
    Send email when invoice transitions to PAID.
    """
    if created:
        return

    previous_status = getattr(instance, "_previous_status", None)

    if previous_status == instance.status:
        return

    if instance.status != "paid":
        return

    if not instance.client_email:
        return

    try:
        from .sendgrid_service import SendGridEmailService
        service = SendGridEmailService()
        result = service.send_invoice_paid(instance, instance.client_email)

        if result.get("status") == "sent":
            logger.info("Invoice paid email sent: %s", instance.invoice_id)
        elif result.get("configured") is False:
            logger.info("Email disabled; invoice paid email skipped")
        else:
            logger.error("Invoice paid email failed: %s", result.get("message"))

    except Exception as exc:
        logger.exception("Invoice paid email handler failed: %s", exc)


# =============================================================================
# CACHE INVALIDATION
# =============================================================================

@receiver(post_delete, sender='invoices.Invoice')
def invalidate_cache_on_invoice_delete(
    sender, instance, **kwargs: Any
) -> None:
    """
    Invalidate analytics cache when an invoice is deleted.
    """
    try:
        from .services import AnalyticsService

        AnalyticsService.invalidate_user_cache(instance.user_id)
        logger.debug("Cache invalidated for user %s (invoice delete)", instance.user_id)

    except Exception as exc:
        logger.warning("Cache invalidation failed (invoice delete): %s", exc)


@receiver(post_delete, sender='invoices.LineItem')
def invalidate_cache_on_lineitem_delete(
    sender, instance, **kwargs: Any
) -> None:
    """
    Invalidate analytics cache when a line item is deleted.
    """
    try:
        if instance.invoice_id:
            from .services import AnalyticsService

            AnalyticsService.invalidate_user_cache(instance.invoice.user_id)
            logger.debug(
                "Cache invalidated for user %s (line item delete)",
                instance.invoice.user_id,
            )
    except Exception as exc:
        logger.warning("Cache invalidation failed (line item delete): %s", exc)
