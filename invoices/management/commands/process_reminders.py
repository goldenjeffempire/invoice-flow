"""
Management command to process pending payment reminders.

Usage:
    python manage.py process_reminders           # Process all pending reminders
    python manage.py process_reminders --dry-run # Show what would be processed
    python manage.py process_reminders --verbose # Show detailed output
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from invoices.reminder_service import ReminderSchedulingService
from invoices.models import ScheduledReminder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending payment reminders that are due to be sent'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending reminders',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of reminders to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        limit = options['limit']

        now = timezone.now()
        
        pending = ScheduledReminder.objects.filter(
            status=ScheduledReminder.Status.PENDING,
            scheduled_for__lte=now
        ).select_related('invoice', 'rule', 'invoice__user')[:limit]

        pending_count = pending.count()

        if pending_count == 0:
            self.stdout.write(self.style.SUCCESS('No pending reminders to process'))
            return

        self.stdout.write(f'Found {pending_count} pending reminder(s)')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No reminders will be sent'))
            for reminder in pending:
                invoice = reminder.invoice
                self.stdout.write(
                    f'  - Invoice #{invoice.invoice_id} to {invoice.client_email} '
                    f'(scheduled for {reminder.scheduled_for})'
                )
            return

        if verbose:
            self.stdout.write('Processing reminders...')

        try:
            processed_count = ReminderSchedulingService.process_pending_reminders()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {processed_count} reminder(s)')
            )
            
            failed = ScheduledReminder.objects.filter(
                status=ScheduledReminder.Status.FAILED,
                updated_at__gte=now
            ).count()
            
            if failed > 0:
                self.stdout.write(
                    self.style.WARNING(f'{failed} reminder(s) failed after all retries')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing reminders: {str(e)}')
            )
            logger.exception('Error in process_reminders command')
            raise
