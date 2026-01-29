from django.utils import timezone
from django.db import transaction
from .models import Invoice, ReminderRule, ScheduledReminder, ReminderLog
from .sendgrid_service import SendGridEmailService
import logging

logger = logging.getLogger(__name__)


class ReminderFailureAlertService:
    """Service for sending failure alerts when reminders fail after all retries."""
    
    @staticmethod
    def send_failure_alert(reminder: ScheduledReminder, error: str):
        """Send failure alert to the invoice owner when a reminder fails."""
        try:
            email_service = SendGridEmailService()
            invoice = reminder.invoice
            user = invoice.user
            
            if not user.email:
                logger.warning(f"Cannot send failure alert for reminder {reminder.id}: no user email")
                return False
            
            subject = f"Reminder Failed: Invoice #{invoice.invoice_id}"
            body = f"""
            <html>
            <body>
            <h2>Payment Reminder Failed</h2>
            <p>We were unable to send a payment reminder for invoice <strong>#{invoice.invoice_id}</strong> after multiple attempts.</p>
            
            <h3>Invoice Details</h3>
            <ul>
                <li><strong>Client:</strong> {invoice.client_name}</li>
                <li><strong>Amount:</strong> {invoice.currency} {invoice.total}</li>
                <li><strong>Due Date:</strong> {invoice.due_date}</li>
            </ul>
            
            <h3>Error Details</h3>
            <p style="color: #dc2626; background: #fef2f2; padding: 12px; border-radius: 6px;">{error}</p>
            
            <h3>What to do next</h3>
            <p>Please check the client's email address and try sending the reminder manually from your dashboard.</p>
            
            <p>Best regards,<br>InvoiceFlow Team</p>
            </body>
            </html>
            """
            
            result = email_service.send_generic_email(
                to_email=user.email,
                subject=subject,
                html_content=body
            )
            
            if result.get("status") == "sent":
                logger.info(f"Failure alert sent to {user.email} for reminder {reminder.id}")
                return True
            else:
                logger.error(f"Failed to send failure alert: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Exception sending failure alert for reminder {reminder.id}: {e}")
            return False

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

            # Prioritize invoice-specific rules, fallback to user-level rules
            rules = invoice.reminder_rules.filter(is_active=True)
            if not rules.exists():
                rules = ReminderRule.objects.filter(user=invoice.user, is_active=True)
            
            for rule in rules:
                scheduled_time = None
                if rule.trigger_type == ReminderRule.TriggerType.UPON_CREATION:
                    scheduled_time = timezone.now()
                elif rule.trigger_type == ReminderRule.TriggerType.ON_DUE and invoice.due_date:
                    due_date = invoice.due_date
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(due_date, timezone.datetime.min.time()))
                elif rule.trigger_type == ReminderRule.TriggerType.BEFORE_DUE and invoice.due_date:
                    due_date = invoice.due_date
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(due_date, timezone.datetime.min.time())) - timezone.timedelta(days=rule.days_delta)
                elif rule.trigger_type == ReminderRule.TriggerType.AFTER_DUE and invoice.due_date:
                    due_date = invoice.due_date
                    scheduled_time = timezone.make_aware(timezone.datetime.combine(due_date, timezone.datetime.min.time())) + timezone.timedelta(days=rule.days_delta)

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
                from django.conf import settings
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
                error_msg = str(e)
                max_attempts = getattr(reminder.rule, 'max_retries', 3) if reminder.rule else 3
                
                if reminder.attempts >= max_attempts:
                    reminder.status = ScheduledReminder.Status.FAILED
                    reminder.error_log = error_msg
                    reminder.save()
                    
                    ReminderLog.objects.create(
                        scheduled_reminder=reminder,
                        invoice=invoice,
                        recipient_email=invoice.client_email,
                        subject="",
                        body="",
                        success=False,
                        error_message=error_msg
                    )
                    
                    ReminderFailureAlertService.send_failure_alert(reminder, error_msg)
                    logger.error(f"Reminder {reminder.id} failed after {reminder.attempts} attempts: {e}")
                else:
                    reminder.error_log = error_msg
                    reminder.save()
                    logger.warning(f"Reminder {reminder.id} attempt {reminder.attempts} failed, will retry: {e}")
        
        logger.info(f"Processed {processed_count} reminders successfully")
        return processed_count
