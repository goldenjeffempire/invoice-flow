from django.core.management.base import BaseCommand
from invoices.models import Payment
from invoices.paystack_service import PaystackService


class Command(BaseCommand):
    help = "Reconcile pending Paystack payments"

    def handle(self, *args, **kwargs):
        service = PaystackService()

        pending = Payment.objects.filter(
            status=Payment.STATUS_PENDING
        )

        for payment in pending:
            try:
                service.verify_payment(payment.paystack_reference)
            except Exception:
                continue
