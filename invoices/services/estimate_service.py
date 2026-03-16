from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from ..models import Estimate, EstimateItem, EstimateActivity, Invoice, LineItem


def _auto_estimate_number(workspace):
    last = (
        Estimate.objects
        .filter(workspace=workspace)
        .order_by('-id')
        .values_list('estimate_number', flat=True)
        .first()
    )
    year = timezone.now().year
    if last:
        try:
            seq = int(last.split('-')[-1]) + 1
        except (ValueError, AttributeError):
            seq = 1
    else:
        seq = 1
    return f"EST-{year}-{seq:04d}"


def _recalculate_totals(estimate):
    subtotal = Decimal('0.00')
    tax_total = Decimal('0.00')
    for item in estimate.items.all():
        line = item.quantity * item.unit_price
        tax = (line * item.tax_rate / Decimal('100')).quantize(Decimal('0.01'))
        item.subtotal = line
        item.total = line + tax
        item.save(update_fields=['subtotal', 'total'])
        subtotal += line
        tax_total += tax
    estimate.subtotal = subtotal
    estimate.tax_total = tax_total
    estimate.total_amount = subtotal + tax_total
    estimate.save(update_fields=['subtotal', 'tax_total', 'total_amount'])


class EstimateService:

    @staticmethod
    @transaction.atomic
    def create_estimate(workspace, client, created_by, data):
        estimate_number = data.get('estimate_number', '').strip() or _auto_estimate_number(workspace)

        expiry_date = data.get('expiry_date')
        if not expiry_date:
            expiry_date = (timezone.now().date() + timezone.timedelta(days=30))

        issue_date = data.get('issue_date') or timezone.now().date()
        currency = data.get('currency') or 'NGN'

        estimate = Estimate.objects.create(
            workspace=workspace,
            client=client,
            created_by=created_by,
            estimate_number=estimate_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            currency=currency,
            status=Estimate.Status.DRAFT,
            client_notes=data.get('client_notes', ''),
            internal_notes=data.get('internal_notes', ''),
            terms_conditions=data.get('terms_conditions', ''),
        )

        for item_data in data.get('items', []):
            EstimateItem.objects.create(
                estimate=estimate,
                description=item_data['description'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                tax_rate=item_data.get('tax_rate', Decimal('0')),
            )

        _recalculate_totals(estimate)

        EstimateActivity.objects.create(
            estimate=estimate,
            user=created_by,
            action="Created estimate",
        )
        return estimate

    @staticmethod
    @transaction.atomic
    def update_estimate(estimate, updated_by, data):
        if estimate.status != Estimate.Status.DRAFT:
            raise ValueError("Only draft estimates can be edited.")

        estimate_number = data.get('estimate_number', '').strip()
        if estimate_number:
            estimate.estimate_number = estimate_number

        if data.get('issue_date'):
            estimate.issue_date = data['issue_date']
        if data.get('expiry_date'):
            estimate.expiry_date = data['expiry_date']
        if data.get('currency'):
            estimate.currency = data['currency']

        estimate.client_notes = data.get('client_notes', estimate.client_notes)
        estimate.internal_notes = data.get('internal_notes', estimate.internal_notes)
        estimate.terms_conditions = data.get('terms_conditions', estimate.terms_conditions)
        estimate.save()

        if 'items' in data:
            incoming_ids = {str(i['id']) for i in data['items'] if i.get('id')}
            estimate.items.exclude(id__in=incoming_ids).delete()

            for item_data in data['items']:
                item_id = item_data.get('id')
                if item_id:
                    try:
                        item = estimate.items.get(id=item_id)
                        item.description = item_data['description']
                        item.quantity = item_data['quantity']
                        item.unit_price = item_data['unit_price']
                        item.tax_rate = item_data.get('tax_rate', Decimal('0'))
                        item.save()
                    except EstimateItem.DoesNotExist:
                        EstimateItem.objects.create(
                            estimate=estimate,
                            description=item_data['description'],
                            quantity=item_data['quantity'],
                            unit_price=item_data['unit_price'],
                            tax_rate=item_data.get('tax_rate', Decimal('0')),
                        )
                else:
                    EstimateItem.objects.create(
                        estimate=estimate,
                        description=item_data['description'],
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price'],
                        tax_rate=item_data.get('tax_rate', Decimal('0')),
                    )

        _recalculate_totals(estimate)

        EstimateActivity.objects.create(
            estimate=estimate,
            user=updated_by,
            action="Updated estimate",
        )
        return estimate

    @staticmethod
    @transaction.atomic
    def send_estimate(estimate, sent_by, message_text=''):
        if estimate.status not in (Estimate.Status.DRAFT, Estimate.Status.SENT):
            raise ValueError(f"Cannot send estimate with status '{estimate.status}'.")

        estimate.status = Estimate.Status.SENT
        estimate.sent_at = timezone.now()
        estimate.save(update_fields=['status', 'sent_at'])

        public_url = f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else ''}{estimate.get_public_url()}"

        try:
            body_lines = []
            if message_text:
                body_lines.append(message_text)
                body_lines.append('')
            body_lines += [
                f"Dear {estimate.client.name},",
                '',
                f"Please find your estimate {estimate.estimate_number} attached.",
                f"Total: {estimate.currency} {estimate.total_amount:,.2f}",
                f"Valid until: {estimate.expiry_date}",
                '',
                f"View & respond to this estimate online: {public_url}",
                '',
                "Thank you for your business.",
            ]
            send_mail(
                subject=f"Estimate {estimate.estimate_number} from {estimate.workspace.business_name}",
                message='\n'.join(body_lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[estimate.client.email],
                fail_silently=True,
            )
        except Exception:
            pass

        EstimateActivity.objects.create(
            estimate=estimate,
            user=sent_by,
            action=f"Sent estimate to {estimate.client.email}",
        )
        return estimate

    @staticmethod
    @transaction.atomic
    def void_estimate(estimate, voided_by, reason=''):
        if estimate.status == Estimate.Status.VOID:
            raise ValueError("Estimate is already void.")

        old_status = estimate.status
        estimate.status = Estimate.Status.VOID
        estimate.save(update_fields=['status'])

        detail = f"Voided (was {old_status})"
        if reason:
            detail += f". Reason: {reason}"

        EstimateActivity.objects.create(
            estimate=estimate,
            user=voided_by,
            action=detail,
        )
        return estimate

    @staticmethod
    @transaction.atomic
    def duplicate_estimate(estimate, duplicated_by):
        new_number = _auto_estimate_number(estimate.workspace)

        new_estimate = Estimate.objects.create(
            workspace=estimate.workspace,
            client=estimate.client,
            created_by=duplicated_by,
            estimate_number=new_number,
            issue_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timezone.timedelta(days=30),
            currency=estimate.currency,
            status=Estimate.Status.DRAFT,
            client_notes=estimate.client_notes,
            internal_notes=estimate.internal_notes,
            terms_conditions=estimate.terms_conditions,
        )

        for item in estimate.items.all():
            EstimateItem.objects.create(
                estimate=new_estimate,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
            )

        _recalculate_totals(new_estimate)

        EstimateActivity.objects.create(
            estimate=new_estimate,
            user=duplicated_by,
            action=f"Duplicated from {estimate.estimate_number}",
        )
        return new_estimate

    @staticmethod
    @transaction.atomic
    def convert_to_invoice(estimate, created_by):
        if estimate.status == Estimate.Status.INVOICED:
            raise ValueError("Estimate has already been converted to an invoice.")
        if estimate.status not in (Estimate.Status.APPROVED, Estimate.Status.SENT, Estimate.Status.VIEWED):
            raise ValueError(f"Cannot convert estimate with status '{estimate.status}'. It must be approved or sent.")

        from ..services.invoice_service import InvoiceService

        invoice_number = InvoiceService.generate_invoice_number(estimate.workspace)
        due_date = timezone.now().date() + timezone.timedelta(days=14)

        invoice = Invoice.objects.create(
            workspace=estimate.workspace,
            client=estimate.client,
            created_by=created_by,
            invoice_number=invoice_number,
            issue_date=timezone.now().date(),
            due_date=due_date,
            currency=estimate.currency,
            subtotal=estimate.subtotal,
            total_amount=estimate.total_amount,
            amount_due=estimate.total_amount,
            client_memo=estimate.client_notes,
            terms_conditions=estimate.terms_conditions,
        )

        for item in estimate.items.all():
            LineItem.objects.create(
                invoice=invoice,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
            )

        estimate.status = Estimate.Status.INVOICED
        estimate.converted_invoice = invoice
        estimate.save(update_fields=['status', 'converted_invoice'])

        EstimateActivity.objects.create(
            estimate=estimate,
            user=created_by,
            action=f"Converted to invoice {invoice.invoice_number}",
        )
        return invoice
