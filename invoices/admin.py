from django.contrib import admin
from .models import (
    UserProfile, MFAProfile, SecurityEvent, UserSession, EmailToken,
    Invoice, InvoiceTemplate, LineItem, Payment, WorkspaceInvitation,
    RecurringInvoice, Waitlist, ContactSubmission, SocialAccount
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'two_factor_enabled')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'client_name', 'status', 'created_at')

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
admin.site.register(ContactSubmission)
admin.site.register(SocialAccount)
