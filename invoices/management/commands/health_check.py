"""Management command for comprehensive system health check."""
import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = "Run comprehensive health checks on all system components"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("InvoiceFlow System Health Check"))
        self.stdout.write("=" * 60)
        
        checks_passed = 0
        checks_failed = 0

        checks_passed, checks_failed = self._check_database(checks_passed, checks_failed)
        checks_passed, checks_failed = self._check_email(checks_passed, checks_failed)
        checks_passed, checks_failed = self._check_payments(checks_passed, checks_failed)
        checks_passed, checks_failed = self._check_sentry(checks_passed, checks_failed)
        checks_passed, checks_failed = self._check_security(checks_passed, checks_failed)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"Results: {self.style.SUCCESS(f'{checks_passed} passed')}, {self.style.ERROR(f'{checks_failed} failed') if checks_failed else f'{checks_failed} failed'}")
        
        if checks_failed == 0:
            self.stdout.write(self.style.SUCCESS("\nAll systems are operational!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n{checks_failed} check(s) need attention."))

    def _check_database(self, passed, failed):
        self.stdout.write("\n[Database]")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(f"  Connection: {self.style.SUCCESS('OK')}")
            passed += 1
        except Exception as e:
            self.stdout.write(f"  Connection: {self.style.ERROR('FAILED')} - {str(e)}")
            failed += 1
        return passed, failed

    def _check_email(self, passed, failed):
        self.stdout.write("\n[Email - SendGrid]")
        try:
            from invoices.sendgrid_service import SendGridEmailService
            service = SendGridEmailService()
            if service.is_configured:
                self.stdout.write(f"  API Key: {self.style.SUCCESS('Configured')}")
                passed += 1
            else:
                self.stdout.write(f"  API Key: {self.style.ERROR('Not Configured')}")
                failed += 1
            self.stdout.write(f"  From Email: {service.from_email}")
        except Exception as e:
            self.stdout.write(f"  Status: {self.style.ERROR('FAILED')} - {str(e)}")
            failed += 1
        return passed, failed

    def _check_payments(self, passed, failed):
        self.stdout.write("\n[Payments - Paystack]")
        try:
            from invoices.paystack_service import PaystackService
            service = PaystackService()
            if service.is_configured:
                self.stdout.write(f"  Secret Key: {self.style.SUCCESS('Configured')}")
                passed += 1
                result = service.list_banks()
                if result.get("status") == "success":
                    self.stdout.write(f"  API Connection: {self.style.SUCCESS('OK')}")
                    passed += 1
                else:
                    self.stdout.write(f"  API Connection: {self.style.ERROR('FAILED')}")
                    failed += 1
            else:
                self.stdout.write(f"  Secret Key: {self.style.ERROR('Not Configured')}")
                failed += 1
        except Exception as e:
            self.stdout.write(f"  Status: {self.style.ERROR('FAILED')} - {str(e)}")
            failed += 1
        return passed, failed

    def _check_sentry(self, passed, failed):
        self.stdout.write("\n[Error Monitoring - Sentry]")
        sentry_dsn = os.environ.get("SENTRY_DSN", "")
        if sentry_dsn:
            self.stdout.write(f"  DSN: {self.style.SUCCESS('Configured')}")
            passed += 1
            if not settings.DEBUG:
                try:
                    import sentry_sdk
                    self.stdout.write(f"  SDK Active: {self.style.SUCCESS('Yes (DSN configured)')}")
                    passed += 1
                except ImportError:
                    self.stdout.write(f"  SDK Active: {self.style.WARNING('sentry-sdk not installed')}")
                    failed += 1
            else:
                self.stdout.write(f"  SDK Active: {self.style.WARNING('Disabled (DEBUG=True)')}")
        else:
            self.stdout.write(f"  DSN: {self.style.ERROR('Not Configured')}")
            failed += 1
        return passed, failed

    def _check_security(self, passed, failed):
        self.stdout.write("\n[Security]")
        
        secret_key = os.environ.get("SECRET_KEY", "")
        if secret_key and not secret_key.startswith("django-insecure-"):
            self.stdout.write(f"  SECRET_KEY: {self.style.SUCCESS('Secure')}")
            passed += 1
        else:
            self.stdout.write(f"  SECRET_KEY: {self.style.ERROR('Insecure')}")
            failed += 1

        encryption_salt = os.environ.get("ENCRYPTION_SALT", "")
        if encryption_salt and encryption_salt != "dev-salt-only-for-local-testing":
            self.stdout.write(f"  ENCRYPTION_SALT: {self.style.SUCCESS('Secure')}")
            passed += 1
        else:
            self.stdout.write(f"  ENCRYPTION_SALT: {self.style.ERROR('Insecure')}")
            failed += 1

        if not settings.DEBUG:
            self.stdout.write(f"  DEBUG Mode: {self.style.SUCCESS('Disabled')}")
            passed += 1
        else:
            self.stdout.write(f"  DEBUG Mode: {self.style.WARNING('Enabled')}")
            failed += 1

        return passed, failed
