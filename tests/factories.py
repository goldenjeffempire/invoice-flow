from datetime import date, timedelta
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from invoices.models import Client, Invoice, LineItem, UserProfile, Workspace, WorkspaceMember

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")

    @factory.post_generation
    def profile(obj, create, extracted, **kwargs):
        if create:
            UserProfile.objects.get_or_create(
                user=obj,
                defaults={"email_verified": True, "company_name": f"{obj.username}'s Co"},
            )


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Workspace {n}")
    slug = factory.Sequence(lambda n: f"workspace-{n}")
    owner = factory.SubFactory(UserFactory)
    currency = "USD"
    is_active = True

    @factory.post_generation
    def members(obj, create, extracted, **kwargs):
        if create:
            WorkspaceMember.objects.get_or_create(
                workspace=obj,
                user=obj.owner,
                defaults={"role": "owner"},
            )
            try:
                profile = obj.owner.profile
                if not profile.current_workspace:
                    profile.current_workspace = obj
                    profile.save(update_fields=["current_workspace"])
            except Exception:
                pass


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Client

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Faker("company")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    billing_address = factory.Faker("street_address")
    billing_city = factory.Faker("city")
    billing_country = "US"
    currency = "USD"


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    workspace = factory.SubFactory(WorkspaceFactory)
    client = factory.LazyAttribute(lambda obj: ClientFactory(workspace=obj.workspace))
    created_by = factory.LazyAttribute(lambda obj: obj.workspace.owner)
    invoice_number = factory.Sequence(lambda n: f"INV-2025-{n:04d}")
    status = Invoice.Status.DRAFT
    issue_date = factory.LazyFunction(date.today)
    due_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    currency = "USD"


class LineItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LineItem

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Faker("sentence")
    quantity = Decimal("1.00")
    unit_price = Decimal("100.00")
    tax_rate = Decimal("0.00")
