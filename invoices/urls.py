from django.urls import path

from . import views
from . import settings_views
from . import admin_views
from . import paystack_views
from . import invoice_create_views


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

    # ------------------------------------------------------------------
    # CREATE INVOICE (Production-grade with comprehensive validation)
    # ------------------------------------------------------------------
    path("create/", invoice_create_views.create_invoice_start, name="create_invoice_start"),
    path("create/load-template/", invoice_create_views.load_template, name="load_template"),
    path("create/validate/", invoice_create_views.validate_invoice_form, name="validate_invoice_form"),
    path("create/calculate/", invoice_create_views.calculate_totals, name="calculate_totals"),

    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoice/<int:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),
    path("invoice/<int:invoice_id>/duplicate/", views.duplicate_invoice, name="duplicate_invoice"),
    path("invoice/<int:invoice_id>/status/", views.update_invoice_status, name="update_invoice_status"),
    path("invoice/<int:invoice_id>/pdf/", views.generate_pdf, name="generate_pdf"),
    path("invoice/<int:invoice_id>/email/", views.send_invoice_email, name="send_invoice_email"),
    path("invoice/<int:invoice_id>/whatsapp/", views.whatsapp_share, name="whatsapp_share"),

    # ------------------------------------------------------------------
    # PUBLIC INVOICE & PAYMENTS
    # ------------------------------------------------------------------
    path("invoice/<int:invoice_id>/public/", views.public_invoice, name="public_invoice"),
    path("invoice/<int:invoice_id>/pay/", views.public_payment, name="public_payment"),
    path("payment/callback/", views.payment_callback, name="payment_callback"),

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
    # DASHBOARD & PROFILE
    # ------------------------------------------------------------------
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_page, name="profile"),
    path("profile/update/", views.profile_update, name="profile_update"),
    path("paystack-setup/", views.paystack_setup, name="paystack_setup"),
    
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
]
