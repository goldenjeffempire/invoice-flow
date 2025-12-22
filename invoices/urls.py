from django.urls import path

from . import views
from . import payment_settings_views
from . import settings_views

urlpatterns = [
    path("", views.invoice_list, name="invoice_list"),
    path("list/", views.invoice_list, name="invoice_list_alt"),
    path("bulk-action/", views.bulk_invoice_action, name="bulk_invoice_action"),
    path("export-csv/", views.export_invoices_csv, name="export_invoices_csv"),
    path("analytics/", views.analytics, name="analytics"),
    path("create/", views.create_invoice, name="create_invoice"),
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoice/<int:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),
    path("invoice/<int:invoice_id>/duplicate/", views.duplicate_invoice, name="duplicate_invoice"),
    path(
        "invoice/<int:invoice_id>/status/",
        views.update_invoice_status,
        name="update_invoice_status",
    ),
    path("invoice/<int:invoice_id>/pdf/", views.generate_pdf, name="generate_pdf"),
    path("invoice/<int:invoice_id>/email/", views.send_invoice_email, name="send_invoice_email"),
    path("invoice/<int:invoice_id>/whatsapp/", views.whatsapp_share, name="whatsapp_share"),
    path("waitlist/", views.waitlist_subscribe, name="waitlist_subscribe"),
    
    # Unified Settings Routes
    path("settings/", settings_views.settings_dashboard, name="settings"),
    path("settings/profile/", settings_views.settings_profile, name="settings_profile"),
    path("settings/business/", settings_views.settings_business, name="settings_business"),
    path("settings/payments/", settings_views.settings_payments, name="settings_payments"),
    path("settings/security/", settings_views.settings_security, name="settings_security"),
    path("settings/notifications/", settings_views.settings_notifications, name="settings_notifications"),
    path("settings/billing/", settings_views.settings_billing, name="settings_billing"),
    path("settings/sessions/<int:session_id>/revoke/", settings_views.revoke_session, name="revoke_session"),
    path("settings/sessions/revoke-all/", settings_views.revoke_all_sessions, name="revoke_all_sessions"),
    
    # Payment Management Routes
    path("api/verify-bank-account/", payment_settings_views.verify_bank_account, name="verify_bank_account"),
    path("api/list-banks/", payment_settings_views.list_banks, name="api_list_banks"),
    path("payments/settings/", payment_settings_views.payment_settings_dashboard, name="payment_settings"),
    path("payments/preferences/", payment_settings_views.payment_preferences, name="payment_preferences"),
    path("payments/setup-subaccount/", payment_settings_views.setup_subaccount, name="setup_subaccount"),
    path("payments/toggle-subaccount/", payment_settings_views.toggle_subaccount, name="toggle_subaccount"),
    path("payments/recipients/", payment_settings_views.manage_recipients, name="manage_recipients"),
    path("payments/recipients/<int:recipient_id>/delete/", payment_settings_views.delete_recipient, name="delete_recipient"),
    path("payments/recipients/<int:recipient_id>/primary/", payment_settings_views.set_primary_recipient, name="set_primary_recipient"),
    path("payments/cards/", payment_settings_views.saved_cards, name="saved_cards"),
    path("payments/cards/<int:card_id>/delete/", payment_settings_views.delete_card, name="delete_card"),
    path("payments/cards/<int:card_id>/primary/", payment_settings_views.set_primary_card, name="set_primary_card"),
    path("payments/history/", payment_settings_views.payment_history, name="payment_history"),
    path("payments/payouts/", payment_settings_views.payout_history, name="payout_history"),
    path("payments/<int:payment_id>/", payment_settings_views.payment_detail, name="payment_detail"),
    
    # Invoice & Payment Routes
    path("invoice/<int:invoice_id>/public/", views.public_invoice, name="public_invoice"),
    path("invoice/<int:invoice_id>/pay/", views.public_payment, name="public_payment"),
    path("payment-callback/", views.payment_callback, name="payment_callback"),
    path("webhook/paystack/", views.payment_webhook, name="payment_webhook"),
]
