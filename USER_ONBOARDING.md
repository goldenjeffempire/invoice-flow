# InvoiceFlow User Onboarding Guide

Welcome to InvoiceFlow! This guide walks new users through getting started.

---

## First Time Setup (5 minutes)

### 1. Create Your Account
- Go to `/signup/`
- Enter your email and password
- Click "Sign Up"
- Check email for verification link
- Click link to verify

### 2. Complete Your Profile
- Go to Dashboard → Settings
- Update your company information:
  - Company Name
  - Business Email
  - Business Phone
  - Business Address
- Set defaults:
  - Currency (USD, EUR, NGN, etc.)
  - Tax Rate (0% for none)
  - Invoice Prefix (INV, BIL, etc.)
- Click "Save"

### 3. Enable Security
- Go to Settings → Security
- **Enable 2FA (Two-Factor Authentication)**
  - Click "Enable 2FA"
  - Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
  - Enter 6-digit code to verify
  - Save backup codes in safe place
  - Click "Done"

✅ Your account is now set up!

---

## Create Your First Invoice (2 minutes)

### Step 1: Start New Invoice
1. Click "Create Invoice" button
2. Fill in client details:
   - Client Name
   - Client Email
   - Client Phone (optional)
   - Client Address (optional)

### Step 2: Add Items
1. Click "Add Item"
2. Enter:
   - Description (e.g., "Web Development Services")
   - Quantity (e.g., 10 hours)
   - Unit Price (e.g., $100/hour)
3. Click "Add Item" again for more items
4. Tax rate auto-applies from your settings

### Step 3: Review & Send
1. Review invoice total (Subtotal + Tax + Total)
2. Optional: Add notes or terms
3. Click "Send Invoice"
4. Enter recipient email (or use client email)
5. Add custom message (optional)
6. Click "Send"

✅ Invoice sent! Client receives email with payment link.

---

## Accept Payments

### For Clients
When clients receive your invoice email:
1. Click "Pay Now" button
2. Choose payment method
3. Complete Paystack payment
4. Get payment confirmation

### For You
When payment is received:
1. Invoice automatically marked as "Paid"
2. You receive payment notification email
3. Payment appears in Dashboard
4. Money deposited to your bank account

---

## Key Features

### Invoice Templates
Save time with templates:
1. Go to "My Templates"
2. Click "Create Template"
3. Fill in your standard company info
4. Click "Save as Template"
5. Use when creating invoices

### Recurring Invoices
Set up automatic invoicing:
1. Go to "Recurring Invoices"
2. Click "New Recurring"
3. Set frequency (Weekly, Monthly, etc.)
4. Configure default items
5. Choose clients to auto-invoice
6. Click "Enable"

### Invoice Status Tracking
Track invoice status:
- **Draft** - Not sent yet
- **Sent** - Waiting for payment
- **Viewed** - Client opened email
- **Paid** - Payment received
- **Overdue** - Past due date

### Dashboard Analytics
View your business at a glance:
- Total invoices
- Revenue this month
- Outstanding amount
- Payment trends

---

## Common Tasks

### Send Invoice Reminder
1. Go to Invoices
2. Find unpaid invoice
3. Click "Send Reminder"
4. Confirm email address
5. Click "Send"

### Edit Invoice (Before Sending)
1. Go to Invoices
2. Click invoice number
3. Click "Edit"
4. Update details
5. Click "Save"

### Mark as Paid
1. Go to Invoices
2. Click invoice
3. Click "Mark as Paid"
4. Enter payment details (optional)
5. Click "Confirm"

### Duplicate Invoice
1. Go to Invoices
2. Click invoice
3. Click "Duplicate"
4. Modify details
5. Click "Send"

### Email Settings
1. Go to Settings → Email
2. Configure:
   - Email signature
   - Default message
   - Auto-reminders
3. Click "Save"

---

## Payment Methods Supported

✅ **Paystack** (Primary)
- Debit/Credit Cards
- Bank Transfers
- Mobile Money

---

## Security Best Practices

1. **Password**
   - Use strong password (12+ characters)
   - Unique to InvoiceFlow
   - Don't share with others

2. **2FA**
   - Enable 2FA (Recommended)
   - Save backup codes
   - Keep authenticator app secure

3. **Devices**
   - Log out on shared computers
   - Use "Log Out All Devices" if compromised
   - Update password regularly

4. **Data**
   - Don't share API tokens
   - Update company info regularly
   - Archive old invoices

---

## Troubleshooting

### Can't Login
1. Check email/password correct
2. Reset password: Forgot Password link
3. Check 2FA app (if enabled)

### Invoice Not Sending
1. Verify client email is correct
2. Check SENDGRID configuration
3. Verify email isn't in spam filter

### Payment Not Processing
1. Verify Paystack is configured
2. Check payment method is supported
3. Ensure sufficient funds

### Need Help
1. Check FAQ: `/faq/`
2. Email support: support@yourdomain.com
3. Check docs: ADMIN_GUIDE.md

---

## Settings Overview

### Account Settings
- Email address
- Password
- 2FA authentication
- Account deletion

### Business Settings
- Company name & logo
- Contact information
- Default currency
- Tax rate
- Invoice prefix

### Email Settings
- Email signature
- Default message
- Auto-reminders
- Notification preferences

### Payment Settings
- Paystack account
- Bank details
- Settlement preferences

### Privacy
- Data export
- Data deletion
- Cookie preferences

---

## Email Notifications

You'll receive emails for:
- ✅ Invoice created (you)
- ✅ Invoice sent (you)
- ✅ Invoice viewed (you)
- ✅ Payment received (you)
- ✅ Invoice overdue (you)
- ✅ Weekly summary (optional)

Configure which emails you want in Settings.

---

## API Access

For advanced users:
1. Go to Settings → API
2. Click "Generate Token"
3. Copy your API token
4. Use in API calls: `Authorization: Bearer TOKEN`

See API_QUICKSTART.md for examples.

---

## Tips for Success

1. **Use Templates** - Save time on recurring invoices
2. **Set Payment Terms** - Customize due dates
3. **Add Notes** - Include payment instructions
4. **Follow Up** - Send reminders before due date
5. **Review Analytics** - Track business growth
6. **Archive Old** - Clean up completed invoices

---

## Keyboard Shortcuts

- `?` - Show help
- `G` then `D` - Go to Dashboard
- `G` then `I` - Go to Invoices
- `G` then `S` - Go to Settings
- `Esc` - Close modal/popup

---

## Mobile App

Access InvoiceFlow on mobile:
1. Go to https://yourdomain.com/
2. Add to home screen (iOS/Android)
3. Use like native app

Features work full on mobile:
- ✅ Create invoices
- ✅ View payments
- ✅ Check status
- ✅ Manage settings

---

## When You're Ready

**Congratulations!** You're now ready to:
- ✅ Create professional invoices
- ✅ Accept payments online
- ✅ Track business finances
- ✅ Automate recurring billing

Start creating invoices and getting paid faster! 🚀

---

## Questions?

- **FAQ:** `/faq/` - Common questions
- **Support:** support@yourdomain.com
- **Docs:** See README.md
- **Video Help:** Available on Features page

---

**Last Updated:** December 22, 2025
