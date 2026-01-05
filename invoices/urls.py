from django.urls import path

from . import views
from . import admin_views
from . import paystack_views


app_name = "invoices"

urlpatterns = [
    # ------------------------------------------------------------------
    # INVOICE CORE
    # ------------------------------------------------------------------
    path("", views.invoice_list, name="invoice_list"),
    path("list/", views.invoice_list, name="invoice_list_alt"),
    path("analytics/", views.analytics, name="analytics"),
    path("bulk-action/", views.bulk_invoice_action, name="bulk_invoice_action"),
    path("export-csv/", views.export_invoices_csv, name="export_invoices_csv"),

    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoice/<int:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),
    path("invoice/<int:invoice_id>/duplicate/", views.duplicate_invoice, name="duplicate_invoice"),
    path("invoice/<int:invoice_id>/status/", views.update_invoice_status, name="update_invoice_status"),
    path("invoice/<int:invoice_id>/mark-paid/", views.mark_invoice_paid, name="mark_invoice_paid"),
    path("invoice/<int:invoice_id>/pdf/", views.generate_pdf, name="generate_pdf"),
    path("invoice/<int:invoice_id>/email/", views.send_invoice_email, name="send_invoice_email"),
    path("invoice/<int:invoice_id>/whatsapp/", views.whatsapp_share, name="whatsapp_share"),

    # ------------------------------------------------------------------
    # PUBLIC INVOICE & PAYMENTS
    # ------------------------------------------------------------------
    path("invoice/<int:invoice_id>/public/", views.public_invoice, name="public_invoice"),
    path("payments/callback/<int:invoice_id>/", views.payment_callback, name="payment_callback"),

    # ------------------------------------------------------------------
    # PAYSTACK (SERVER-SIDE)
    # ------------------------------------------------------------------
    path("payments/init/", paystack_views.initialize_payment, name="init_payment"),
    path("payments/webhook/paystack/", paystack_views.paystack_webhook, name="paystack_webhook"),

    # ------------------------------------------------------------------
    # WAITLIST
    # ------------------------------------------------------------------
    path("waitlist/", views.waitlist_subscribe, name="waitlist_subscribe"),

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------
    path("payments/history/", views.payment_history, name="payment_history"),
    path("payments/<int:payment_id>/", views.payment_detail, name="payment_detail"),

    # ------------------------------------------------------------------
    # SETTINGS (Modern & Production-grade)
    # ------------------------------------------------------------------
    path("settings/", views.settings_page, name="settings"),
    path("settings/profile/", views.profile_update_ajax, name="settings_profile_update"),
    path("settings/security/", views.security_update_ajax, name="settings_security_update"),
    path("settings/notifications/", views.notifications_update_ajax, name="settings_notifications_update"),
    path("settings/reminders/", views.reminder_dashboard, name="reminder_dashboard"),
    path("settings/reminders/rules/", views.reminder_settings, name="reminder_rules"),
    path("settings/reminders/track/<int:log_id>/", views.track_reminder_click, name="track_reminder_click"),
    path("settings/reminders/pixel/<int:log_id>/", views.track_reminder_open, name="track_reminder_open"),
    path("settings/payments/", views.payment_settings_update_ajax, name="settings_payments_update"),
    
    # Redirects for backward compatibility
    path("profile/", views.settings_page, name="settings_profile_redirect"),
    path("profile/update/", views.settings_page, name="settings_profile_update_redirect"),
    path("paystack-setup/", views.settings_page, name="settings_paystack_redirect"),
    
    # ------------------------------------------------------------------
    # MFA
    # ------------------------------------------------------------------
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("mfa/disable/", views.mfa_disable, name="mfa_disable"),
    path("mfa/backup-codes/", views.mfa_backup_codes, name="mfa_backup_codes"),
    
    # ------------------------------------------------------------------
    # RECURRING INVOICES
    # ------------------------------------------------------------------
    path("recurring/", views.recurring_invoices_list, name="recurring_invoices"),
    path("recurring/create/", views.create_recurring_invoice, name="create_recurring"),
    path("recurring/<int:recurring_id>/edit/", views.edit_recurring_invoice, name="edit_recurring"),
    path("recurring/<int:recurring_id>/delete/", views.delete_recurring_invoice, name="delete_recurring"),
    path("recurring/<int:recurring_id>/pause/", views.pause_recurring_invoice, name="pause_recurring"),
    path("recurring/<int:recurring_id>/resume/", views.resume_recurring_invoice, name="resume_recurring"),
    path("api/engagement/record/", views.record_engagement, name="record_engagement"),
    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),
]
