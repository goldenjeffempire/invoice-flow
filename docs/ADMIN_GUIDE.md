# InvoiceFlow Admin Guide

Complete administration guide for managing the InvoiceFlow platform.

---

## Admin Access

**URL:** `https://yoursite.com/admin/`

**Credentials:**
- Username: `admin`
- Password: `admin123` (change this immediately!)

---

## First Steps as Admin

### 1. Change Admin Password (CRITICAL!)

```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(username='admin')
>>> user.set_password('your-strong-password')
>>> user.save()
>>> exit()
```

Or use admin interface:
1. Log in to `/admin/`
2. Click your username (top right)
3. Change Password

### 2. Configure Site Information

In Admin Dashboard:
1. Go to **Sites** > **Sites** (if using Django's site framework)
2. Update domain to your production domain
3. Save changes

### 3. Set Up User Profiles

For each user, configure:
1. **Default Currency** - USD, EUR, NGN, etc.
2. **Default Tax Rate** - Your VAT/GST rate
3. **Invoice Prefix** - INV, BIL, etc.
4. **Timezone** - User's timezone
5. **Business Info** - Company details

---

## Core Admin Functions

### User Management

**Path:** `/admin/auth/user/`

Tasks:
- Create new users
- Reset passwords
- Manage user permissions
- View user activity
- Deactivate inactive users

### User Profiles

**Path:** `/admin/invoices/userprofile/`

Configure per user:
- Company name and logo
- Business contact info
- Invoice defaults (currency, tax, prefix)
- Payment settings (Paystack subaccounts)
- Notification preferences
- Timezone and locale

### Invoices

**Path:** `/admin/invoices/invoice/`

Monitor:
- All invoices created
- Invoice status (draft, sent, paid, overdue)
- Total revenue
- Outstanding amount
- Payment dates

**Actions:**
- View invoice details
- Filter by status/date/user
- Export invoice reports

### Payments

**Path:** `/admin/invoices/payment/`

Track:
- All payments received
- Payment method (bank, Paystack, etc.)
- Payment status
- Transaction IDs
- Reconciliation status

### Email Logs

**Path:** `/admin/invoices/emaildeliverylog/`

Monitor:
- All sent emails
- Delivery status (sent, bounced, failed)
- Recipient addresses
- Timestamps
- Error messages

**Troubleshoot:**
- Check if emails are being sent
- Identify delivery issues
- Resend failed emails

### Email Retry Queue

**Path:** `/admin/invoices/emailretryqueue/`

Monitor:
- Failed emails pending retry
- Retry attempts count
- Error reasons
- Retry schedules

---

## Reporting & Analytics

### Key Metrics to Monitor

1. **User Growth**
   - New users this week/month
   - Active users
   - Inactive users (churn alert)

2. **Invoice Statistics**
   - Total invoices created
   - Average invoice value
   - Payment success rate
   - Days to payment

3. **Revenue**
   - Total revenue
   - Revenue this period
   - Outstanding invoices
   - Overdue invoices

4. **System Health**
   - Email delivery rate
   - Payment success rate
   - API error rate
   - Database response time

### Generate Reports

```bash
# Invoice summary
python manage.py shell << 'EOF'
from invoices.models import Invoice
from django.utils import timezone
from datetime import timedelta

week_ago = timezone.now() - timedelta(days=7)
recent = Invoice.objects.filter(created_at__gte=week_ago)

print(f"Invoices created this week: {recent.count()}")
print(f"Total value: {recent.aggregate(Sum('total'))}")
print(f"Paid: {recent.filter(status='paid').count()}")
EOF

# User activity
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

active = User.objects.filter(last_login__gte=timezone.now()-timedelta(days=7))
print(f"Active users (7d): {active.count()}")

dormant = User.objects.filter(last_login__lt=timezone.now()-timedelta(days=30))
print(f"Dormant users (30d): {dormant.count()}")
EOF
```

---

## Security Management

### Monitor Security Events

Check `/admin/invoices/auditlog/` if available:
- Failed login attempts
- Permission changes
- Data access
- Suspicious activities

### User Permissions

**Path:** `/admin/auth/group/`

Predefined groups:
- **Administrators** - Full access
- **Accountants** - Invoice and payment access
- **Support** - User support and refunds
- **Viewers** - Read-only access

Assign users to groups based on roles.

### API Keys

For users integrating via API:
1. Go to `/admin/invoices/apitoken/` (if enabled)
2. Generate new tokens
3. Revoke expired/compromised tokens
4. Monitor API usage

### Password Policy

Enforce in user management:
- Minimum 12 characters
- Require complexity (mix of chars, numbers, symbols)
- Expiration (90 days recommended)
- Prevent reuse (last 5 passwords)

---

## Database Management

### Backups

Automated by Replit/hosting provider. Check:
1. Last backup timestamp
2. Backup retention policy
3. Restoration procedure

### Database Maintenance

```bash
# Optimize database
python manage.py optimize_indexes

# Clear old sessions
python manage.py clearsessions

# Check database integrity
python manage.py dbshell
> PRAGMA integrity_check;  -- SQLite
> SELECT pg_stat_all_indexes;  -- PostgreSQL
```

### Data Cleanup

Remove old data safely:

```bash
# Delete old email logs (older than 90 days)
python manage.py shell << 'EOF'
from invoices.models import EmailDeliveryLog
from datetime import timedelta
from django.utils import timezone

old = EmailDeliveryLog.objects.filter(
    created_at__lt=timezone.now() - timedelta(days=90)
)
count = old.count()
old.delete()
print(f"Deleted {count} old email logs")
EOF

# Archive overdue invoices
python manage.py shell << 'EOF'
from invoices.models import Invoice
from datetime import timedelta
from django.utils import timezone

old_unpaid = Invoice.objects.filter(
    status='unpaid',
    due_date__lt=timezone.now() - timedelta(days=180)
)
# Consider marking as archived instead of deleting
EOF
```

---

## Monitoring & Alerts

### Health Checks

**URL:** `/health/`

Check system health:
- Database connection
- Cache status
- Email service
- Payment gateway
- Error monitoring

**Response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "email": "configured",
    "cache": "active"
}
```

### Check Logs

**Path:** `/admin/invoices/systemlog/` (if available)

Monitor:
- Application errors
- Performance issues
- Warning events
- Info messages

### Performance Monitoring

```bash
# View database query count
python manage.py runserver --debug-toolbar

