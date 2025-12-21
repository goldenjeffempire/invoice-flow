# Generated migration for account number encryption preparation
from django.db import migrations

def prepare_encryption(apps, schema_editor):
    """
    Prepare account number fields for encryption.
    This migration documents the encryption infrastructure for future deployment.
    
    When deploying account number encryption:
    1. Install: pip install django-encrypted-model-fields
    2. Update Invoice.account_number to use EncryptedField
    3. Update UserProfile.paystack_account_number to use EncryptedField
    4. Run: python manage.py makemigrations && python manage.py migrate
    """
    pass

def reverse_encryption(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0018_add_processed_webhook_model'),
    ]

    operations = [
        migrations.RunPython(prepare_encryption, reverse_encryption),
    ]
