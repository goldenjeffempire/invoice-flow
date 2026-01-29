from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class CoreWorkflowsTest(TestCase):
    def test_landing_page(self):
        response = self.client.get(reverse('invoices:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "InvoiceFlow")

    def test_auth_pages_accessible(self):
        for url_name in ['login', 'signup', 'password_reset']:
            response = self.client.get(reverse(f'invoices:{url_name}'))
            self.assertEqual(response.status_code, 200)

    def test_security_page_auth_required(self):
        response = self.client.get(reverse('invoices:security'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_signup_page_content(self):
        response = self.client.get(reverse('invoices:signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get Started")
