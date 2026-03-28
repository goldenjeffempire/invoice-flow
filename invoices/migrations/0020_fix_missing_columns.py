import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0019_fix_reportexport_schema'),
    ]

    operations = [
        # UserSession: add last_activity and is_active
        migrations.AddField(
            model_name='usersession',
            name='last_activity',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='usersession',
            name='is_active',
            field=models.BooleanField(default=True),
        ),

        # SocialAccount: add uid
        migrations.AddField(
            model_name='socialaccount',
            name='uid',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),

        # SharedReportLink: add report_params, name, last_viewed_at, updated_at
        migrations.AddField(
            model_name='sharedreportlink',
            name='report_params',
            field=models.JSONField(blank=True, default=dict, help_text='Report parameters like date range, filters'),
        ),
        migrations.AddField(
            model_name='sharedreportlink',
            name='name',
            field=models.CharField(blank=True, default='', max_length=255, help_text='Optional name for the shared report'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sharedreportlink',
            name='last_viewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sharedreportlink',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),

        # ProcessedWebhook: add created_at
        migrations.AddField(
            model_name='processedwebhook',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
