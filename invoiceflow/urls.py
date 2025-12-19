# type: ignore
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path

from invoiceflow import cookie_consent, gdpr, mfa
from invoices import paystack_views, views
from invoices.health import detailed_health, health_check, liveness_check, readiness_check
from invoices.sitemap import sitemaps

handler404 = "invoices.views.custom_404"
handler500 = "invoices.views.custom_500"

urlpatterns = [
    # REST API v1 (versioned endpoints)
    path("api/", include("invoices.api.urls")),
    # Cookie Consent & GDPR Compliance
    path("api/consent/set/", cookie_consent.set_cookie_consent, name="set_cookie_consent"),
    path("api/consent/get/", cookie_consent.get_cookie_consent, name="get_cookie_consent"),
    path(
        "api/consent/withdraw/",
        cookie_consent.withdraw_cookie_consent,
        name="withdraw_cookie_consent",
    ),
    path("api/gdpr/export/", gdpr.export_user_data, name="gdpr_export"),
    path("api/gdpr/delete/", gdpr.request_data_deletion, name="gdpr_delete"),
    path("api/gdpr/sar/", gdpr.submit_sar, name="gdpr_sar"),
    # MFA (Two-Factor Authentication)
    path("mfa/setup/", mfa.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", mfa.mfa_verify, name="mfa_verify"),
    path("mfa/disable/", mfa.mfa_disable, name="mfa_disable"),
    path("mfa/recovery/regenerate/", mfa.mfa_regenerate_recovery, name="mfa_regenerate_recovery"),
    # Health checks
    path("health/", health_check, name="health_check"),
    path("health/ready/", readiness_check, name="readiness_check"),
    path("health/live/", liveness_check, name="liveness_check"),
    path("health/detailed/", detailed_health, name="detailed_health"),
    # Robots.txt (dynamic)
    path("robots.txt", views.robots_txt, name="robots_txt"),
    # Service worker (served from root for proper scope)
    path("sw.js", views.service_worker, name="service_worker"),
    # Sitemap for SEO
    path(
        "sitemap.xml",
        sitemap_view,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # Admin
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify-email/<str:token>/", views.verify_email, name="verify_email"),
    path("verification-sent/", views.verification_sent, name="verification_sent"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("forgot-password/sent/", views.forgot_password_sent, name="forgot_password_sent"),
    path("reset-password/<str:token>/", views.reset_password, name="reset_password"),
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    # Settings pages
    path("settings/", views.settings_view, name="settings"),
    path("settings/profile/", views.settings_profile, name="settings_profile"),
    path("settings/business/", views.settings_business, name="settings_business"),
    path("settings/security/", views.settings_security, name="settings_security"),
    path("settings/notifications/", views.settings_notifications, name="settings_notifications"),
    path("settings/billing/", views.settings_billing, name="settings_billing"),
    # Design System (Phase 1)
    path("components-showcase/", views.components_showcase, name="components_showcase"),
    # Footer pages
    path("features/", views.features, name="features"),
    path("pricing/", views.pricing, name="pricing"),
    path("templates/", views.templates_page, name="templates"),
    path("api-access/", views.api_access, name="api"),
    path("about/", views.about, name="about"),
    path("careers/", views.careers, name="careers"),
    path("contact/", views.contact, name="contact"),
    path("changelog/", views.changelog, name="changelog"),
    path("system-status/", views.system_status, name="status"),
    path("support/", views.support, name="support"),
    path("faq/", views.faq, name="faq"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("security/", views.security, name="security"),
    path("blog/", views.blog, name="blog"),
    path("blog/<slug:slug>/", views.blog_article, name="blog_article"),
    path("offline/", views.offline, name="offline"),
    path("newsletter/signup/", views.newsletter_signup, name="newsletter_signup"),
    path("newsletter/subscribe/", views.newsletter_signup, name="newsletter_subscribe"),
    # User features
    path("profile/", views.profile, name="profile"),
    path("my-templates/", views.invoice_templates, name="invoice_templates"),
    path("my-templates/<int:template_id>/delete/", views.delete_template, name="delete_template"),
    path("recurring/", views.recurring_invoices, name="recurring_invoices"),
    # Admin endpoints
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-users/", views.admin_users, name="admin_users"),
    path("admin-content/", views.admin_content, name="admin_content"),
    path("admin-settings/", views.admin_settings, name="admin_settings"),
    # Payment routes (Paystack)
    path("payments/invoice/<int:invoice_id>/pay/", paystack_views.initiate_invoice_payment, name="initiate_payment"),
    path("payments/callback/<int:invoice_id>/", paystack_views.payment_callback, name="payment_callback"),
    path("payments/webhook/", paystack_views.paystack_webhook, name="paystack_webhook"),
    path("payments/status/<int:invoice_id>/", paystack_views.payment_status, name="payment_status"),
    # Public invoice payment (client access without login)
    path("pay/<int:invoice_id>/", paystack_views.public_invoice_view, name="public_invoice"),
    path("pay/<int:invoice_id>/checkout/", paystack_views.public_initiate_payment, name="public_payment"),
    path("pay/<int:invoice_id>/callback/", paystack_views.public_payment_callback, name="public_payment_callback"),
    # Invoices (all invoice routes)
    path("invoices/", include("invoices.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
