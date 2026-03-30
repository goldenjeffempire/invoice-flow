"""
Tests for key application views.
Verifies page accessibility, authentication requirements, and basic rendering.
"""
import pytest

from tests.factories import InvoiceFactory, UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard_requires_login(self, client):
        response = client.get("/dashboard/")
        assert response.status_code == 302
        assert "login" in response.url.lower()

    def test_dashboard_authenticated(self, authenticated_client):
        response = authenticated_client.get("/dashboard/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoiceViews:
    def test_invoice_list_authenticated(self, authenticated_client, user):
        workspace = WorkspaceFactory(owner=user)
        InvoiceFactory(workspace=workspace, created_by=user)
        response = authenticated_client.get("/invoices/")
        assert response.status_code == 200

    def test_invoice_list_requires_login(self, client):
        response = client.get("/invoices/")
        assert response.status_code == 302
        assert "login" in response.url.lower()

    def test_invoice_detail_own_invoice(self, authenticated_client, user):
        workspace = WorkspaceFactory(owner=user)
        invoice = InvoiceFactory(workspace=workspace, created_by=user)
        response = authenticated_client.get(f"/invoices/{invoice.pk}/")
        assert response.status_code == 200

    def test_invoice_detail_other_workspace(self, authenticated_client, user):
        other_user = UserFactory()
        other_workspace = WorkspaceFactory(owner=other_user)
        invoice = InvoiceFactory(workspace=other_workspace, created_by=other_user)
        response = authenticated_client.get(f"/invoices/{invoice.pk}/")
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestLandingPage:
    def test_landing_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_ready_endpoint(self, client):
        response = client.get("/health/ready/")
        assert response.status_code == 200

    def test_health_live_endpoint(self, client):
        response = client.get("/health/live/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestPublicPages:
    def test_features_page(self, client):
        response = client.get("/features/")
        assert response.status_code == 200

    def test_about_page(self, client):
        response = client.get("/about/")
        assert response.status_code == 200

    def test_contact_page(self, client):
        response = client.get("/contact/")
        assert response.status_code == 200

    def test_terms_page(self, client):
        response = client.get("/terms/")
        assert response.status_code == 200

    def test_privacy_page(self, client):
        response = client.get("/privacy/")
        assert response.status_code == 200

    def test_login_page(self, client):
        response = client.get("/login/")
        assert response.status_code == 200

    def test_signup_page(self, client):
        response = client.get("/signup/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthViews:
    def test_logout_redirects(self, authenticated_client):
        response = authenticated_client.get("/logout/")
        assert response.status_code == 302

    def test_login_with_invalid_credentials(self, client):
        response = client.post("/login/", {"username": "invalid", "password": "wrong"})
        assert response.status_code in (200, 302)


@pytest.mark.django_db
class TestSEOEndpoints:
    def test_robots_txt(self, client):
        response = client.get("/robots.txt")
        assert response.status_code == 200

    def test_sitemap_xml(self, client):
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
