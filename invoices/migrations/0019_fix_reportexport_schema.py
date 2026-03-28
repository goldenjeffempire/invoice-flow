from django.db import migrations, models


def add_columns_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'invoices_reportexport'
        """)
        existing = {row[0] for row in cursor.fetchall()}

        if 'report_params' not in existing:
            cursor.execute("ALTER TABLE invoices_reportexport ADD COLUMN report_params jsonb NOT NULL DEFAULT '{}'")
        if 'export_format' not in existing:
            cursor.execute("ALTER TABLE invoices_reportexport ADD COLUMN export_format varchar(10) NOT NULL DEFAULT 'csv'")
        if 'file_name' not in existing:
            cursor.execute("ALTER TABLE invoices_reportexport ADD COLUMN file_name varchar(255) NOT NULL DEFAULT ''")
        if 'file_size' not in existing:
            cursor.execute("ALTER TABLE invoices_reportexport ADD COLUMN file_size integer NOT NULL DEFAULT 0")


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0018_repair_missing_tables'),
    ]

    operations = [
        migrations.RunPython(add_columns_if_missing, migrations.RunPython.noop),
    ]
