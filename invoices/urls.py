from django.urls import path

from . import views


app_name = "invoices"

urlpatterns = [
    path("", views.home, name="home"),
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

    path("invoices/create/", views.invoice_create, name="invoices_create_legacy"),
    path("invoices/<str:invoice_id>/", views.invoice_detail, name="invoice_detail_legacy"),
    
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics, name="analytics"),
    path("create/", views.invoice_create, name="invoice_create"),
    path("list/", views.invoices_list, name="invoices_list"),
    path("<str:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("<str:invoice_id>/edit/", views.invoice_edit, name="invoice_edit"),
    path("<str:invoice_id>/delete/", views.invoice_delete, name="invoice_delete_legacy"),
    path("<str:invoice_id>/pdf/", views.invoice_pdf, name="invoice_pdf_legacy"),
    
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
    path("pricing/", views.pricing_view, name="pricing"),
    
    path("api/engagement/record/", views.record_engagement, name="record_engagement"),
    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),
]
