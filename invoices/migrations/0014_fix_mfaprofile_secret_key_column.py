"""
Migration: Neutralize the old `secret_key` column on invoices_mfaprofile.

The production PostgreSQL database was created with an older schema that
named the MFA secret column `secret_key` (NOT NULL, no default). The current
model and code use `secret`. Migration 0013 added the `secret` column, but
the old `secret_key` column remains with its NOT NULL constraint and no
default, causing every INSERT to violate the constraint.

This migration:
  1. Gives `secret_key` a safe empty-string default so existing INSERTs
     (which don't include that column) no longer fail.
  2. Also drops the NOT NULL constraint so future rows are never blocked.

It is fully idempotent: if `secret_key` does not exist, nothing happens.
"""

from django.db import migrations


def fix_secret_key_column(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        with schema_editor.connection.cursor() as cursor:
            # Check whether secret_key column exists
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'invoices_mfaprofile'
                  AND column_name = 'secret_key';
            """)
            exists = cursor.fetchone() is not None

        if exists:
            schema_editor.execute(
                "ALTER TABLE invoices_mfaprofile "
                "ALTER COLUMN secret_key SET DEFAULT '';"
            )
            schema_editor.execute(
                "ALTER TABLE invoices_mfaprofile "
                "ALTER COLUMN secret_key DROP NOT NULL;"
            )
            # Back-fill any existing NULLs that slipped through
            schema_editor.execute(
                "UPDATE invoices_mfaprofile "
                "SET secret_key = '' WHERE secret_key IS NULL;"
            )

    elif vendor == "sqlite":
        # SQLite doesn't support ALTER COLUMN; column defaults live only in
        # the CREATE TABLE statement, which we cannot change. The column is
        # already nullable in SQLite by default, so no action needed.
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0013_fix_mfaprofile_missing_columns"),
    ]

    operations = [
        migrations.RunPython(
            fix_secret_key_column,
            migrations.RunPython.noop,
        ),
    ]
