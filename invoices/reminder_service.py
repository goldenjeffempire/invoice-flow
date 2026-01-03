from django.utils import timezone
from .models import Invoice, ReminderRule, ScheduledReminder, ReminderLog
from .sendgrid_service import SendGridEmailService
import logging

logger = logging.getLogger(__name__)

class ReminderSchedulingService:
    @staticmethod
    def schedule_reminders_for_invoice(invoice: Invoice):
        """Schedules all applicable reminders for a given invoice based on user's active rules."""
        # Use a transaction to ensure atomicity
        from django.db import transaction
        with transaction.atomic():
            # type: ignore[attr-defined]
            ScheduledReminder.objects.filter(
                invoice=invoice, 
                status=ScheduledReminder.Status.PENDING
            ).update(status=ScheduledReminder.Status.CANCELLED)

            if invoice.status == Invoice.Status.PAID:
                return

            rules = ReminderRule.objects.filter(user=invoice.user, is_active=True)
            
            for rule in rules:
                scheduled_time = None
                if rule.trigger_type == ReminderRule.TriggerType.UPON_CREATION:
                    scheduled_time = timezone.now()
                elif rule.trigger_type == ReminderRule.TriggerType.ON_DUE and invoice.due_date:
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(invoice.due_date, timezone.datetime.min.time()))
                elif rule.trigger_type == ReminderRule.TriggerType.BEFORE_DUE and invoice.due_date:
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(invoice.due_date, timezone.datetime.min.time())) - timezone.timedelta(days=rule.days_delta)
                elif rule.trigger_type == ReminderRule.TriggerType.AFTER_DUE and invoice.due_date:
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(invoice.due_date, timezone.datetime.min.time())) + timezone.timedelta(days=rule.days_delta)

                if scheduled_time:
                    # Adjust for weekends if rule specified
                    if rule.exclude_weekends and scheduled_time.weekday() >= 5:
                        days_to_add = (7 - scheduled_time.weekday())
                        scheduled_time += timezone.timedelta(days=days_to_add)

                    # Ensure we don't schedule in the past for future triggers
                    if scheduled_time < timezone.now() and rule.trigger_type != ReminderRule.TriggerType.UPON_CREATION:
                        continue

                    # Use update_or_create to prevent duplicate scheduling
                    # type: ignore[attr-defined]
                    ScheduledReminder.objects.update_or_create(
                        invoice=invoice,
                        rule=rule,
                        status=ScheduledReminder.Status.PENDING,
                        defaults={'scheduled_for': scheduled_time}
                    )

    @classmethod
    def process_pending_reminders(cls):
        """Finds and sends all pending reminders that are due."""
        now = timezone.now()
        # type: ignore[attr-defined]
        pending = ScheduledReminder.objects.filter(
            status=ScheduledReminder.Status.PENDING,
            scheduled_for__lte=now
        ).select_related('invoice', 'rule', 'invoice__user')

        email_service = SendGridEmailService()
        processed_count = 0

        for reminder in pending:
            try:
                invoice = reminder.invoice
                rule = reminder.rule
                
                # Check if invoice is already paid
                if invoice.status == Invoice.Status.PAID:
                    reminder.status = ScheduledReminder.Status.CANCELLED
                    reminder.save()
                    continue

                # Check for existing log to prevent duplicate sends (idempotency)
                if ReminderLog.objects.filter(scheduled_reminder=reminder, success=True).exists():
                    reminder.status = ScheduledReminder.Status.SENT
                    reminder.save()
                    continue

                # Dynamic template rendering
                subject_template = rule.subject_template or "Payment Reminder: Invoice #{invoice_id}"
                body_template = rule.body_template or "Hi {client_name},\n\nThis is a reminder that invoice #{invoice_id} is due on {due_date}."
                
                context = {
                    "invoice_id": str(invoice.invoice_id),
                    "client_name": str(invoice.client_name),
                    "due_date": str(invoice.due_date),
                    "total_amount": f"{invoice.currency} {invoice.total}"
                }
                
                subject = subject_template.format(**context)
                body = body_template.format(**context)
                
                # Append tracking pixel and link wrapping (simplified for now)
                tracking_pixel_url = f"{settings.SITE_URL}/invoices/settings/reminders/pixel/{reminder.id}/"
                body += f"\n\n<img src='{tracking_pixel_url}' width='1' height='1' />"

                # Multi-channel routing
                if rule.channel == 'email':
                    from .async_tasks import AsyncTaskService
                    AsyncTaskService.send_payment_reminder_async(
                        invoice.id, 
                        subject=subject, 
                        body=body,
                        max_retries=rule.max_retries if rule.retry_on_failure else 0,
                        attach_pdf=rule.attach_pdf,
                        reply_to=rule.reply_to_email,
                        sender_name=rule.custom_sender_name
                    )
                elif rule.channel == 'in_app':
                    from .models import InAppNotification
                    InAppNotification.objects.create(
                        user=invoice.user,
                        invoice=invoice,
                        title=subject,
                        message=body
                    )
                
                reminder.status = ScheduledReminder.Status.SENT
                reminder.save()
                
                ReminderLog.objects.create(
                    scheduled_reminder=reminder,
                    invoice=invoice,
                    recipient_email=invoice.client_email,
                    subject=subject,
                    body=body,
                    success=True
                )
                processed_count += 1
            except Exception as e:
                reminder.attempts += 1
                if reminder.attempts >= 3:
                    reminder.status = ScheduledReminder.Status.FAILED
                reminder.error_log = str(e)
                reminder.save()
                logger.error(f"Failed to send reminder {reminder.id}: {e}")
        
        return processed_count
