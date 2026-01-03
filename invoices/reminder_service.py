from django.utils import timezone
from .models import Invoice, ReminderRule, ScheduledReminder
import logging

logger = logging.getLogger(__name__)

class ReminderSchedulingService:
    @staticmethod
    def schedule_reminders_for_invoice(invoice: Invoice):
        """
        Schedules all applicable reminders for a given invoice based on user's active rules.
        """
        # Cancel existing pending reminders for this invoice to avoid duplicates/stale schedules
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

            if scheduled_time and scheduled_time > timezone.now():
                ScheduledReminder.objects.create(
                    invoice=invoice,
                    rule=rule,
                    scheduled_for=scheduled_time,
                    status=ScheduledReminder.Status.PENDING
                )
                logger.info(f"Scheduled reminder {rule.name} for invoice {invoice.invoice_id} at {scheduled_time}")

    @staticmethod
    def process_pending_reminders():
        """
        Finds and sends all pending reminders that are due.
        """
        now = timezone.now()
        pending = ScheduledReminder.objects.filter(
            status=ScheduledReminder.Status.PENDING,
            scheduled_for__lte=now
        ).select_related('invoice', 'rule', 'invoice__user')

        for reminder in pending:
            try:
                # Actual email sending logic would go here, integrating with SendGrid service
                reminder.status = ScheduledReminder.Status.SENT
                reminder.save()
                logger.info(f"Sent reminder {reminder.id} for invoice {reminder.invoice.invoice_id}")
            except Exception as e:
                reminder.attempts += 1
                reminder.status = ScheduledReminder.Status.FAILED
                reminder.error_log = str(e)
                reminder.save()
                logger.error(f"Failed to send reminder {reminder.id}: {e}")
