from django.core.management.base import BaseCommand
from django.utils import timezone
from invoices.services import AutomatedReminderService

class Command(BaseCommand):
    help = 'Processes pending automated reminders'

    def handle(self, *args, **options):
        self.stdout.write('Processing pending reminders...')
        sent_count = AutomatedReminderService.process_pending_reminders()
        self.stdout.write(self.style.SUCCESS(f'Successfully sent {sent_count} reminders'))
