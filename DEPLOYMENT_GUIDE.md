# InvoiceFlow - Render Deployment Guide

Complete instructions for deploying InvoiceFlow to Render.com with production-grade Gunicorn configuration.

## Prerequisites

- GitHub repository with InvoiceFlow codebase
- Render.com account (free or paid)
- SendGrid account for email delivery
- Custom domain (invoiceflow.com.ng) or use Render subdomain

## Deployment Steps

### 1. Configure Environment Variables in Render Dashboard

1. Go to **Render Dashboard** > Select your service > **Environment**
2. Set the following secrets (do NOT set in .env.render):

```
SECRET_KEY: django-insecure-xxx...  (generate via Django shell)
ENCRYPTION_SALT: xxx...              (generate via secrets.token_hex(16))
SENDGRID_API_KEY: SG.xxx...          (from SendGrid account)
HCAPTCHA_SITEKEY: xxx...             (optional, from hCaptcha)
HCAPTCHA_SECRET: xxx...              (optional, from hCaptcha)
```

#### Generating Secrets

```bash
# Generate SECRET_KEY
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate ENCRYPTION_SALT
python -c "import secrets; print(secrets.token_hex(16))"
```

### 2. Connect Repository to Render

1. Go to **Render Dashboard** > **New +** > **Web Service**
2. Connect your GitHub repository
3. Set **Build Command**: `bash build.sh`
4. Set **Start Command**: `gunicorn invoiceflow.wsgi:application -c gunicorn.conf.py`
5. Select **Python 3.13** runtime
6. Select **Standard** plan or higher

### 3. Configure Database

1. Render automatically creates PostgreSQL 15 database from `render.yaml`
2. Database credentials are automatically set as `DATABASE_URL`
3. No manual configuration needed

### 4. Deploy

1. Push to `main` branch
2. Render automatically triggers build
3. Watch build logs in **Render Dashboard** > **Logs**
4. Monitor health checks: `/api/health/` endpoint

### 5. Configure Custom Domain (Optional)

1. Go to **Render Dashboard** > **Settings** > **Custom Domain**
2. Add `invoiceflow.com.ng` and `www.invoiceflow.com.ng`
3. Update DNS records at DomainKing:
   - Type: CNAME
   - Name: @ (root)
   - Value: your-render-deployment.onrender.com

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Render Infrastructure              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  HTTPS Termination (Render Proxy)                   │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │  Gunicorn WSGI Server (Port 5000)      │        │
│  │  - 2-7 workers (auto-scaled)           │        │
│  │  - 4 threads per worker                │        │
│  │  - 120s timeout per request            │        │
│  │  - Memory leak prevention              │        │
│  └─────────────────────────────────────────┘        │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │  Django Application (Python 3.13)      │        │
│  │  - Static files (WhiteNoise)           │        │
│  │  - Template rendering                 │        │
│  │  - ORM queries                         │        │
│  └─────────────────────────────────────────┘        │
│         ↓                                            │
│  ┌─────────────────────────────────────────┐        │
│  │  PostgreSQL 15 (Render-managed)        │        │
│  │  - Connection pooling                  │        │
│  │  - Daily automatic backups             │        │
│  │  - High availability                   │        │
│  └─────────────────────────────────────────┘        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Production Build Pipeline

The `build.sh` script automates pre-deployment preparation:

1. **Upgrade pip** - Latest package manager
2. **Install Python dependencies** - From requirements.txt
3. **Install Node.js dependencies** - If package.json exists
4. **Build assets** - CSS/JS minification (npm run build:prod)
5. **Database migrations** - Apply pending migrations
6. **Create cache table** - For Django caching
7. **Collect static files** - Via WhiteNoise for production serving
8. **Django checks** - Verify deployment settings

## Gunicorn Configuration

**File**: `gunicorn.conf.py`

### Worker Scaling
- **Standard plan (1 CPU)**: 2-3 workers
- **Pro plan (2-4 CPUs)**: 3-7 workers
- **Auto-scaling**: Based on CPU cores detected

### Memory Management
- **Worker restart**: Every 1,000 requests
- **Prevents memory leaks** from long-running processes
- **Graceful restart**: No request loss

### Request Handling
- **Timeout**: 120 seconds per request
- **Keepalive**: 5 seconds
- **Graceful shutdown**: 30-second window
- **Thread pool**: 4 threads per gthread worker

### Logging
- **Access logs**: Stdout (Render captures)
- **Error logs**: Stderr (Render captures)
- **Format**: Professional with response time
- **Level**: INFO (production) or DEBUG (development)

## Security Configuration

### HTTPS & Certificates
- **Render handles HTTPS** at proxy level
- **No SSL termination** in Gunicorn needed
- **Automatic certificate renewal** via Let's Encrypt

### Secure Headers
- **SECURE_SSL_REDIRECT**: Enabled in production
- **SECURE_PROXY_SSL_HEADER**: None (Gunicorn handles detection)
- **SESSION_COOKIE_SECURE**: Enabled in production
- **CSRF_COOKIE_SECURE**: Enabled in production
- **HSTS preload**: 1 year (31536000 seconds)

### Security Middleware
- 12 middleware layers active
- Content Security Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer Policy: strict-origin-when-cross-origin

## Health Checks

**Endpoint**: `GET /api/health/`

