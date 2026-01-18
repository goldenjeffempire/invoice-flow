from decimal import Decimal

import pytest
from rest_framework import status

from tests.factories import InvoiceFactory, LineItemFactory, UserFactory


@pytest.mark.django_db
class TestInvoiceAPI:
    def test_list_invoices_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_invoices(self, authenticated_api_client, user):
        InvoiceFactory(user=user)
        InvoiceFactory(user=user)

        response = authenticated_api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_list_invoices_only_own(self, authenticated_api_client, user):
        InvoiceFactory(user=user)
        other_user = UserFactory()
        InvoiceFactory(user=other_user)

        response = authenticated_api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_invoice_detail(self, authenticated_api_client, user):
        invoice = InvoiceFactory(user=user)
        LineItemFactory(invoice=invoice)

        response = authenticated_api_client.get(f"/api/v1/invoices/{invoice.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["invoice_id"] == invoice.invoice_id

    def test_filter_by_status(self, authenticated_api_client, user):
        InvoiceFactory(user=user, status="paid")
        InvoiceFactory(user=user, status="unpaid")

        response = authenticated_api_client.get("/api/v1/invoices/?status=paid")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["status"] == "paid"

    def test_search_invoices(self, authenticated_api_client, user):
        InvoiceFactory(user=user, client_name="Acme Corporation")
        InvoiceFactory(user=user, client_name="Other Company")

        response = authenticated_api_client.get("/api/v1/invoices/?search=Acme")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_update_invoice_status(self, authenticated_api_client, user):
        invoice = InvoiceFactory(user=user, status="unpaid")

        response = authenticated_api_client.post(
            f"/api/v1/invoices/{invoice.pk}/status/", {"status": "paid"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["status"] == "paid"

        invoice.refresh_from_db()
        assert invoice.status == "paid"

    def test_get_stats(self, authenticated_api_client, user):
        invoice1 = InvoiceFactory(user=user, status="paid")
        LineItemFactory(invoice=invoice1, quantity=Decimal("1"), unit_price=Decimal("100.00"))
        invoice2 = InvoiceFactory(user=user, status="unpaid")
        LineItemFactory(invoice=invoice2, quantity=Decimal("1"), unit_price=Decimal("200.00"))

        response = authenticated_api_client.get("/api/v1/invoices/stats/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "total_invoices" in response.data["data"]


@pytest.mark.django_db
class TestInvoiceTemplateAPI:
    def test_list_templates(self, authenticated_api_client, user):
        from tests.factories import InvoiceTemplateFactory

        InvoiceTemplateFactory(user=user)

        response = authenticated_api_client.get("/api/v1/templates/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
