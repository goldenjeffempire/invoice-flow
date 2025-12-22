# InvoiceFlow Monitoring & Alerts Setup

Complete guide to monitor your InvoiceFlow platform in production.

---

## Health Endpoints

### Basic Health Check
```bash
curl https://yourdomain.com/health/
```

Response:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-12-22T23:30:00Z"
}
```

### Readiness Check (for load balancers)
```bash
curl https://yourdomain.com/health/ready/
```

### Liveness Check (for uptime monitors)
```bash
curl https://yourdomain.com/health/live/
```

### Detailed Health
```bash
curl https://yourdomain.com/health/detailed/
```

Full status of all systems.

---

## Monitoring Tools Setup

### 1. Sentry Error Tracking

**Setup:**
1. Create Sentry account: https://sentry.io/
2. Create new project (Django)
3. Copy DSN from settings
4. Add to Replit Secrets: `SENTRY_DSN=your_dsn`
5. Restart workflow

**Monitor:**
- Application errors
- Performance issues
- Releases & deployments
- Alerts & notifications

**Benefits:**
- Real-time error alerts
- Error trends and patterns
- User impact analysis
- Custom alerts

### 2. Uptime Monitoring

**Using Uptimerobot (Free):**
1. Go to https://uptimerobot.com/
2. Create account
3. Add monitor:
   - Name: InvoiceFlow
   - URL: https://yourdomain.com/health/
   - Type: HTTP(s)
   - Check frequency: 5 minutes
4. Set alerts:
   - Email notification
   - Slack integration (optional)

**Check Status:**
- Dashboard shows uptime %
- Incident history
- Response times

### 3. Google Analytics

**Setup:**
1. Create Google Analytics 4 account
2. Get Measurement ID
3. Add to templates or custom script
4. Link to dashboard

**Monitor:**
- User traffic
- Conversion rates
- Page load times
- Device types

---

## Email Delivery Monitoring

### Check Email Status in Admin

```bash
# Check today's emails
python manage.py shell << 'EOF'
from invoices.models import EmailDeliveryLog
from datetime import timedelta
from django.utils import timezone

today = EmailDeliveryLog.objects.filter(
    created_at__date=timezone.now().date()
)

print(f"Total sent: {today.filter(status='sent').count()}")
print(f"Failed: {today.filter(status='failed').count()}")
print(f"Bounced: {today.filter(status='bounced').count()}")
print(f"Bounce rate: {(today.filter(status='bounced').count() / today.count() * 100):.1f}%" if today.count() > 0 else "No emails")
EOF
```

### SendGrid Dashboard
1. Go to SendGrid settings
2. Go to Activity
3. Monitor:
   - Delivery rate
   - Bounce rate
   - Spam reports
   - Unsubscribes

**Alert Thresholds:**
- Bounce rate > 1% = Investigate
- Delivery < 99% = Alert
- Spam reports > 0.1% = Check

---

## Payment Monitoring

### Check Payment Status

```bash
python manage.py shell << 'EOF'
from invoices.models import Payment
from datetime import timedelta
from django.utils import timezone

recent = Payment.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=7)
)

print(f"Payments received (7d): {recent.count()}")
print(f"Total revenue: {recent.aggregate(Sum('amount_paid'))['amount_paid__sum']}")
print(f"Average transaction: {recent.aggregate(Avg('amount_paid'))['amount_paid__avg']}")
EOF
```

### Paystack Dashboard
1. Log in to Paystack
2. Go to Dashboard
3. Monitor:
   - Daily transactions
   - Payment success rate
   - Refunds
   - Settlement schedule

**Alert Thresholds:**
- Payment failures > 2% = Investigate
- Settlement delay = Contact support
- Suspicious activity = Review transactions

---

## Database Monitoring

### Check Database Health

```bash
python manage.py shell << 'EOF'
from django.db import connection
from django.db.backends.utils import CursorWrapper

with connection.cursor() as cursor:
    # Check connection
    cursor.execute("SELECT 1")
    print("✓ Database connected")
    
    # Check slow queries (PostgreSQL)
    cursor.execute("""
        SELECT mean_exec_time FROM pg_stat_statements 
        WHERE mean_exec_time > 100 
        ORDER BY mean_exec_time DESC LIMIT 5
    """)
    results = cursor.fetchall()
    if results:
        print(f"Slow queries detected: {results}")
