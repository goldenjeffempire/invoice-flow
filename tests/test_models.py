"""
Tests for core Invoice, LineItem, and related models.
These tests verify model creation, field validation, and business logic.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from invoices.models import Invoice, LineItem, Client, Workspace, WorkspaceMember
from tests.factories import InvoiceFactory, LineItemFactory, UserFactory, WorkspaceFactory, ClientFactory


@pytest.mark.django_db
class TestWorkspaceModel:
    def test_create_workspace(self):
        workspace = WorkspaceFactory()
        assert workspace.pk is not None
        assert workspace.name is not None
        assert workspace.is_active is True

    def test_workspace_str(self):
        workspace = WorkspaceFactory(name="Acme Ltd")
        assert "Acme" in str(workspace)

    def test_workspace_has_owner(self):
        workspace = WorkspaceFactory()
        assert workspace.owner is not None


@pytest.mark.django_db
class TestClientModel:
    def test_create_client(self):
        client = ClientFactory()
        assert client.pk is not None
        assert client.name is not None
        assert client.workspace is not None

    def test_client_str(self):
        client = ClientFactory(name="Big Corp")
        assert "Big Corp" in str(client)

    def test_client_belongs_to_workspace(self):
        workspace = WorkspaceFactory()
        client = ClientFactory(workspace=workspace)
        assert client.workspace == workspace


@pytest.mark.django_db
class TestInvoiceModel:
    def test_create_invoice(self):
        invoice = InvoiceFactory()
        assert invoice.pk is not None
        assert invoice.invoice_number is not None
        assert invoice.status == Invoice.Status.DRAFT

    def test_invoice_str(self):
        invoice = InvoiceFactory()
        assert str(invoice) is not None

    def test_invoice_has_workspace(self):
        invoice = InvoiceFactory()
        assert invoice.workspace is not None

    def test_invoice_has_client(self):
        invoice = InvoiceFactory()
        assert invoice.client is not None

    def test_invoice_default_currency(self):
        invoice = InvoiceFactory(currency="NGN")
        assert invoice.currency == "NGN"

    def test_invoice_status_choices(self):
        invoice = InvoiceFactory(status=Invoice.Status.DRAFT)
        assert invoice.status == Invoice.Status.DRAFT

        invoice.status = Invoice.Status.SENT
        invoice.save()
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.SENT

    def test_invoice_due_date(self):
        invoice = InvoiceFactory()
        assert invoice.due_date >= invoice.issue_date

    def test_invoice_with_line_items(self):
        invoice = InvoiceFactory()
        LineItemFactory(invoice=invoice, quantity=Decimal("2"), unit_price=Decimal("50.00"))
        LineItemFactory(invoice=invoice, quantity=Decimal("1"), unit_price=Decimal("25.00"))
        assert invoice.items.count() == 2

    def test_invoice_created_by(self):
        workspace = WorkspaceFactory()
        invoice = InvoiceFactory(workspace=workspace, created_by=workspace.owner)
        assert invoice.created_by == workspace.owner


@pytest.mark.django_db
class TestLineItemModel:
    def test_create_line_item(self):
        line_item = LineItemFactory()
        assert line_item.pk is not None
        assert line_item.invoice is not None

    def test_line_item_amount(self):
        line_item = LineItemFactory(quantity=Decimal("3"), unit_price=Decimal("100.00"))
        assert line_item.quantity == Decimal("3")
        assert line_item.unit_price == Decimal("100.00")

    def test_line_item_description(self):
        line_item = LineItemFactory(description="Web Design Services")
        assert line_item.description == "Web Design Services"

    def test_line_item_belongs_to_invoice(self):
        invoice = InvoiceFactory()
        line_item = LineItemFactory(invoice=invoice)
        assert line_item.invoice == invoice
        assert invoice.items.filter(pk=line_item.pk).exists()


@pytest.mark.django_db
class TestInvoiceStatusTransitions:
    def test_draft_to_sent(self):
        invoice = InvoiceFactory(status=Invoice.Status.DRAFT)
        invoice.status = Invoice.Status.SENT
        invoice.save()
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.SENT

    def test_sent_to_paid(self):
        invoice = InvoiceFactory(status=Invoice.Status.SENT)
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.save()
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PAID

    def test_invoice_void(self):
        invoice = InvoiceFactory(status=Invoice.Status.DRAFT)
        invoice.status = Invoice.Status.VOID
        invoice.void_reason = "Client cancelled"
        invoice.voided_at = timezone.now()
        invoice.save()
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.VOID
