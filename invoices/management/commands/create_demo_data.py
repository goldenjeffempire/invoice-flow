"""Management command to create comprehensive demo data for InvoiceFlow."""

import random
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from invoices.models import (
    Client, Estimate, EstimateItem, Expense, ExpenseCategory,
    Invoice, LineItem, Payment, RecurringSchedule,
    UserProfile, Workspace, WorkspaceMember,
)


CLIENTS = [
    {"name": "Apex Tech Solutions", "email": "billing@apextech.io", "phone": "+1 (415) 555-0101", "city": "San Francisco", "country": "US", "currency": "USD"},
    {"name": "Zenith Marketing Group", "email": "accounts@zenithmarketing.co", "phone": "+1 (212) 555-0202", "city": "New York", "country": "US", "currency": "USD"},
    {"name": "Bolt Creative Studio", "email": "finance@boltcreative.design", "phone": "+44 20 7946 0333", "city": "London", "country": "GB", "currency": "USD"},
    {"name": "Green Leaf Organics", "email": "admin@greenleaf.ng", "phone": "+234 803 555 0404", "city": "Lagos", "country": "NG", "currency": "NGN"},
    {"name": "DataStream Analytics", "email": "payments@datastream.ai", "phone": "+1 (650) 555-0505", "city": "Palo Alto", "country": "US", "currency": "USD"},
    {"name": "NovaBuild Construction", "email": "billing@novabuild.com", "phone": "+234 901 555 0606", "city": "Abuja", "country": "NG", "currency": "NGN"},
    {"name": "Luminary Events Co", "email": "invoices@luminaryevents.co", "phone": "+1 (310) 555-0707", "city": "Los Angeles", "country": "US", "currency": "USD"},
    {"name": "SwiftLogix Supply Chain", "email": "ap@swiftlogix.com", "phone": "+44 161 555 0808", "city": "Manchester", "country": "GB", "currency": "USD"},
]

SERVICES = [
    ("Web Development", "Custom web application development and deployment", Decimal("8500.00")),
    ("UI/UX Design", "Full product design with wireframes and high-fidelity mockups", Decimal("4200.00")),
    ("Brand Identity Package", "Logo, brand guidelines, and visual identity system", Decimal("3500.00")),
    ("SEO Optimization", "3-month comprehensive SEO audit and implementation", Decimal("2800.00")),
    ("Mobile App Development", "Native iOS and Android app development", Decimal("15000.00")),
    ("Data Analytics Dashboard", "Custom BI dashboard with live data integration", Decimal("6500.00")),
    ("Content Strategy", "12-month content calendar and editorial strategy", Decimal("1800.00")),
    ("DevOps & Infrastructure Setup", "CI/CD pipeline, Docker, and cloud setup", Decimal("4800.00")),
    ("API Integration Services", "Third-party API integration and documentation", Decimal("2400.00")),
    ("Monthly Strategy Retainer", "Strategic consulting and advisory services", Decimal("3200.00")),
    ("Email Marketing Campaign", "Full campaign strategy, design and execution", Decimal("1500.00")),
    ("Security Audit & Pen Testing", "Comprehensive application security assessment", Decimal("5500.00")),
]

EXPENSE_ITEMS = [
    ("GitHub Pro subscription", "software", Decimal("21.00"), "USD"),
    ("Figma Business Plan", "software", Decimal("45.00"), "USD"),
    ("AWS EC2 Hosting (monthly)", "software", Decimal("180.00"), "USD"),
    ("MacBook Pro M3 14-inch", "equipment", Decimal("2499.00"), "USD"),
    ("External SSD 2TB", "equipment", Decimal("159.00"), "USD"),
    ("Flight — Lagos to Abuja", "travel", Decimal("85000.00"), "NGN"),
    ("Uber rides (weekly)", "travel", Decimal("12500.00"), "NGN"),
    ("Google Ads Campaign", "marketing", Decimal("320.00"), "USD"),
    ("Office electricity (monthly)", "utilities", Decimal("45000.00"), "NGN"),
    ("Legal retainer fee", "professional_services", Decimal("250000.00"), "NGN"),
    ("Client lunch — Apex Tech", "meals_entertainment", Decimal("18500.00"), "NGN"),
    ("Slack Business subscription", "software", Decimal("62.50"), "USD"),
    ("Notion Team plan", "software", Decimal("32.00"), "USD"),
    ("Zoom Pro", "software", Decimal("14.99"), "USD"),
    ("Twitter/X Promoted Posts", "marketing", Decimal("150.00"), "USD"),
]


