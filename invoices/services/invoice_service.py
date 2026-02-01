import secrets
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404

from ..models import Invoice, LineItem, InvoiceActivity, InvoiceAttachment, InvoicePayment, Client, Payment

logger = logging.getLogger(__name__)


class InvoiceValidationError(Exception):
    def __init__(self, errors: Dict[str, List[str]]):
        self.errors = errors
        super().__init__(str(errors))


class InvoiceStateError(Exception):
    pass


class InvoiceService:
    VALID_TRANSITIONS = {
        Invoice.Status.DRAFT: [Invoice.Status.SENT, Invoice.Status.VOID],
        Invoice.Status.SENT: [Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.PAID, Invoice.Status.OVERDUE, Invoice.Status.VOID],
        Invoice.Status.VIEWED: [Invoice.Status.PART_PAID, Invoice.Status.PAID, Invoice.Status.OVERDUE, Invoice.Status.VOID],
        Invoice.Status.PART_PAID: [Invoice.Status.PAID, Invoice.Status.OVERDUE, Invoice.Status.VOID, Invoice.Status.WRITE_OFF],
        Invoice.Status.OVERDUE: [Invoice.Status.PART_PAID, Invoice.Status.PAID, Invoice.Status.VOID, Invoice.Status.WRITE_OFF],
        Invoice.Status.PAID: [],
        Invoice.Status.VOID: [],
        Invoice.Status.WRITE_OFF: [],
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    @staticmethod
    def generate_invoice_number(workspace, prefix: str = "INV", format_str: str = "{prefix}-{year}-{number:04d}") -> str:
        from django.db.models import Max
        year = timezone.now().year
        year_start = timezone.datetime(year, 1, 1, tzinfo=timezone.get_current_timezone())

        last_invoice = Invoice.objects.filter(
            workspace=workspace,
            created_at__gte=year_start
        ).aggregate(Max('id'))

        next_num = (last_invoice['id__max'] or 0) + 1
        return format_str.format(prefix=prefix, year=year, number=next_num)

    @staticmethod
    def validate_invoice_data(data: Dict[str, Any], items: List[Dict[str, Any]], is_update: bool = False) -> Dict[str, List[str]]:
        errors = {}

        if not is_update:
            if not data.get('client_id') and not data.get('client'):
                errors['client'] = ['Client is required']

        if not data.get('due_date'):
            errors['due_date'] = ['Due date is required']
        elif data.get('issue_date') and data['due_date'] < data['issue_date']:
            errors['due_date'] = ['Due date cannot be before issue date']

        if not items or len(items) == 0:
            errors['items'] = ['At least one line item is required']
        else:
            for i, item in enumerate(items):
                if not item.get('description', '').strip():
                    errors[f'items.{i}.description'] = ['Description is required']
                if Decimal(str(item.get('quantity', 0))) <= 0:
                    errors[f'items.{i}.quantity'] = ['Quantity must be greater than 0']
                if Decimal(str(item.get('unit_price', 0))) < 0:
                    errors[f'items.{i}.unit_price'] = ['Unit price cannot be negative']

        return errors

    @staticmethod
    def calculate_line_item(item_data: Dict[str, Any], tax_mode: str = 'exclusive') -> Dict[str, Decimal]:
        quantity = Decimal(str(item_data.get('quantity', 1)))
        unit_price = Decimal(str(item_data.get('unit_price', 0)))
        tax_rate = Decimal(str(item_data.get('tax_rate', 0)))
        discount_type = item_data.get('discount_type', 'flat')
        discount_value = Decimal(str(item_data.get('discount_value', 0)))

        line_subtotal = (quantity * unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if discount_type == 'percentage':
            discount_amount = (line_subtotal * discount_value / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            discount_amount = discount_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        after_discount = line_subtotal - discount_amount

        if tax_mode == 'inclusive':
            base_amount = (after_discount / (1 + tax_rate / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            tax_amount = after_discount - base_amount
            subtotal = base_amount
            total = after_discount
        else:
            tax_amount = (after_discount * tax_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal = after_discount
            total = (after_discount + tax_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'total': total,
        }

    @staticmethod
    def calculate_invoice_totals(items: List[Dict[str, Any]], tax_mode: str = 'exclusive',
                                  global_discount_type: str = 'flat', global_discount_value: Decimal = Decimal('0')) -> Dict[str, Decimal]:
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        line_discount_total = Decimal('0.00')

        for item in items:
            calc = InvoiceService.calculate_line_item(item, tax_mode)
            subtotal += calc['subtotal']
            tax_total += calc['tax_amount']
            line_discount_total += calc['discount_amount']

        if global_discount_type == 'percentage':
            global_discount_amount = (subtotal * global_discount_value / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            global_discount_amount = global_discount_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        discount_total = line_discount_total + global_discount_amount
        total_amount = (subtotal + tax_total - global_discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'subtotal': subtotal,
            'tax_total': tax_total,
            'discount_total': discount_total,
            'global_discount_amount': global_discount_amount,
            'total_amount': max(total_amount, Decimal('0.00')),
            'amount_due': max(total_amount, Decimal('0.00')),
        }

    @classmethod
    @transaction.atomic
    def create_invoice(cls, workspace, user, data: Dict[str, Any], items: List[Dict[str, Any]],
                       source_type: str = 'manual', source_id: int = None) -> Invoice:
        errors = cls.validate_invoice_data(data, items)
        if errors:
            raise InvoiceValidationError(errors)

        client_id = data.pop('client_id', None) or data.pop('client', None)
        if isinstance(client_id, Client):
            client = client_id
        else:
            client = get_object_or_404(Client, id=client_id, workspace=workspace)

        profile = user.profile
        invoice_number = data.get('invoice_number') or cls.generate_invoice_number(
            workspace,
            prefix=profile.invoice_prefix or 'INV',
            format_str=profile.invoice_numbering_format or '{prefix}-{year}-{number:04d}'
        )

        tax_mode = data.get('tax_mode', profile.vat_registered and 'inclusive' or 'exclusive')
        default_tax_rate = data.get('default_tax_rate', profile.default_tax_rate)
        global_discount_type = data.get('discount_type', 'flat')
        global_discount_value = Decimal(str(data.get('global_discount_value', 0)))

        for item in items:
            if 'tax_rate' not in item:
                item['tax_rate'] = float(default_tax_rate)

        totals = cls.calculate_invoice_totals(items, tax_mode, global_discount_type, global_discount_value)

        invoice = Invoice.objects.create(
            workspace=workspace,
            client=client,
            created_by=user,
            invoice_number=invoice_number,
            status=Invoice.Status.DRAFT,
            source_type=source_type,
            source_id=source_id,
            issue_date=data.get('issue_date', timezone.now().date()),
            due_date=data['due_date'],
            currency=data.get('currency', profile.default_currency or 'NGN'),
            base_currency=profile.default_currency or 'NGN',
            exchange_rate=Decimal(str(data.get('exchange_rate', 1))),
            tax_mode=tax_mode,
            default_tax_rate=default_tax_rate,
            discount_type=global_discount_type,
            global_discount_value=global_discount_value,
            global_discount_amount=totals['global_discount_amount'],
            subtotal=totals['subtotal'],
            tax_total=totals['tax_total'],
            discount_total=totals['discount_total'],
            total_amount=totals['total_amount'],
            amount_due=totals['amount_due'],
            client_memo=data.get('client_memo', ''),
            internal_notes=data.get('internal_notes', ''),
            terms_conditions=data.get('terms_conditions', ''),
            footer_note=data.get('footer_note', ''),
            payment_instructions=data.get('payment_instructions', profile.payment_instructions or ''),
            reminder_enabled=data.get('reminder_enabled', True),
            reminder_days_before=data.get('reminder_days_before', 3),
        )

        for idx, item_data in enumerate(items):
            calc = cls.calculate_line_item(item_data, tax_mode)
            LineItem.objects.create(
                invoice=invoice,
                item_type=item_data.get('item_type', 'service'),
                product_id_ref=item_data.get('product_id'),
                description=item_data['description'],
                long_description=item_data.get('long_description', ''),
                unit=item_data.get('unit', 'unit'),
                quantity=Decimal(str(item_data.get('quantity', 1))),
                unit_price=Decimal(str(item_data.get('unit_price', 0))),
                tax_rate=Decimal(str(item_data.get('tax_rate', 0))),
                tax_amount=calc['tax_amount'],
                discount_type=item_data.get('discount_type', 'flat'),
                discount_value=Decimal(str(item_data.get('discount_value', 0))),
                discount_amount=calc['discount_amount'],
                subtotal=calc['subtotal'],
                total=calc['total'],
                sort_order=idx,
            )

        cls.log_activity(invoice, user, InvoiceActivity.ActionType.CREATED, f"Invoice {invoice_number} created")

        if not profile.first_invoice_created_at:
            profile.first_invoice_created_at = timezone.now()
            profile.save(update_fields=['first_invoice_created_at'])

        logger.info(f"Invoice {invoice.id} created by user {user.id}")
        return invoice

    @classmethod
    @transaction.atomic
    def update_invoice(cls, invoice: Invoice, user, data: Dict[str, Any], items: List[Dict[str, Any]]) -> Invoice:
        if not invoice.can_edit:
            raise InvoiceStateError(f"Invoice in status '{invoice.status}' cannot be edited")

        errors = cls.validate_invoice_data(data, items, is_update=True)
        if errors:
            raise InvoiceValidationError(errors)

        if 'client_id' in data:
            invoice.client = get_object_or_404(Client, id=data['client_id'], workspace=invoice.workspace)

        tax_mode = data.get('tax_mode', invoice.tax_mode)
        global_discount_type = data.get('discount_type', invoice.discount_type)
        global_discount_value = Decimal(str(data.get('global_discount_value', invoice.global_discount_value)))

        totals = cls.calculate_invoice_totals(items, tax_mode, global_discount_type, global_discount_value)

        invoice.issue_date = data.get('issue_date', invoice.issue_date)
        invoice.due_date = data.get('due_date', invoice.due_date)
        invoice.currency = data.get('currency', invoice.currency)
        invoice.exchange_rate = Decimal(str(data.get('exchange_rate', invoice.exchange_rate)))
        invoice.tax_mode = tax_mode
        invoice.default_tax_rate = Decimal(str(data.get('default_tax_rate', invoice.default_tax_rate)))
        invoice.discount_type = global_discount_type
        invoice.global_discount_value = global_discount_value
        invoice.global_discount_amount = totals['global_discount_amount']
        invoice.subtotal = totals['subtotal']
        invoice.tax_total = totals['tax_total']
        invoice.discount_total = totals['discount_total']
        invoice.total_amount = totals['total_amount']
        invoice.amount_due = totals['total_amount'] - invoice.amount_paid
        invoice.client_memo = data.get('client_memo', invoice.client_memo)
        invoice.internal_notes = data.get('internal_notes', invoice.internal_notes)
        invoice.terms_conditions = data.get('terms_conditions', invoice.terms_conditions)
        invoice.footer_note = data.get('footer_note', invoice.footer_note)
        invoice.payment_instructions = data.get('payment_instructions', invoice.payment_instructions)
        invoice.version += 1
        invoice.save()

        invoice.items.all().delete()
        for idx, item_data in enumerate(items):
            calc = cls.calculate_line_item(item_data, tax_mode)
            LineItem.objects.create(
                invoice=invoice,
                item_type=item_data.get('item_type', 'service'),
                product_id_ref=item_data.get('product_id'),
                description=item_data['description'],
                long_description=item_data.get('long_description', ''),
                unit=item_data.get('unit', 'unit'),
                quantity=Decimal(str(item_data.get('quantity', 1))),
                unit_price=Decimal(str(item_data.get('unit_price', 0))),
                tax_rate=Decimal(str(item_data.get('tax_rate', 0))),
                tax_amount=calc['tax_amount'],
                discount_type=item_data.get('discount_type', 'flat'),
                discount_value=Decimal(str(item_data.get('discount_value', 0))),
                discount_amount=calc['discount_amount'],
                subtotal=calc['subtotal'],
                total=calc['total'],
                sort_order=idx,
            )

        cls.log_activity(invoice, user, InvoiceActivity.ActionType.UPDATED, "Invoice updated")
        logger.info(f"Invoice {invoice.id} updated by user {user.id}")
        return invoice

    @classmethod
    @transaction.atomic
    def transition_status(cls, invoice: Invoice, user, new_status: str, reason: str = "", metadata: Dict = None) -> Invoice:
        old_status = invoice.status

        if not cls.can_transition(old_status, new_status):
            raise InvoiceStateError(f"Cannot transition from '{old_status}' to '{new_status}'")

        invoice.status = new_status

        if new_status == Invoice.Status.SENT and not invoice.sent_at:
            invoice.sent_at = timezone.now()
        elif new_status == Invoice.Status.VIEWED and not invoice.first_viewed_at:
            invoice.first_viewed_at = timezone.now()
        elif new_status == Invoice.Status.PAID:
            invoice.paid_at = timezone.now()
            invoice.amount_due = Decimal('0.00')
        elif new_status == Invoice.Status.VOID:
            invoice.voided_at = timezone.now()
            invoice.void_reason = reason

        invoice.save()

        action = InvoiceActivity.ActionType.STATUS_CHANGED
        if new_status == Invoice.Status.VOID:
            action = InvoiceActivity.ActionType.VOIDED
        elif new_status == Invoice.Status.WRITE_OFF:
            action = InvoiceActivity.ActionType.WRITTEN_OFF

        cls.log_activity(
            invoice, user, action,
            f"Status changed from {old_status} to {new_status}. {reason}".strip(),
            metadata=metadata or {'old_status': old_status, 'new_status': new_status}
        )

        logger.info(f"Invoice {invoice.id} transitioned from {old_status} to {new_status}")
        return invoice

    @classmethod
    @transaction.atomic
    def send_invoice(cls, invoice: Invoice, user, delivery_method: str = 'email') -> Invoice:
        if invoice.status == Invoice.Status.DRAFT:
            invoice = cls.transition_status(invoice, user, Invoice.Status.SENT)
        elif invoice.status in [Invoice.Status.SENT, Invoice.Status.VIEWED]:
            pass
        else:
            raise InvoiceStateError(f"Cannot send invoice in status '{invoice.status}'")

        if delivery_method == 'email':
            invoice.delivery_email_sent = True
        elif delivery_method == 'whatsapp':
            invoice.delivery_whatsapp_sent = True

        invoice.save()

        cls.log_activity(invoice, user, InvoiceActivity.ActionType.SENT, f"Invoice sent via {delivery_method}")
        return invoice

    @classmethod
    @transaction.atomic
    def record_view(cls, invoice: Invoice, ip_address: str = None, user_agent: str = "") -> Invoice:
        invoice.view_count += 1
        invoice.last_viewed_at = timezone.now()
        if ip_address:
            invoice.last_viewed_ip = ip_address

        if not invoice.first_viewed_at:
            invoice.first_viewed_at = timezone.now()

        if invoice.status == Invoice.Status.SENT:
            invoice.status = Invoice.Status.VIEWED

        invoice.save()

        InvoiceActivity.objects.create(
            invoice=invoice,
            user=None,
            action=InvoiceActivity.ActionType.VIEWED,
            description="Invoice viewed via public link",
            ip_address=ip_address,
            user_agent=user_agent,
            is_system=True,
        )

        return invoice

    @classmethod
    @transaction.atomic
    def record_payment(cls, invoice: Invoice, user, amount: Decimal, payment_method: str = 'bank_transfer',
                       reference: str = None, external_reference: str = "", payment_date: date = None,
                       notes: str = "", metadata: Dict = None) -> Tuple[Invoice, Any]:

        if not invoice.can_record_payment:
            raise InvoiceStateError(f"Cannot record payment for invoice in status '{invoice.status}'")

        if amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        if amount > invoice.amount_due:
            raise ValidationError(f"Payment amount {amount} exceeds amount due {invoice.amount_due}")

        reference = reference or f"PAY-{secrets.token_hex(8).upper()}"

        from ..models import InvoicePayment
        payment = InvoicePayment.objects.create(
            invoice=invoice,
            recorded_by=user,
            reference=reference,
            external_reference=external_reference,
            amount=amount,
            currency=invoice.currency,
            payment_method=payment_method,
            status=InvoicePayment.PaymentStatus.COMPLETED,
            payment_date=payment_date or timezone.now().date(),
            notes=notes,
            metadata=metadata or {},
            is_partial=amount < invoice.amount_due,
        )

        invoice.amount_paid += amount
        invoice.amount_due = invoice.total_amount - invoice.amount_paid

        if invoice.amount_due <= 0:
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.amount_due = Decimal('0.00')
        elif invoice.amount_paid > 0:
            invoice.status = Invoice.Status.PART_PAID

        invoice.save()

        cls.log_activity(
            invoice, user, InvoiceActivity.ActionType.PAYMENT_RECEIVED,
            f"Payment of {invoice.currency_symbol}{amount} recorded via {payment_method}",
            metadata={'payment_id': payment.id, 'amount': str(amount), 'method': payment_method}
        )

        logger.info(f"Payment {payment.id} of {amount} recorded for invoice {invoice.id}")
        return invoice, payment

    @classmethod
    @transaction.atomic
    def void_invoice(cls, invoice: Invoice, user, reason: str) -> Invoice:
        if not invoice.can_void:
            raise InvoiceStateError(f"Cannot void invoice in status '{invoice.status}'")

        if not reason.strip():
            raise ValidationError("Void reason is required")

        return cls.transition_status(invoice, user, Invoice.Status.VOID, reason=reason)

    @classmethod
    @transaction.atomic
    def write_off_invoice(cls, invoice: Invoice, user, reason: str) -> Invoice:
        if invoice.status not in [Invoice.Status.OVERDUE, Invoice.Status.PART_PAID]:
            raise InvoiceStateError(f"Cannot write off invoice in status '{invoice.status}'")

        if not reason.strip():
            raise ValidationError("Write-off reason is required")

        return cls.transition_status(invoice, user, Invoice.Status.WRITE_OFF, reason=reason)

    @classmethod
    @transaction.atomic
    def duplicate_invoice(cls, invoice: Invoice, user) -> Invoice:
        items_data = []
        for item in invoice.items.all():
            items_data.append({
                'item_type': item.item_type,
                'product_id': item.product_id,
                'description': item.description,
                'long_description': item.long_description,
                'unit': item.unit,
                'quantity': float(item.quantity),
                'unit_price': float(item.unit_price),
                'tax_rate': float(item.tax_rate),
                'discount_type': item.discount_type,
                'discount_value': float(item.discount_value),
            })

        data = {
            'client_id': invoice.client_id,
            'due_date': timezone.now().date() + timedelta(days=30),
            'issue_date': timezone.now().date(),
            'currency': invoice.currency,
            'exchange_rate': float(invoice.exchange_rate),
            'tax_mode': invoice.tax_mode,
            'default_tax_rate': float(invoice.default_tax_rate),
            'discount_type': invoice.discount_type,
            'global_discount_value': float(invoice.global_discount_value),
            'client_memo': invoice.client_memo,
            'internal_notes': invoice.internal_notes,
            'terms_conditions': invoice.terms_conditions,
            'footer_note': invoice.footer_note,
            'payment_instructions': invoice.payment_instructions,
        }

        new_invoice = cls.create_invoice(
            invoice.workspace, user, data, items_data,
            source_type='duplicate', source_id=invoice.id
        )

        new_invoice.parent_invoice = invoice
        new_invoice.save(update_fields=['parent_invoice'])

        cls.log_activity(invoice, user, InvoiceActivity.ActionType.DUPLICATED, f"Duplicated to {new_invoice.invoice_number}")

        logger.info(f"Invoice {invoice.id} duplicated to {new_invoice.id}")
        return new_invoice

    @classmethod
    def check_and_mark_overdue(cls, workspace=None) -> int:
        today = timezone.now().date()
        queryset = Invoice.objects.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID],
            due_date__lt=today,
            amount_due__gt=0,
        )

        if workspace:
            queryset = queryset.filter(workspace=workspace)

        count = 0
        for invoice in queryset:
            invoice.status = Invoice.Status.OVERDUE
            invoice.save(update_fields=['status'])
            InvoiceActivity.objects.create(
                invoice=invoice,
                action=InvoiceActivity.ActionType.STATUS_CHANGED,
                description="Invoice marked as overdue (automated)",
                is_system=True,
            )
            count += 1

        logger.info(f"Marked {count} invoices as overdue")
        return count

    @staticmethod
    def log_activity(invoice: Invoice, user, action: str, description: str, metadata: Dict = None,
                     ip_address: str = None, user_agent: str = ""):
        InvoiceActivity.objects.create(
            invoice=invoice,
            user=user,
            action=action,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            is_system=user is None,
        )

    @staticmethod
    def get_invoice_stats(workspace) -> Dict[str, Any]:
        invoices = Invoice.objects.filter(workspace=workspace)

        stats = {
            'total_count': invoices.count(),
            'draft_count': invoices.filter(status=Invoice.Status.DRAFT).count(),
            'sent_count': invoices.filter(status=Invoice.Status.SENT).count(),
            'viewed_count': invoices.filter(status=Invoice.Status.VIEWED).count(),
            'paid_count': invoices.filter(status=Invoice.Status.PAID).count(),
            'overdue_count': invoices.filter(status=Invoice.Status.OVERDUE).count(),
            'part_paid_count': invoices.filter(status=Invoice.Status.PART_PAID).count(),
            'total_outstanding': invoices.filter(
                status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.PART_PAID, Invoice.Status.OVERDUE]
            ).aggregate(total=Sum('amount_due'))['total'] or Decimal('0.00'),
            'total_paid': invoices.filter(status=Invoice.Status.PAID).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
        }

        return stats

    @staticmethod
    def search_invoices(workspace, query: str = None, status: str = None, client_id: int = None,
                        date_from: date = None, date_to: date = None, ordering: str = '-created_at'):
        queryset = Invoice.objects.filter(workspace=workspace).select_related('client')

        if query:
            queryset = queryset.filter(
                Q(invoice_number__icontains=query) |
                Q(client__name__icontains=query) |
                Q(client__email__icontains=query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)

        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        return queryset.order_by(ordering)
