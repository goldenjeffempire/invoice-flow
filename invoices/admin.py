from django.contrib import admin
from .models import (
    UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken,
    Invoice, Payment, WorkspaceInvitation,
    Waitlist, SocialAccount, Client, ClientNote, CommunicationLog,
    InvoiceActivity, RecurringSchedule, ScheduleExecution, PaymentAttempt,
    RecurringScheduleAuditLog
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
