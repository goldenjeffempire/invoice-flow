# InvoiceFlow - Customization Guide

Complete guide to customize branding, email templates, and invoicing defaults.

---

## 1. Branding & Logo Configuration

### Update Site Branding

**File:** `invoiceflow/settings.py`

Add these settings to customize your brand:

```python
# Add to settings.py

# Branding Configuration
SITE_NAME = "YourCompany Invoices"  # Your business name
SITE_DOMAIN = "invoices.yourcompany.com"  # Your domain
BRAND_COLOR_PRIMARY = "#6366f1"  # Primary brand color (Indigo)
BRAND_COLOR_SECONDARY = "#10b981"  # Secondary brand color (Green)
BRAND_LOGO_TEXT = "YourCompany"  # Logo text
```

### Update Navigation Logo

**File:** `templates/base/layout-light.html` (line 77)

Change:
```html
<span class="nav-landing-logo-text">InvoiceFlow</span>
```

To:
```html
<span class="nav-landing-logo-text">{{ settings.BRAND_LOGO_TEXT }}</span>
```

### Replace Logo Files

Replace these files in `static/` directory:
- `favicon.svg` - Website favicon
- `favicon-16x16.png` - Small favicon
- `favicon-32x32.png` - Medium favicon
- `apple-touch-icon.png` - Mobile icon (add if missing)

**How to add logos:**

1. Create your logo files (SVG recommended for favicon)
2. Upload them to `/static/` folder
3. Ensure they're at least 512x512 pixels for the touch icon

---

## 2. Email Template Customization

### Overview

Email templates are located in `templates/emails/`:
- `verify_email.html` - Email verification
- `password_reset.html` - Password reset

### Customize Email Color Scheme

**Update in both email templates:**

```html
<!-- Old color (Indigo) -->
<h1 style="color: #6366f1;">InvoiceFlow</h1>

<!-- New color -->
<h1 style="color: YOUR_BRAND_COLOR;">Your Brand Name</h1>
```

**Replace these colors throughout the templates:**
- `#6366f1` → Your primary brand color
- `#1e293b` → Your heading color
- `#475569` → Your text color

### Customize Email Sender Name

**File:** `invoiceflow/settings.py` (line 321)

```python
SENDGRID_FROM_EMAIL = "noreply@yourdomain.com"
```

Or for branded emails:

```python
SENDGRID_FROM_EMAIL = "invoicing@yourcompany.com"
DEFAULT_FROM_EMAIL = "noreply@yourcompany.com"
```

### Add Company Logo to Emails

To add your company logo to emails, modify templates:

```html
<!-- Add after <tr><td style="padding: 40px 40px 30px; text-align: center;"> -->
<img src="{{ logo_url }}" alt="Your Company Logo" style="max-width: 200px; height: auto; margin-bottom: 20px;">
```

Then pass `logo_url` in email context:

```python
context = {
    'user': user,
    'verification_url': url,
    'site_name': 'Your Company',
    'logo_url': 'https://yourdomain.com/static/logo.png',
}
```

### Create Additional Email Templates

**Example: Invoice sent notification**

Create `templates/emails/invoice_sent.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Invoice Sent</title>
</head>
<body style="font-family: Arial, sans-serif;">
    <h2>Invoice #{{ invoice.invoice_id }} Sent</h2>
    <p>Hello {{ recipient_name }},</p>
    <p>We've sent invoice #{{ invoice.invoice_id }} ({{ invoice.total_amount }}) to {{ recipient_email }}.</p>
    <p>Payment is due by {{ invoice.due_date|date:"F j, Y" }}</p>
    <a href="{{ invoice_url }}" style="background: #6366f1; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
        View Invoice
    </a>
</body>
</html>
```

---

## 3. Invoicing Defaults Configuration

### Update User Profile Defaults

**File:** `invoices/models.py` (UserProfile model, lines 88-136)

Current defaults:
```python
default_currency = models.CharField(max_length=3, default="USD")
default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
invoice_prefix = models.CharField(max_length=10, default="INV")
```

### Change Invoice Prefix

**In Django Admin:**

1. Go to `/admin/invoices/userprofile/`
2. Select user's profile
3. Change `invoice_prefix` from `"INV"` to your prefix (e.g., `"INV-2024"`, `"BIL"`)

