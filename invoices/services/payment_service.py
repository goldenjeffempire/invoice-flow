from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from ..models import Payment, Transaction, Invoice, PaymentAuditLog

class PaymentService:
    @staticmethod
    @transaction.atomic
    def record_offline_payment(invoice, amount, method, user, notes=""):
        payment = Payment.objects.create(
            workspace=invoice.workspace,
            invoice=invoice,
            amount=amount,
            currency=invoice.currency,
            status=Payment.Status.COMPLETED,
            payment_method=method,
            notes=notes,
            completed_at=timezone.now()
        )
        
        # Update invoice status
        invoice.amount_paid += amount
        invoice.amount_due -= amount
        if invoice.amount_due <= 0:
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
        else:
            invoice.status = Invoice.Status.PART_PAID
        invoice.save()
        
        Transaction.objects.create(
            workspace=invoice.workspace,
            payment=payment,
            transaction_type=Transaction.Type.PAYMENT,
            amount=amount,
            currency=invoice.currency,
            description=f"Offline payment for Invoice {invoice.invoice_number}"
        )
        
        PaymentAuditLog.objects.create(
            payment=payment,
            user=user,
            action="recorded_offline_payment",
            details={"method": method, "amount": str(amount)}
        )
        return payment

    @staticmethod
    def process_webhook(provider, payload):
        # Implementation for Stripe/Paystack webhook reconciliation
        pass
