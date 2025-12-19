from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0007_add_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='business_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='business_phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='business_address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_invoice_created',
            field=models.BooleanField(default=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_payment_received',
            field=models.BooleanField(default=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_invoice_viewed',
            field=models.BooleanField(default=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_invoice_overdue',
            field=models.BooleanField(default=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_weekly_summary',
            field=models.BooleanField(default=False, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_security_alerts',
            field=models.BooleanField(default=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='notify_password_changes',
            field=models.BooleanField(default=True, blank=True),
        ),
    ]
