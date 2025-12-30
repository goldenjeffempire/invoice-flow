# InvoiceFlow - Render Deployment Guide

## Overview
InvoiceFlow is now fully configured for production deployment on Render with zero-downtime deployments, automatic scaling, and comprehensive monitoring.

## Deployment Configuration Files

### 1. **gunicorn.conf.py** (WSGI Server)
- **Purpose**: Configures the Gunicorn application server
- **Features**:
  - Dynamic worker scaling (2-7 workers based on CPU)
  - Memory leak prevention (worker restart after 1000 requests)
  - 120s request timeout (prevents hanging requests)
  - 30s graceful shutdown (in-flight request completion)
  - Comprehensive logging and monitoring
  - Production-grade security settings

### 2. **render.yaml** (Render Deployment)
- **Purpose**: Defines Render service infrastructure
- **Includes**:
  - Web service configuration (Python 3.13)
  - PostgreSQL database (Render-managed)
  - Environment variables
  - Health checks every 30 seconds
  - Zero-downtime deployment settings
  - Auto-deploy on git push to main

### 3. **build.sh** (Build Process)
- **Purpose**: Pre-deployment preparation
- **Steps**:
  1. Upgrade pip/setuptools
  2. Install Python dependencies
  3. Install & build Node.js assets (if needed)
  4. Run database migrations
  5. Create cache tables
  6. Collect static files
  7. Run deployment checks

### 4. **Procfile** (Process Definition)
- **Purpose**: Defines how to start the web server
- **Command**: `gunicorn invoiceflow.wsgi:application -c gunicorn.conf.py`

## Deployment Steps

### Step 1: Prepare Render Project
1. Login to render.com
2. Create new service from this repository
3. Connect your Git repository

### Step 2: Set Environment Variables in Render Dashboard
Go to **Settings > Environment** and set:

**Required Secrets:**
- `SECRET_KEY` - Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `ENCRYPTION_SALT` - Generate with: `python -c "import secrets; print(secrets.token_hex(16))"`
- `SENDGRID_API_KEY` - Your SendGrid API key
- `HCAPTCHA_SITEKEY` - Your hCaptcha public key
- `HCAPTCHA_SECRET` - Your hCaptcha secret key

**Public Variables:**
- `PRODUCTION=true` - Enables production mode
- `DEBUG=false` - Disables debug mode
- `ALLOWED_HOSTS` - Already configured in render.yaml

### Step 3: Deploy
1. Push code to main branch
2. Render automatically starts build (via build.sh)
3. Database migrations run automatically
4. Static files collected automatically
5. Gunicorn server starts
6. Health checks begin (every 30 seconds)

### Step 4: Verify Deployment
1. Check Render Dashboard > Logs for startup messages
2. Verify service is "Live"
3. Test health endpoint: `https://invoiceflow.onrender.com/api/health/`
4. Monitor logs for errors

## Key Features

### Zero-Downtime Deployments
- Old process gracefully shuts down (30-second window)
- New process starts in parallel
- Requests automatically routed to new process
- No downtime for users

### Automatic Monitoring
- Health checks every 30 seconds
- Failed checks trigger automatic restart
- Logs streamed to Render Dashboard
- Email alerts for failures (configurable)

### Resource Management
- Conservative worker scaling (prevents OOM)
- Worker restart cycles (memory leak prevention)
- Connection pooling
- Request timeouts

### Security
- Environment variables encrypted
- No secrets in code
- HTTPS enforced
- HSTS headers
- CSRF protection
- XSS protection

## Performance Optimization

### Static Files
- Collected via WhiteNoise middleware
- Cached for 1 year (immutable)
- Compressed automatically

### Database
- Connection pooling (600s max age)
- Health checks enabled
- Automatic backups (daily)

### Caching
- Database cache table for sessions
- Optimized for production

## Troubleshooting

### Build Fails
1. Check build.sh output in Render logs
2. Verify environment variables are set
3. Check requirements.txt for version conflicts
4. Ensure database connection string is correct

### Application Crashes
1. Check logs in Render Dashboard
2. Verify SECRET_KEY and ENCRYPTION_SALT are set
3. Check database connectivity
4. Review Django system checks: `python manage.py check --deploy`

### Slow Performance
1. Check worker count in gunicorn.conf.py
2. Monitor request timeouts in logs
3. Review database query performance
4. Check memory usage in Render Dashboard

## Production Monitoring

### Key Metrics to Monitor
- Request response time (target: <500ms)
- Worker count and utilization
- Database connection pool usage
- Memory consumption per worker
- HTTP status code distribution

### Logging
- Access logs: `[response_time] [worker_id]` in stdout
- Error logs: Full traceback in stderr
- Application logs: Structured JSON format

## Scaling

### Horizontal Scaling
- Upgrade Render plan for more CPU/RAM
- Additional workers spawn automatically
- No code changes needed

### Database Scaling
- Upgrade PostgreSQL plan in Render
- Automatic replication available
- Backups retained for 14 days

## Security Checklist
- [ ] SECRET_KEY set in environment
- [ ] ENCRYPTION_SALT set in environment
- [ ] DEBUG=false in production
- [ ] HTTPS enforced via Django
- [ ] CSRF tokens enabled
- [ ] SendGrid API key secured
- [ ] hCaptcha keys if used
- [ ] Regular security updates

## Maintenance

### Regular Tasks
- Monitor logs daily
- Review performance metrics
- Update dependencies monthly
- Test disaster recovery quarterly

### Database Maintenance
- Monitor backup status
- Test backup restoration
- Vacuum and analyze (automatic on Render)
- Monitor connection pool usage

## Support & Monitoring
- Render Dashboard: https://dashboard.render.com
- Logs: Via Render Dashboard > Logs
- Metrics: Via Render Dashboard > Metrics
- Alerts: Configurable in Render Dashboard

---

**Deployment Version**: 1.0.0
**Last Updated**: December 27, 2025
**Django Version**: 5.2.9
**Python Version**: 3.13
**Platform**: Render
