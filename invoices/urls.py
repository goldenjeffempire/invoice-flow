from django.urls import path
from .views import main_views as views
from .views import onboarding_views
from .views import workspace_views
from .views import ux_views

from .views import dashboard_views

from .views import invoice_views

app_name = "invoices"

urlpatterns = [
    path('', views.landing_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('onboarding/', onboarding_views.onboarding_router, name='onboarding_router'),
    path('onboarding/welcome/', onboarding_views.onboarding_welcome, name='onboarding_welcome'),
    path('onboarding/business/', onboarding_views.onboarding_business, name='onboarding_business'),
    path('onboarding/branding/', onboarding_views.onboarding_branding, name='onboarding_branding'),
    path('onboarding/tax/', onboarding_views.onboarding_tax, name='onboarding_tax'),
    path('onboarding/payments/', onboarding_views.onboarding_payments, name='onboarding_payments'),
    path('onboarding/import/', onboarding_views.onboarding_import, name='onboarding_import'),
    path('onboarding/templates/', onboarding_views.onboarding_templates, name='onboarding_templates'),
    path('onboarding/team/', onboarding_views.onboarding_team, name='onboarding_team'),
    path('onboarding/complete/', onboarding_views.onboarding_complete, name='onboarding_complete'),
    path('mfa/setup/', views.mfa_setup, name='mfa_setup'),
    path('mfa/verify/', views.mfa_verify, name='mfa_verify'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('api/search/', ux_views.global_search, name='global_search_api'),
    path('activity/', ux_views.activity_timeline, name='activity_timeline'),
    path('notifications/mark-read/<int:pk>/', ux_views.mark_notification_read, name='mark_notification_read'),
    path('api/appearance/', ux_views.set_appearance_preference, name='set_appearance'),

    path('dashboard/', dashboard_views.dashboard_overview, name='dashboard'),
    path('settings/', views.settings_page, name='settings'),
    path('settings/profile/', views.profile_update_ajax, name='settings_profile_update'),
    path('settings/security/update/', views.security_update_ajax, name='settings_security_update'),
    path('settings/notifications/', views.notifications_update_ajax, name='settings_notifications_update'),
    path('settings/payments/', views.payment_settings_update_ajax, name='settings_payments_update'),
    path('settings/reminders/', views.reminder_dashboard, name='reminder_dashboard'),
    path('settings/reminders/rules/', views.reminder_settings, name='reminder_rules'),
    path('settings/reminders/track/<int:log_id>/', views.track_reminder_click, name='track_reminder_click'),
    path('settings/reminders/pixel/<int:log_id>/', views.track_reminder_open, name='track_reminder_open'),

    path("about/", views.about_view, name="about"),
    path("features/", views.features_view, name="features"),
    path("contact/", views.contact_view, name="contact"),
    path("faq/", views.faq_view, name="faq"),
    path("terms/", views.terms_view, name="terms"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("security/", views.security_view, name="security"),
    path("use-cases/", views.use_cases_view, name="use_cases"),
    path("templates/", views.templates_view, name="templates"),
    path("integrations/", views.integrations_view, name="integrations"),
    path("resources/", views.resources_view, name="resources"),

    path('clients/', invoice_views.invoice_list, name='client_list'),
    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),
    path("api/faq/", views.faq_api, name="faq_api"),

    path("payments/history/", views.payment_history, name="payment_history"),
    path("payments/<int:payment_id>/", views.payment_detail, name="payment_detail"),

    path('invoices/', invoice_views.invoice_list, name='invoice_list'),
    path('invoices/create/', invoice_views.invoice_create, name='invoice_create'),
    path('invoices/<str:invoice_number>/', invoice_views.invoice_detail, name='invoice_detail'),
    path('invoices/<str:invoice_number>/edit/', invoice_views.invoice_edit, name='invoice_edit'),
    path('i/<str:token>/', invoice_views.public_invoice_view, name='public_invoice'),
]
