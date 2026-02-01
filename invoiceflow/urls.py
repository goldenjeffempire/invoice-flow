from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from invoices import admin_views, health, views
from invoices.sitemap import sitemaps

handler404 = "invoices.views.custom_404_view"
handler500 = "invoices.views.custom_500_view"

from django.views.decorators.cache import cache_page

from django.views.generic import TemplateView

urlpatterns = [
    path("sw.js", TemplateView.as_view(template_name="sw.js", content_type="application/javascript"), name="service_worker"),
    re_path(r'^favicon\.ico/?$', cache_page(60 * 60 * 24)(views.favicon_view), name="favicon"),
    path("admin/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("admin/users/", admin_views.admin_users, name="admin_users"),
    path("admin/payments/", admin_views.admin_payments, name="admin_payments"),
    path("admin/invoices/", admin_views.admin_invoices, name="admin_invoices"),
    path("admin/contacts/", admin_views.admin_contacts, name="admin_contacts"),
    path("admin/contacts/<int:submission_id>/status/", admin_views.update_contact_status, name="update_contact_status"),
    path("admin/settings/", admin_views.admin_settings, name="admin_settings"),
    path("admin/", admin.site.urls),
    path("health/", health.health_check, name="health_check"),
    path("health/ready/", health.readiness_check, name="readiness_check"),
    path("health/live/", health.liveness_check, name="liveness_check"),
    path("health/details/", health.detailed_health, name="detailed_health"),
    path("robots.txt", views.robots_txt_view, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("api/v1/", include("invoices.api.urls")),
    path("", include("invoices.urls", namespace="invoices")),
]
