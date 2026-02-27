from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import (
        RecurringSchedule, ScheduleExecution, PaymentAttempt,
        RecurringScheduleAuditLog, Invoice, Client, Workspace
    )

logger = logging.getLogger(__name__)


class RecurringBillingService:

    @staticmethod
    def get_schedules_for_workspace(workspace: "Workspace", status: Optional[str] = None) -> List["RecurringSchedule"]:
        from invoices.models import RecurringSchedule
        qs = RecurringSchedule.objects.filter(workspace=workspace).select_related('client')
        if status:
            qs = qs.filter(status=status)
        return list(qs.order_by('-created_at'))

    @staticmethod
    def get_schedule_by_id(schedule_id: int, workspace: "Workspace") -> Optional["RecurringSchedule"]:
        from invoices.models import RecurringSchedule
        try:
            return RecurringSchedule.objects.select_related('client', 'created_by').get(
                id=schedule_id, workspace=workspace
            )
        except RecurringSchedule.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_schedule(
        workspace: "Workspace",
        client: "Client",
        user: "User",
        description: str,
        interval_type: str,
        start_date: date,
        base_amount: Decimal,
        currency: str = "USD",
        end_date: Optional[date] = None,
        custom_interval_days: Optional[int] = None,
        proration_enabled: bool = False,
        anchor_day: Optional[int] = None,
        tax_rate: Decimal = Decimal('0.00'),
        line_items_template: Optional[List[Dict]] = None,
        invoice_terms: str = "",
        invoice_notes: str = "",
        payment_terms_days: int = 30,
        auto_send: bool = True,
        retry_enabled: bool = True,
        max_retry_attempts: int = 3,
        retry_interval_hours: int = 24,
        tz: str = "UTC",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str, Optional["RecurringSchedule"]]:
        from invoices.models import RecurringSchedule, RecurringScheduleAuditLog

        try:
            schedule = RecurringSchedule(
                workspace=workspace,
                client=client,
                created_by=user,
                description=description,
                interval_type=interval_type,
                custom_interval_days=custom_interval_days,
                start_date=start_date,
                end_date=end_date,
                next_run_date=start_date,
                timezone=tz,
                proration_enabled=proration_enabled,
                anchor_day=anchor_day,
                currency=currency,
                base_amount=base_amount,
                tax_rate=tax_rate,
                line_items_template=line_items_template or [],
                invoice_terms=invoice_terms,
                invoice_notes=invoice_notes,
                payment_terms_days=payment_terms_days,
                auto_send=auto_send,
                retry_enabled=retry_enabled,
                max_retry_attempts=max_retry_attempts,
                retry_interval_hours=retry_interval_hours,
            )
            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                user=user,
                action=RecurringScheduleAuditLog.Action.CREATED,
                description=f"Schedule created for {client.name}",
                new_values={
                    'interval_type': interval_type,
                    'base_amount': str(base_amount),
                    'start_date': start_date.isoformat(),
                },
                ip_address=ip_address,
            )

            logger.info(f"Created recurring schedule {schedule.id} for workspace {workspace.id}")
            return True, "Schedule created successfully.", schedule

        except Exception as e:
            logger.exception("Error creating recurring schedule")
            return False, f"Error creating schedule: {str(e)}", None

    @staticmethod
    @transaction.atomic
    def update_schedule(
        schedule: "RecurringSchedule",
        user: "User",
        data: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        from invoices.models import RecurringScheduleAuditLog

        try:
            old_values = {}
            new_values = {}

            updatable_fields = [
                'description', 'interval_type', 'custom_interval_days', 'end_date',
                'proration_enabled', 'anchor_day', 'base_amount', 'tax_rate',
                'line_items_template', 'invoice_terms', 'invoice_notes',
                'payment_terms_days', 'auto_send', 'retry_enabled',
                'max_retry_attempts', 'retry_interval_hours', 'timezone'
            ]

            for field in updatable_fields:
                if field in data:
                    old_val = getattr(schedule, field)
                    new_val = data[field]
                    if old_val != new_val:
                        old_values[field] = str(old_val) if hasattr(old_val, '__str__') else old_val
                        new_values[field] = str(new_val) if hasattr(new_val, '__str__') else new_val
                        setattr(schedule, field, new_val)

            schedule.save()

            if old_values:
                RecurringScheduleAuditLog.objects.create(
                    schedule=schedule,
                    user=user,
                    action=RecurringScheduleAuditLog.Action.UPDATED,
                    description="Schedule settings updated",
                    old_values=old_values,
                    new_values=new_values,
                    ip_address=ip_address,
                )

            logger.info(f"Updated recurring schedule {schedule.id}")
            return True, "Schedule updated successfully."

        except Exception as e:
            logger.exception("Error updating recurring schedule")
            return False, f"Error updating schedule: {str(e)}"

    @staticmethod
    @transaction.atomic
    def pause_schedule(
        schedule: "RecurringSchedule",
        user: "User",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        from invoices.models import RecurringSchedule, RecurringScheduleAuditLog

        if schedule.status != RecurringSchedule.Status.ACTIVE:
            return False, "Only active schedules can be paused."

        try:
            old_status = schedule.status
            schedule.status = RecurringSchedule.Status.PAUSED
            schedule.paused_at = timezone.now()
            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                user=user,
                action=RecurringScheduleAuditLog.Action.PAUSED,
                description="Schedule paused",
                old_values={'status': old_status},
                new_values={'status': schedule.status},
                ip_address=ip_address,
            )

            logger.info(f"Paused recurring schedule {schedule.id}")
            return True, "Schedule paused successfully."

        except Exception as e:
            logger.exception("Error pausing schedule")
            return False, f"Error pausing schedule: {str(e)}"

    @staticmethod
    @transaction.atomic
    def resume_schedule(
        schedule: "RecurringSchedule",
        user: "User",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        from invoices.models import RecurringSchedule, RecurringScheduleAuditLog

        if schedule.status != RecurringSchedule.Status.PAUSED:
            return False, "Only paused schedules can be resumed."

        try:
            old_status = schedule.status
            schedule.status = RecurringSchedule.Status.ACTIVE
            schedule.paused_at = None

            if schedule.next_run_date < timezone.now().date():
                schedule.next_run_date = timezone.now().date()

            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                user=user,
                action=RecurringScheduleAuditLog.Action.RESUMED,
                description="Schedule resumed",
                old_values={'status': old_status},
                new_values={'status': schedule.status},
                ip_address=ip_address,
            )

            logger.info(f"Resumed recurring schedule {schedule.id}")
            return True, "Schedule resumed successfully."

        except Exception as e:
            logger.exception("Error resuming schedule")
            return False, f"Error resuming schedule: {str(e)}"

    @staticmethod
    @transaction.atomic
    def cancel_schedule(
        schedule: "RecurringSchedule",
        user: "User",
        reason: str = "",
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        from invoices.models import RecurringSchedule, RecurringScheduleAuditLog

        if schedule.status in [RecurringSchedule.Status.CANCELLED, RecurringSchedule.Status.COMPLETED]:
            return False, "Schedule is already cancelled or completed."

        try:
            old_status = schedule.status
            schedule.status = RecurringSchedule.Status.CANCELLED
            schedule.cancelled_at = timezone.now()
            schedule.cancellation_reason = reason
            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                user=user,
                action=RecurringScheduleAuditLog.Action.CANCELLED,
                description=f"Schedule cancelled. Reason: {reason}" if reason else "Schedule cancelled",
                old_values={'status': old_status},
                new_values={'status': schedule.status, 'cancellation_reason': reason},
                ip_address=ip_address,
            )

            logger.info(f"Cancelled recurring schedule {schedule.id}")
            return True, "Schedule cancelled successfully."

        except Exception as e:
            logger.exception("Error cancelling schedule")
            return False, f"Error cancelling schedule: {str(e)}"

    @staticmethod
    def get_schedule_executions(schedule: "RecurringSchedule", limit: int = 20) -> List["ScheduleExecution"]:
        return list(schedule.executions.select_related('invoice').order_by('-executed_at')[:limit])

    @staticmethod
    def get_schedule_audit_logs(schedule: "RecurringSchedule", limit: int = 50) -> List["RecurringScheduleAuditLog"]:
        return list(schedule.audit_logs.select_related('user', 'related_invoice').order_by('-timestamp')[:limit])

    @staticmethod
    def get_retry_plan(schedule: "RecurringSchedule") -> Dict[str, Any]:
        if not schedule.retry_enabled:
            return {'enabled': False, 'message': 'Retry is disabled for this schedule'}

        remaining_attempts = schedule.max_retry_attempts - schedule.current_retry_count
        next_delay_hours = schedule.get_retry_delay_hours()

        retry_schedule = []
        current_delay = schedule.retry_interval_hours
        for i in range(remaining_attempts):
            retry_schedule.append({
                'attempt': schedule.current_retry_count + i + 1,
                'delay_hours': int(current_delay),
            })
            current_delay *= float(schedule.retry_backoff_multiplier)

        return {
            'enabled': True,
            'current_retry_count': schedule.current_retry_count,
            'max_attempts': schedule.max_retry_attempts,
            'remaining_attempts': remaining_attempts,
            'next_delay_hours': next_delay_hours,
            'backoff_multiplier': float(schedule.retry_backoff_multiplier),
            'retry_schedule': retry_schedule,
            'next_retry_at': schedule.next_retry_at,
        }


class RecurringInvoiceGenerator:

    @staticmethod
    @transaction.atomic
    def generate_invoice_for_schedule(
        schedule: "RecurringSchedule",
        execution_date: Optional[date] = None,
    ) -> Tuple[bool, str, Optional["Invoice"], Optional["ScheduleExecution"]]:
        from invoices.models import (
            Invoice, LineItem, ScheduleExecution, RecurringScheduleAuditLog, RecurringSchedule
        )

        today = execution_date or timezone.now().date()

        idempotency_key = f"{schedule.id}-{today.isoformat()}"
        existing = ScheduleExecution.objects.filter(
            idempotency_key__startswith=idempotency_key,
            status=ScheduleExecution.Status.SUCCESS
        ).first()
        if existing:
            logger.info(f"Skipping duplicate execution for schedule {schedule.id} on {today}")
            return False, "Invoice already generated for this period.", None, existing

        if schedule.end_date and today > schedule.end_date:
            schedule.status = RecurringSchedule.Status.COMPLETED
            schedule.save()
            return False, "Schedule has ended.", None, None

        period_start = schedule.last_run_date or schedule.start_date
        period_end = today

        try:
            amount = schedule.base_amount
            prorated_amount = None

            if schedule.proration_enabled and schedule.last_run_date:
                expected_days = (schedule.calculate_next_run_date(schedule.last_run_date) - schedule.last_run_date).days
                actual_days = (today - schedule.last_run_date).days
                if actual_days != expected_days and expected_days > 0:
                    proration_factor = Decimal(actual_days) / Decimal(expected_days)
                    prorated_amount = (amount * proration_factor).quantize(Decimal('0.01'))
                    amount = prorated_amount

            tax_amount = (amount * schedule.tax_rate / 100).quantize(Decimal('0.01'))
            total_amount = amount + tax_amount

            invoice_number = f"REC-{schedule.id}-{today.strftime('%Y%m%d')}"
            due_date = today + timedelta(days=schedule.payment_terms_days)

            invoice = Invoice(
                workspace=schedule.workspace,
                client=schedule.client,
                created_by=schedule.created_by,
                invoice_number=invoice_number,
                status=Invoice.Status.DRAFT,
                source_type=Invoice.SourceType.RECURRING,
                source_id=schedule.id,
                issue_date=today,
                due_date=due_date,
                currency=schedule.currency,
                subtotal=amount,
                tax_total=tax_amount,
                total_amount=total_amount,
                amount_due=total_amount,
                default_tax_rate=schedule.tax_rate,
                is_recurring=True,
                terms_conditions=schedule.invoice_terms,
                internal_notes=schedule.invoice_notes,
            )
            invoice.save()

            if schedule.line_items_template:
                for item_data in schedule.line_items_template:
                    LineItem.objects.create(
                        invoice=invoice,
                        description=item_data.get('description', 'Recurring charge'),
                        quantity=Decimal(str(item_data.get('quantity', 1))),
                        unit_price=Decimal(str(item_data.get('unit_price', schedule.base_amount))),
                        tax_rate=schedule.tax_rate,
                    )
            else:
                LineItem.objects.create(
                    invoice=invoice,
                    description=schedule.description,
                    quantity=Decimal('1'),
                    unit_price=amount,
                    tax_rate=schedule.tax_rate,
                )

            invoice.recalculate_totals()

            execution = ScheduleExecution.objects.create(
                schedule=schedule,
                invoice=invoice,
                period_start=period_start,
                period_end=period_end,
                scheduled_date=today,
                status=ScheduleExecution.Status.SUCCESS,
                amount_generated=total_amount,
                prorated_amount=prorated_amount,
            )

            schedule.last_run_date = today
            schedule.next_run_date = schedule.calculate_next_run_date(today)
            schedule.total_invoices_generated += 1
            schedule.total_amount_billed += total_amount
            schedule.current_retry_count = 0
            schedule.next_retry_at = None
            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                action=RecurringScheduleAuditLog.Action.INVOICE_GENERATED,
                description=f"Generated invoice {invoice.invoice_number} for {total_amount} {schedule.currency}",
                related_invoice=invoice,
                related_execution=execution,
                new_values={
                    'invoice_number': invoice.invoice_number,
                    'amount': str(total_amount),
                    'next_run_date': schedule.next_run_date.isoformat(),
                },
            )

            logger.info(f"Generated invoice {invoice.id} for schedule {schedule.id}")
            return True, "Invoice generated successfully.", invoice, execution

        except Exception as e:
            logger.exception(f"Error generating invoice for schedule {schedule.id}")

            ScheduleExecution.objects.create(
                schedule=schedule,
                period_start=period_start,
                period_end=period_end,
                scheduled_date=today,
                status=ScheduleExecution.Status.FAILED,
                error_message=str(e),
            )

            return False, f"Error generating invoice: {str(e)}", None, None

    @staticmethod
    def get_due_schedules(target_date: Optional[date] = None) -> List["RecurringSchedule"]:
        from invoices.models import RecurringSchedule

        target = target_date or timezone.now().date()
        return list(
            RecurringSchedule.objects.filter(
                status=RecurringSchedule.Status.ACTIVE,
                next_run_date__lte=target,
            ).select_related('workspace', 'client', 'created_by')
        )

    @staticmethod
    def process_all_due_schedules(target_date: Optional[date] = None) -> Dict[str, int]:
        schedules = RecurringInvoiceGenerator.get_due_schedules(target_date)

        results = {
            'total': len(schedules),
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }

        for schedule in schedules:
            success, message, invoice, execution = RecurringInvoiceGenerator.generate_invoice_for_schedule(
                schedule, target_date
            )
            if success:
                results['success'] += 1
            elif 'already generated' in message.lower():
                results['skipped'] += 1
            else:
                results['failed'] += 1

        return results


