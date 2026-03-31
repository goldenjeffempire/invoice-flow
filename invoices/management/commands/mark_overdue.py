"""
Management command: mark_overdue
Marks all invoices past their due date as 'overdue' if they are in a collectible status.
Run this daily via cron/scheduler.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from invoices.models import Invoice, ActivityLog


class Command(BaseCommand):
    help = "Mark past-due invoices as overdue and create activity logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = timezone.now().date()

        collectible = ["sent", "viewed", "part_paid"]
        qs = Invoice.objects.filter(
            status__in=collectible,
            due_date__lt=today,
        ).select_related("workspace")

        count = qs.count()
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would mark {count} invoice(s) as overdue"
                )
            )
            for inv in qs[:20]:
                self.stdout.write(f"  - {inv.invoice_number} (due {inv.due_date})")
            return

        updated = 0
        activity_logs = []
        for inv in qs:
            inv.status = "overdue"
            updated += 1
            activity_logs.append(
                ActivityLog(
                    workspace=inv.workspace,
                    action="invoice_marked_overdue",
                    resource_type="Invoice",
                    resource_id=str(inv.id),
                    metadata={"invoice_number": inv.invoice_number, "due_date": str(inv.due_date)},
                )
            )

        Invoice.objects.bulk_update(qs, ["status"])
        ActivityLog.objects.bulk_create(activity_logs, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Marked {updated} invoice(s) as overdue"
            )
        )
