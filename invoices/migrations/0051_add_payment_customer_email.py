from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0050_restore_payment_id_autofield"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="customer_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
