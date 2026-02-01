import stripe
import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import Payment, Transaction, Invoice, PaymentAuditLog, Dispute, Payout

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    @transaction.atomic
    def record_offline_payment(invoice, amount, method, user, notes="", tip_amount=Decimal('0.00'), ip_address=None):
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")
        
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
            description=f"Offline payment for Invoice {invoice.invoice_number}"
        )
        
        PaymentAuditLog.objects.create(
            payment=payment,
            user=user,
            action="recorded_offline_payment",
            details={"method": method, "amount": str(amount), "tip": str(tip_amount)},
            ip_address=ip_address
        )
        return payment

    @staticmethod
    def validate_stripe_webhook(payload, sig_header):
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
            return event
        except Exception as e:
            logger.error(f"Stripe Webhook Error: {str(e)}")
            return None

    @staticmethod
    @transaction.atomic
    def handle_stripe_event(event):
        event_type = event['type']
        data = event['data']['object']
        
        if event_type == 'payment_intent.succeeded':
            PaymentService._handle_successful_payment(data, 'stripe')
        elif event_type == 'charge.dispute.created':
            PaymentService._handle_dispute(data, 'stripe')
        elif event_type == 'payout.created':
            PaymentService._handle_payout(data, 'stripe')
            
    @staticmethod
    def _handle_successful_payment(data, provider):
        # Implementation for reconciling with Payment model and Invoice
        pass