class Command(BaseCommand):
    help = "Create comprehensive demo data for InvoiceFlow"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo", help="Demo user username")

    def handle(self, *args, **options):
        username = options["username"]

        # ── Get or create demo user ─────────────────────────────
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "demo@invoiceflow.com",
                "first_name": "Alex",
                "last_name": "Johnson",
                "is_active": True,
            },
        )
        if created:
            user.set_password("demo1234")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"  Created user: {username}"))
        else:
            self.stdout.write(f"  Using existing user: {username}")

        # ── Get or create workspace ──────────────────────────────
        workspace = Workspace.objects.filter(owner=user).first()
        if not workspace:
            workspace = Workspace.objects.create(
                name="Johnson Consulting",
                slug=f"johnson-consulting-{user.pk}",
                owner=user,
                currency="USD",
            )
            self.stdout.write(self.style.SUCCESS(f"  Created workspace: {workspace.name}"))

        WorkspaceMember.objects.get_or_create(
            user=user, workspace=workspace,
            defaults={"role": "owner"},
        )

        # ── Ensure profile is configured ─────────────────────────
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.current_workspace = workspace
        profile.company_name = "Johnson Consulting LLC"
        profile.business_email = "alex@johnsonconsulting.com"
        profile.business_phone = "+1 (650) 555-9000"
        profile.business_address = "500 Tech Row\nSan Francisco, CA 94105\nUnited States"
        profile.invoice_prefix = "INV"
        profile.invoice_start_number = 1
        profile.notify_payment_received = True
        profile.notify_invoice_viewed = True
        profile.notify_invoice_overdue = True
        profile.notify_weekly_summary = True
        profile.notify_security_alerts = True
        try:
            profile.save()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Profile save warning: {e}"))

        # ── Create clients ──────────────────────────────────────
        clients = []
        for cd in CLIENTS:
            client, _ = Client.objects.get_or_create(
                workspace=workspace,
                email=cd["email"],
                defaults={
                    "name": cd["name"],
                    "phone": cd["phone"],
                    "billing_city": cd["city"],
                    "billing_country": cd["country"],
                    "currency": cd["currency"],
                },
            )
            clients.append(client)
        self.stdout.write(self.style.SUCCESS(f"  Ensured {len(clients)} clients"))

        # ── Create invoices ─────────────────────────────────────
        invoice_statuses = [
            "paid", "paid", "paid", "sent", "overdue",
            "draft", "viewed", "part_paid", "paid", "sent",
            "paid", "overdue", "draft", "paid", "sent",
        ]
        today = date.today()
        invoice_count = 0

        for idx, status in enumerate(invoice_statuses):
            client = clients[idx % len(clients)]
            inv_num = f"INV-{(idx + 1):04d}"

            if Invoice.objects.filter(workspace=workspace, invoice_number=inv_num).exists():
                continue

            issue_days_ago = random.randint(5, 120)
            issue_date = today - timedelta(days=issue_days_ago)
            due_date = issue_date + timedelta(days=random.choice([15, 30, 45]))

            service_picks = random.sample(SERVICES, k=random.randint(1, 3))
            subtotal = sum(p[2] for p in service_picks)

            if client.currency == "NGN":
                subtotal = subtotal * Decimal("1550")

            tax_pct = Decimal("7.5")
            tax_total = (subtotal * tax_pct / Decimal("100")).quantize(Decimal("0.01"))
            total_amount = subtotal + tax_total

            invoice = Invoice.objects.create(
                workspace=workspace,
                client=client,
                created_by=user,
                invoice_number=inv_num,
                status=status,
                issue_date=issue_date,
                due_date=due_date,
                currency=client.currency,
                subtotal=subtotal,
                default_tax_rate=tax_pct,
                tax_total=tax_total,
                total_amount=total_amount,
                amount_paid=Decimal("0"),
                amount_due=total_amount,
                internal_notes="Thank you for your business. Payment is due by the date above.",
                terms_conditions="Payment terms: Net 30. Late payments may incur a 1.5% monthly charge.",
            )

            for sort_i, (svc_name, svc_desc, unit_price) in enumerate(service_picks):
                if client.currency == "NGN":
                    unit_price = unit_price * Decimal("1550")
                LineItem.objects.create(
                    invoice=invoice,
                    description=svc_name,
                    long_description=svc_desc,
                    quantity=Decimal("1.0000"),
                    unit_price=unit_price,
                    subtotal=unit_price,
                    total=unit_price,
                    sort_order=sort_i,
                )

            # Record payment
            if status in ("paid", "part_paid"):
                amount_paid = total_amount if status == "paid" else (total_amount * Decimal("0.5")).quantize(Decimal("0.01"))
                invoice.amount_paid = amount_paid
                invoice.amount_due = total_amount - amount_paid
                invoice.save(update_fields=["amount_paid", "amount_due"])

                Payment.objects.create(
                    workspace=workspace,
                    invoice=invoice,
                    amount=amount_paid,
                    currency=invoice.currency,
                    payment_date=timezone.make_aware(
                        timezone.datetime.combine(
                            due_date - timedelta(days=random.randint(1, 5)),
                            timezone.datetime.min.time()
                        )
                    ),
                    payment_method=random.choice(["bank_transfer", "paystack", "other"]),
                    status=Payment.Status.COMPLETED,
                    provider_reference=f"TXN-{invoice.invoice_number}",
                    net_amount=amount_paid,
                )

            invoice_count += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {invoice_count} new invoices"))

        # ── Ensure expense categories ────────────────────────────
        cat_map = {}
        for key, name in [
            ("software", "Software & SaaS"),
            ("equipment", "Hardware & Equipment"),
            ("travel", "Travel & Transport"),
            ("marketing", "Marketing & Advertising"),
            ("utilities", "Utilities & Office"),
            ("professional_services", "Professional Services"),
            ("meals_entertainment", "Meals & Entertainment"),
            ("other", "Miscellaneous"),
        ]:
            cat, _ = ExpenseCategory.objects.get_or_create(
                workspace=workspace, name=name,
                defaults={"color": "#6366f1"},
            )
            cat_map[key] = cat

        # ── Create expenses ─────────────────────────────────────
        expense_count = 0
        for idx, (desc, cat_key, amount, currency) in enumerate(EXPENSE_ITEMS):
            exp_num = f"EXP-{(idx + 1):04d}"
            if Expense.objects.filter(workspace=workspace, expense_number=exp_num).exists():
                continue
            expense_date = today - timedelta(days=random.randint(1, 90))
            cat = cat_map.get(cat_key, cat_map.get("other"))
            Expense.objects.create(
                workspace=workspace,
                expense_number=exp_num,
                description=desc,
                category=cat,
                created_by=user,
                amount=amount,
                tax_amount=Decimal("0"),
                total_amount=amount,
                base_currency_amount=amount,
                currency=currency,
                expense_date=expense_date,
                payment_method=random.choice(["cash", "credit_card", "bank_transfer"]),
                status="approved",
                is_billable=random.choice([True, False]),
            )
            expense_count += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {expense_count} expenses"))

        # ── Create estimates ────────────────────────────────────
        estimate_data = [
            ("Website Redesign Project", clients[0], "pending", Decimal("12500.00"), "USD"),
            ("Mobile App MVP", clients[1], "approved", Decimal("25000.00"), "USD"),
            ("Brand Strategy Package", clients[2], "sent", Decimal("7800.00"), "USD"),
            ("Annual Retainer Proposal", clients[4], "declined", Decimal("38400.00"), "USD"),
            ("Data Migration Services", clients[6], "approved", Decimal("9200.00"), "USD"),
        ]

        for est_desc, client, status, amount, currency in estimate_data:
            if Estimate.objects.filter(workspace=workspace, client=client, client_notes=est_desc).exists():
                continue
            est_num = f"EST-{random.randint(1000, 9999)}"
            while Estimate.objects.filter(workspace=workspace, estimate_number=est_num).exists():
                est_num = f"EST-{random.randint(1000, 9999)}"
            est = Estimate.objects.create(
                workspace=workspace,
                client=client,
                created_by=user,
                estimate_number=est_num,
                status=status,
                issue_date=today - timedelta(days=random.randint(5, 45)),
                expiry_date=today + timedelta(days=random.randint(10, 60)),
                currency=currency,
                subtotal=amount,
                tax_total=Decimal("0"),
                total_amount=amount,
                client_notes=est_desc,
                internal_notes="",
            )
            EstimateItem.objects.create(
                estimate=est,
                description=est_desc,
                quantity=Decimal("1.0000"),
                unit_price=amount,
                tax_rate=Decimal("0"),
                subtotal=amount,
                total=amount,
            )

        self.stdout.write(self.style.SUCCESS("  Ensured estimates"))

        # ── Create recurring schedules ─────────────────────────
        recurring_data = [
            ("Monthly retainer — Apex Tech", clients[0], RecurringSchedule.IntervalType.MONTHLY, "active", Decimal("3200.00"), "USD"),
            ("SEO retainer — Zenith Marketing", clients[1], RecurringSchedule.IntervalType.MONTHLY, "active", Decimal("2800.00"), "USD"),
            ("Analytics reports — DataStream", clients[4], RecurringSchedule.IntervalType.QUARTERLY, "active", Decimal("6500.00"), "USD"),
            ("Content package — Luminary Events", clients[6], RecurringSchedule.IntervalType.WEEKLY, "paused", Decimal("800.00"), "USD"),
        ]

        for desc, client, interval, status, base_amount, currency in recurring_data:
            if RecurringSchedule.objects.filter(workspace=workspace, description=desc).exists():
                continue
            start_date = today - timedelta(days=random.randint(30, 180))
            next_run = today + timedelta(days=random.randint(1, 30))
            RecurringSchedule.objects.create(
                workspace=workspace,
                client=client,
                created_by=user,
                description=desc,
                interval_type=interval,
                status=status,
                base_amount=base_amount,
                currency=currency,
                start_date=start_date,
                next_run_date=next_run,
                payment_terms_days=30,
                total_invoices_generated=random.randint(1, 8),
                idempotency_key=secrets.token_urlsafe(32),
            )

        self.stdout.write(self.style.SUCCESS("  Ensured recurring schedules"))
        self.stdout.write(self.style.SUCCESS(
            f"\n✅  Demo data ready! Login: username='{username}', password='demo1234'"
        ))
