"""
Tests for Create Invoice functionality with production-grade coverage.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from invoices.models import Invoice, LineItem, UserProfile


class CreateInvoiceStepTests(TestCase):
    """Test multi-step invoice creation workflow."""

    def setUp(self):
        """Set up test user and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!@#'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_step1_requires_login(self):
        """Step 1 requires authentication."""
        response = self.client.get(reverse('invoices:create_invoice_start'))
        self.assertEqual(response.status_code, 302)

    def test_step1_get_success(self):
        """Step 1 GET request returns form."""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.get(reverse('invoices:create_invoice_start'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'invoices/create_invoice/step1_details.html')

    def test_step1_post_valid_data(self):
        """Step 1 POST with valid data saves to session."""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.post(reverse('invoices:create_invoice_start'), {
            'invoice_date': '2025-12-30',
            'due_date': '2026-01-30',
            'currency': 'USD',
            'invoice_number': 'INV-001',
            'description': 'Test invoice',
            'client_name': 'John Doe',
            'client_email': 'john@example.com',
            'client_phone': '+1234567890',
            'client_address': '123 Main St',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('invoice_details', self.client.session)
        self.assertIn('client_details', self.client.session)

    def test_step1_invalid_dates(self):
        """Step 1 rejects due date before invoice date."""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.post(reverse('invoices:create_invoice_start'), {
            'invoice_date': '2026-01-30',
            'due_date': '2025-12-30',  # Before invoice date
            'currency': 'USD',
            'client_name': 'John Doe',
            'client_email': 'john@example.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'details_form', None, 'Due date cannot be before invoice date.')

    def test_step2_requires_step1(self):
        """Step 2 requires step 1 completion."""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.get(reverse('invoices:create_invoice_items'))
        self.assertEqual(response.status_code, 302)

    def test_step3_requires_items(self):
        """Step 3 requires line items."""
        self.client.login(username='testuser', password='TestPass123!@#')
        session = self.client.session
        session['invoice_details'] = {'currency': 'USD'}
        session.save()
        
        response = self.client.get(reverse('invoices:create_invoice_taxes'))
        self.assertEqual(response.status_code, 302)

    def test_full_workflow_success(self):
        """Complete invoice creation workflow."""
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # Step 1: Details
        self.client.post(reverse('invoices:create_invoice_start'), {
            'invoice_date': '2025-12-30',
            'due_date': '2026-01-30',
            'currency': 'USD',
            'client_name': 'John Doe',
            'client_email': 'john@example.com',
        })
        
        # Step 2: Items (via session)
        session = self.client.session
        session['line_items'] = [{
            'description': 'Service',
            'quantity': '2',
            'unit_price': '100.00'
        }]
        session.save()
        
        # Step 3: Taxes
        self.client.post(reverse('invoices:create_invoice_taxes'), {
            'tax_rate': '10.00',
            'discount_type': 'none',
        })
        
        # Step 4: Review and submit
        response = self.client.post(reverse('invoices:create_invoice_review'), {
            'payment_terms': 'Due on receipt',
            'notes': 'Thank you!',
            'send_invoice': False,
            'save_as_draft': False,
        }, follow=True)
        
        # Verify invoice was created
        invoice = Invoice.objects.filter(user=self.user).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.client_name, 'John Doe')
        self.assertEqual(invoice.tax_rate, Decimal('10.00'))


class InvoiceCreateFormTests(TestCase):
    """Test Create Invoice forms."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(username='testuser')

    def test_invoice_details_form_valid(self):
        """Valid invoice details form."""
        from invoices.invoice_create_forms import InvoiceDetailsForm
        form = InvoiceDetailsForm({
            'invoice_date': '2025-12-30',
            'due_date': '2026-01-30',
            'currency': 'USD',
        })
        self.assertTrue(form.is_valid())

    def test_line_item_form_validation(self):
        """Line item form validates quantity and price."""
        from invoices.invoice_create_forms import LineItemForm
        
        # Invalid: quantity = 0
        form = LineItemForm({
            'description': 'Service',
            'quantity': '0',
            'unit_price': '100.00'
        })
        self.assertFalse(form.is_valid())
        
        # Invalid: negative price
        form = LineItemForm({
            'description': 'Service',
            'quantity': '1',
            'unit_price': '-50.00'
        })
        self.assertFalse(form.is_valid())

    def test_tax_discount_form_validation(self):
        """Tax and discount form validates ranges."""
        from invoices.invoice_create_forms import TaxesDiscountsForm
        
        # Invalid: tax > 100
        form = TaxesDiscountsForm({
            'tax_rate': '150',
        })
        self.assertFalse(form.is_valid())