**Programmatically:**

```python
from invoices.models import UserProfile

profile = UserProfile.objects.get(user=user)
profile.invoice_prefix = "INV-2024"
profile.default_currency = "NGN"  # Nigerian Naira
profile.default_tax_rate = Decimal("7.50")  # 7.5% VAT
profile.save()
```

### Set Default Tax Rate

**For all users:**

```python
# In a Django management command or shell
from invoices.models import UserProfile

UserProfile.objects.all().update(default_tax_rate=Decimal("10.00"))
```

**For specific user:**

```python
from invoices.models import UserProfile

profile = UserProfile.objects.get(user=user)
profile.default_tax_rate = Decimal("10.00")  # 10%
profile.save()
```

### Configure Invoice Template Defaults

**File:** `invoices/models.py` (InvoiceTemplate model, lines 142-177)

When creating templates, set as default:

```python
template = InvoiceTemplate.objects.create(
    user=user,
    name="Standard Invoice",
    business_name="Your Company Ltd.",
    business_email="billing@yourcompany.com",
    business_phone="+1-555-123-4567",
    business_address="123 Business Street, City, Country",
    bank_name="Your Bank",
    account_name="Company Account",
    currency="NGN",
    tax_rate=Decimal("7.50"),
    is_default=True,  # Set as default
)
```

### Set Currency and Timezone

**File:** `invoices/models.py` (UserProfile, lines 101-105)

Add to profile setup:

```python
profile.default_currency = "NGN"  # Your default currency code
profile.timezone = "Africa/Lagos"  # Your timezone
profile.save()
```

### Configure Payment Terms

**Create payment terms for invoices:**

Create `templates/invoices/payment_terms.html`:

```html
<div class="payment-terms">
    <h3>Payment Terms</h3>
    <ul>
        <li>Invoice due: 30 days from invoice date</li>
        <li>Late payment: 1.5% per month interest</li>
        <li>Accepted payment methods: Bank transfer, PayStack</li>
        <li>Bank details provided in invoice footer</li>
    </ul>
</div>
```

---

## 4. Complete Customization Checklist

### Branding
- [ ] Update `SITE_NAME` in settings
- [ ] Update `BRAND_LOGO_TEXT`
- [ ] Upload custom favicon files
- [ ] Update brand colors (primary, secondary)
- [ ] Update logo/images in templates

### Email
- [ ] Update sender email (`SENDGRID_FROM_EMAIL`)
- [ ] Customize email colors
- [ ] Add company logo to email templates
- [ ] Update company name in email footers
- [ ] Test email delivery

### Invoicing
- [ ] Set default invoice prefix
- [ ] Set default tax rate
- [ ] Configure default currency
- [ ] Set company timezone
- [ ] Create default invoice template
- [ ] Add bank account details to templates
- [ ] Configure payment terms

### Optional
- [ ] Add custom CSS styling
- [ ] Create additional email templates
- [ ] Customize invoice PDF layout
- [ ] Add custom payment instructions
- [ ] Configure late payment notices

---

## 5. Testing Your Changes

### Test Branding

1. Log in to dashboard
2. Verify navigation logo and colors
3. Check all pages load with correct branding

### Test Email Templates

1. Create a test account
2. Trigger email verification
3. Check email formatting and branding
4. Test password reset email

### Test Invoicing Defaults

1. Create an invoice
2. Verify default tax rate applied
3. Check currency display
4. Verify invoice number prefix

---

## 6. Advanced Customization

### Add Custom CSS

**File:** `static/css/custom-branding.css`

```css
:root {
    --brand-primary: #6366f1;
    --brand-secondary: #10b981;
    --text-primary: #1e293b;
    --text-secondary: #475569;
}

/* Override default colors */
.nav-landing-btn-primary {
    background: var(--brand-primary);
}

.btn-primary {
    background: var(--brand-primary);
    color: white;
}
```

### Customize Invoice PDF

**File:** `invoices/services/invoice_pdf.py`

Modify to include custom branding, logos, and formatting.

---

## Support

For help with customization:
1. Check `/admin/` interface for quick edits
2. Review model defaults in `invoices/models.py`
3. Check email templates in `templates/emails/`
4. Customize CSS in `static/css/`

All changes are applied immediately - no deployment needed for most customizations!
