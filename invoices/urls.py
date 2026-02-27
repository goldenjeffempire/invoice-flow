from django.urls import path
from .views import main_views as views
from .views import onboarding_views
from .views import workspace_views
from .views import ux_views

from .views import dashboard_views
from .views import invoice_views
from .views import payment_views
from .views import client_views
from .views import export_views
from .views import recurring_views
from .views import expense_views
from .views import report_views
from .views import portal_views
from .views import estimate_views

app_name = "invoices"

urlpatterns = [
    # ... existing patterns ...
    path('portal/login/', portal_views.portal_login, name='portal_login'),
    path('portal/auth/<str:token>/', portal_views.portal_authenticate, name='portal_authenticate'),
    path('portal/dashboard/', portal_views.portal_dashboard, name='portal_dashboard'),
    path('portal/invoices/<int:invoice_id>/', portal_views.portal_invoice_detail, name='portal_invoice_detail'),
    path('portal/profile/', portal_views.portal_profile, name='portal_profile'),
    path('portal/logout/', portal_views.portal_logout, name='portal_logout'),
    path('', views.landing_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verification-sent/', views.verification_sent, name='verification_sent'),
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
    path('mfa/disable/', views.mfa_disable, name='mfa_disable'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('security/change-password/', views.change_password, name='change_password'),
    path('security/sessions/<int:session_id>/revoke/', views.revoke_session, name='revoke_session'),
    path('security/sessions/revoke-all/', views.revoke_all_sessions, name='revoke_all_sessions'),
    path('logout/', views.logout_view, name='logout'),
    path('api/search/', ux_views.global_search, name='global_search_api'),
    path('activity/', ux_views.activity_timeline, name='activity_timeline'),
    path('notifications/mark-read/<int:pk>/', ux_views.mark_notification_read, name='mark_notification_read'),
    path('api/appearance/', ux_views.set_appearance_preference, name='set_appearance'),

    # Client Portal
    path('portal/login/', portal_views.portal_login, name='portal_login'),
    path('portal/auth/<str:token>/', portal_views.portal_authenticate, name='portal_authenticate'),
    path('portal/dashboard/', portal_views.portal_dashboard, name='portal_dashboard'),
    path('portal/invoices/<int:invoice_id>/', portal_views.portal_invoice_detail, name='portal_invoice_detail'),
    path('portal/invoices/<int:invoice_id>/pdf/', portal_views.portal_invoice_pdf, name='portal_invoice_pdf'),
    path('portal/profile/', portal_views.portal_profile, name='portal_profile'),
    path('portal/logout/', portal_views.portal_logout, name='portal_logout'),

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

    path("api/feedback/submit/", views.submit_feedback, name="submit_feedback"),
    path("api/faq/", views.faq_api, name="faq_api"),

    path("payments/", payment_views.payment_overview, name="payment_overview"),
    path("payments/transactions/", payment_views.transaction_list, name="transaction_list"),
    path("payments/<int:payment_id>/", payment_views.payment_detail, name="payment_detail"),
    path("invoices/<int:invoice_id>/record-payment/", payment_views.record_offline_payment, name="record_offline_payment"),
    path("webhooks/paystack/", payment_views.paystack_webhook, name="paystack_webhook"),

    # Clients
    path('clients/', client_views.client_list, name='client_list'),
    path('clients/new/', client_views.client_create, name='client_create'),
    path('clients/<int:client_id>/', client_views.client_detail, name='client_detail'),
    path('clients/<int:client_id>/edit/', client_views.client_edit, name='client_edit'),
    path('clients/<int:client_id>/delete/', client_views.client_delete, name='client_delete'),

    path('invoices/', invoice_views.invoice_list, name='invoice_list'),
    path('invoices/create/', invoice_views.invoice_create, name='invoice_create'),
    path('invoices/export/csv/', invoice_views.invoice_export_csv, name='invoice_export_csv'),
    path('invoices/<int:invoice_id>/', invoice_views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/edit/', invoice_views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:invoice_id>/preview/', invoice_views.invoice_preview, name='invoice_preview'),
    path('invoices/<int:invoice_id>/pdf/', invoice_views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:invoice_id>/send/', invoice_views.invoice_send, name='invoice_send'),
    path('invoices/<int:invoice_id>/share/', invoice_views.invoice_share_link, name='invoice_share'),
    path('invoices/<int:invoice_id>/payment/', invoice_views.invoice_record_payment, name='invoice_record_payment'),
    path('invoices/<int:invoice_id>/void/', invoice_views.invoice_void, name='invoice_void'),
    path('invoices/<int:invoice_id>/duplicate/', invoice_views.invoice_duplicate, name='invoice_duplicate'),

    path('i/<str:token>/', invoice_views.public_invoice_view, name='public_invoice'),
    path('i/<str:token>/pdf/', invoice_views.public_invoice_pdf, name='public_invoice_pdf'),
    path('i/<str:token>/pay/', invoice_views.public_initiate_payment, name='public_initiate_payment'),

    path('api/invoices/calculate/', invoice_views.api_invoice_calculate, name='api_invoice_calculate'),
    path('api/clients/create/', invoice_views.api_client_create, name='api_client_create'),
    path('api/clients/search/', invoice_views.api_clients_search, name='api_clients_search'),

    # Workspace & Team
    path('settings/workspace/', workspace_views.workspace_settings, name='workspace_settings'),
    path('settings/workspace/invitations/<int:invite_id>/revoke/', workspace_views.revoke_invitation, name='revoke_invitation'),
    path('settings/workspace/members/<int:member_id>/remove/', workspace_views.remove_member, name='remove_member'),

    # Exports
    path('export/clients/csv/', export_views.export_clients_csv, name='export_clients_csv'),
    path('export/transactions/csv/', export_views.export_transactions_csv, name='export_transactions_csv'),

    # Recurring Billing
    path('recurring/', recurring_views.schedule_list, name='schedule_list'),
    path('recurring/create/', recurring_views.schedule_create, name='schedule_create'),
    path('recurring/<int:schedule_id>/', recurring_views.schedule_detail, name='schedule_detail'),
    path('recurring/<int:schedule_id>/edit/', recurring_views.schedule_edit, name='schedule_edit'),
    path('recurring/<int:schedule_id>/pause/', recurring_views.schedule_pause, name='schedule_pause'),
    path('recurring/<int:schedule_id>/resume/', recurring_views.schedule_resume, name='schedule_resume'),
    path('recurring/<int:schedule_id>/cancel/', recurring_views.schedule_cancel, name='schedule_cancel'),

    # Expenses
    path('expenses/', expense_views.expense_list, name='expense_list'),
    path('expenses/create/', expense_views.expense_create, name='expense_create'),
    path('expenses/export/csv/', expense_views.expense_export_csv, name='expense_export_csv'),
    path('expenses/categories/', expense_views.category_list, name='category_list'),
    path('expenses/categories/<int:category_id>/edit/', expense_views.category_edit, name='category_edit'),
    path('expenses/vendors/', expense_views.vendor_list, name='vendor_list'),
    path('expenses/vendors/create/', expense_views.vendor_create, name='vendor_create'),
    path('expenses/vendors/<int:vendor_id>/', expense_views.vendor_detail, name='vendor_detail'),
    path('expenses/vendors/<int:vendor_id>/edit/', expense_views.vendor_edit, name='vendor_edit'),
    path('expenses/pl-report/', expense_views.expense_pl_report, name='expense_pl_report'),
    path('expenses/<int:expense_id>/', expense_views.expense_detail, name='expense_detail'),
    path('expenses/<int:expense_id>/edit/', expense_views.expense_edit, name='expense_edit'),
    path('expenses/<int:expense_id>/submit/', expense_views.expense_submit, name='expense_submit'),
    path('expenses/<int:expense_id>/approve/', expense_views.expense_approve, name='expense_approve'),
    path('expenses/<int:expense_id>/reject/', expense_views.expense_reject, name='expense_reject'),
    path('expenses/<int:expense_id>/reimburse/', expense_views.expense_reimburse, name='expense_reimburse'),
    path('expenses/<int:expense_id>/upload-receipt/', expense_views.expense_upload_receipt, name='expense_upload_receipt'),
    path('expenses/<int:expense_id>/attachments/<int:attachment_id>/delete/', expense_views.expense_delete_attachment, name='expense_delete_attachment'),

    # Billable Expenses to Invoice
    path('invoices/<int:invoice_id>/add-expenses/', expense_views.billable_expenses_select, name='billable_expenses_select'),

    # Estimates
    path('estimates/', estimate_views.estimate_list, name='estimate_list'),
    path('estimates/create/', estimate_views.estimate_builder, name='estimate_create'),
    path('estimates/<int:estimate_id>/', estimate_views.estimate_detail, name='estimate_detail'),
    path('estimates/<int:estimate_id>/edit/', estimate_views.estimate_builder, name='estimate_edit'),
    path('estimates/<int:estimate_id>/convert/', estimate_views.convert_estimate, name='estimate_convert'),

    # Reports & Analytics
    path('reports/', report_views.reports_home, name='reports_home'),
    path('reports/revenue/', report_views.revenue_report, name='revenue_report'),
    path('reports/aging/', report_views.aging_report, name='aging_report'),
    path('reports/cashflow/', report_views.cashflow_report, name='cashflow_report'),
    path('reports/profitability/', report_views.profitability_report, name='profitability_report'),
    path('reports/tax/', report_views.tax_report, name='tax_report'),
    path('reports/expense/', report_views.expense_report, name='expense_analysis'),
    path('reports/forecast/', report_views.forecast_report, name='forecast_report'),
    path('reports/exports/', report_views.exports_hub, name='exports_hub'),
    path('reports/export/<str:report_type>/csv/', report_views.export_report_csv, name='export_report_csv'),
    path('reports/shared/', report_views.shared_links_list, name='shared_links_list'),
    path('reports/shared/create/', report_views.create_shared_link, name='create_shared_link'),
    path('reports/shared/<str:token>/', report_views.shared_report_view, name='shared_report_view'),
    path('reports/shared/<str:token>/revoke/', report_views.revoke_shared_link, name='revoke_shared_link'),
]
