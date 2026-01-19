from django.urls import path

from . import paystack_views, views


app_name = "invoices"

urlpatterns = [
    path("", views.login_view, name="home"),
    path("features/", views.features_view, name="features"),
    path("pricing/", views.pricing_view, name="pricing"),
    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("terms/", views.terms_view, name="terms"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("security/", views.security_view, name="security"),
    path("faq/", views.faq_view, name="faq"),
    path("support/", views.support_view, name="support"),
    path("careers/", views.careers_view, name="careers"),
    path("blog/", views.blog_view, name="blog"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("verification-sent/", views.verification_sent, name="verification_sent"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/done/", views.password_reset_done, name="password_reset_done"),
    path("password-reset-confirm/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("invoices/<str:invoice_id>/pdf/", views.download_invoice_pdf, name="invoice_pdf"),
    path("invoices/<str:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),
    path("invoices/<str:invoice_id>/reminder/", views.send_reminder, name="send_reminder"),
    
    # ------------------------------------------------------------------
    # WAITLIST
    # ------------------------------------------------------------------
    path("waitlist/", views.waitlist_subscribe, name="waitlist_subscribe"),

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------
    path("payments/history/", views.payment_history, name="payment_history"),
    path("payments/<int:payment_id>/", views.payment_detail, name="payment_detail"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),
    path("create/", views.invoice_create, name="invoice_create"),
    path("list/", views.invoices_list, name="invoices_list"),
    path("invoice/<str:invoice_id>/", views.invoice_detail, name="invoice_detail_by_pk"),
    
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
    
    path("api/engagement/record/", views.record_engagement, name="record_engagement"),
    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),

    # ------------------------------------------------------------------
    # PAYMENTS (PAYSTACK)
    # ------------------------------------------------------------------
    path("payments/initialize/", paystack_views.initialize_payment, name="payment_initialize"),
    path("payments/webhooks/paystack/", paystack_views.paystack_webhook, name="paystack_webhook"),
    path("payments/invoices/<str:invoice_id>/initiate/", paystack_views.initiate_invoice_payment, name="invoice_payment_initiate"),
    path("payments/callback/<str:invoice_id>/", paystack_views.payment_callback, name="payment_callback"),
    path("payments/<str:invoice_id>/status/", paystack_views.payment_status, name="payment_status"),
    path("pay/<str:invoice_id>/", paystack_views.public_invoice_view, name="public_invoice"),
    path("pay/<str:invoice_id>/init/", paystack_views.public_initiate_payment, name="public_initiate_payment"),
    path("pay/<str:invoice_id>/callback/", paystack_views.public_payment_callback, name="public_payment_callback"),

    path("invoices/create/", views.invoice_create, name="invoices_create_legacy"),
    path("invoices/<str:invoice_id>/", views.invoice_detail, name="invoice_detail_legacy"),
    path("<str:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("<str:invoice_id>/edit/", views.invoice_edit, name="invoice_edit"),
    path("<str:invoice_id>/delete/", views.invoice_delete, name="invoice_delete_legacy"),
    path("<str:invoice_id>/pdf/", views.invoice_pdf, name="invoice_pdf_legacy"),
]
