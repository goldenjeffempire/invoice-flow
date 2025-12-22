"""Load testing script for InvoiceFlow API"""
from locust import HttpUser, task, between
import random
import json


class InvoiceFlowUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Set up test user and get auth token"""
        # Create test user
        self.username = f"loadtest_{random.randint(1000, 9999)}"
        self.email = f"{self.username}@example.com"
        
        # Note: In real test, would register user first
        # For now, using existing user if available
        self.token = None
    
    @task(3)
    def list_invoices(self):
        """List invoices - most common operation"""
        headers = {}
        if self.token:
            headers['Authorization'] = f'Token {self.token}'
        
        response = self.client.get(
            "/api/v1/invoices/",
            headers=headers,
            name="/api/v1/invoices/ [GET]"
        )
        
    @task(2)
    def health_check(self):
        """Check health endpoint - should be fast"""
        self.client.get(
            "/health/",
            name="/health/ [GET]"
        )
    
    @task(1)
    def get_home(self):
        """Load home page"""
        response = self.client.get(
            "/",
            name="/ [GET]"
        )
    
    @task(1)
    def api_docs(self):
        """Load API documentation"""
        response = self.client.get(
            "/api/schema/swagger/",
            name="/api/schema/swagger/ [GET]"
        )


class AdminUser(HttpUser):
    wait_time = between(1, 2)
    
    @task(2)
    def dashboard(self):
        """Admin accessing dashboard"""
        self.client.get(
            "/invoices/dashboard/",
            name="/invoices/dashboard/ [GET]"
        )
    
    @task(1)
    def list_templates(self):
        """List templates"""
        self.client.get(
            "/api/v1/templates/",
            name="/api/v1/templates/ [GET]"
        )
