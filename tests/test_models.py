from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from invoices.models import Invoice, Payment
from invoices.paystack_service import finalize_payment_from_verification
from tests.factories import InvoiceFactory, InvoiceTemplateFactory, LineItemFactory, UserFactory


@pytest.mark.django_db
class TestInvoiceModel:
    def test_create_invoice(self):
        invoice = InvoiceFactory()
        assert invoice.pk is not None
        assert invoice.invoice_id.startswith("INV")
        assert invoice.status == "unpaid"

    def test_invoice_str(self):
        invoice = InvoiceFactory(client_name="Test Corp")
        assert "Test Corp" in str(invoice)

    def test_invoice_with_line_items(self):
        invoice = InvoiceFactory()
        LineItemFactory(invoice=invoice, quantity=Decimal("2"), unit_price=Decimal("50.00"))
        LineItemFactory(invoice=invoice, quantity=Decimal("1"), unit_price=Decimal("25.00"))

        assert invoice.line_items.count() == 2

    def test_invoice_subtotal_calculation(self):
        invoice = InvoiceFactory()
        LineItemFactory(invoice=invoice, quantity=Decimal("2"), unit_price=Decimal("50.00"))
        LineItemFactory(invoice=invoice, quantity=Decimal("1"), unit_price=Decimal("25.00"))

        assert invoice.subtotal == Decimal("125.00")

    def test_invoice_status_choices(self):
        invoice = InvoiceFactory(status="paid")
        assert invoice.status == "paid"

        invoice.status = "unpaid"
        invoice.save()
        invoice.refresh_from_db()
        assert invoice.status == "unpaid"

    def test_invoice_validation_rejects_invalid_discount(self):
        user = UserFactory()
        invoice = InvoiceFactory.build(user=user, discount=Decimal("150.00"))
        with pytest.raises(ValidationError):
            invoice.full_clean()

    def test_invoice_validation_rejects_due_date_before_invoice_date(self):
        user = UserFactory()
        invoice = InvoiceFactory.build(user=user)
        invoice.due_date = invoice.invoice_date - timedelta(days=1)
        with pytest.raises(ValidationError):
            invoice.full_clean()

    def test_invoice_validation_rejects_invalid_tax_rate(self):
        user = UserFactory()
        invoice = InvoiceFactory.build(user=user, tax_rate=Decimal("150.00"))
        with pytest.raises(ValidationError):
            invoice.full_clean()


@pytest.mark.django_db
class TestLineItemModel:
    def test_create_line_item(self):
        line_item = LineItemFactory()
        assert line_item.pk is not None
        assert line_item.invoice is not None

    def test_line_item_total_calculation(self):
        line_item = LineItemFactory(quantity=Decimal("3"), unit_price=Decimal("100.00"))
        assert line_item.total == Decimal("300.00")

    def test_line_item_validation_rejects_zero_quantity(self):
        line_item = LineItemFactory.build(quantity=Decimal("0.00"))
        with pytest.raises(ValidationError):
            line_item.full_clean()

    def test_line_item_validation_rejects_negative_unit_price(self):
        line_item = LineItemFactory.build(unit_price=Decimal("-1.00"))
        with pytest.raises(ValidationError):
            line_item.full_clean()


@pytest.mark.django_db
class TestInvoiceTemplateModel:
    def test_create_template(self):
        template = InvoiceTemplateFactory()
        assert template.pk is not None
        assert template.user is not None

    def test_template_str(self):
        template = InvoiceTemplateFactory(name="My Template")
        assert "My Template" in str(template)

    def test_template_tax_rate(self):
        template = InvoiceTemplateFactory(tax_rate=Decimal("15.00"))
        assert template.tax_rate == Decimal("15.00")


@pytest.mark.django_db
class TestPaymentFinalization:
    def test_finalize_payment_updates_invoice_status(self):
        user = UserFactory()
        invoice = InvoiceFactory(user=user, status=Invoice.Status.UNPAID)
        payment = Payment.objects.create(
            invoice=invoice,
            user=user,
            reference="ref_123",
            amount=invoice.total,
            currency=invoice.currency,
            status=Payment.Status.PENDING,
        )

        finalize_payment_from_verification(
            payment=payment,
            verification={"verified": True},
        )

        invoice.refresh_from_db()
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCESS
        assert invoice.status == Invoice.Status.PAID
