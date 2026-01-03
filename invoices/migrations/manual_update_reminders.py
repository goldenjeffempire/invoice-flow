from django.db import migrations, models
from django.utils import timezone

def create_default_settings(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserReminderSettings = apps.get_model('invoices', 'UserReminderSettings')
    for user in User.objects.all():
        UserReminderSettings.objects.get_or_create(user=user)

class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userremindersettings',
            name='max_retries',
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name='userremindersettings',
            name='retry_delay_minutes',
            field=models.IntegerField(default=60),
        ),
        migrations.AddField(
            model_name='userremindersettings',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userremindersettings',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(create_default_settings),
    ]
