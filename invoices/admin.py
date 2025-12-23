from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ContactSubmission,
    Invoice,
    InvoiceTemplate,
    LineItem,
    RecurringInvoice,
    UserProfile,
    Waitlist,
    Payment,
    MFAProfile,
    SocialAccount,
)


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_id",
        "client_name",
        "business_name",
        "status",
        "total",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("invoice_id", "client_name", "business_name", "client_email")
    readonly_fields = ("invoice_id", "created_at", "updated_at")
    inlines = [LineItemInline]

    fieldsets = (
        (
            "Invoice Information",
            {"fields": ("invoice_id", "user", "status", "currency", "tax_rate")},
        ),
        (
            "Business Details",
            {"fields": ("business_name", "business_email", "business_phone", "business_address")},
        ),
        (
            "Client Details",
            {"fields": ("client_name", "client_email", "client_phone", "client_address")},
        ),
        ("Dates", {"fields": ("invoice_date", "due_date")}),
        ("Branding", {"fields": ("brand_name", "brand_color", "logo")}),
        ("Bank Details", {"fields": ("bank_name", "account_name", "account_number")}),
        ("Additional", {"fields": ("notes", "created_at", "updated_at")}),
    )


@admin.register(LineItem)
class LineItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_price", "total")
    search_fields = ("description", "invoice__invoice_id")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "default_currency", "created_at")
    search_fields = ("user__username", "company_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "business_name", "currency", "is_default")
    list_filter = ("currency", "is_default", "created_at")
    search_fields = ("name", "business_name", "user__username")
    readonly_fields = ("created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "invoice", "user", "amount", "status_badge", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "invoice__invoice_id", "user__username")
    readonly_fields = ("created_at", "updated_at")
    
    def status_badge(self, obj):
        colors = {"pending": "orange", "completed": "green", "failed": "red"}
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"


@admin.register(MFAProfile)
class MFAProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_enabled", "created_at")
    list_filter = ("is_enabled", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("user__username", "user__email")


@admin.register(RecurringInvoice)
class RecurringInvoiceAdmin(admin.ModelAdmin):
    list_display = ("client_name", "user", "frequency", "status", "next_generation")
    list_filter = ("frequency", "status", "created_at")
    search_fields = ("client_name", "user__username", "client_email")
    readonly_fields = ("created_at", "last_generated")
    fieldsets = (
        (
            "Client Information",
            {"fields": ("user", "client_name", "client_email", "client_phone", "client_address")},
        ),
        (
            "Business Information",
            {"fields": ("business_name", "business_email", "currency", "tax_rate")},
        ),
        (
            "Schedule",
            {"fields": ("frequency", "start_date", "end_date", "next_generation", "status")},
        ),
        ("Metadata", {"fields": ("notes", "created_at", "last_generated")}),
    )


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ("email", "feature", "subscribed_at", "is_notified")
    list_filter = ("feature", "is_notified", "subscribed_at")
    search_fields = ("email",)
    readonly_fields = ("subscribed_at",)
    actions = ["mark_as_notified"]

    @admin.action(description="Mark selected entries as notified")
    def mark_as_notified(self, request, queryset):
        updated = queryset.update(is_notified=True)
        self.message_user(request, f"{updated} entries marked as notified.")


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status", "submitted_at")
    list_filter = ("subject", "status", "submitted_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("submitted_at", "ip_address", "user_agent")
    ordering = ("-submitted_at",)
    actions = ["mark_as_resolved", "mark_as_in_progress"]

    fieldsets = (
        ("Contact Information", {"fields": ("name", "email", "subject")}),
        ("Message", {"fields": ("message",)}),
        ("Status", {"fields": ("status", "admin_notes", "resolved_at")}),
        ("Metadata", {"fields": ("ip_address", "user_agent", "submitted_at")}),
    )

    @admin.action(description="Mark selected as resolved")
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(status="resolved", resolved_at=timezone.now())
        self.message_user(request, f"{updated} submissions marked as resolved.")

    @admin.action(description="Mark selected as in progress")
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status="in_progress")
        self.message_user(request, f"{updated} submissions marked as in progress.")
