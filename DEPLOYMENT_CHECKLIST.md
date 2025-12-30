# InvoiceFlow Production Deployment Checklist

This checklist ensures safe, reliable deployments to Render (or similar production environments).

## Pre-Deployment: Code & Configuration

- [ ] **Migrations Applied**: Run `python manage.py migrate` before deployment
  - Ensure no pending migrations: `python manage.py showmigrations`
- [ ] **Static Files Collected**: Run `python manage.py collectstatic --noinput`
  - Verify all assets in `staticfiles/` directory
- [ ] **Tests Pass**: Run full test suite (if applicable)
  - `pytest` or `python manage.py test`
- [ ] **LSP/Lint Clean**: No type checking errors
  - All critical code reviewed for security issues
- [ ] **Secret Rotation**: 
  - [ ] `SECRET_KEY` is production-grade (use `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
  - [ ] `ENCRYPTION_SALT` is set and NOT "dev-salt"
  - [ ] Database credentials are secure (use managed services like Neon)

## Environment Variables (Render Secrets)

**Required for Production (`PRODUCTION=true`):**
- [ ] `SECRET_KEY` - Strong, random string (48+ chars)
- [ ] `DATABASE_URL` - PostgreSQL connection string (use Neon if on Render)
- [ ] `EMAIL_HOST_USER` - SendGrid API key or similar
- [ ] `EMAIL_HOST_PASSWORD` - Email service password
- [ ] `ENCRYPTION_SALT` - Unique salt (48+ chars)

**Optional but Recommended:**
- [ ] `HCAPTCHA_SITEKEY` - hCaptcha site key (for form protection)
- [ ] `HCAPTCHA_SECRET` - hCaptcha secret key
- [ ] `GUNICORN_MAX_REQUESTS` - Set to 0 only after memory profiling (default: 1000)
- [ ] `WEB_CONCURRENCY` - Override worker count (default: calculated from CPU cores)

**Always Set in Render:**
- [ ] `PRODUCTION=true` - Enables strict validation and security headers
- [ ] `RENDER=true` - Automatically set by Render platform

## Deployment Steps (Render)

1. **Create or Update Service**
   - [ ] Build Command: `python manage.py migrate && python manage.py collectstatic --noinput && gunicorn invoiceflow.wsgi -c gunicorn.conf.py`
   - [ ] Start Command: (same as build, or use Procfile)
   - [ ] Plan: Pro or higher (Standard can run but has memory constraints)

2. **Configure Render Settings**
   - [ ] Region: Closest to your users (or us-east for global default)
   - [ ] Auto-deploy: Enable if desired
   - [ ] Healthcheck Path: `/health/ready/` (includes DB, cache, migrations)
   - [ ] Healthcheck Start Period: 30 seconds (allow startup time)

3. **Set Environment Variables** in Render Dashboard
   - Copy all required vars to Render's "Environment" section
   - Use Render's native secret management (not .env files)

4. **Deploy**
   - [ ] Trigger deployment via Render dashboard or `git push`
   - [ ] Monitor build logs for errors
   - [ ] Wait for health checks to pass (should see "Your service is live 🎉")

## Post-Deployment Verification

### Immediate (First 5 minutes)
- [ ] **Service Status**: Check Render dashboard - should show "Running" (green)
- [ ] **Health Endpoint**: Test `https://invoiceflow.com.ng/health/ready/`
  - Should return `{"status": "ready", "checks": {"database": true, ...}}`
- [ ] **Homepage Loads**: Visit `https://invoiceflow.com.ng/`
  - Should render without errors (CSS, JS should load)
- [ ] **Check Logs**: Render dashboard "Logs" tab
  - Look for startup messages
  - Ensure no ERROR or CRITICAL messages
  - Expected: `✓ Gunicorn READY at...` message

### First Hour
- [ ] **Database Connectivity**: 
  - Admin panel should load: `/admin/`
  - Test user login works
- [ ] **Cache System**: Verify cache warming occurred
  - Check logs for cache version bump
- [ ] **HTTPS Redirect**: 
  - Visiting http://invoiceflow.com.ng should redirect to https://
  - All security headers should be present
- [ ] **Email Integration**: 
  - Test sending an email (if available in your app)
  - Check SendGrid logs for successful deliveries
- [ ] **No Warnings in Logs**:
  - No "Contradictory scheme headers" warnings
  - No duplicate "Environment validation" messages
  - No ".env not found" messages

### Daily (First Week)
- [ ] **Monitor Resource Usage**: 
  - Memory usage should stabilize after initial requests
  - Check Render metrics dashboard
  - If memory keeps growing = possible leak (enable profiling)
- [ ] **Check Uptime**: 
  - No unexpected restarts
  - If workers restarting frequently = memory leak or config issue
- [ ] **Review Error Logs**: 
  - Filter for ERROR level messages
  - Check for database connection issues
  - Look for timeout errors (>120s requests)
- [ ] **Test Key Features**: 
  - Create an invoice
  - Export data
  - Send payment links
  - Verify email delivery

## Rollback Procedure

If deployment has critical issues:

1. **Identify the Problem**
   - Check Render logs for error messages
   - Verify health check endpoint: `/health/detailed/`
   - Check database status

2. **Quick Rollback**
   - Render > Service > "Redeploy" previous build
   - Or: Push previous git commit and trigger redeploy
   - Verify health checks pass before resuming traffic

3. **Root Cause Analysis**
   - Review logs from failed deployment
   - Check environment variables were set correctly
   - Verify migrations applied successfully
   - Run locally: `PRODUCTION=true python manage.py check --deploy`

## Performance Optimization

### After Initial Deployment
- [ ] **Memory Profiling**: If workers restart >1x/day
  - Set `GUNICORN_MAX_REQUESTS=0` temporarily
  - Monitor memory growth over 24 hours
  - Use `/health/detailed/` to check memory metrics
  - Profile with py-spy (see PROFILING_GUIDE.md)

- [ ] **Database Optimization**: Monitor query performance
  - Enable slow query logging (PostgreSQL)
  - Check connection pool usage (max 20 by default)
  - Review `/health/detailed/` for database latency

- [ ] **Cache Warming**: Verify it completes within 5 seconds
  - Should see "Cache version bumped" in logs
  - Check `/health/detailed/` cache stats

### Ongoing (Monthly)
- [ ] Review Render analytics for error rates
- [ ] Check SSL certificate expiration (Render handles auto-renewal)
- [ ] Monitor database size and growth
- [ ] Review access logs for unusual traffic patterns

## Security Checklist

- [ ] **HTTPS Only**: All traffic redirected to HTTPS
  - Check: `SECURE_SSL_REDIRECT = True` in settings
  - Verify: No HTTP access to sensitive endpoints
- [ ] **Security Headers**: 
  - HSTS enabled (31536000 seconds = 1 year)
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - CSP headers configured
- [ ] **Session Security**:
  - `SESSION_COOKIE_SECURE = True`
  - `SESSION_COOKIE_HTTPONLY = True`
  - `SESSION_COOKIE_SAMESITE = "Strict"`
- [ ] **CSRF Protection**:
  - `CSRF_COOKIE_SECURE = True`
  - `CSRF_COOKIE_HTTPONLY = True`
  - Verify CSRF tokens in forms
- [ ] **Admin Access**: Restrict `/admin/` to your IP or VPN
  - Ideally behind organization login
- [ ] **Secrets Never Logged**: 
  - No API keys, passwords, tokens in application logs
  - Use Render's secret management exclusively

## Troubleshooting Common Issues

### "Health check failed" on Render
**Solution**: 
- Increase health check timeout to 30 seconds in Render settings
- Verify database is available
- Check `/health/ready/` endpoint returns 200
- Ensure migrations completed successfully

### "Contradictory scheme headers" in logs
**Solution**: 
- Already fixed in this version (Gunicorn config simplified)
- If still occurring: Check Render proxy configuration

### Application crashes on startup
**Solution**: 
- Check logs for specific error
- Verify SECRET_KEY and ENCRYPTION_SALT are set
- Ensure all migrations applied
- Run locally with `PRODUCTION=true` to reproduce

### Memory keeps growing (workers restart often)
**Solution**: 
- Profile application (see PROFILING_GUIDE.md)
- Check for circular references or cached data not cleared
- Review background tasks
- Increase worker restart cycle: `GUNICORN_MAX_REQUESTS=5000`

### Database connection errors
**Solution**: 
- Verify DATABASE_URL is correct
- Ensure PostgreSQL database exists and is accessible
- Check connection pool exhaustion: `/health/detailed/`
- Verify CONN_MAX_AGE setting (default: 600 seconds)

## Quick Reference: Important Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/health/` | Basic health check | Load balancer (may have redirects) |
| `/health/ready/` | Readiness check | Orchestration (no redirects, includes DB/cache/migrations) |
| `/health/live/` | Liveness check | Orchestration (quick, no external deps) |
| `/health/detailed/` | Extended metrics | Debugging, monitoring dashboards |
| `/admin/` | Django admin | Admin access, user management |

## Support & Documentation

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com
- **Gunicorn Docs**: https://docs.gunicorn.org
- **PostgreSQL Docs**: https://www.postgresql.org/docs
- **InvoiceFlow Guides**: 
  - PROFILING_GUIDE.md - Memory profiling and performance optimization
  - README.md - Project overview and features