EOF
```

### Monitor
- Query performance
- Connection pool usage
- Backup status
- Disk space

---

## Application Monitoring

### Check Django System

```bash
python manage.py check --deploy
```

Returns warnings about:
- Debug mode status
- Security settings
- Database configuration
- Email configuration

### Monitor
- Request/response times
- Error rates
- Cache hit rates
- Static file serving

---

## Custom Monitoring Dashboard

Create a monitoring page at `/admin/monitoring/`:

```python
# in invoices/views.py
def monitoring_dashboard(request):
    """Internal monitoring dashboard"""
    if not request.user.is_staff:
        return redirect('login')
    
    stats = {
        'total_invoices': Invoice.objects.count(),
        'total_revenue': Invoice.objects.aggregate(Sum('amount'))['amount__sum'],
        'paid_invoices': Invoice.objects.filter(status='paid').count(),
        'overdue': Invoice.objects.filter(
            status__in=['sent', 'viewed'],
            due_date__lt=timezone.now()
        ).count(),
        'email_errors': EmailDeliveryLog.objects.filter(
            status__in=['failed', 'bounced']
        ).count(),
        'active_users': User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }
    
    return render(request, 'admin/monitoring.html', stats)
```

---

## Alert Configuration

### Email Alerts

Create cron job to check health and send alerts:

```bash
# Run daily at 9 AM
0 9 * * * /path/to/check_health.py
```

### Slack Integration

1. Create Slack webhook
2. Add to environment: `SLACK_WEBHOOK_URL`
3. Send alerts to Slack:

```python
import requests

def send_slack_alert(message, severity='warning'):
    webhook = os.getenv('SLACK_WEBHOOK_URL')
    payload = {
        'text': f":{severity}: {message}",
        'channel': '#alerts'
    }
    requests.post(webhook, json=payload)
```

---

## Monitoring Schedule

### Daily (Automated)
- ✅ Health check every 5 minutes
- ✅ Email delivery status
- ✅ Payment reconciliation
- ✅ Error tracking

### Weekly (Manual)
- ✅ Review analytics
- ✅ Check slow queries
- ✅ Verify backups
- ✅ Security logs

### Monthly
- ✅ Performance review
- ✅ Cost analysis
- ✅ Capacity planning
- ✅ Update documentation

### Quarterly
- ✅ Security audit
- ✅ Performance optimization
- ✅ Dependency updates
- ✅ Disaster recovery test

---

## Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Response Time | > 2s | > 5s | Investigate bottleneck |
| Error Rate | > 0.5% | > 1% | Check logs |
| CPU Usage | > 70% | > 90% | Scale up resources |
| Memory Usage | > 70% | > 90% | Restart or scale |
| Email Bounce | > 1% | > 2% | Review templates |
| Payment Fail | > 1% | > 2% | Contact Paystack |
| Disk Space | > 80% | > 95% | Archive old data |
| Uptime | < 99.5% | < 99% | Investigate outage |

---

## Incident Response

### If System Down

1. **Check health endpoint:**
   ```bash
   curl https://yourdomain.com/health/
   ```

2. **Check logs:**
   - Application logs in Replit
   - Sentry for errors
   - Database logs

3. **Determine root cause:**
   - Database issue?
   - Out of memory?
   - Payment gateway down?
   - Email service down?

4. **Take action:**
   - Restart workflow
   - Scale resources
   - Contact service provider
   - Implement workaround

5. **Communicate:**
   - Notify users
   - Post status update
   - Provide ETA
   - Follow up

---

## Reporting

### Weekly Report Email

Send automated weekly report:

```python
from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_weekly_report():
    stats = {
        'invoices_created': Invoice.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'revenue': Invoice.objects.filter(
            status='paid',
            paid_at__gte=timezone.now() - timedelta(days=7)
        ).aggregate(Sum('amount'))['amount__sum'],
        'uptime': get_uptime(),
        'errors': get_error_count(),
    }
    
    html = render_to_string('reports/weekly.html', stats)
    send_mail(
        'Weekly Report',
        html,
        'noreply@yourdomain.com',
        ['admin@yourdomain.com'],
        html_message=html
    )
```

---

## Best Practices

1. **Monitor Early** - Start before going live
2. **Set Baselines** - Know your normal metrics
3. **Alert Wisely** - Only critical issues
4. **Document Issues** - Track problems & solutions
5. **Review Regularly** - Weekly analysis
6. **Test Alerts** - Verify alerts work
7. **Update Thresholds** - As you grow
8. **Keep Records** - Incident history

---

## Resources

- **Sentry:** https://sentry.io/
- **UptimeRobot:** https://uptimerobot.com/
- **Google Analytics:** https://analytics.google.com/
- **SendGrid Stats:** https://app.sendgrid.com/stats
- **Paystack Dashboard:** https://dashboard.paystack.co/

---

**Last Updated:** December 22, 2025
