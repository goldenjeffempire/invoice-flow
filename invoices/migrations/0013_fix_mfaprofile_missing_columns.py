"""
Migration: Add missing columns to invoices_mfaprofile.

The production database (Render/PostgreSQL) was provisioned from an older
schema version that did not include the columns added later to MFAProfile
(secret, recovery_codes, recovery_codes_viewed, last_used, updated_at).
Migration 0001 is already recorded as applied in that database, so Django
never ran the CREATE TABLE with those columns.

This migration repairs the table safely using IF NOT EXISTS (PostgreSQL) or
by inspecting PRAGMA table_info (SQLite), so it is idempotent and harmless
if the columns already exist.
"""

from django.db import migrations


def add_missing_mfaprofile_columns(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        stmts = [
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS secret VARCHAR(64) NOT NULL DEFAULT '';",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT FALSE;",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS recovery_codes JSONB NOT NULL DEFAULT '[]';",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS recovery_codes_viewed BOOLEAN NOT NULL DEFAULT FALSE;",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS last_used TIMESTAMPTZ;",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;",
            "ALTER TABLE invoices_mfaprofile ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;",
        ]
        for stmt in stmts:
            schema_editor.execute(stmt)

    elif vendor == "sqlite":
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(invoices_mfaprofile)")
            existing = {row[1] for row in cursor.fetchall()}

        sqlite_cols = [
            ("secret", "varchar(64) NOT NULL DEFAULT ''"),
            ("is_enabled", "bool NOT NULL DEFAULT 0"),
            ("recovery_codes", "text NOT NULL DEFAULT '[]'"),
            ("recovery_codes_viewed", "bool NOT NULL DEFAULT 0"),
            ("last_used", "datetime NULL"),
            ("created_at", "datetime NULL"),
            ("updated_at", "datetime NULL"),
        ]
        for col_name, col_def in sqlite_cols:
            if col_name not in existing:
                schema_editor.execute(
                    f"ALTER TABLE invoices_mfaprofile ADD COLUMN {col_name} {col_def};"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0012_newsletter_campaign"),
    ]

    operations = [
        migrations.RunPython(
            add_missing_mfaprofile_columns,
            migrations.RunPython.noop,
        ),
    ]
