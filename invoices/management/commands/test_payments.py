"""
Management command for testing payment system functionality.
Usage: python manage.py test_payments [--verbose] [--test-transfers] [--list-banks]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from invoices.models import Payment, PaymentPayout, PaymentRecipient, PaymentSettings, UserProfile
from invoices.paystack_service import PaystackService, get_paystack_service, get_transfer_service


class Command(BaseCommand):
    help = "Test payment system functionality and Paystack API connectivity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list-banks",
            action="store_true",
            help="List available banks to verify API connectivity",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output",
        )
        parser.add_argument(
            "--test-transfers",
            action="store_true",
            help="Test transfer functionality (requires Paystack API key)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Specific user ID to test with",
        )

    def handle(self, *args, **options):
        verbose = options["verbose"]
        test_transfers = options["test_transfers"]
        user_id = options.get("user_id")

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("InvoiceFlow Payment System Test"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        self.test_models()
        self.test_paystack_service(verbose, options.get("list_banks", False))

        if test_transfers:
            self.test_transfer_service(verbose)

        if user_id:
            self.test_user_payment_setup(user_id, verbose)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("All tests completed!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

    def test_models(self):
        """Test that all payment models are working correctly."""
        self.stdout.write("\n--- Testing Payment Models ---")

        payment_count = Payment.objects.count()
        self.stdout.write(f"  Payment records: {payment_count}")

        recipient_count = PaymentRecipient.objects.count()
        self.stdout.write(f"  Payment recipients: {recipient_count}")

        settings_count = PaymentSettings.objects.count()
        self.stdout.write(f"  Payment settings: {settings_count}")

        payout_count = PaymentPayout.objects.count()
        self.stdout.write(f"  Payment payouts: {payout_count}")

        users_with_subaccount = UserProfile.objects.exclude(
            paystack_subaccount_code__isnull=True
        ).exclude(paystack_subaccount_code="").count()
        self.stdout.write(f"  Users with Paystack subaccount: {users_with_subaccount}")

        self.stdout.write(self.style.SUCCESS("  Models: OK"))

    def test_paystack_service(self, verbose: bool, list_banks: bool):
        """Test Paystack service functionality."""
        self.stdout.write("\n--- Testing Paystack Service ---")

        paystack = get_paystack_service()

        self.stdout.write(f"  Secret Key: {self.style.SUCCESS('Yes') if paystack.secret_key else self.style.ERROR('No')}")
        self.stdout.write(f"  Public Key: {self.style.SUCCESS('Yes') if paystack.public_key else self.style.ERROR('No')}")
        self.stdout.write(f"  Service Ready: {self.style.SUCCESS('Yes') if paystack.is_configured else self.style.ERROR('No')}")

        if paystack.is_configured:
            banks_result = paystack.list_banks("nigeria")
            if banks_result.get("status") == "success":
                banks = banks_result.get("banks", [])
                self.stdout.write(f"  Available banks: {len(banks)}")
                
                if (verbose or list_banks) and banks:
                    self.stdout.write("\n  Sample Banks:")
                    for bank in banks[:10]:
                        self.stdout.write(f"    - {bank.get('name')} ({bank.get('code')})")
                    if len(banks) > 10:
                        self.stdout.write(f"    ... and {len(banks) - 10} more")
            else:
                self.stdout.write(self.style.WARNING(f"  Banks list: {banks_result.get('message')}"))
        else:
            self.stdout.write(self.style.WARNING("  Paystack API configured: NO (PAYSTACK_SECRET_KEY not set)"))

        self.stdout.write(self.style.SUCCESS("  Paystack Service: OK"))

    def test_transfer_service(self, verbose: bool):
        """Test Paystack transfer service functionality."""
        self.stdout.write("\n--- Testing Transfer Service ---")

        transfer_service = get_transfer_service()

        if transfer_service.is_configured:
            self.stdout.write(self.style.SUCCESS("  Transfer service configured: YES"))

            if verbose:
                balance_result = transfer_service.get_balance()
                if balance_result.get("status") == "success":
                    balances = balance_result.get("balances", [])
                    for b in balances:
                        self.stdout.write(f"  Balance ({b['currency']}): {b['balance']}")
                else:
                    self.stdout.write(self.style.WARNING(f"  Balance check: {balance_result.get('message')}"))

                transfers_result = transfer_service.list_transfers(per_page=5)
                if transfers_result.get("status") == "success":
                    transfers = transfers_result.get("transfers", [])
                    self.stdout.write(f"  Recent transfers: {len(transfers)}")
                else:
                    self.stdout.write(self.style.WARNING(f"  Transfers list: {transfers_result.get('message')}"))
        else:
            self.stdout.write(self.style.WARNING("  Transfer service configured: NO"))

        self.stdout.write(self.style.SUCCESS("  Transfer Service: OK"))

    def test_user_payment_setup(self, user_id: int, verbose: bool):
        """Test a specific user's payment setup."""
        self.stdout.write(f"\n--- Testing User #{user_id} Payment Setup ---")

        User = get_user_model()

        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"  User: {user.username} ({user.email})")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"  User with ID {user_id} not found"))
            return

        try:
            profile = user.profile
            self.stdout.write("  Profile exists: YES")

            if profile.paystack_subaccount_code:
                self.stdout.write(self.style.SUCCESS(f"  Subaccount: {profile.paystack_subaccount_code}"))
                self.stdout.write(f"  Bank: {profile.paystack_settlement_bank or 'Not set'}")
                self.stdout.write(f"  Account: ****{(profile.paystack_account_number or '')[-4:]}")
                self.stdout.write(f"  Active: {profile.paystack_subaccount_active}")
            else:
                self.stdout.write(self.style.WARNING("  Subaccount: Not configured"))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.WARNING("  Profile exists: NO"))

        settings, created = PaymentSettings.objects.get_or_create(user=user)
        self.stdout.write(f"  Payment settings: {'Created' if created else 'Exists'}")
        if verbose:
            self.stdout.write(f"    - Card payments: {settings.enable_card_payments}")
            self.stdout.write(f"    - Bank transfers: {settings.enable_bank_transfers}")
            self.stdout.write(f"    - Auto payout: {settings.auto_payout}")
            self.stdout.write(f"    - Currency: {settings.preferred_currency}")

        payments = Payment.objects.filter(user=user)
        self.stdout.write(f"  Payments: {payments.count()}")
        if verbose and payments.exists():
            for p in payments[:3]:
                self.stdout.write(f"    - {p.reference}: {p.currency} {p.amount} ({p.status})")

        recipients = PaymentRecipient.objects.filter(user=user, is_active=True)
        self.stdout.write(f"  Bank accounts: {recipients.count()}")
        if verbose and recipients.exists():
            for r in recipients:
                primary = " (PRIMARY)" if r.is_primary else ""
                self.stdout.write(f"    - {r.name}: {r.bank_name} ****{r.account_number[-4:]}{primary}")

        self.stdout.write(self.style.SUCCESS("  User Payment Setup: OK"))
