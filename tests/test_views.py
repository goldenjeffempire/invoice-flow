import pytest

from tests.factories import InvoiceFactory, UserFactory


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard_requires_login(self, client):
        response = client.get("/invoices/dashboard/")
        assert response.status_code == 302
        assert "login" in response.url.lower()

    def test_dashboard_authenticated(self, authenticated_client):
        response = authenticated_client.get("/invoices/dashboard/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoiceViews:
    def test_invoice_list_authenticated(self, authenticated_client, user):
        InvoiceFactory(user=user)
        response = authenticated_client.get("/invoices/list/")
        assert response.status_code == 200

    def test_invoice_detail_own_invoice(self, authenticated_client, user):
        invoice = InvoiceFactory(user=user)
        response = authenticated_client.get(f"/invoices/invoice/{invoice.pk}/")
        assert response.status_code == 200

    def test_invoice_detail_other_user(self, authenticated_client, user):
        other_user = UserFactory()
        invoice = InvoiceFactory(user=other_user)
        response = authenticated_client.get(f"/invoices/invoice/{invoice.pk}/")
        assert response.status_code == 404


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

    def test_security_page(self, client):
        response = client.get("/security/")
        assert response.status_code == 200

    def test_faq_page(self, client):
        response = client.get("/faq/")
        assert response.status_code == 200

    def test_support_page(self, client):
        response = client.get("/support/")
        assert response.status_code == 200

    def test_careers_page(self, client):
        response = client.get("/careers/")
        assert response.status_code == 200

    def test_blog_page(self, client):
        response = client.get("/blog/")
        assert response.status_code == 200

    def test_login_page(self, client):
        response = client.get("/login/")
        assert response.status_code == 200

    def test_signup_page(self, client):
        response = client.get("/signup/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthViews:
    def test_logout_redirects_to_home(self, authenticated_client):
        response = authenticated_client.get("/logout/")
        assert response.status_code == 302
        assert response.url == "/"

    def test_login_with_invalid_credentials(self, client):
        response = client.post("/login/", {"username": "invalid", "password": "wrong"})
        assert response.status_code == 200


@pytest.mark.django_db
class TestSEOEndpoints:
    def test_robots_txt(self, client):
        response = client.get("/robots.txt")
        assert response.status_code == 200

    def test_sitemap_xml(self, client):
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
