import hashlib
import hmac
import json
import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import Payment, Transaction, Invoice, PaymentAuditLog, Dispute, Payout

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    def verify_paystack_signature(payload, signature):
        secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        computed_hmac = hmac.new(
            secret.encode('utf-8'),
            payload,
            digestmod=hashlib.sha512
        ).hexdigest()
        return computed_hmac == signature

    @staticmethod
    @transaction.atomic
    def handle_paystack_webhook(payload_dict):
        event = payload_dict.get('event')
        data = payload_dict.get('data')
        
        if event == 'charge.success':
            PaymentService._process_successful_charge(data)
        elif event == 'transfer.success':
            PaymentService._process_successful_transfer(data)
        elif event == 'transfer.failed':
            PaymentService._process_failed_transfer(data)
            
    @staticmethod
    def _process_successful_charge(data):
        from ..models import Payment, Transaction, Invoice
        reference = data.get('reference')
        amount = Decimal(str(data.get('amount'))) / 100
        metadata = data.get('metadata', {})
        invoice_id = metadata.get('invoice_id')
        
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if not invoice:
            logger.error(f"Invoice {invoice_id} not found for payment {reference}")
            return

        payment, created = Payment.objects.get_or_create(
            provider_reference=reference,
            defaults={
                'workspace': invoice.workspace,
                'invoice': invoice,
                'amount': amount,
                'currency': data.get('currency'),
                'status': Payment.Status.COMPLETED,
                'payment_method': Payment.Method.PAYSTACK,
                'completed_at': timezone.now()
            }
        )
        
        if created:
            invoice.amount_paid += amount
            invoice.amount_due = max(0, invoice.total_amount - invoice.amount_paid)
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
                description=f"Paystack payment for Invoice {invoice.invoice_number}"
            )

    @staticmethod
    @transaction.atomic
    def record_offline_payment(invoice, amount, method, user, notes="", tip_amount=Decimal('0.00'), ip_address=None):
        amount = Decimal(str(amount))
        tip_amount = Decimal(str(tip_amount))
        
        payment = Payment.objects.create(
            workspace=invoice.workspace,
            invoice=invoice,
            amount=amount,
            tip_amount=tip_amount,
            currency=invoice.currency,
            status=Payment.Status.COMPLETED,
            payment_method=method,
            notes=notes,
            completed_at=timezone.now()
        )
        
        invoice.amount_paid += amount
        invoice.amount_due = max(0, invoice.total_amount - invoice.amount_paid)
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
            amount=amount + tip_amount,
            currency=invoice.currency,
            description=f"Offline payment ({method}) for Invoice {invoice.invoice_number}"
        )
        
        PaymentAuditLog.objects.create(
            payment=payment,
            user=user,
            action="offline_payment_recorded",
            details={"method": method, "amount": str(amount), "tip": str(tip_amount)},
            ip_address=ip_address
        )
        return payment
