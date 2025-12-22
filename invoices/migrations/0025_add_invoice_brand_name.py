from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0024_add_missing_userprofile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='brand_name',
            field=models.CharField(max_length=200, default=''),
        ),
    ]
