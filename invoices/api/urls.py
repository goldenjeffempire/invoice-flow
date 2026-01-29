"""API URL routing for InvoiceFlow."""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, InvoiceTemplateViewSet
from .validation_views import validation_constraints

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='api-invoices')
router.register(r'templates', InvoiceTemplateViewSet, basename='api-templates')

urlpatterns = router.urls + [
    path('validation/constraints/', validation_constraints, name='validation-constraints'),
]
