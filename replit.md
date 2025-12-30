# InvoiceFlow - Production-Ready Deployment Platform

## Overview
InvoiceFlow is a sophisticated Django 5.2.9 SaaS invoicing platform, now comprehensively production-hardened and fully configured for Render deployment. The platform offers secure payment processing, robust API validation, optimized database performance, and enhanced security features. Purpose: reliable, scalable, secure invoicing solution for thousands of users.

## Current Status: FULLY CONFIGURED FOR RENDER DEPLOYMENT ✓

### Deployment Infrastructure (Render-Ready)
- **gunicorn.conf.py**: Enterprise-grade WSGI server (dynamic workers, memory leak prevention, graceful shutdown)
- **render.yaml**: Complete Render service definition with PostgreSQL database
- **build.sh**: Production build pipeline (pip, Node, migrations, static files, checks)
- **Procfile**: Process definition for Render
- **DEPLOYMENT_GUIDE.md**: Complete deployment instructions
- **.env.render**: Environment template for secrets management

## User Preferences
I prefer detailed explanations and iterative development. Ask before making major changes. I value clear, concise communication and prefer if the agent focuses on high-level feature implementation rather than granular code details unless specifically asked.

## System Architecture

### Deployment Stack (Render)
1. **Web Service**: Python 3.13 on Render Standard plan
2. **WSGI Server**: Gunicorn with gthread workers (2-7 workers based on CPU)
3. **Database**: PostgreSQL 15 (Render-managed, daily backups)
4. **Static Files**: WhiteNoise middleware (cached for 1 year)
5. **Caching**: Django database cache table
6. **Health Checks**: Every 30 seconds via `/api/health/` endpoint
7. **Monitoring**: Logs captured automatically via stdout/stderr

### Gunicorn Configuration Features
- **Dynamic Worker Scaling**: 2-7 workers based on CPU cores (prevents OOM)
- **Memory Management**: Worker restart after 1000 requests (prevents leaks)
- **Request Timeout**: 120 seconds (prevents hanging requests)
- **Graceful Shutdown**: 30-second window for in-flight request completion
- **TCP Keepalive**: 5-second health checks for dead connections
- **Request Limits**: DoS protection via size/count limits
- **Production Logging**: Structured logs with response timing
- **Signal Handling**: SIGINT (graceful), SIGQUIT (immediate)
- **Preload App**: Application loaded before worker fork (faster restarts)
- **Zero-Downtime**: Full support for seamless deployments

### Build Pipeline (build.sh)
1. Upgrade pip/setuptools/wheel
2. Install Python dependencies
3. Install Node.js dependencies (if package.json exists)
4. Build production assets (CSS/JS minification)
5. Run database migrations (with 5-minute timeout)
6. Create cache tables
7. Collect static files via WhiteNoise
8. Run Django deployment checks

### Render Configuration (render.yaml)
- **Service**: Web application auto-deploy on git push
- **Runtime**: Python 3.13
- **Build Command**: `bash build.sh`
- **Start Command**: `gunicorn invoiceflow.wsgi:application -c gunicorn.conf.py`
- **Health Check**: Every 30 seconds, 5-minute startup timeout
- **Database**: PostgreSQL 15 with automatic backups
- **Environment Variables**: Secret variables via Render Dashboard
- **Region**: Ohio (US)
- **Plan**: Standard (auto-upgrade on performance needs)

### UI/UX Decisions
Fast, responsive user experience with secure payment processing. Multi-currency support and real-time payment status tracking are key features.

### Technical Implementations
- **API Validation**: Strict serializer validation, Decimal types for financial accuracy, cross-field constraints
- **Payment Security**: Idempotent payment handling with `IdempotencyKey`, webhook deduplication via `ProcessedWebhook`, HMAC verification
- **Database Optimization**: Strategic indexing, PostgreSQL backend, connection pooling (600s max age)
- **Security Headers**: SECURE_CROSS_ORIGIN_OPENER_POLICY, SECURE_CROSS_ORIGIN_EMBEDDER_POLICY
- **Server Configuration**: Gunicorn with TCP keepalives, connection pooling, graceful shutdown
- **Security Posture**: 12 middleware layers, CSP, HSTS preload, rate limiting, field encryption
- **Production Logging**: Structured JSON format with request IDs
- **Performance**: Static file caching, database query optimization, connection pooling

### Feature Specifications
- Comprehensive API documentation
- Health check endpoints (`/api/health/`)
- Structured JSON logging
- Multi-currency support
- Recurring invoice automation
- Admin interface with superuser capability
- hCaptcha form protection
- SendGrid email integration
- Role-based access control

### System Design Choices
Architecture prioritizes security-by-default with idempotent payment processing and webhook deduplication. Performance optimized through database indexing and efficient server configs. Designed for scalability and maintainability with clear separation of concerns.

## External Dependencies

- **Database**: PostgreSQL 15 (Neon on Render)
- **Payment Gateway**: Paystack
- **Email Service**: SendGrid
- **Deployment Platform**: Render
- **Domain Registrar**: DomainKing (custom domain configuration)
- **Static Files**: WhiteNoise (included in requirements.txt)
- **Form Protection**: hCaptcha (optional)

## Deployment Instructions

