"""
Test suite for user settings management system.
Tests profile, business, payment, security, notification, and billing settings.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from invoices.models import UserProfile, PaymentSettings


class SettingsViewsTestCase(TestCase):
    """Test suite for unified settings views."""

    def setUp(self):
        """Set up test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.payment_settings, _ = PaymentSettings.objects.get_or_create(user=self.user)

    def test_settings_dashboard_requires_login(self):
        """Test that settings dashboard requires authentication."""
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_settings_profile_requires_login(self):
        """Test that profile settings requires authentication."""
        response = self.client.get(reverse('settings_profile'))
        self.assertEqual(response.status_code, 302)

    def test_settings_profile_get(self):
        """Test GET request to profile settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-profile.html')

    def test_settings_business_get(self):
        """Test GET request to business settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_business'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-business.html')

    def test_settings_payments_get(self):
        """Test GET request to payment settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_payments'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-payments.html')

    def test_settings_security_get(self):
        """Test GET request to security settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_security'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-security.html')

    def test_settings_notifications_get(self):
        """Test GET request to notification settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-notifications.html')

    def test_settings_billing_get(self):
        """Test GET request to billing settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('settings_billing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/settings-billing.html')

    def test_profile_update(self):
        """Test updating user profile."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('settings_profile'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'company_name': 'Test Company',
            'business_email': 'business@example.com',
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')

    def test_business_settings_update(self):
        """Test updating business settings."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('settings_business'), {
            'company_name': 'My Business',
            'business_email': 'company@example.com',
            'default_currency': 'USD',
            'default_tax_rate': '10.00',
        })
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.company_name, 'My Business')
        self.assertEqual(self.profile.default_currency, 'USD')


class PaymentSettingsTestCase(TestCase):
    """Test suite for payment configuration."""

    def setUp(self):
        """Set up test user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.payment_settings, _ = PaymentSettings.objects.get_or_create(user=self.user)

    def test_payment_settings_toggle_card_payments(self):
        """Test toggling card payments."""
        self.client.login(username='testuser', password='testpass123')
        initial_state = self.payment_settings.enable_card_payments
        
        response = self.client.post(reverse('settings_payments'), {
            'enable_card_payments': not initial_state,
            'enable_bank_transfers': self.payment_settings.enable_bank_transfers,
            'preferred_currency': 'USD',
        })
        
        self.payment_settings.refresh_from_db()
        self.assertNotEqual(
            self.payment_settings.enable_card_payments,
            initial_state
        )

    def test_payment_settings_payout_schedule(self):
        """Test setting payout schedule."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('settings_payments'), {
            'enable_card_payments': True,
            'enable_bank_transfers': True,
            'preferred_currency': 'USD',
            'payout_schedule': 'weekly',
            'payout_threshold': '1000.00',
        })
        
        self.payment_settings.refresh_from_db()
        self.assertEqual(self.payment_settings.payout_schedule, 'weekly')
        self.assertEqual(self.payment_settings.payout_threshold, 1000.00)

    def test_payment_settings_auto_payout(self):
        """Test enabling auto-payout."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('settings_payments'), {
            'enable_card_payments': True,
            'enable_bank_transfers': True,
            'preferred_currency': 'USD',
            'auto_payout': True,
        })
        
        self.payment_settings.refresh_from_db()
        self.assertTrue(self.payment_settings.auto_payout)


class NotificationSettingsTestCase(TestCase):
    """Test suite for notification preferences."""

    def setUp(self):
        """Set up test user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)

    def test_notification_preferences_update(self):
        """Test updating notification preferences."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('settings_notifications'), {
            'notify_invoice_created': False,
            'notify_payment_received': True,
            'notify_invoice_viewed': False,
            'notify_invoice_overdue': True,
            'notify_weekly_summary': False,
            'notify_security_alerts': True,
            'notify_password_changes': True,
        })
        
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.notify_invoice_created)
        self.assertTrue(self.profile.notify_payment_received)
        self.assertTrue(self.profile.notify_invoice_overdue)
