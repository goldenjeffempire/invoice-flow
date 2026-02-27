from django.test import TestCase
from django.urls import reverse

class CoreWorkflowsTest(TestCase):
    def test_landing_page(self):
        response = self.client.get(reverse('invoices:home'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "InvoiceFlow")

    def test_auth_pages_accessible(self):
        for url_name in ['login', 'signup', 'password_reset']:
            response = self.client.get(reverse(f'invoices:{url_name}'), follow=True)
            self.assertEqual(response.status_code, 200)

    def test_security_page_auth_required(self):
        response = self.client.get(reverse('invoices:security'), follow=True)
        # It should redirect to login, and follow the redirect to 200
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_signup_page_content(self):
        response = self.client.get(reverse('invoices:signup'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get Started")
