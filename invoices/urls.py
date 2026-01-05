from django.urls import path

from . import views


app_name = "invoices"

urlpatterns = [
    # ------------------------------------------------------------------
    # WAITLIST
    # ------------------------------------------------------------------
    path("waitlist/", views.waitlist_subscribe, name="waitlist_subscribe"),

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
    
    path("api/engagement/record/", views.record_engagement, name="record_engagement"),
    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),
]
