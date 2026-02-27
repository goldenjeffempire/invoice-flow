"""Management command to guide SendGrid email verification setup."""

from django.core.management.base import BaseCommand

from invoices.models import Invoice


class Command(BaseCommand):
    help = "Guide and verify SendGrid email setup"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("SENDGRID EMAIL VERIFICATION SETUP GUIDE"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))

        # Get current business email
        invoice = Invoice.objects.first()
        if not invoice:
            self.stdout.write(self.style.WARNING("⚠️  No invoices found. Create an invoice first."))
            return

        business_email = invoice.business_email

        self.stdout.write(self.style.WARNING(f"Your business email: {business_email}\n"))

        self.stdout.write(self.style.SUCCESS("WHAT YOU NEED TO DO:"))
        self.stdout.write(
            """
1. Go to SendGrid Dashboard
   https://app.sendgrid.com/settings/sender_authentication

2. Click "Create New" or "Create Sender"

3. Enter these details:
   • From Email: {}
   • From Name: {}

4. Click "Create"

5. Check your email ({})
   • Find the verification email from SendGrid
   • Click the verification link

6. Wait 1-2 minutes for SendGrid to confirm

7. Test by sending an invoice email in your app

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHY THIS IS NEEDED:

SendGrid requires proof that you own the email address you're sending from.
This is a security feature to prevent spam.

ONCE VERIFIED:

✅ Emails will send automatically
✅ PDF attachments included
✅ All 6 email types working
✅ No more 403 errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TROUBLESHOOTING:

Still getting 403 after verification?
  → Wait 5 minutes (SendGrid backend propagation)
  → Check you're using the EXACT same email address
  → Refresh your browser

Can't find verification email?
  → Check spam/junk folder
  → Verify email is correct in SendGrid settings
  → Request new verification link

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """.format(
                business_email, invoice.business_name, business_email
            )
        )

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Run this command anytime to see these instructions."))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))
