"""Management command to test email sending functionality."""
import json
from django.core.management.base import BaseCommand, CommandError
from invoices.sendgrid_service import SendGridEmailService


class Command(BaseCommand):
    help = "Test SendGrid email configuration and send a test email"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            help="Email address to send test email to",
        )
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Only check configuration without sending email",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Testing SendGrid Email Configuration..."))
        self.stdout.write("-" * 50)

        service = SendGridEmailService()

        self.stdout.write(f"API Key Configured: {self.style.SUCCESS('Yes') if service.is_configured else self.style.ERROR('No')}")
        self.stdout.write(f"From Email: {service.from_email}")
        self.stdout.write(f"Platform Name: {service.platform_from_name}")

        template_status = []
        for name, template_id in service.TEMPLATE_IDS.items():
            status = self.style.SUCCESS("Set") if template_id else self.style.WARNING("Not Set")
            template_status.append(f"  - {name}: {status}")
        
        self.stdout.write("\nTemplate IDs:")
        for status in template_status:
            self.stdout.write(status)

        if not service.is_configured:
            self.stdout.write(self.style.ERROR("\nSendGrid is not configured. Set SENDGRID_API_KEY environment variable."))
            return

        if options["check_only"]:
            self.stdout.write(self.style.SUCCESS("\nConfiguration check complete. SendGrid is ready."))
            return

        to_email = options.get("to")
        if not to_email:
            self.stdout.write(self.style.WARNING("\nNo --to email specified. Use --to=email@example.com to send a test email."))
            self.stdout.write(self.style.SUCCESS("Configuration check passed."))
            return

        self.stdout.write(f"\nSending test email to: {to_email}")

        result = service._send_simple_email(
            from_email=service.from_email,
            from_name="InvoiceFlow Test",
            to_email=to_email,
            subject="InvoiceFlow Email Test - Configuration Verified",
            template_data={
                "message": "This is a test email from InvoiceFlow to verify your email configuration is working correctly.",
                "timestamp": "Sent via management command",
            },
            reply_to_email=None,
        )

        if result.get("status") == "sent":
            self.stdout.write(self.style.SUCCESS(f"\nTest email sent successfully!"))
            self.stdout.write(f"Message ID: {result.get('message_id', 'N/A')}")
        else:
            self.stdout.write(self.style.ERROR(f"\nFailed to send test email: {result.get('message', 'Unknown error')}"))
