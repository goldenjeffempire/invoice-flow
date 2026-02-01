from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import secrets


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invoices', '0003_invoice_lifecycle_rebuild'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RecurringInvoice',
        ),
        migrations.CreateModel(
            name='RecurringSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(help_text='Brief description of recurring charge', max_length=255)),
                ('interval_type', models.CharField(choices=[('weekly', 'Weekly'), ('biweekly', 'Every 2 Weeks'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly'), ('custom', 'Custom Interval')], default='monthly', max_length=20)),
                ('custom_interval_days', models.PositiveIntegerField(blank=True, help_text='Days between invoices for custom interval', null=True)),
                ('start_date', models.DateField(help_text='When to start generating invoices')),
                ('end_date', models.DateField(blank=True, help_text='Optional end date for the schedule', null=True)),
                ('next_run_date', models.DateField(db_index=True, help_text='Next scheduled invoice generation date')),
                ('last_run_date', models.DateField(blank=True, null=True)),
                ('timezone', models.CharField(default='UTC', help_text='Timezone for schedule execution', max_length=50)),
                ('status', models.CharField(choices=[('active', 'Active'), ('paused', 'Paused'), ('cancelled', 'Cancelled'), ('completed', 'Completed'), ('failed', 'Failed (Retry Exhausted)')], db_index=True, default='active', max_length=20)),
                ('paused_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('cancellation_reason', models.TextField(blank=True)),
                ('proration_enabled', models.BooleanField(default=False, help_text='Prorate partial periods')),
                ('anchor_day', models.PositiveSmallIntegerField(blank=True, help_text='Day of month to anchor billing (1-31)', null=True)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('base_amount', models.DecimalField(decimal_places=2, help_text='Base invoice amount before tax', max_digits=15)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('line_items_template', models.JSONField(blank=True, default=list, help_text='Template line items for generated invoices')),
                ('invoice_terms', models.TextField(blank=True, help_text='Terms to include on generated invoices')),
                ('invoice_notes', models.TextField(blank=True, help_text='Notes to include on generated invoices')),
                ('payment_terms_days', models.PositiveIntegerField(default=30, help_text='Days until due date from issue')),
                ('auto_send', models.BooleanField(default=True, help_text='Automatically send invoice to client')),
                ('retry_enabled', models.BooleanField(default=True)),
                ('max_retry_attempts', models.PositiveSmallIntegerField(default=3, help_text='Max payment retry attempts')),
                ('retry_interval_hours', models.PositiveIntegerField(default=24, help_text='Hours between retry attempts')),
                ('retry_backoff_multiplier', models.DecimalField(decimal_places=1, default=Decimal('2.0'), help_text='Backoff multiplier for retries', max_digits=3)),
                ('current_retry_count', models.PositiveSmallIntegerField(default=0)),
                ('next_retry_at', models.DateTimeField(blank=True, null=True)),
                ('failure_notification_sent', models.BooleanField(default=False)),
                ('idempotency_key', models.CharField(db_index=True, max_length=64, unique=True)),
                ('total_invoices_generated', models.PositiveIntegerField(default=0)),
                ('total_amount_billed', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_schedules', to='invoices.client')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_schedules', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_schedules', to='invoices.workspace')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ScheduleExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateField(help_text='Start of billing period')),
                ('period_end', models.DateField(help_text='End of billing period')),
                ('scheduled_date', models.DateField(help_text='When this execution was scheduled to run')),
                ('executed_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')], default='pending', max_length=20)),
                ('amount_generated', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('prorated_amount', models.DecimalField(blank=True, decimal_places=2, help_text='Prorated amount if applicable', max_digits=15, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('retry_count', models.PositiveSmallIntegerField(default=0)),
                ('idempotency_key', models.CharField(db_index=True, max_length=64, unique=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='schedule_executions', to='invoices.invoice')),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='invoices.recurringschedule')),
            ],
            options={
                'ordering': ['-executed_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt_number', models.PositiveSmallIntegerField(default=1)),
                ('attempted_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('currency', models.CharField(max_length=3)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('provider', models.CharField(blank=True, max_length=50)),
                ('provider_transaction_id', models.CharField(blank=True, max_length=255)),
                ('error_code', models.CharField(blank=True, max_length=50)),
                ('error_message', models.TextField(blank=True)),
                ('next_retry_at', models.DateTimeField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_attempts', to='invoices.scheduleexecution')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_payment_attempts', to='invoices.invoice')),
            ],
            options={
                'ordering': ['-attempted_at'],
            },
        ),
        migrations.CreateModel(
            name='RecurringScheduleAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'Schedule Created'), ('updated', 'Schedule Updated'), ('paused', 'Schedule Paused'), ('resumed', 'Schedule Resumed'), ('cancelled', 'Schedule Cancelled'), ('invoice_generated', 'Invoice Generated'), ('payment_attempted', 'Payment Attempted'), ('payment_success', 'Payment Successful'), ('payment_failed', 'Payment Failed'), ('retry_scheduled', 'Retry Scheduled'), ('retry_exhausted', 'Retry Attempts Exhausted'), ('notification_sent', 'Notification Sent')], max_length=50)),
                ('description', models.TextField(blank=True)),
                ('old_values', models.JSONField(blank=True, default=dict)),
                ('new_values', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('related_attempt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoices.paymentattempt')),
                ('related_execution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoices.scheduleexecution')),
                ('related_invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoices.invoice')),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='invoices.recurringschedule')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='recurringschedule',
            index=models.Index(fields=['status', 'next_run_date'], name='invoices_re_status_a3b4c5_idx'),
        ),
        migrations.AddIndex(
            model_name='recurringschedule',
            index=models.Index(fields=['workspace', 'status'], name='invoices_re_workspa_d6e7f8_idx'),
        ),
        migrations.AddIndex(
            model_name='scheduleexecution',
            index=models.Index(fields=['schedule', 'status'], name='invoices_sc_schedul_9a0b1c_idx'),
        ),
        migrations.AddIndex(
            model_name='scheduleexecution',
            index=models.Index(fields=['scheduled_date'], name='invoices_sc_schedul_2d3e4f_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentattempt',
            index=models.Index(fields=['execution', 'status'], name='invoices_pa_executi_5g6h7i_idx'),
        ),
        migrations.AddIndex(
            model_name='recurringscheduleauditlog',
            index=models.Index(fields=['schedule', 'action'], name='invoices_re_schedul_8j9k0l_idx'),
        ),
    ]
