from django.contrib import admin
from django.urls import path, include
from invoices import views

handler404 = "invoices.views.custom_404"
handler500 = "invoices.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("invoices.urls", namespace="invoices")),
]
