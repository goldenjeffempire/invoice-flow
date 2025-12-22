# Incident Response & Disaster Recovery Plan

## Overview
This document outlines procedures for responding to critical incidents and recovering from disasters in InvoiceFlow production environment.

## 1. Incident Severity Levels

### Level 1 - Critical (All Users Affected)
- Application completely down
- Database unavailable
- Payment processing failures
- Data loss or corruption
- **Response Time: Immediate (< 5 minutes)**

### Level 2 - High (Significant Service Degradation)
- Core features unavailable (invoicing, payments)
- Performance degradation (>2 second response times)
- Authentication failures
- **Response Time: 15 minutes**

### Level 3 - Medium (Limited Impact)
- Non-critical features affected
- Minor performance issues
- Affects subset of users
- **Response Time: 1 hour**

### Level 4 - Low (Minimal Impact)
- UI/UX issues
- Minor bugs
- Cosmetic problems
- **Response Time: Next business day**

## 2. Incident Response Procedures

### Step 1: Assessment (First 5 Minutes)
1. Identify severity level
2. Check status page: https://status.invoiceflow.com
3. Review error logs in Replit Logs
4. Assess number of affected users
5. Notify incident commander

### Step 2: Immediate Actions (Level 1-2 Only)
```bash
# Check application status
curl https://invoiceflow.com/health/

# View recent error logs
tail -100 /tmp/logs/Django_Development_Server_*.log

# Check database connectivity
python manage.py shell
>>> from django.db import connection
>>> connection.ensure_connection()  # Will raise exception if down
```

### Step 3: Communication
1. **Update Status Page** - Indicate incident and ETA
2. **Notify Users** - Email significant service degradation
3. **Alert Team** - Use incident channel in chat
4. **Document Timeline** - Record all actions taken

### Step 4: Mitigation
- Deploy hotfix if code issue
- Restart services if frozen
- Scale resources if overloaded
- Activate failover systems
- Roll back recent deployments if necessary

### Step 5: Resolution
- Implement permanent fix
- Deploy to production
- Verify all systems operational
- Update status page

### Step 6: Post-Incident
- Conduct root cause analysis
- Document lessons learned
- Update runbooks
- Schedule preventive measures

## 3. Common Incidents & Solutions

### Incident: Database Down
```bash
# 1. Check database connection
python manage.py dbshell

# 2. If connection fails, restart Replit database
# Go to Replit > Database > Restart

# 3. Verify migrations are current
python manage.py migrate --plan

# 4. If corrupted, restore from backup
pg_restore -d invoiceflow backup.sql
```

### Incident: Application Memory Leak
```bash
# 1. Monitor memory usage
watch -n 1 'ps aux | grep python'

# 2. Restart application gracefully
# The workflow will auto-restart

# 3. Review recent code changes for leaks
git log --oneline -5

# 4. If persistent, roll back to stable version
git revert <commit-hash>
python manage.py runserver 0.0.0.0:5000
```

### Incident: High CPU Usage
```bash
# 1. Check running processes
ps aux | grep python | grep -v grep

# 2. Monitor with top
top -p $(pgrep -f "manage.py runserver")

# 3. Check for long-running queries
# Enable slow query log in settings.py
DATABASES = {
    'default': {
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'options': {'timeout': 20}
        }
    }
}

# 4. Optimize slow queries
python manage.py shell
>>> from django.db import connection
>>> connection.queries  # View all queries in request
```

### Incident: Email Delivery Failures
```bash
# 1. Verify SendGrid API key
echo $SENDGRID_API_KEY

# 2. Test email sending
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test message', 'test@invoiceflow.com', ['recipient@example.com'])

# 3. Check SendGrid dashboard for bounces/blocks
# Visit https://app.sendgrid.com/email_activity

# 4. Verify email templates are correct
# Check /templates/emails/ directory
```

### Incident: Payment Processing Issues
```bash
# 1. Check Paystack API status
# Visit https://status.paystack.com

# 2. Verify Paystack credentials
echo $PAYSTACK_SECRET_KEY

# 3. Test payment endpoint
python manage.py shell
>>> import requests
>>> response = requests.get('https://api.paystack.co/bank')

# 4. Check webhook logs
# Query webhook_log table for recent events
```

## 4. Disaster Recovery

