import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from invoices.services.recurring_service import RecurringInvoiceGenerator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process recurring schedules and generate invoices for due schedules"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date for processing (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually generating invoices.',
        )

    def handle(self, *args, **options):
        target_date = None
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {options['date']}"))
                return

        target_date = target_date or timezone.now().date()
        dry_run = options['dry_run']

        self.stdout.write(f"Processing recurring schedules for {target_date}")

        if dry_run:
            schedules = RecurringInvoiceGenerator.get_due_schedules(target_date)
            self.stdout.write(f"[DRY RUN] Found {len(schedules)} schedules due for processing:")
            for schedule in schedules:
                self.stdout.write(
                    f"  - Schedule #{schedule.id}: {schedule.client.name} "
                    f"({schedule.interval_type}) - {schedule.base_amount} {schedule.currency}"
                )
            return

        results = RecurringInvoiceGenerator.process_all_due_schedules(target_date)

        self.stdout.write(self.style.SUCCESS(
            f"Processing complete: "
            f"{results['success']} successful, "
            f"{results['failed']} failed, "
            f"{results['skipped']} skipped "
            f"(of {results['total']} total)"
        ))

        if results['failed'] > 0:
            self.stdout.write(self.style.WARNING(
                f"Check logs for details on {results['failed']} failed generations."
            ))
