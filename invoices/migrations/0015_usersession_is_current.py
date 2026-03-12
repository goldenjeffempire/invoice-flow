from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0014_fix_mfaprofile_secret_key_column'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersession',
            name='is_current',
            field=models.BooleanField(default=False),
        ),
    ]
