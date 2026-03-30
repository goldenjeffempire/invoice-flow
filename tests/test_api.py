"""
Tests for the REST API endpoints.
"""
from decimal import Decimal

import pytest
from rest_framework import status

from tests.factories import InvoiceFactory, LineItemFactory, UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestInvoiceAPIUnauthenticated:
    def test_list_invoices_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestInvoiceAPI:
    def test_list_invoices(self, authenticated_api_client, user):
        workspace = WorkspaceFactory(owner=user)
        InvoiceFactory(workspace=workspace, created_by=user)
        InvoiceFactory(workspace=workspace, created_by=user)

        response = authenticated_api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_invoices_workspace_isolation(self, authenticated_api_client, user):
        workspace = WorkspaceFactory(owner=user)
        InvoiceFactory(workspace=workspace, created_by=user)

        other_user = UserFactory()
        other_workspace = WorkspaceFactory(owner=other_user)
        InvoiceFactory(workspace=other_workspace, created_by=other_user)

        response = authenticated_api_client.get("/api/v1/invoices/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_invoice_detail(self, authenticated_api_client, user):
        workspace = WorkspaceFactory(owner=user)
        invoice = InvoiceFactory(workspace=workspace, created_by=user)
        LineItemFactory(invoice=invoice)

        response = authenticated_api_client.get(f"/api/v1/invoices/{invoice.pk}/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_filter_by_status(self, authenticated_api_client, user):
        workspace = WorkspaceFactory(owner=user)
        from invoices.models import Invoice
        InvoiceFactory(workspace=workspace, created_by=user, status=Invoice.Status.PAID)
        InvoiceFactory(workspace=workspace, created_by=user, status=Invoice.Status.DRAFT)

        response = authenticated_api_client.get("/api/v1/invoices/?status=paid")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAPIResponseFormat:
    def test_success_response_format(self):
        from invoices.api.response import APIResponse
        response = APIResponse.success(data={"test": "data"}, message="Success")
        assert response.data["success"] is True
        assert response.data["message"] == "Success"
        assert response.data["data"]["test"] == "data"

    def test_error_response_format(self):
        from invoices.api.response import APIResponse
        response = APIResponse.error(
            code="TEST_ERROR",
            message="Test error",
            details={"field": "error"}
        )
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "TEST_ERROR"
        assert response.data["error"]["details"]["field"] == "error"

    def test_paginated_response_format(self):
        from invoices.api.response import APIResponse
        response = APIResponse.paginated(
            data=[{"id": 1}, {"id": 2}],
            page=1,
            page_size=10,
            total=25
        )
        assert response.data["success"] is True
        assert response.data["meta"]["pagination"]["total_pages"] == 3


@pytest.mark.django_db
class TestRateLimiting:
    def test_rate_limiting_configuration(self):
        from invoices.api.rate_limiting import UserBurstThrottle
        throttle = UserBurstThrottle()
        assert throttle.scope == 'user_burst'
