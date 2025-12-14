"""Management command to test Paystack payment configuration."""
from django.core.management.base import BaseCommand
from invoices.paystack_service import PaystackService


class Command(BaseCommand):
    help = "Test Paystack payment configuration and API connectivity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list-banks",
            action="store_true",
            help="List available banks to verify API connectivity",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Testing Paystack Payment Configuration..."))
        self.stdout.write("-" * 50)

        service = PaystackService()

        self.stdout.write(f"Secret Key Configured: {self.style.SUCCESS('Yes') if service.secret_key else self.style.ERROR('No')}")
        self.stdout.write(f"Public Key Configured: {self.style.SUCCESS('Yes') if service.public_key else self.style.ERROR('No')}")
        self.stdout.write(f"Service Ready: {self.style.SUCCESS('Yes') if service.is_configured else self.style.ERROR('No')}")

        if not service.is_configured:
            self.stdout.write(self.style.ERROR("\nPaystack is not configured. Set PAYSTACK_SECRET_KEY and PAYSTACK_PUBLIC_KEY."))
            return

        self.stdout.write("\nTesting API connectivity...")
        
        result = service.list_banks()
        
        if result.get("status") == "success":
            banks = result.get("banks", [])
            self.stdout.write(self.style.SUCCESS(f"API Connection: Successful"))
            self.stdout.write(f"Available Banks: {len(banks)}")
            
            if options["list_banks"] and banks:
                self.stdout.write("\nSample Banks:")
                for bank in banks[:10]:
                    self.stdout.write(f"  - {bank.get('name')} ({bank.get('code')})")
                if len(banks) > 10:
                    self.stdout.write(f"  ... and {len(banks) - 10} more")
        else:
            self.stdout.write(self.style.ERROR(f"API Connection Failed: {result.get('message', 'Unknown error')}"))
            return

        self.stdout.write(self.style.SUCCESS("\nPaystack configuration verified and ready for payments!"))
