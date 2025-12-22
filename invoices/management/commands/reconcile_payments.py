"""
Management command to reconcile payments and process recovery.
Runs automatically to ensure payment state consistency and fraud prevention.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from invoices.models import Payment, PaymentReconciliation
from invoices.paystack_reconciliation_service import (
    get_reconciliation_service,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile payments with Paystack and process recovery attempts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Reconcile payments from last N days (default: 7)",
        )
        parser.add_argument(
            "--status",
            type=str,
            default="pending",
            help="Reconcile payments with specific status (pending/failed/all)",
        )

    def handle(self, *args, **options):
        service = get_reconciliation_service()
        days = options["days"]
        status_filter = options["status"]

        cutoff = timezone.now() - timezone.timedelta(days=days)

        query = Payment.objects.filter(created_at__gte=cutoff)

        if status_filter == "pending":
            query = query.filter(status=Payment.Status.PENDING)
        elif status_filter == "failed":
            query = query.filter(status=Payment.Status.FAILED)

        total = query.count()
        self.stdout.write(f"Reconciling {total} payments...")

        verified_count = 0
        mismatch_count = 0
        failed_count = 0

        for payment in query:
            try:
                reconciliation = service.reconcile_payment(payment)

                if (
                    reconciliation.status
                    == PaymentReconciliation.ReconciliationStatus.VERIFIED
                ):
                    verified_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {payment.reference} verified"
                        )
                    )
                elif (
                    reconciliation.status
                    == PaymentReconciliation.ReconciliationStatus.MISMATCH
                ):
                    mismatch_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ {payment.reference} mismatch - recovery triggered"
                        )
                    )
                else:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ {payment.reference} failed"
                        )
                    )

            except Exception as e:
                failed_count += 1
                logger.error(f"Reconciliation error for {payment.reference}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"✗ {payment.reference} error: {e}")
                )

        # Process recovery attempts
        self.stdout.write("\nProcessing recovery attempts...")
        recovery_stats = service.process_pending_recoveries()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nReconciliation Summary:\n"
                f"  Verified: {verified_count}\n"
                f"  Mismatches: {mismatch_count}\n"
                f"  Failed: {failed_count}\n"
                f"Recovery Summary:\n"
                f"  Attempted: {recovery_stats['attempted']}\n"
                f"  Successful: {recovery_stats['successful']}\n"
                f"  Failed: {recovery_stats['failed']}"
            )
        )
