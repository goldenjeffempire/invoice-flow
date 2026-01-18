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
- 2026-01-18: Initial Replit setup
  - Configured PostgreSQL database
  - Installed Python 3.11 and dependencies
  - Added Replit domain to CSRF_TRUSTED_ORIGINS
  - Fixed missing PaymentReconciliation import in paystack_service.py
  - Ran all database migrations
  - Set up development workflow on port 5000
