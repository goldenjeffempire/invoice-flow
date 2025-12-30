# Production Deployment Checklist

Complete checklist before deploying InvoiceFlow to production.

---

## Pre-Deployment (Phase 1)

### Environment & Security
- [ ] Change admin password from default
- [ ] Generate strong SECRET_KEY
- [ ] Generate ENCRYPTION_SALT
- [ ] Set SENDGRID_API_KEY
- [ ] Set PAYSTACK_SECRET_KEY and PUBLIC_KEY
- [ ] Set DEBUG=False in production
- [ ] Set PRODUCTION=true
- [ ] Configure ALLOWED_HOSTS with your domain

### Database
- [ ] Run `python manage.py migrate`
- [ ] Verify all 47 migrations applied
- [ ] Test database connection
- [ ] Set up automated backups
- [ ] Test backup restoration

### Static Files & Media
- [ ] Run `python manage.py collectstatic`
- [ ] Verify 260+ files collected
- [ ] Test static file serving
- [ ] Configure CDN (optional)
- [ ] Verify image optimization

### Testing
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify all 57 tests pass
- [ ] Test critical workflows:
  - [ ] User signup
  - [ ] Email verification
  - [ ] Invoice creation
  - [ ] Invoice sending
  - [ ] Payment initiation
  - [ ] MFA setup

---

## Pre-Deployment (Phase 2)

### Email Configuration
- [ ] SendGrid account created
- [ ] API key obtained and stored securely
- [ ] Email sender verified: `noreply@yourdomain.com`
- [ ] Test email sending: `python manage.py test_email`
- [ ] Configure email templates with branding
- [ ] Set up bounce handling
- [ ] Configure reply-to address

### Payment Gateway
- [ ] Paystack account created
- [ ] API keys obtained and stored securely
- [ ] Webhook endpoint registered: `/payments/webhook/`
- [ ] Test payment flow with test keys
- [ ] Configure settlement account
- [ ] Set up payment notifications

### Domain & SSL
- [ ] Purchase domain name
- [ ] Configure DNS records:
  - [ ] A record to your server IP
  - [ ] CNAME for www (optional)
  - [ ] MX records for email
- [ ] Install SSL certificate (auto with Replit)
- [ ] Verify HTTPS working
- [ ] Set SECURE_SSL_REDIRECT=True

### Monitoring & Logging
- [ ] Set up error monitoring (Sentry recommended)
- [ ] Configure log aggregation
- [ ] Set up performance monitoring
- [ ] Configure alerts for errors
- [ ] Set up uptime monitoring
- [ ] Configure backup monitoring

---

## Deployment (Phase 3)

### Click Publish in Replit
- [ ] Click "Publish" button
- [ ] Configure custom domain
- [ ] Wait for deployment to complete
- [ ] Verify site loads at new domain

### Post-Deployment Verification
- [ ] Homepage loads: `https://yourdomain.com/`
- [ ] Login page works: `/login/`
- [ ] Signup works: `/signup/`
- [ ] Health check passes: `/health/`
- [ ] Admin panel works: `/admin/`
- [ ] API documentation loads: `/api/schema/`

### Test Critical Flows

1. **User Registration**
   - [ ] Create new account
   - [ ] Receive verification email
   - [ ] Verify email successfully
   - [ ] Login with new account

2. **Invoice Creation**
   - [ ] Create invoice
   - [ ] Add line items
   - [ ] Verify calculations
   - [ ] Save as draft
   - [ ] Send to client

3. **Email Delivery**
   - [ ] Verify invoice email received
   - [ ] Check email formatting
   - [ ] Verify links work
   - [ ] Check bounce handling

4. **Payment Processing**
   - [ ] Initiate payment
   - [ ] Test Paystack payment flow
   - [ ] Verify payment confirmation
   - [ ] Check payment status updated

5. **Security**
   - [ ] Test MFA setup
   - [ ] Verify CSRF protection
   - [ ] Test rate limiting
   - [ ] Verify SSL/TLS working

---

## Post-Deployment (Phase 4)

