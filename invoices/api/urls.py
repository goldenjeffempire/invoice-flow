"""API URL routing for InvoiceFlow."""
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, InvoiceTemplateViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='api-invoices')
router.register(r'templates', InvoiceTemplateViewSet, basename='api-templates')

urlpatterns = router.urls
