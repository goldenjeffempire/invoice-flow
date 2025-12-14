"""Management command to test Sentry error monitoring configuration."""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Test Sentry error monitoring configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--trigger-error",
            action="store_true",
            help="Trigger a test error to verify Sentry is capturing events",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Testing Sentry Error Monitoring Configuration..."))
        self.stdout.write("-" * 50)

        sentry_dsn = os.environ.get("SENTRY_DSN", "")
        is_debug = settings.DEBUG
        is_production = getattr(settings, "IS_PRODUCTION", False)

        self.stdout.write(f"SENTRY_DSN Configured: {self.style.SUCCESS('Yes') if sentry_dsn else self.style.ERROR('No')}")
        self.stdout.write(f"DEBUG Mode: {self.style.WARNING('True') if is_debug else self.style.SUCCESS('False')}")
        self.stdout.write(f"Production Mode: {self.style.SUCCESS('True') if is_production else self.style.WARNING('False')}")

        if not sentry_dsn:
            self.stdout.write(self.style.ERROR("\nSentry is not configured. Set SENTRY_DSN environment variable."))
            return

        if is_debug:
            self.stdout.write(self.style.WARNING("\nSentry is configured but DEBUG=True. Sentry only initializes when DEBUG=False."))
            self.stdout.write("Set DEBUG=False to enable Sentry error tracking.")
            return

        try:
            import sentry_sdk
            
            self.stdout.write(self.style.SUCCESS("\nSentry SDK is installed and DSN is configured!"))
            self.stdout.write(f"Environment: {'production' if is_production else 'development'}")
            
            if options["trigger_error"]:
                self.stdout.write("\nSending test event to Sentry...")
                event_id = sentry_sdk.capture_message("Test message from InvoiceFlow management command")
                if event_id:
                    self.stdout.write(self.style.SUCCESS(f"Test event sent! Event ID: {event_id}"))
                else:
                    self.stdout.write(self.style.WARNING("Event queued (check Sentry dashboard)"))
                self.stdout.write("Check your Sentry dashboard to verify the event was received.")
            else:
                self.stdout.write(self.style.SUCCESS("\nSentry is ready. Use --trigger-error to send a test event."))
        except ImportError:
            self.stdout.write(self.style.ERROR("\nsentry-sdk is not installed. Install it with: pip install sentry-sdk"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nError checking Sentry: {str(e)}"))
