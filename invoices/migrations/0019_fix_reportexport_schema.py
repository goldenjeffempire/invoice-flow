from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0018_repair_missing_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportexport',
            name='report_params',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='reportexport',
            name='export_format',
            field=models.CharField(
                choices=[('csv', 'CSV'), ('pdf', 'PDF'), ('excel', 'Excel')],
                default='csv',
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reportexport',
            name='file_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reportexport',
            name='file_size',
            field=models.PositiveIntegerField(default=0, help_text='File size in bytes'),
        ),
    ]
