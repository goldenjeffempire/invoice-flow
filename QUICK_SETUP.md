# Quick Customization Setup (5 minutes)

Fast way to customize InvoiceFlow for your business.

## Step 1: Update Basic Branding (1 min)

Open `invoiceflow/settings.py` and add at the end:

```python
# Branding Configuration
SITE_NAME = "Your Company Name"
BRAND_LOGO_TEXT = "Your Company"
BRAND_COLOR_PRIMARY = "#6366f1"  # Your primary color
SENDGRID_FROM_EMAIL = "billing@yourcompany.com"
```

## Step 2: Set Invoice Defaults (2 min)

Go to Django Admin at `/admin/` (login with admin/admin123):

1. Click **Invoices > User Profiles**
2. Click on admin user's profile
3. Update:
   - **Default Currency:** NGN (or your currency)
   - **Default Tax Rate:** 7.50 (for 7.5% VAT)
   - **Invoice Prefix:** INV (or your prefix)
   - **Company Name:** Your Company Name
   - **Business Email:** your-email@company.com
4. Click **Save**

## Step 3: Customize Email (1 min)

Edit `templates/emails/verify_email.html`:
- Find `InvoiceFlow` and replace with your company name
- Find `#6366f1` and replace with your brand color
- Find line 51 and update site name

Repeat for `templates/emails/password_reset.html`

## Step 4: Update Logo (1 min)

Replace these files in `static/`:
- `favicon.svg` - Your logo (SVG format recommended)
- `favicon-16x16.png` - 16x16 pixel version
- `favicon-32x32.png` - 32x32 pixel version

Or keep the default InvoiceFlow logos.

## Done! 

Restart the server and check:
1. Home page shows your branding
2. Email verification works with your email
3. Dashboard shows your company name
4. Invoices use your defaults

---

## Next Steps

For more detailed customization, see `CUSTOMIZATION_GUIDE.md`

- Add custom CSS styling
- Configure payment terms
- Create invoice templates
- Set notification preferences
