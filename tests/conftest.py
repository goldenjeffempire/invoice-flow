import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    from invoices.models import UserProfile
    u = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    UserProfile.objects.get_or_create(
        user=u,
        defaults={"email_verified": True, "company_name": "Test Co"},
    )
    return u


@pytest.fixture
def workspace(db, user):
    from tests.factories import WorkspaceFactory
    return WorkspaceFactory(owner=user)


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
