from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0023_add_email_delivery_and_retry'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
    ]
