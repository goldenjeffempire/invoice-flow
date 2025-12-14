from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("list/", views.invoice_list, name="invoice_list"),
    path("bulk-action/", views.bulk_invoice_action, name="bulk_invoice_action"),
    path("export-csv/", views.export_invoices_csv, name="export_invoices_csv"),
    path("analytics/", views.analytics, name="analytics"),
    path("settings/", views.settings_view, name="settings"),
    path("create/", views.create_invoice, name="create_invoice"),
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/edit/", views.edit_invoice, name="edit_invoice"),
    path("invoice/<int:invoice_id>/delete/", views.delete_invoice, name="delete_invoice"),
    path("invoice/<int:invoice_id>/duplicate/", views.duplicate_invoice, name="duplicate_invoice"),
    path(
        "invoice/<int:invoice_id>/status/",
        views.update_invoice_status,
        name="update_invoice_status",
    ),
    path("invoice/<int:invoice_id>/pdf/", views.generate_pdf, name="generate_pdf"),
    path("invoice/<int:invoice_id>/email/", views.send_invoice_email, name="send_invoice_email"),
    path("invoice/<int:invoice_id>/whatsapp/", views.whatsapp_share, name="whatsapp_share"),
    path("waitlist/", views.waitlist_subscribe, name="waitlist_subscribe"),
]
