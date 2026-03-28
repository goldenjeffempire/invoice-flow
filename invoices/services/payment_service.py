import hashlib
import hmac
import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import Payment, Transaction, Invoice, PaymentAuditLog

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    def verify_paystack_signature(payload, signature):
        secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not secret or not signature:
            return False
        computed_hmac = hmac.new(
            secret.encode('utf-8'),
            payload,
            digestmod=hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(computed_hmac, signature)

    @staticmethod
    @transaction.atomic
    def handle_paystack_webhook(payload_dict):
        from ..models import ProcessedWebhook
        event = payload_dict.get('event')
        data = payload_dict.get('data', {}) or {}

        event_id = str(data.get('id', ''))
        if event_id:
            _, created = ProcessedWebhook.objects.get_or_create(
                event_id=event_id,
                defaults={'event_type': event or ''},
            )
            if not created:
                logger.info("Skipping already-processed webhook event_id=%s event=%s", event_id, event)
                return

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
        if not reference:
            logger.error("Paystack charge.success received with no reference; skipping")
            return
        amount = Decimal(str(data.get('amount', 0))) / 100
        metadata = data.get('metadata') or {}
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
            update_fields = ['amount_paid', 'amount_due', 'status']
            if invoice.amount_due <= 0:
                invoice.status = Invoice.Status.PAID
                invoice.paid_at = timezone.now()
                update_fields.append('paid_at')
            else:
                invoice.status = Invoice.Status.PART_PAID
            invoice.save(update_fields=update_fields)

            Transaction.objects.create(
                workspace=invoice.workspace,
                payment=payment,
                transaction_type=Transaction.Type.PAYMENT,
                amount=amount,
                currency=invoice.currency,
                description=f"Paystack payment for Invoice {invoice.invoice_number}"
            )

    @staticmethod
    def _process_successful_transfer(data):
        from ..models import Payout
        provider_id = data.get('transfer_code') or data.get('reference', '')
        amount = Decimal(str(data.get('amount', 0))) / 100
        try:
            payout = Payout.objects.filter(provider_payout_id=provider_id).first()
            if payout:
                payout.status = Payout.Status.SUCCESS
                payout.save(update_fields=['status'])
                logger.info("Payout %s marked successful (amount=%s)", provider_id, amount)
            else:
                logger.warning("No payout found for provider_payout_id=%s", provider_id)
        except Exception as exc:
            logger.error("Error processing successful transfer %s: %s", provider_id, exc)

    @staticmethod
    def _process_failed_transfer(data):
        from ..models import Payout
        provider_id = data.get('transfer_code') or data.get('reference', '')
        try:
            payout = Payout.objects.filter(provider_payout_id=provider_id).first()
            if payout:
                payout.status = Payout.Status.FAILED
                payout.save(update_fields=['status'])
                logger.warning("Payout %s marked failed", provider_id)
            else:
                logger.warning("No payout found for failed provider_payout_id=%s", provider_id)
        except Exception as exc:
            logger.error("Error processing failed transfer %s: %s", provider_id, exc)

    @staticmethod
    @transaction.atomic
    def record_offline_payment(invoice, amount, method, user, notes="", tip_amount=Decimal('0.00'), ip_address=None):
        amount = Decimal(str(amount))
        tip_amount = Decimal(str(tip_amount))

        payment = Payment.objects.create(
            workspace=invoice.workspace,
            invoice=invoice,
            amount=amount,
            currency=invoice.currency,
            status=Payment.Status.COMPLETED,
            payment_method=method,
            notes=notes,
            completed_at=timezone.now(),
            metadata={"tip_amount": str(tip_amount)} if tip_amount else {},
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
