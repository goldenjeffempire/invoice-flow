from django.db import migrations, models


ADD_COLUMNS_SQL = """
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS device_fingerprint varchar(64) NOT NULL DEFAULT '';
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS browser varchar(50) NOT NULL DEFAULT '';
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS os varchar(50) NOT NULL DEFAULT '';
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS device_type varchar(20) NOT NULL DEFAULT 'desktop';
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS location varchar(100) NOT NULL DEFAULT '';
ALTER TABLE invoices_usersession ADD COLUMN IF NOT EXISTS is_current boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS invoices_usersession_device_fp_idx ON invoices_usersession (device_fingerprint);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0014_fix_mfaprofile_secret_key_column'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(sql=ADD_COLUMNS_SQL, reverse_sql=migrations.RunSQL.noop),
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
