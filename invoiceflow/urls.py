from django.contrib import admin
from django.urls import path, include
from invoices import views

handler404 = "invoices.views.custom_404"
handler500 = "invoices.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("invoices/", views.invoices_list, name="invoices_list"),
    path("invoices/create/", views.invoice_create, name="invoice_create"),
    path("invoices/<str:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("analytics/", views.analytics, name="analytics"),
    path("clients/", views.clients, name="clients"),
    path("settings/", views.settings_view, name="settings"),
]
