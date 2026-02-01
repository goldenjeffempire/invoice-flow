from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from ..models import Invoice, LineItem, InvoiceActivity

class InvoiceService:
    @staticmethod
    @transaction.atomic
    def create_invoice(workspace, user, data, items):
        if not data.get('invoice_number'):
            last_invoice = Invoice.objects.filter(workspace=workspace).order_by('-id').first()
            next_num = (last_invoice.id + 1) if last_invoice else 1
            data['invoice_number'] = f"INV-{timezone.now().year}-{next_num:04d}"

        invoice = Invoice.objects.create(
            workspace=workspace,
            **data
        )

        subtotal = Decimal('0.00')
        for item_data in items:
            qty = Decimal(str(item_data.get('quantity', 1)))
            price = Decimal(str(item_data.get('unit_price', 0)))
            item_subtotal = qty * price
            
            LineItem.objects.create(
                invoice=invoice,
                subtotal=item_subtotal,
                total=item_subtotal,
                **item_data
            )
            subtotal += item_subtotal

        invoice.subtotal = subtotal
        invoice.total_amount = subtotal
        invoice.amount_due = subtotal
        invoice.save()

        InvoiceActivity.objects.create(
            invoice=invoice,
            user=user,
            action="created",
            description=f"Invoice {invoice.invoice_number} created"
        )
        
        return invoice

    @staticmethod
    @transaction.atomic
    def update_status(invoice, user, new_status, reason=""):
        old_status = invoice.status
        invoice.status = new_status
        invoice.save()

        InvoiceActivity.objects.create(
            invoice=invoice,
            user=user,
            action="status_change",
            description=f"Status changed from {old_status} to {new_status}. {reason}"
        )