### Quick Start on Render
1. Connect repository to Render dashboard
2. Set environment variables in Render Dashboard:
   - `SECRET_KEY` (generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `ENCRYPTION_SALT` (generate: `python -c "import secrets; print(secrets.token_hex(16))"`)
   - `SENDGRID_API_KEY`
   - `HCAPTCHA_SITEKEY` (optional)
   - `HCAPTCHA_SECRET` (optional)
3. Push to main branch - automatic deployment starts
4. Monitor build logs in Render Dashboard
5. Access application at `https://invoiceflow.onrender.com`

### Key Deployment Settings
- **PRODUCTION=true**: Enables production security settings (already set in render.yaml)
- **DEBUG=false**: Disables debug mode (already set in render.yaml)
- **ALLOWED_HOSTS**: Configured for invoiceflow.com.ng and Render subdomains
- **SECURE_SSL_REDIRECT**: Enabled in production
- **SECURE_HSTS_SECONDS**: 31536000 (1 year) in production

## Monitoring & Operations

### Health Checks
- Endpoint: `GET /api/health/`
- Frequency: Every 30 seconds
- Timeout: 5 minutes for cold start
- Automatic restart on failure

### Logging
- **Access Logs**: stdout (response time, worker ID)
- **Error Logs**: stderr (full traceback)
- **Application Logs**: Structured format (INFO/WARNING/ERROR)
- **Captured by**: Render dashboard automatically

### Key Metrics to Monitor
- Request response time (target <500ms)
- Worker count and utilization
- Database connection pool usage
- Memory per worker
- HTTP status distribution

## Production Checklist
✓ Django settings hardened for production
✓ Gunicorn configured with optimal workers
✓ Database configured with connection pooling
✓ Static files optimized via WhiteNoise
✓ Security headers enabled
✓ HTTPS enforced
✓ Request timeouts configured
✓ Graceful shutdown enabled
✓ Health checks configured
✓ Logging structured and comprehensive
✓ Zero-downtime deployment ready
✓ Build pipeline automated
✓ Environment variables managed securely

## Recent Changes (December 28-30, 2025)

### Production-Grade Gunicorn Configuration (COMPLETE)
- **Complete Gunicorn Configuration**: Enterprise-grade gunicorn.conf.py with:
  - Dynamic worker scaling (2-7 workers based on CPU cores)
  - Memory leak prevention (1000-request restart cycles)
  - 120-second request timeout protection
  - 30-second graceful shutdown window
  - TCP keepalive health checks (5s interval)
  - DoS protection via request size limits
  - Structured logging to stdout/stderr
  - Render-optimized thread pool (4 threads per worker)
  - Connection pooling and forwarded header handling

### Logging & Proxy Header Fixes (COMPLETE)
- **Fixed Gunicorn logging error**: Changed %(p)d to %(p)s in access_log_format
  - Gunicorn v23 provides worker PID as string, not integer
  - Changed response_time format from %%D (numeric) to %(D)s (string)
  - Eliminated "Value is not callable: None" logging exceptions
- **Fixed contradictory scheme headers**: Removed duplicate X-Forwarded-Proto detection
  - Set SECURE_PROXY_SSL_HEADER = None (Gunicorn's secure_scheme_headers handles it)
  - Prevents Django and Gunicorn from conflicting on scheme detection
  - Only Gunicorn processes X-Forwarded-Proto in production mode
  - No more "Contradictory scheme headers" warnings

### Other Fixes & Verification
- Fixed SSL/TLS configuration: Removed `ssl_context = None` causing errors
- Made cookie security settings conditional on IS_PRODUCTION
- Removed empty `secure_scheme_headers = {}` in development
- Render HTTPS termination configured (no SSL needed in Gunicorn)
- All deployment files verified and production-ready
- Development server running cleanly (0 errors/warnings)
- Zero-downtime deployment ready for Render
- **Status**: Production-ready for custom domain (invoiceflow.com.ng)

## Files Structure
```
invoiceflow/
├── gunicorn.conf.py         # Gunicorn WSGI server config
├── render.yaml              # Render deployment definition
├── build.sh                 # Production build pipeline
├── Procfile                 # Process definition
├── DEPLOYMENT_GUIDE.md      # Complete deployment guide
├── .env.render              # Environment template
├── invoiceflow/
│   ├── settings.py          # Django production settings
│   ├── wsgi.py              # WSGI application
│   ├── urls.py
│   ├── middleware/
│   ├── context_processors.py
│   └── ...
├── invoices/
│   ├── models.py
│   ├── views.py
│   ├── api/
│   ├── services.py
│   ├── async_tasks.py
│   └── ...
├── templates/
├── static/
└── requirements.txt
```

## Deployment Workflow
1. **Local Development**: Run on `0.0.0.0:5000` via Django dev server
2. **Version Control**: Push to main branch
3. **Render Detection**: Render webhook triggered
4. **Build Phase**: build.sh executes (migrations, static files, checks)
5. **Server Start**: Gunicorn starts with dynamic workers
6. **Health Checks**: Every 30 seconds verify `/api/health/`
7. **Production**: Application live at custom domain or Render subdomain

## Next Steps for Production Launch
1. Set all required environment variables in Render Dashboard
2. Configure custom domain (invoiceflow.com.ng) via DomainKing
3. Test health endpoint after deployment
4. Monitor logs for first 24 hours
5. Set up monitoring alerts in Render Dashboard
6. Configure backup retention policy (default: 14 days)
7. Schedule regular security audits
8. Monitor cost metrics in Render dashboard

## Support & Troubleshooting
- **Logs**: Render Dashboard > Logs
- **Metrics**: Render Dashboard > Metrics
- **Status**: Render Dashboard > Events
- **Build Issues**: Check build.sh output in logs
- **Runtime Issues**: Check Django system checks: `python manage.py check --deploy`
