"""
Test suite for admin dashboard and management system.
Tests user management, payment monitoring, invoice tracking, and contact handling.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from invoices.models import Invoice, Payment, ContactSubmission, UserProfile
from decimal import Decimal


class AdminAuthenticationTestCase(TestCase):
    """Test admin authentication and authorization."""

    def setUp(self):
        """Set up test users."""
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True,
            is_active=True
        )

    def test_admin_dashboard_requires_staff(self):
        """Test that admin dashboard requires staff access."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_regular_user_cannot_access_admin_dashboard(self):
        """Test that regular users cannot access admin dashboard."""
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to home

    def test_admin_can_access_dashboard(self):
        """Test that admin users can access dashboard."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dashboard.html')

    def test_admin_can_access_users(self):
        """Test that admin can access user management."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/users.html')

    def test_admin_can_access_payments(self):
        """Test that admin can access payment monitoring."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_payments'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/payments.html')

    def test_admin_can_access_invoices(self):
        """Test that admin can access invoice management."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_invoices'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/invoices.html')

    def test_admin_can_access_contacts(self):
        """Test that admin can access contact management."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_contacts'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/contacts.html')

    def test_admin_can_access_settings(self):
        """Test that admin can access system settings."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/settings.html')


class AdminDashboardTestCase(TestCase):
    """Test admin dashboard functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_dashboard_shows_user_count(self):
        """Test that dashboard displays total user count."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, '2')  # admin + testuser

    def test_dashboard_shows_invoice_stats(self):
        """Test that dashboard displays invoice statistics."""
        # Create test invoice
        Invoice.objects.create(
            user=self.user,
            business_name='Test Business',
            client_name='Test Client',
            client_email='client@example.com',
            client_address='123 Main St',
            status='unpaid'
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['total_invoices'], 1)
        self.assertEqual(context['pending_invoices'], 1)


class AdminUserManagementTestCase(TestCase):
    """Test admin user management."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        for i in range(5):
            User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )

    def test_users_page_lists_users(self):
        """Test that users page lists all users."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin')

    def test_user_search_functionality(self):
        """Test user search."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_users'), {'search': 'user1'})
        self.assertEqual(response.status_code, 200)

    def test_user_status_filter(self):
        """Test filtering users by status."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_users'), {'status': 'active'})
        self.assertEqual(response.status_code, 200)


class AdminPaymentMonitoringTestCase(TestCase):
    """Test admin payment monitoring."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_payments_page_displays_transactions(self):
        """Test that payments page shows transactions."""
        # Create test invoice and payment
        invoice = Invoice.objects.create(
            user=self.user,
            business_name='Test',
            client_name='Client',
            client_email='client@example.com',
            client_address='123 St',
            status='paid'
        )
        Payment.objects.create(
            invoice=invoice,
            user=self.user,
            reference='TEST001',
            amount=Decimal('100.00'),
            currency='USD',
            status='success',
            customer_email='client@example.com'
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_payments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST001')

    def test_payment_status_filtering(self):
        """Test filtering payments by status."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_payments'), {'status': 'success'})
        self.assertEqual(response.status_code, 200)


class AdminContactManagementTestCase(TestCase):
    """Test admin contact submission management."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )

    def test_contacts_page_lists_submissions(self):
        """Test that contacts page lists submissions."""
        ContactSubmission.objects.create(
            name='John Doe',
            email='john@example.com',
            subject='general',
            message='Test message',
            status='new'
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_contacts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')

    def test_update_contact_status(self):
        """Test updating contact submission status."""
        submission = ContactSubmission.objects.create(
            name='John Doe',
            email='john@example.com',
            subject='general',
            message='Test message',
            status='new'
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('update_contact_status', args=[submission.id]),
            {'status': 'resolved'}
        )
        
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'resolved')

    def test_contact_status_filter(self):
        """Test filtering contacts by status."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin_contacts'), {'status': 'new'})
        self.assertEqual(response.status_code, 200)
