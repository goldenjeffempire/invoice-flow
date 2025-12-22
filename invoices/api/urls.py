"""API URL routing for InvoiceFlow."""
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, InvoiceTemplateViewSet
from .settings_api import SettingsViewSet

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet, basename='api-invoices')
router.register(r'templates', InvoiceTemplateViewSet, basename='api-templates')
router.register(r'settings', SettingsViewSet, basename='api-settings')

urlpatterns = router.urls
