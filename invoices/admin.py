from django.contrib import admin
from .models import (
    UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken,
    Invoice, Payment, WorkspaceInvitation,
    Waitlist, SocialAccount, Client, ClientNote, CommunicationLog,
    InvoiceActivity, RecurringSchedule, ScheduleExecution, PaymentAttempt,
    RecurringScheduleAuditLog, Expense, ExpenseCategory, Vendor,
    ExpenseAttachment, ExpenseAuditLog
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'two_factor_enabled')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'workspace')
    search_fields = ('invoice_number', 'client__name')

@admin.register(InvoiceActivity)
class InvoiceActivityAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'action', 'user', 'timestamp')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'workspace', 'created_at')
    search_fields = ('name', 'email')
    list_filter = ('workspace',)

@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ('client', 'user', 'created_at')

@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'subject', 'medium', 'sent_at')

admin.site.register(MFAProfile)
admin.site.register(SecurityEvent)
admin.site.register(UserSession)
admin.site.register(EmailToken)
admin.site.register(Payment)
admin.site.register(WorkspaceInvitation)
admin.site.register(Waitlist)
admin.site.register(SocialAccount)


@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'workspace', 'interval_type', 'status', 'next_run_date', 'created_at')
    list_filter = ('status', 'interval_type', 'workspace')
    search_fields = ('client__name', 'description')
    readonly_fields = ('idempotency_key', 'created_at', 'updated_at')


@admin.register(ScheduleExecution)
class ScheduleExecutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'schedule', 'invoice', 'status', 'executed_at')
    list_filter = ('status',)
    search_fields = ('schedule__client__name', 'invoice__invoice_number')
    readonly_fields = ('idempotency_key', 'executed_at')


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'execution', 'attempt_number', 'status', 'attempted_at')
    list_filter = ('status',)
    readonly_fields = ('attempted_at',)


@admin.register(RecurringScheduleAuditLog)
class RecurringScheduleAuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'schedule', 'action', 'user', 'timestamp')
    list_filter = ('action',)
    search_fields = ('schedule__client__name', 'description')
    readonly_fields = ('timestamp',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'color', 'is_active', 'is_tax_deductible')
    list_filter = ('workspace', 'is_active', 'is_tax_deductible')
    search_fields = ('name', 'description')


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'email', 'total_expenses', 'is_active')
    list_filter = ('workspace', 'is_active')
    search_fields = ('name', 'email', 'contact_name')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('expense_number', 'description', 'workspace', 'category', 'vendor', 'total_amount', 'status', 'is_billable', 'expense_date')
    list_filter = ('status', 'workspace', 'category', 'is_billable', 'is_billed')
    search_fields = ('expense_number', 'description', 'vendor__name')
    readonly_fields = ('expense_number', 'created_at', 'updated_at')
    date_hierarchy = 'expense_date'


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_file_name', 'expense', 'file_type', 'file_size', 'uploaded_by', 'created_at')
    list_filter = ('file_type',)
    search_fields = ('original_file_name', 'expense__expense_number')
    readonly_fields = ('created_at',)


@admin.register(ExpenseAuditLog)
class ExpenseAuditLogAdmin(admin.ModelAdmin):
    list_display = ('expense', 'action', 'user', 'timestamp')
    list_filter = ('action',)
    search_fields = ('expense__expense_number', 'description')
    readonly_fields = ('timestamp',)
