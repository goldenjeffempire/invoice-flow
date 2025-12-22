from datetime import date, timedelta
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from invoices.models import Invoice, InvoiceTemplate, LineItem, UserProfile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")
    
    @factory.post_generation
    def profile(obj, create, extracted, **kwargs):
        if create:
            UserProfile.objects.get_or_create(user=obj, defaults={"company_name": f"{obj.username}'s Company"})


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    user = factory.SubFactory(UserFactory)
    business_name = factory.Faker("company")
    business_email = factory.Faker("email")
    business_phone = factory.Faker("phone_number")
    business_address = factory.Faker("address")
    client_name = factory.Faker("company")
    client_email = factory.Faker("email")
    client_phone = factory.Faker("phone_number")
    client_address = factory.Faker("address")
    invoice_date = factory.LazyFunction(date.today)
    due_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    status = "unpaid"
    tax_rate = Decimal("10.00")
    currency = "USD"


class LineItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LineItem

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Faker("sentence")
    quantity = Decimal("1.00")
    unit_price = Decimal("100.00")


class InvoiceTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceTemplate

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Template {n}")
    description = factory.Faker("paragraph")
    business_name = factory.Faker("company")
    business_email = factory.Faker("email")
    business_phone = factory.Faker("phone_number")
    business_address = factory.Faker("address")
    currency = "USD"
    tax_rate = Decimal("10.00")
    bank_name = factory.Faker("company")
    account_name = factory.Faker("name")
    is_default = False
