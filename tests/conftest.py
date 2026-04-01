import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    from invoices.models import UserProfile, Workspace, WorkspaceMember
    u = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    profile, _ = UserProfile.objects.get_or_create(user=u)
    profile.email_verified = True
    profile.company_name = "Test Co"
    profile.onboarding_completed = True
    workspace, _ = Workspace.objects.get_or_create(
        slug="test-co",
        defaults={"name": "Test Co", "owner": u, "currency": "NGN"},
    )
    WorkspaceMember.objects.get_or_create(workspace=workspace, user=u, defaults={"role": "owner"})
    profile.current_workspace = workspace
    profile.save()
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