- **Frequency**: Every 30 seconds
- **Timeout**: 5 minutes for cold start
- **On failure**: Automatic restart
- **Response**: JSON with application status

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "cache": "available"
}
```

## Monitoring & Logs

### Access Logs
Available in **Render Dashboard** > **Logs**

Format: IP, method, path, status, response_time, worker_id

Example:
```
127.0.0.1 - - [30/Dec/2025 00:23:06] "GET /api/health/ HTTP/1.1" 200 145 response_time=45234_us worker_id=237
```

### Error Logs
Any application errors appear in **Render Dashboard** > **Logs**

- Django errors with full traceback
- Gunicorn worker issues
- Database connection errors

### Metrics
Render Dashboard provides:
- CPU usage
- Memory usage
- Request count
- Error rate
- Response times

## Troubleshooting

### Build Fails

Check **Render Dashboard** > **Logs** > **Build**

Common issues:
- Missing `SECRET_KEY` or `ENCRYPTION_SALT`
- Database migration errors
- Static file collection failures

Solution: Check build.sh output, review Django errors

### Application Won't Start

Check **Render Dashboard** > **Logs** > **Runtime**

Common issues:
- `GUNICORN_WORKERS` misconfiguration
- Memory constraints (OOM)
- Worker timeout during startup

Solution: Increase plan (Standard → Pro), check logs

### Health Check Fails

Endpoint: `GET /api/health/`

Common issues:
- Database not accessible
- Cache table not created
- Application initialization error

Solution: Check database connection, verify migrations ran

### Static Files 404

Issue: CSS/JS not loading

Solution:
1. Verify `build.sh` ran successfully
2. Check `STATIC_URL = "/static/"`
3. Ensure WhiteNoise middleware is active

### Email Not Sending

Issue: `SENDGRID_API_KEY` not set or invalid

Solution:
1. Verify `SENDGRID_API_KEY` in Render Dashboard
2. Test with `python manage.py shell`
3. Check SendGrid account status

## Zero-Downtime Deployment

Render automatically handles graceful deployments:

1. New build completes
2. New container starts with `/api/health/` checks passing
3. Load balancer switches traffic to new container
4. Old container receives SIGTERM (graceful shutdown)
5. Gunicorn waits 30 seconds for in-flight requests
6. Old container terminates
7. Zero requests lost

## Performance Tuning

### Database Connection Pooling
- Enabled automatically via psycopg2
- Max connections: 600 seconds age limit
- Prevents "too many connections" errors

### Static File Caching
- WhiteNoise sets 1-year cache headers
- Browser caches CSS/JS/images
- Reduces server load

### Request Optimization
- Django ORM select_related/prefetch_related
- Redis caching for expensive queries
- Gzip compression enabled

## Scaling

### Manual Scaling
Upgrade Render plan in **Dashboard** > **Settings** > **Plan**:
- Standard → Pro (double CPU/RAM)
- Pro → Standard+ (more CPU cores)

### Auto-Scaling
Render Standard plan auto-upgrades if:
- CPU utilization > 80% for 5 minutes
- Memory utilization > 90% for 5 minutes

### Load Balancing
Render automatically distributes requests across:
- Multiple instances (if scaled)
- Gunicorn worker threads
- Database connection pool

## Backup & Recovery

### Database Backups
- Render takes daily backups automatically
- Retention: 14 days (default)
- Point-in-time recovery available

### Manual Backup
```bash
pg_dump $DATABASE_URL > invoiceflow_backup.sql
```

### Recovery
Contact Render support to restore from backup

## Custom Domain Setup

### DNS Configuration (DomainKing)

Add CNAME records:
```
Name: @
Type: CNAME
Value: your-deployment.onrender.com
TTL: 3600
```

Or for subdomain:
```
Name: www
Type: CNAME
Value: your-deployment.onrender.com
TTL: 3600
```

### SSL/TLS Certificate
- Render auto-provisions via Let's Encrypt
- Automatic renewal 30 days before expiry
- No manual action needed

## Environment Variables Reference

### Required
- `PRODUCTION=true` - Enable production mode
- `SECRET_KEY` - Django secret key
- `ENCRYPTION_SALT` - Field encryption salt
- `SENDGRID_API_KEY` - Email service API key

### Optional
- `HCAPTCHA_SITEKEY` - Form protection
- `HCAPTCHA_SECRET` - Form protection
- `DEBUG=false` - Disable debug mode
- `WEB_CONCURRENCY` - Override worker count

### Auto-Set by Render
- `DATABASE_URL` - PostgreSQL connection string
- `PORT` - Server port (default: 5000)
- `RENDER` - Environment detection flag
- `DYNO` - Instance identifier

## Support & Further Help

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com/en/5.2
- **Gunicorn Docs**: https://docs.gunicorn.org
- **This Project**: https://invoiceflow.com.ng

## Deployment Checklist

- [ ] GitHub repository set up
- [ ] Render account created
- [ ] Environment variables configured in Render
- [ ] SendGrid account ready with API key
- [ ] Custom domain registered (optional)
- [ ] DNS records configured (if using custom domain)
- [ ] Build tested locally
- [ ] First deployment initiated
- [ ] Health checks passing
- [ ] Application responding correctly
- [ ] Static files loading
- [ ] Email sending working
- [ ] Monitoring logs accessible
- [ ] Database backups configured
- [ ] SSL/TLS certificate issued

## Post-Deployment

1. **Monitor logs** for first 24 hours
2. **Test all features** with real data
3. **Set up alerts** for errors/downtime
4. **Configure email** forwarding if needed
5. **Test payment** processing (if applicable)
6. **Announce** service launch

---

**Last Updated**: December 30, 2025
**InvoiceFlow Version**: 1.0.0
**Deployment Platform**: Render.com
