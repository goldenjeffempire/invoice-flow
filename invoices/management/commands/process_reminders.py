from django.core.management.base import BaseCommand
from invoices.services import AutomatedReminderService

class Command(BaseCommand):
    help = 'Processes pending automated reminders'

    def handle(self, *args, **options):
        self.stdout.write('Processing pending reminders...')
        sent_count = AutomatedReminderService.process_pending_reminders()
        self.stdout.write(self.style.SUCCESS(f'Successfully processed reminders. Sent: {sent_count}'))
