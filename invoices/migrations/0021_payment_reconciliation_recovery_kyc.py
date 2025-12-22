# Generated migration for payment reconciliation, recovery, and KYC

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0020_account_encryption_preparation'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentReconciliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending Reconciliation'), ('in_progress', 'Reconciliation In Progress'), ('verified', 'Verified with Paystack'), ('mismatch', 'Amount/Status Mismatch'), ('recovered', 'Recovered via Retry'), ('failed', 'Reconciliation Failed')], default='pending', max_length=20)),
                ('paystack_status', models.CharField(blank=True, max_length=50)),
                ('local_status', models.CharField(max_length=50)),
                ('amount_match', models.BooleanField(default=True)),
                ('currency_match', models.BooleanField(default=True)),
                ('status_match', models.BooleanField(default=True)),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('last_attempt', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reconciliation', to='invoices.payment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_reconciliations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentRecovery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('strategy', models.CharField(choices=[('immediate_retry', 'Immediate Retry'), ('scheduled_retry', 'Scheduled Retry (30s)'), ('webhook_retry', 'Webhook Verification'), ('manual_verification', 'Manual Verification')], default='webhook_retry', max_length=30)),
                ('attempt_number', models.PositiveIntegerField(default=1)),
                ('max_attempts', models.PositiveIntegerField(default=3)),
                ('error_reason', models.TextField(blank=True)),
                ('error_code', models.CharField(blank=True, max_length=50)),
                ('is_successful', models.BooleanField(default=False)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('next_retry_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recovery_attempts', to='invoices.payment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_recoveries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-attempted_at'],
            },
        ),
        migrations.CreateModel(
            name='UserIdentityVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('unverified', 'Not Verified'), ('pending', 'Pending Review'), ('verified', 'Verified'), ('rejected', 'Rejected'), ('expired', 'Verification Expired')], default='unverified', max_length=20)),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=50)),
                ('country', models.CharField(blank=True, max_length=100)),
                ('document_type', models.CharField(blank=True, choices=[('passport', 'Passport'), ('national_id', 'National ID'), ('drivers_license', "Driver's License"), ('bvn', 'Bank Verification Number (BVN)')], max_length=20)),
                ('document_number', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('document_expiry', models.DateField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('verified_by', models.CharField(blank=True, max_length=100)),
                ('rejection_reason', models.TextField(blank=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='identity_verification', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='paymentrecovery',
            index=models.Index(fields=['user', 'is_successful'], name='invoices_pa_user_id_7f8c9e_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentrecovery',
            index=models.Index(fields=['next_retry_at'], name='invoices_pa_next_re_3a2b8c_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentreconciliation',
            index=models.Index(fields=['user', 'status'], name='invoices_pa_user_id_9f7b6e_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentreconciliation',
            index=models.Index(fields=['status', '-created_at'], name='invoices_pa_status_2c4e8b_idx'),
        ),
        migrations.AddIndex(
            model_name='useridentityverification',
            index=models.Index(fields=['status'], name='invoices_us_status_1a5c7d_idx'),
        ),
        migrations.AddIndex(
            model_name='useridentityverification',
            index=models.Index(fields=['user', 'status'], name='invoices_us_user_id_3f7b2e_idx'),
        ),
    ]
