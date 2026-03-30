from django.db import migrations, models


def add_columns_if_missing(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
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

    elif vendor == "sqlite":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(invoices_reportexport)")
            existing = {row[1] for row in cursor.fetchall()}

            cols = [
                ("report_params", "text NOT NULL DEFAULT '{}'"),
                ("export_format", "varchar(10) NOT NULL DEFAULT 'csv'"),
                ("file_name", "varchar(255) NOT NULL DEFAULT ''"),
                ("file_size", "integer NOT NULL DEFAULT 0"),
            ]
            for col_name, col_def in cols:
                if col_name not in existing:
                    cursor.execute(
                        f"ALTER TABLE invoices_reportexport ADD COLUMN {col_name} {col_def}"
                    )


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0018_repair_missing_tables'),
    ]

    operations = [
        migrations.RunPython(add_columns_if_missing, migrations.RunPython.noop),
    ]
