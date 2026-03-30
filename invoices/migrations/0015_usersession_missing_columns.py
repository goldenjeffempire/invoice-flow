from django.db import migrations, models


def add_usersession_columns(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        stmts = [
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS device_fingerprint varchar(64) NOT NULL DEFAULT '';",
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS browser varchar(50) NOT NULL DEFAULT '';",
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS os varchar(50) NOT NULL DEFAULT '';",
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS device_type varchar(20) NOT NULL DEFAULT 'desktop';",
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS location varchar(100) NOT NULL DEFAULT '';",
            "ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS is_current boolean NOT NULL DEFAULT false;",
            "CREATE INDEX IF NOT EXISTS invoices_usersession_device_fp_idx ON invoices_usersession (device_fingerprint);",
        ]
        for stmt in stmts:
            schema_editor.execute(stmt)

    elif vendor == "sqlite":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(invoices_usersession)")
            existing = {row[1] for row in cursor.fetchall()}

        cols = [
            ("device_fingerprint", "varchar(64) NOT NULL DEFAULT ''"),
            ("browser", "varchar(50) NOT NULL DEFAULT ''"),
            ("os", "varchar(50) NOT NULL DEFAULT ''"),
            ("device_type", "varchar(20) NOT NULL DEFAULT 'desktop'"),
            ("location", "varchar(100) NOT NULL DEFAULT ''"),
            ("is_current", "bool NOT NULL DEFAULT 0"),
        ]
        for col_name, col_def in cols:
            if col_name not in existing:
                schema_editor.execute(
                    f"ALTER TABLE invoices_usersession ADD COLUMN {col_name} {col_def};"
                )


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0014_fix_mfaprofile_secret_key_column'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_usersession_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='usersession',
                    name='device_fingerprint',
                    field=models.CharField(blank=True, db_index=True, max_length=64),
                ),
                migrations.AddField(
                    model_name='usersession',
                    name='browser',
                    field=models.CharField(blank=True, max_length=50),
                ),
                migrations.AddField(
                    model_name='usersession',
                    name='os',
                    field=models.CharField(blank=True, max_length=50),
                ),
                migrations.AddField(
                    model_name='usersession',
                    name='device_type',
                    field=models.CharField(default='desktop', max_length=20),
                ),
                migrations.AddField(
                    model_name='usersession',
                    name='location',
                    field=models.CharField(blank=True, max_length=100),
                ),
                migrations.AddField(
                    model_name='usersession',
                    name='is_current',
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]
