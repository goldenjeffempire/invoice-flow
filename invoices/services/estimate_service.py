from django.db import transaction
from django.utils import timezone
from ..models import Estimate, EstimateItem, EstimateActivity, Invoice, LineItem

class EstimateService:
    @staticmethod
    @transaction.atomic
    def create_estimate(workspace, client, created_by, data):
        estimate = Estimate.objects.create(
            workspace=workspace,
            client=client,
            created_by=created_by,
            estimate_number=data.get('estimate_number'),
            expiry_date=data.get('expiry_date'),
            currency=data.get('currency', workspace.profile.default_currency),
            client_notes=data.get('client_notes', ''),
            terms_conditions=data.get('terms_conditions', '')
        )
        
        for item_data in data.get('items', []):
            EstimateItem.objects.create(
                estimate=estimate,
                description=item_data['description'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                tax_rate=item_data.get('tax_rate', 0)
            )
            
        EstimateActivity.objects.create(
            estimate=estimate,
            user=created_by,
            action="Created estimate"
        )
        return estimate

    @staticmethod
    @transaction.atomic
    def convert_to_invoice(estimate, created_by):
        if estimate.status == Estimate.Status.INVOICED:
            raise ValueError("Estimate already converted to invoice")
            
        invoice = Invoice.objects.create(
            workspace=estimate.workspace,
            client=estimate.client,
            created_by=created_by,
            invoice_number=f"INV-{estimate.estimate_number}",
            due_date=timezone.now() + timezone.timedelta(days=14),
            currency=estimate.currency,
            total_amount=estimate.total_amount,
            amount_due=estimate.total_amount
        )
        
        for item in estimate.items.all():
            LineItem.objects.create(
                invoice=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate
            )
            
        estimate.status = Estimate.Status.INVOICED
        estimate.converted_invoice = invoice
        estimate.save()
        
        EstimateActivity.objects.create(
            estimate=estimate,
            user=created_by,
            action="Converted to invoice",
            details=f"Invoice ID: {invoice.id}"
        )
        return invoice
