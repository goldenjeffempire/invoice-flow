from django.utils import timezone
from .models import Invoice, ReminderRule, ScheduledReminder, ReminderLog
from .sendgrid_service import SendGridEmailService
import logging

logger = logging.getLogger(__name__)

class ReminderSchedulingService:
    @staticmethod
    def schedule_reminders_for_invoice(invoice: Invoice):
        """Schedules all applicable reminders for a given invoice based on user's active rules."""
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
                # Use update_or_create to prevent duplicate scheduling
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

                # Dynamic template rendering
                subject_template = rule.subject_template or "Payment Reminder: Invoice #{invoice_id}"
                body_template = rule.body_template or "Hi {client_name},\n\nThis is a reminder that invoice #{invoice_id} is due on {due_date}."
                
                context = {
                    "invoice_id": str(invoice.invoice_id),
                    "client_name": str(invoice.client_name),
                    "due_date": str(invoice.due_date),
                    "total_amount": f"{invoice.currency} {invoice.total_amount}"
                }
                
                subject = subject_template.format(**context)
                body = body_template.format(**context)

                email_service.send_invoice_email(
                    invoice=invoice,
                    subject_override=subject,
                    body_override=body
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
