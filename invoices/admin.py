from django.contrib import admin
from .models import (
    UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken,
    Invoice, InvoiceTemplate, LineItem, Payment, WorkspaceInvitation,
    RecurringInvoice, Waitlist, SocialAccount, Client, ClientNote, CommunicationLog
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'two_factor_enabled')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'client_name', 'status', 'created_at')

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
admin.site.register(InvoiceTemplate)
admin.site.register(LineItem)
admin.site.register(Payment)
admin.site.register(WorkspaceInvitation)
admin.site.register(RecurringInvoice)
admin.site.register(Waitlist)
admin.site.register(SocialAccount)
