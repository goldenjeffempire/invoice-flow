# InvoiceFlow

## Overview
InvoiceFlow is a professional invoicing platform built with Django 5.x. It provides features for creating, managing, and tracking invoices with support for multiple payment methods and automated reminders.

## Project Architecture

### Tech Stack
- **Backend**: Django 5.2.9 with Django REST Framework
- **Database**: PostgreSQL (via DATABASE_URL environment variable)
- **Static Files**: WhiteNoise for serving static files
- **PDF Generation**: WeasyPrint/ReportLab
- **Cache**: Redis (optional) or Local Memory Cache
- **Task Queue**: Not currently configured

### Directory Structure
```
├── invoiceflow/          # Django project settings
│   ├── settings.py       # Main settings file
│   ├── urls.py           # Root URL configuration
│   ├── wsgi.py           # WSGI application
│   └── asgi.py           # ASGI application
├── invoices/             # Main Django app
│   ├── models.py         # Database models
│   ├── views.py          # View functions
│   ├── api/              # REST API endpoints
│   └── templates/        # App-specific templates
├── templates/            # Project-wide templates
├── static/               # Static files (CSS, JS, images)
├── staticfiles/          # Collected static files
└── requirements.txt      # Python dependencies
```

### Key Models
- User, UserProfile
- Invoice, InvoiceItem
- Client
- Payment, PaymentReconciliation
- RecurringTemplate

## Development Setup

### Running Locally
The project runs on port 5000 with the Django development server:
```bash
python manage.py runserver 0.0.0.0:5000
```

### Database
PostgreSQL is configured via the DATABASE_URL environment variable. Migrations are in `invoices/migrations/`.

### Environment Variables
Required for production:
- SECRET_KEY
- DATABASE_URL
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD

Optional:
- HCAPTCHA_SITEKEY/HCAPTCHA_SECRET
- PAYSTACK_SECRET_KEY
- SENTRY_DSN
- REDIS_URL

## Deployment
Production deployment uses Gunicorn:
```bash
gunicorn --bind 0.0.0.0:5000 invoiceflow.wsgi:application
```

## Recent Changes
- 2026-01-19: Cleanup and production readiness
  - Fixed Python version mismatch issues (linked dependencies to Python 3.12)
  - Deduplicated and cleaned up requirements.txt
  - Audited settings.py: removed duplicates, improved environment variable handling
  - Hardened security: implemented HMAC signature verification for Paystack webhooks
  - Implemented stubbed background tasks in enterprise_tasks.py
  - Fleshed out placeholder forms (PaymentRecipientForm)
  - Improved analytics cache invalidation logic
  - Applied all pending database migrations
  - Set up development workflow on port 5000
  - Hardened data integrity with explicit domain methods and consolidated validation
  - Optimized production caching with Redis support and tuned rate-limiting
