"""API URL routing for InvoiceFlow."""
from rest_framework.routers import DefaultRouter
from .settings_api import SettingsViewSet

router = DefaultRouter()
router.register(r'settings', SettingsViewSet, basename='api-settings')

urlpatterns = router.urls
