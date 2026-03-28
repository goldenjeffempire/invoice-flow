import django.utils.timezone
from django.db import migrations, models


def add_columns_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:

        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'invoices_usersession'
        """)
        existing = {row[0] for row in cursor.fetchall()}
        if 'last_activity' not in existing:
            cursor.execute("ALTER TABLE invoices_usersession ADD COLUMN last_activity timestamptz NOT NULL DEFAULT now()")
        if 'is_active' not in existing:
            cursor.execute("ALTER TABLE invoices_usersession ADD COLUMN is_active boolean NOT NULL DEFAULT true")

        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'invoices_socialaccount'
        """)
        existing = {row[0] for row in cursor.fetchall()}
        if 'uid' not in existing:
            cursor.execute("ALTER TABLE invoices_socialaccount ADD COLUMN uid varchar(255) NOT NULL DEFAULT ''")

        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'invoices_sharedreportlink'
        """)
        existing = {row[0] for row in cursor.fetchall()}
        if 'report_params' not in existing:
            cursor.execute("ALTER TABLE invoices_sharedreportlink ADD COLUMN report_params jsonb NOT NULL DEFAULT '{}'")
        if 'name' not in existing:
            cursor.execute("ALTER TABLE invoices_sharedreportlink ADD COLUMN name varchar(255) NOT NULL DEFAULT ''")
        if 'last_viewed_at' not in existing:
            cursor.execute("ALTER TABLE invoices_sharedreportlink ADD COLUMN last_viewed_at timestamptz NULL")
        if 'updated_at' not in existing:
            cursor.execute("ALTER TABLE invoices_sharedreportlink ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now()")

        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'invoices_processedwebhook'
        """)
        existing = {row[0] for row in cursor.fetchall()}
        if 'created_at' not in existing:
            cursor.execute("ALTER TABLE invoices_processedwebhook ADD COLUMN created_at timestamptz NOT NULL DEFAULT now()")


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0019_fix_reportexport_schema'),
    ]

    operations = [
        migrations.RunPython(add_columns_if_missing, migrations.RunPython.noop),
    ]
