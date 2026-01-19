from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0049_reintroduce_processed_webhook"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
