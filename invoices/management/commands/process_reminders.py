from django.core.management.base import BaseCommand
from invoices.reminder_service import ReminderSchedulingService

class Command(BaseCommand):
    help = 'Processes pending automated reminders and sends them via SendGrid.'

    def handle(self, *args, **options):
        self.stdout.write('Processing pending reminders...')
        try:
            processed_count = ReminderSchedulingService.process_pending_reminders()
            self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed_count} reminders.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Critical failure in reminder processing: {e}'))
