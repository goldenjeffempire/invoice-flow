from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import secrets
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invoices', '0002_sync_model_with_db'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
            DROP TABLE IF EXISTS invoices_invoiceactivity CASCADE;
            DROP TABLE IF EXISTS invoices_invoiceattachment CASCADE;
            DROP TABLE IF EXISTS invoices_invoicepayment CASCADE;
            DROP TABLE IF EXISTS invoices_lineitem CASCADE;
            DROP TABLE IF EXISTS invoices_invoice CASCADE;
            DROP TABLE IF EXISTS invoices_payment CASCADE;
            ''',
            reverse_sql=migrations.RunSQL.noop,
        ),

        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(db_index=True, max_length=50)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('viewed', 'Viewed'), ('part_paid', 'Partially Paid'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('void', 'Void'), ('write_off', 'Write-off')], db_index=True, default='draft', max_length=20)),
                ('source_type', models.CharField(choices=[('manual', 'Manual'), ('estimate', 'From Estimate'), ('recurring', 'From Recurring'), ('duplicate', 'Duplicated'), ('api', 'API Created')], default='manual', max_length=20)),
                ('source_id', models.IntegerField(blank=True, null=True)),
                ('issue_date', models.DateField(default=django.utils.timezone.now)),
                ('due_date', models.DateField()),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('first_viewed_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('voided_at', models.DateTimeField(blank=True, null=True)),
                ('void_reason', models.TextField(blank=True)),
                ('currency', models.CharField(choices=[('NGN', '₦ - Nigerian Naira'), ('USD', '$ - US Dollar'), ('EUR', '€ - Euro'), ('GBP', '£ - British Pound'), ('ZAR', 'R - South African Rand'), ('GHS', '₵ - Ghanaian Cedi'), ('KES', 'KSh - Kenyan Shilling'), ('CAD', '$ - Canadian Dollar'), ('AUD', '$ - Australian Dollar'), ('INR', '₹ - Indian Rupee')], default='NGN', max_length=3)),
                ('base_currency', models.CharField(default='NGN', max_length=3)),
                ('exchange_rate', models.DecimalField(decimal_places=6, default=Decimal('1.000000'), max_digits=15)),
                ('exchange_rate_date', models.DateField(blank=True, null=True)),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('tax_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('discount_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('amount_due', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('tax_mode', models.CharField(choices=[('exclusive', 'Tax Exclusive (added on top)'), ('inclusive', 'Tax Inclusive (included in price)')], default='exclusive', max_length=20)),
                ('default_tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('flat', 'Fixed Amount')], default='flat', max_length=20)),
                ('global_discount_value', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('global_discount_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('client_memo', models.TextField(blank=True)),
                ('internal_notes', models.TextField(blank=True)),
                ('terms_conditions', models.TextField(blank=True)),
                ('footer_note', models.TextField(blank=True)),
                ('payment_instructions', models.TextField(blank=True)),
                ('public_token', models.CharField(db_index=True, default=secrets.token_urlsafe, max_length=64, unique=True)),
                ('view_count', models.IntegerField(default=0)),
                ('last_viewed_at', models.DateTimeField(blank=True, null=True)),
                ('last_viewed_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('is_recurring', models.BooleanField(default=False)),
                ('recurring_schedule', models.JSONField(blank=True, default=dict)),
                ('reminder_enabled', models.BooleanField(default=True)),
                ('reminder_days_before', models.IntegerField(default=3)),
                ('last_reminder_sent_at', models.DateTimeField(blank=True, null=True)),
                ('reminder_count', models.IntegerField(default=0)),
                ('delivery_email_sent', models.BooleanField(default=False)),
                ('delivery_email_opened', models.BooleanField(default=False)),
                ('delivery_whatsapp_sent', models.BooleanField(default=False)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='invoices.client')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_invoices', to=settings.AUTH_USER_MODEL)),
                ('parent_invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_invoices', to='invoices.invoice')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='invoices.workspace')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('workspace', 'invoice_number')},
            },
        ),
        
        migrations.CreateModel(
            name='LineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('service', 'Service'), ('product', 'Product'), ('expense', 'Expense'), ('discount', 'Discount Line'), ('other', 'Other')], default='service', max_length=20)),
                ('product_id_ref', models.IntegerField(blank=True, null=True)),
                ('description', models.CharField(max_length=500)),
                ('long_description', models.TextField(blank=True)),
                ('unit', models.CharField(blank=True, default='unit', max_length=50)),
                ('quantity', models.DecimalField(decimal_places=4, default=Decimal('1.0000'), max_digits=15)),
                ('unit_price', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('flat', 'Fixed Amount')], default='flat', max_length=20)),
                ('discount_value', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15)),
                ('sort_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='invoices.invoice')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
        
        migrations.CreateModel(
            name='InvoiceActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'Invoice Created'), ('updated', 'Invoice Updated'), ('sent', 'Invoice Sent'), ('viewed', 'Invoice Viewed'), ('payment_received', 'Payment Received'), ('payment_failed', 'Payment Failed'), ('status_changed', 'Status Changed'), ('reminder_sent', 'Reminder Sent'), ('voided', 'Invoice Voided'), ('written_off', 'Invoice Written Off'), ('duplicated', 'Invoice Duplicated'), ('attachment_added', 'Attachment Added'), ('attachment_removed', 'Attachment Removed'), ('comment_added', 'Comment Added'), ('downloaded', 'PDF Downloaded'), ('shared', 'Link Shared')], max_length=50)),
                ('description', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('is_system', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='invoices.invoice')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timestamp'],
                'verbose_name_plural': 'Invoice activities',
            },
        ),
        
        migrations.CreateModel(
            name='InvoiceAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='invoice_attachments/%Y/%m/')),
                ('filename', models.CharField(max_length=255)),
                ('file_type', models.CharField(choices=[('document', 'Document'), ('image', 'Image'), ('contract', 'Contract'), ('receipt', 'Receipt'), ('other', 'Other')], default='document', max_length=20)),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('file_size', models.IntegerField(default=0)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('is_visible_to_client', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='invoices.invoice')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        migrations.CreateModel(
            name='InvoicePayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(db_index=True, max_length=255, unique=True)),
                ('external_reference', models.CharField(blank=True, db_index=True, max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('currency', models.CharField(default='NGN', max_length=3)),
                ('payment_method', models.CharField(choices=[('card', 'Card Payment'), ('bank_transfer', 'Bank Transfer'), ('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('paystack', 'Paystack'), ('stripe', 'Stripe'), ('check', 'Check/Cheque'), ('other', 'Other')], default='bank_transfer', max_length=30)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('payment_date', models.DateField(default=django.utils.timezone.now)),
                ('notes', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_partial', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='invoices.invoice')),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['workspace', 'status'], name='invoices_in_workspa_idx01'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['workspace', 'due_date'], name='invoices_in_workspa_idx02'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['client', 'status'], name='invoices_in_client_idx'),
        ),
    ]