### Recovery Scenarios

#### Scenario A: Data Loss/Corruption
**Recovery Time Objective (RTO): 2 hours**
**Recovery Point Objective (RPO): 15 minutes**

1. Identify last clean backup
2. Stop application to prevent further writes
3. Restore database from backup:
   ```bash
   pg_restore -d invoiceflow backup-2024-12-22.sql
   ```
4. Verify data integrity
5. Restart application
6. Notify affected users

#### Scenario B: Complete Application Failure
**RTO: 30 minutes**
**RPO: 5 minutes**

1. Verify database is accessible
2. Redeploy application:
   ```bash
   git pull origin main
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
3. Restart services
4. Run health checks
5. Verify critical functions

#### Scenario C: Extended Outage (> 4 hours)
1. Activate fallback website at fallback.invoiceflow.com
2. Direct traffic via DNS failover
3. Execute full system recovery in background
4. Monitor services hourly
5. Communicate status to users

### Backup & Recovery

#### Automated Backups
- **Frequency**: Daily at 2 AM UTC
- **Retention**: 30-day rolling window
- **Storage**: Replit managed backups + AWS S3
- **Testing**: Monthly restore drills

#### Manual Backup
```bash
pg_dump -h $PGHOST -U $PGUSER -d $PGDATABASE > backup-$(date +%Y%m%d).sql
# Upload to secure storage
```

#### Restore Procedure
```bash
# 1. Stop application
# 2. Restore database
psql -h $PGHOST -U $PGUSER -d invoiceflow < backup-2024-12-22.sql
# 3. Run migrations if needed
python manage.py migrate
# 4. Restart application
```

## 5. Escalation Matrix

| Severity | Owner | Escalate To | Threshold |
|----------|-------|-------------|-----------|
| Level 1 | On-call Engineer | CTO | Immediate |
| Level 2 | On-call Engineer | Tech Lead | 30 min unresolved |
| Level 3 | Support Lead | Engineering Manager | 2 hours unresolved |
| Level 4 | Support Team | Support Manager | Next day |

## 6. Communication Templates

### Initial Notification
```
Subject: [INCIDENT] InvoiceFlow Service Disruption

We're currently experiencing issues with [SERVICE]. We're investigating and will provide updates every 30 minutes.

Status: https://status.invoiceflow.com
```

### Recovery Update
```
Subject: [UPDATE] InvoiceFlow Incident Recovery in Progress

Our team is actively working on restoring [SERVICE]. We expect to have more information within [TIME].

Estimated Resolution: [TIME]
```

### Resolution Notification
```
Subject: [RESOLVED] InvoiceFlow Service Restored

[SERVICE] is now operational. We apologize for the disruption and will provide a full post-incident report.
```

## 7. Monitoring & Prevention

### Key Metrics to Monitor
- Application response time (target: < 500ms)
- Database query time (target: < 100ms)
- Error rate (target: < 0.1%)
- Payment success rate (target: > 99.5%)
- CPU usage (alert: > 80%)
- Memory usage (alert: > 85%)
- Disk space (alert: < 10% free)

### Preventive Measures
1. **Code Reviews**: All changes reviewed before merge
2. **Automated Testing**: 80%+ test coverage
3. **Staging Environment**: Test all changes before production
4. **Rate Limiting**: Protect against abuse
5. **Database Optimization**: Regular query analysis
6. **Security Updates**: Patch promptly
7. **Load Testing**: Quarterly capacity testing

## 8. Contact Information

| Role | Name | Phone | Email | Timezone |
|------|------|-------|-------|----------|
| Incident Commander | - | - | oncall@invoiceflow.com | UTC |
| CTO | - | - | cto@invoiceflow.com | UTC |
| Database Admin | - | - | dba@invoiceflow.com | UTC |
| Support Lead | - | - | support@invoiceflow.com | UTC |

## 9. Testing & Drills

### Monthly Testing Schedule
- **Week 1**: Database recovery drill
- **Week 2**: Application failover test
- **Week 3**: Email service verification
- **Week 4**: Payment system validation

### Annual Review
- Test complete disaster recovery
- Review and update this document
- Update contact information
- Verify backup integrity

## Revision History
| Date | Version | Changes |
|------|---------|---------|
| 2024-12-22 | 1.0 | Initial incident response plan |