### Monitor First 24 Hours
- [ ] Check error logs every hour
- [ ] Monitor email delivery rate
- [ ] Monitor payment processing
- [ ] Check system performance
- [ ] Monitor user signups

### First Week
- [ ] Monitor error trends
- [ ] Check API usage
- [ ] Review user feedback
- [ ] Verify backups completing
- [ ] Monitor database performance

### Ongoing
- [ ] Daily: Check health endpoint
- [ ] Daily: Review error logs
- [ ] Weekly: Review metrics
- [ ] Weekly: Test backup restoration
- [ ] Monthly: Security audit

---

## Rollback Plan

If issues occur:

1. **Immediate Actions**
   ```bash
   # Check logs
   tail -f /path/to/logs/production.log
   
   # Check health
   curl https://yourdomain.com/health/
   
   # Restart if needed
   # (Replit will auto-restart)
   ```

2. **Rollback Steps**
   - Return to previous checkpoint
   - Fix the issue
   - Re-deploy

3. **Communication**
   - Notify users of downtime
   - Post status updates
   - Provide ETA for fix

---

## Production Maintenance

### Daily Checks
```bash
# Health check
curl https://yourdomain.com/health/

# Check recent errors
tail -50 /path/to/application.log

# Monitor email delivery
python manage.py shell << 'EOF'
from invoices.models import EmailDeliveryLog
from datetime import timedelta
from django.utils import timezone

today = EmailDeliveryLog.objects.filter(
    created_at__date=timezone.now().date()
)
failed = today.filter(status='failed').count()
sent = today.filter(status='sent').count()

print(f"Emails sent today: {sent}")
print(f"Failed today: {failed}")
print(f"Bounce rate: {failed/sent*100:.1f}%" if sent > 0 else "No emails sent")
EOF
```

### Weekly Tasks
- [ ] Review performance metrics
- [ ] Check disk usage
- [ ] Verify database backups
- [ ] Review security logs
- [ ] Check for software updates

### Monthly Tasks
- [ ] Generate revenue report
- [ ] Review user metrics
- [ ] Test disaster recovery
- [ ] Security audit
- [ ] Update documentation

---

## Performance Targets

- **Page Load:** < 2 seconds
- **API Response:** < 500ms
- **Email Delivery:** 99% within 1 minute
- **Payment Success:** 98%+
- **Uptime:** 99.5%+
- **Error Rate:** < 0.1%

---

## Disaster Recovery

### Backup Restoration
1. Contact Replit support
2. Request backup restoration
3. Verify database integrity
4. Test all critical functions
5. Inform users if needed

### Data Loss Prevention
- [ ] Daily automated backups (Replit)
- [ ] Weekly manual backups (export)
- [ ] Monthly long-term archives
- [ ] Test restoration quarterly

### Incident Response
1. Assess severity
2. Notify stakeholders
3. Implement fix
4. Monitor closely
5. Post-incident review

---

## Security Hardening

### Before Going Live
- [ ] Update all dependencies
- [ ] Run security audit
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable monitoring

### Ongoing Security
- [ ] Weekly: Review security logs
- [ ] Monthly: Check for vulnerabilities
- [ ] Quarterly: Security audit
- [ ] Annually: Penetration testing

---

## Success Criteria

Deployment is successful when:

✅ All pages load without errors
✅ User signup/login works
✅ Emails are delivered successfully
✅ Payments process correctly
✅ Health checks pass
✅ No error rate spikes
✅ Performance targets met
✅ SSL certificate valid
✅ All backups verified
✅ Monitoring alerts active

---

## Support Contacts

- **Replit Support:** replit.com/support
- **SendGrid Support:** sendgrid.com/support
- **Paystack Support:** paystack.com/support
- **Your Domain Registrar:** [Your registrar name]

---

## Documentation References

- PRODUCTION_READY.md - Overall production status
- CUSTOMIZATION_GUIDE.md - Branding customization
- ADMIN_GUIDE.md - Admin operations
- docs/DEPLOYMENT.md - Detailed deployment guide
- docs/PAYSTACK_SETUP.md - Payment setup

---

**Last Updated:** December 22, 2025
**Status:** ✅ Ready for Production
