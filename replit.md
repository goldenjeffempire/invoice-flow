# InvoiceFlow - Professional Invoicing Platform

## Overview

InvoiceFlow is a production-ready professional invoicing platform built with Django 5.2. The platform enables users to create, manage, and send professional invoices with features including PDF generation, email distribution, WhatsApp integration, multi-currency support, recurring invoices, and payment processing via Paystack.

The application follows a monolithic Django architecture with a single `invoices` app containing all business logic, with clear separation between views, services, and models. It's optimized for deployment on Render with Gunicorn WSGI server.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Django 5.2.9** as the core web framework
- **Gunicorn** as the production WSGI server with dynamic worker scaling (2-7 workers based on CPU cores)
- **WhiteNoise** for static file serving with Brotli compression

### Database
- **PostgreSQL** via `psycopg2-binary` and `dj-database-url` for connection management
- Drizzle is not used; the project uses Django's built-in ORM exclusively
- Database URL configured via `DATABASE_URL` environment variable

### Authentication & Security
- Django's built-in authentication with custom extensions
- **Multi-Factor Authentication (MFA)** using TOTP via `pyotp` with QR code generation
- **Email verification** required for sensitive operations
- **OAuth integration** for Google and GitHub login
- Custom password validators with breach detection
- Field-level encryption for sensitive data using Fernet (AES-256)
- GDPR compliance endpoints for data export and deletion

### Payment Processing
- **Paystack** as the primary payment gateway
- Payment reconciliation service for state consistency
- Idempotency keys for preventing duplicate transactions
- Webhook handling for real-time payment status updates

### Email Services
- **SendGrid** for transactional emails with dynamic templates
- Invoice delivery, payment reminders, and verification emails
- Fallback to Django's built-in email backend

### PDF Generation
- **WeasyPrint** for HTML-to-PDF invoice generation
- **ReportLab** as an alternative PDF library

### Frontend
- **Tailwind CSS** for styling with PostCSS processing
- Server-side rendered templates using Django's template engine
- Asset minification pipeline (Terser for JS, cssnano for CSS)
- Dark mode support

### Caching
- **Django-Redis** for caching layer
- Cache warming on user login
- Performance monitoring decorators

### API Architecture
- **Django REST Framework** for API endpoints
- **drf-spectacular** for OpenAPI schema generation
- Versioned API at `/api/v1/`
- Standardized response format with enterprise error handling

### Background Tasks
- ThreadPoolExecutor-based async task processing (no Celery/Redis dependency)
- Task tracking with retry logic and exponential backoff

### Monitoring & Observability
- Structured JSON logging for production
- Health check endpoints (`/health/`, `/health/ready/`, `/health/live/`)
- Performance monitoring middleware
- Sentry integration for error tracking

### Key Design Patterns
- **Strict Layered Architecture**: Clear separation between layers:
  - **Models** (`invoices/models.py`): Pure data + constraints only, no business logic
  - **Services** (`invoices/services/`): All business logic, transactions, and side effects
  - **Views** (`invoices/views.py`): Request parsing, auth checks, response mapping only
  - **Templates**: Presentation only
- **Service Layer** (`invoices/services/`): Modular service classes:
  - `InvoiceService` - Invoice lifecycle management
  - `UserService`, `ProfileService`, `NotificationService`, `PaymentSettingsService` - User management
  - `PaymentService` - Payment processing and webhook handling
  - `AnalyticsService` - Dashboard statistics with caching
  - `EmailService` - Email delivery orchestration
  - `PDFService` - Invoice PDF generation
- **Repository Pattern**: Models with custom managers for query encapsulation
- **Decorator Pattern**: Extensive use for authentication, rate limiting, and monitoring
- **Middleware Stack**: Security headers, request logging, MFA enforcement

### Service Layer Architecture
All business logic flows through the `invoices/services/` directory:
```
invoices/services/
├── __init__.py          # Exports all services
├── invoice_service.py   # Invoice CRUD and status transitions
├── user_service.py      # Profile, notifications, payment settings
├── payment_service.py   # Payment processing and webhooks
├── analytics_service.py # Dashboard stats with caching
├── email_service.py     # Email delivery
└── pdf_service.py       # PDF generation
```

## External Dependencies

### Payment Gateway
- **Paystack API** (`PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY`) - Payment processing for Nigerian market

### Email Service
- **SendGrid API** (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`) - Transactional email delivery

### OAuth Providers
- **Google OAuth** (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`)
- **GitHub OAuth** (`GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`)

### CAPTCHA
- **hCaptcha** (`HCAPTCHA_SITEKEY`, `HCAPTCHA_SECRET`) - Bot protection (optional)

### Database
- **PostgreSQL** - Primary database (configured via `DATABASE_URL`)

### Caching
- **Redis** - Session and cache storage (configured via `django-redis`)

### Error Monitoring
- **Sentry** - Error tracking and performance monitoring

### Required Environment Variables (Production)
```
SECRET_KEY          - Django secret key (must not be insecure default)
DATABASE_URL        - PostgreSQL connection string
EMAIL_HOST_USER     - SendGrid API username
EMAIL_HOST_PASSWORD - SendGrid API key
ENCRYPTION_SALT     - Salt for field-level encryption
PRODUCTION          - Set to "true" for production mode
```

### Deployment Platform
- **Render** - Primary deployment target with autoscaling configuration
- Health checks configured for uptime monitoring
- WhiteNoise for static file serving