class PaymentRetryService:

    @staticmethod
    @transaction.atomic
    def record_payment_attempt(
        execution: "ScheduleExecution",
        status: str,
        amount: Decimal,
        currency: str,
        error_code: str = "",
        error_message: str = "",
        provider: str = "",
        provider_transaction_id: str = "",
    ) -> "PaymentAttempt":
        from invoices.models import PaymentAttempt, RecurringScheduleAuditLog

        attempt_number = execution.payment_attempts.count() + 1

        attempt = PaymentAttempt.objects.create(
            execution=execution,
            invoice=execution.invoice,
            attempt_number=attempt_number,
            status=status,
            amount=amount,
            currency=currency,
            error_code=error_code,
            error_message=error_message,
            provider=provider,
            provider_transaction_id=provider_transaction_id,
        )

        schedule = execution.schedule

        if status == PaymentAttempt.Status.SUCCESS:
            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                action=RecurringScheduleAuditLog.Action.PAYMENT_SUCCESS,
                description=f"Payment successful: {amount} {currency}",
                related_invoice=execution.invoice,
                related_execution=execution,
                related_attempt=attempt,
            )
            schedule.current_retry_count = 0
            schedule.next_retry_at = None
            schedule.failure_notification_sent = False
            schedule.save()

        elif status == PaymentAttempt.Status.FAILED:
            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                action=RecurringScheduleAuditLog.Action.PAYMENT_FAILED,
                description=f"Payment failed: {error_message}",
                related_invoice=execution.invoice,
                related_execution=execution,
                related_attempt=attempt,
            )

            if schedule.can_retry:
                schedule.current_retry_count += 1
                delay_hours = schedule.get_retry_delay_hours()
                schedule.next_retry_at = timezone.now() + timedelta(hours=delay_hours)
                schedule.save()

                attempt.next_retry_at = schedule.next_retry_at
                attempt.save()

                RecurringScheduleAuditLog.objects.create(
                    schedule=schedule,
                    action=RecurringScheduleAuditLog.Action.RETRY_SCHEDULED,
                    description=f"Retry #{schedule.current_retry_count} scheduled in {delay_hours} hours",
                    related_execution=execution,
                )
            else:
                from invoices.models import RecurringSchedule
                schedule.status = RecurringSchedule.Status.FAILED
                schedule.save()

                RecurringScheduleAuditLog.objects.create(
                    schedule=schedule,
                    action=RecurringScheduleAuditLog.Action.RETRY_EXHAUSTED,
                    description="All retry attempts exhausted. Schedule marked as failed.",
                    related_execution=execution,
                )

        return attempt

    @staticmethod
    def send_failure_notification(schedule: "RecurringSchedule") -> bool:
        from invoices.models import RecurringScheduleAuditLog

        if schedule.failure_notification_sent:
            return False

        try:
            logger.info(f"Sending failure notification for schedule {schedule.id}")

            schedule.failure_notification_sent = True
            schedule.save()

            RecurringScheduleAuditLog.objects.create(
                schedule=schedule,
                action=RecurringScheduleAuditLog.Action.NOTIFICATION_SENT,
                description="Payment failure notification sent to workspace owner",
            )

            return True

        except Exception as e:
            logger.exception(f"Error sending failure notification for schedule {schedule.id}")
            return False
