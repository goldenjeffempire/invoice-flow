# type: ignore
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Helper functions for lazy loading views to prevent early model imports
def lazy_view(import_path):
    def wrapper(request, *args, **kwargs):
        import importlib
        module_path, view_name = import_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        view_func = getattr(module, view_name)
        return view_func(request, *args, **kwargs)
    return wrapper

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
    path("api/consent/set/", lazy_view("invoiceflow.cookie_consent.set_cookie_consent"), name="set_cookie_consent"),
    path("api/consent/get/", lazy_view("invoiceflow.cookie_consent.get_cookie_consent"), name="get_cookie_consent"),
    path("api/consent/withdraw/", lazy_view("invoiceflow.cookie_consent.withdraw_cookie_consent"), name="withdraw_cookie_consent"),
    path("api/gdpr/export/", lazy_view("invoiceflow.gdpr.export_user_data"), name="gdpr_export"),
    path("api/gdpr/delete/", lazy_view("invoiceflow.gdpr.request_data_deletion"), name="gdpr_delete"),
    path("api/gdpr/sar/", lazy_view("invoiceflow.gdpr.submit_sar"), name="gdpr_sar"),
    # MFA (Two-Factor Authentication)
    path("mfa/setup/", lazy_view("invoiceflow.mfa.mfa_setup"), name="mfa_setup"),
    path("mfa/verify/", lazy_view("invoiceflow.mfa.mfa_verify"), name="mfa_verify"),
    path("mfa/disable/", lazy_view("invoiceflow.mfa.mfa_disable"), name="mfa_disable"),
    path("mfa/recovery/regenerate/", lazy_view("invoiceflow.mfa.mfa_regenerate_recovery"), name="mfa_regenerate_recovery"),
    # Health checks
    path("health/", lazy_view("invoices.health.health_check"), name="health_check"),
    path("health/ready/", lazy_view("invoices.health.readiness_check"), name="readiness_check"),
    path("health/live/", lazy_view("invoices.health.liveness_check"), name="liveness_check"),
    path("health/detailed/", lazy_view("invoices.health.detailed_health"), name="detailed_health"),
    # Favicon
    path("favicon.ico", RedirectView.as_view(url='/static/favicon.svg'), name="favicon"),
    # Robots.txt (dynamic)
    path("robots.txt", lazy_view("invoices.views.robots_txt"), name="robots_txt"),
    # Service worker (served from root for proper scope)
    path("sw.js", lazy_view("invoices.views.service_worker"), name="service_worker"),
    # Sitemap for SEO
    path("sitemap.xml", sitemap_view, {"sitemaps": {}}, name="django.contrib.sitemaps.views.sitemap"),
    # Admin
    path("admin/", admin.site.urls),
    path("", lazy_view("invoices.views.home"), name="home"),
    path("signup/", lazy_view("invoices.views.signup"), name="signup"),
    path("login/", lazy_view("invoices.views.login_view"), name="login"),
    path("logout/", lazy_view("invoices.views.logout_view"), name="logout"),
    path("verify-email/<str:token>/", lazy_view("invoices.views.verify_email"), name="verify_email"),
    path("verification-sent/", lazy_view("invoices.views.verification_sent"), name="verification_sent"),
    path("resend-verification/", lazy_view("invoices.views.resend_verification"), name="resend_verification"),
    path("forgot-password/", lazy_view("invoices.views.forgot_password"), name="forgot_password"),
    path("forgot-password/sent/", lazy_view("invoices.views.forgot_password_sent"), name="forgot_password_sent"),
    path("reset-password/<str:token>/", lazy_view("invoices.views.reset_password"), name="reset_password"),
    # Dashboard
    path("dashboard/", lazy_view("invoices.views.dashboard"), name="dashboard"),
    # User features
    path("my-templates/", lazy_view("invoices.views.invoice_templates"), name="invoice_templates"),
    path("my-templates/<int:template_id>/delete/", lazy_view("invoices.views.delete_template"), name="delete_template"),
    path("recurring/", lazy_view("invoices.views.recurring_invoices"), name="recurring_invoices"),
    # Admin endpoints
    path("admin-dashboard/", lazy_view("invoices.admin_views.admin_dashboard"), name="admin_dashboard"),
    path("admin-users/", lazy_view("invoices.admin_views.admin_users"), name="admin_users"),
    path("admin-payments/", lazy_view("invoices.admin_views.admin_payments"), name="admin_payments"),
    path("admin-invoices/", lazy_view("invoices.admin_views.admin_invoices"), name="admin_invoices"),
    path("admin-contacts/", lazy_view("invoices.admin_views.admin_contacts"), name="admin_contacts"),
    # Payment routes (Paystack)
    path("payments/invoice/<int:invoice_id>/pay/", lazy_view("invoices.paystack_views.initiate_invoice_payment"), name="initiate_payment"),
    path("payments/callback/<int:invoice_id>/", lazy_view("invoices.paystack_views.payment_callback"), name="payment_callback"),
    path("payments/webhook/", lazy_view("invoices.paystack_views.paystack_webhook"), name="paystack_webhook"),
    path("payments/status/<int:invoice_id>/", lazy_view("invoices.paystack_views.payment_status"), name="payment_status"),
    # Public invoice payment
    path("pay/<int:invoice_id>/", lazy_view("invoices.paystack_views.public_invoice_view"), name="public_invoice"),
    path("pay/<int:invoice_id>/checkout/", lazy_view("invoices.paystack_views.public_initiate_payment"), name="public_payment"),
    path("pay/<int:invoice_id>/callback/", lazy_view("invoices.paystack_views.public_payment_callback"), name="public_payment_callback"),
    # Invoices (all invoice routes including settings, payments)
    path("invoices/", include("invoices.urls")),
    # Root level profile redirect
    path("profile/", RedirectView.as_view(pattern_name='invoices:settings', permanent=True), name="profile"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
