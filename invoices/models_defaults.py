"""
Default configuration for invoicing system.
Update these values to customize defaults for all new users.
"""

from decimal import Decimal

# Invoice Defaults
DEFAULT_INVOICE_PREFIX = "INV"
DEFAULT_CURRENCY = "USD"
DEFAULT_TAX_RATE = Decimal("0.00")  # 0% by default
DEFAULT_PAYMENT_TERMS_DAYS = 30

# Company Defaults
DEFAULT_TIMEZONE = "UTC"
DEFAULT_BUSINESS_COUNTRY = "NG"  # Nigeria

# Email Defaults
DEFAULT_SEND_EMAIL_ON_CREATION = True
DEFAULT_SEND_PAYMENT_REMINDERS = True
DEFAULT_REMIND_DAYS_BEFORE_DUE = 3

# Payment Defaults
DEFAULT_ACCEPT_PAYMENTS = True
DEFAULT_PAYMENT_GATEWAY = "paystack"
DEFAULT_PAYMENT_METHOD = "bank_transfer"

# Notification Defaults
NOTIFICATION_PREFERENCES = {
    "notify_invoice_created": True,
    "notify_payment_received": True,
    "notify_invoice_viewed": True,
    "notify_invoice_overdue": True,
    "notify_weekly_summary": False,
    "notify_security_alerts": True,
    "notify_password_changes": True,
}

# Branding
SITE_NAME = "InvoiceFlow"
BRAND_COLOR_PRIMARY = "#6366f1"
BRAND_COLOR_SECONDARY = "#10b981"
BRAND_LOGO_TEXT = "InvoiceFlow"

# Email Configuration
COMPANY_NAME = "InvoiceFlow"
COMPANY_EMAIL = "noreply@invoiceflow.com.ng"
COMPANY_SUPPORT_EMAIL = "support@invoiceflow.com.ng"
COMPANY_WEBSITE = "https://invoiceflow.com.ng"

# Footer Content
FOOTER_COMPANY_ADDRESS = "123 Business Street, Lagos, Nigeria"
FOOTER_COMPANY_PHONE = "+234 (0) 701-234-5678"
FOOTER_COMPANY_EMAIL = "contact@invoiceflow.com.ng"

# Custom Links
FOOTER_LINKS = {
    "help": "/support/",
    "privacy": "/privacy/",
    "terms": "/terms/",
    "security": "/security/",
    "api": "/api-access/",
}

# Invoice Template Defaults
INVOICE_TEMPLATE_DEFAULTS = {
    "business_name": "Your Company Name",
    "business_email": "billing@yourcompany.com",
    "business_phone": "+234 (0) XXX-XXX-XXXX",
    "business_address": "Your Business Address",
    "bank_name": "Your Bank Name",
    "account_name": "Your Account Name",
    "account_number": "XXXXXXXXXXXX",
}

# Payment Terms
PAYMENT_TERMS = {
    "net_30": "Net 30 days",
    "net_15": "Net 15 days",
    "net_60": "Net 60 days",
    "upon_receipt": "Due Upon Receipt",
    "custom": "Custom Terms",
}

# Tax Configurations
TAX_TYPES = {
    "vat": "Value Added Tax (VAT)",
    "gst": "Goods and Services Tax (GST)",
    "sales_tax": "Sales Tax",
    "service_tax": "Service Tax",
    "custom": "Custom Tax",
}

# Supported Currencies
SUPPORTED_CURRENCIES = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "NGN": "Nigerian Naira",
    "KES": "Kenyan Shilling",
    "ZAR": "South African Rand",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
}

# Timezones (Common African Timezones)
COMMON_TIMEZONES = [
    "UTC",
    "Africa/Lagos",
    "Africa/Johannesburg",
    "Africa/Cairo",
    "Africa/Nairobi",
    "Africa/Accra",
]

import logging
logger = logging.getLogger(__name__)
logger.debug("Default configuration loaded successfully")