# Check slow queries
python manage.py shell << 'EOF'
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as context:
    # Run your code
    pass

for query in context:
    if float(query['time']) > 0.1:  # Queries over 100ms
        print(f"Slow query ({query['time']}s):")
        print(query['sql'])
EOF
```

---

## Incident Response

### Common Issues

#### High Email Bounce Rate

1. Check email configuration: `/admin/invoices/userprofile/`
2. Verify SENDGRID_API_KEY is set
3. Check email templates for errors
4. Review bounce reasons in `/admin/invoices/emaildeliverylog/`

**Action:**
```bash
python manage.py shell << 'EOF'
from invoices.models import EmailDeliveryLog
bounced = EmailDeliveryLog.objects.filter(status='bounced').count()
print(f"Bounced emails: {bounced}")
EOF
```

#### Payment Processing Down

1. Verify PAYSTACK_SECRET_KEY is set
2. Check Paystack dashboard for incidents
3. Review recent payments: `/admin/invoices/payment/`
4. Check payment webhook logs: `/admin/invoices/emailretryqueue/`

**Test Paystack connection:**
```bash
python manage.py shell << 'EOF'
import requests
import os

key = os.getenv('PAYSTACK_SECRET_KEY')
if not key:
    print("ERROR: PAYSTACK_SECRET_KEY not set")
else:
    response = requests.get(
        'https://api.paystack.co/customer',
        headers={'Authorization': f'Bearer {key}'}
    )
    print(f"Paystack API: {response.status_code}")
EOF
```

#### Database Issues

1. Check database connection: `/health/detailed/`
2. Verify DATABASE_URL environment variable
3. Check Replit database status
4. Review slow queries (see Performance section above)

---

## Maintenance Schedule

### Daily
- [ ] Check health endpoint `/health/`
- [ ] Monitor email delivery logs
- [ ] Review error logs
- [ ] Check payment reconciliation

### Weekly
- [ ] Review user activity
- [ ] Check API usage
- [ ] Verify backup completion
- [ ] Review security logs

### Monthly
- [ ] Generate revenue report
- [ ] Review user metrics
- [ ] Analyze performance metrics
- [ ] Update documentation
- [ ] Test disaster recovery

### Quarterly
- [ ] Security audit
- [ ] Database optimization
- [ ] Dependency updates
- [ ] Performance tuning
- [ ] Capacity planning

---

## Advanced Admin Tasks

### Create Test Data

```bash
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from invoices.models import Invoice, InvoiceTemplate
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

# Create test user
test_user, _ = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)
test_user.set_password('testpass123')
test_user.save()

# Create test invoice
Invoice.objects.create(
    user=test_user,
    client_name="Test Client",
    client_email="client@test.com",
    amount=Decimal("1000.00"),
    status='sent'
)

print("Test data created successfully")
EOF
```

### Export Data

```bash
# Export all invoices as CSV
python manage.py shell << 'EOF'
import csv
from invoices.models import Invoice

with open('invoices_export.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', 'Client', 'Amount', 'Status', 'Date'])
    
    for invoice in Invoice.objects.all():
        writer.writerow([
            invoice.id,
            invoice.client_name,
            invoice.amount,
            invoice.status,
            invoice.created_at.date()
        ])

print("Exported to invoices_export.csv")
EOF
```

### Bulk Actions

```bash
# Mark all draft invoices as sent
python manage.py shell << 'EOF'
from invoices.models import Invoice

draft = Invoice.objects.filter(status='draft')
draft.update(status='sent')
print(f"Updated {draft.count()} invoices")
EOF
```

---

## Support & Escalation

### When to Escalate

- Database errors
- Payment gateway failures
- Email delivery issues (>1% bounce rate)
- Security incidents
- Performance degradation (>2x slow queries)

### Emergency Procedures

1. **Take System Offline (if critical issue)**
   ```bash
   # Put in maintenance mode
   export MAINTENANCE_MODE=true
   ```

2. **Notify Users**
   - Send maintenance email
   - Post status on support page

3. **Diagnose Issue**
   - Check logs
   - Run health checks
   - Review recent changes

4. **Restore Service**
   - Apply fix or rollback
   - Clear caches
   - Resume operations

5. **Post-Incident**
   - Document incident
   - Update runbooks
   - Implement monitoring

---

## Resources

- Admin Interface: `/admin/`
- Health Check: `/health/`
- API Docs: `/api/schema/`
- Support: See PRODUCTION_READY.md
- Customization: See CUSTOMIZATION_GUIDE.md
