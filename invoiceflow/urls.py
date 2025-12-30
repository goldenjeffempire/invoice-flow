# type: ignore
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from invoiceflow import cookie_consent, gdpr, mfa
from invoices import paystack_views, views, admin_views, settings_views
from invoices.health import detailed_health, health_check, liveness_check, readiness_check
from invoices.sitemap import sitemaps

handler404 = "invoices.views.custom_404"
handler500 = "invoices.views.custom_500"

urlpatterns = [
    # OpenAPI/Swagger API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="redoc"),
    # REST API v1 (versioned endpoints)
    path("api/v1/", include("invoices.api.urls")),
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
    # Favicon
    path("favicon.ico", RedirectView.as_view(url='/static/favicon.svg'), name="favicon"),
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
    # Invoices (all invoice routes including settings, payments)
    # path("invoices/", include("invoices.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
