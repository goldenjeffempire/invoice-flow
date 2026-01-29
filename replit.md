# InvoiceFlow - Professional Invoicing Platform

## Overview

InvoiceFlow is a production-ready professional invoicing platform built with Django 5.2. The platform enables users to create, manage, and send professional invoices with features including PDF generation, email distribution, WhatsApp integration, multi-currency support, recurring invoices, and payment processing via Paystack.

The application follows a monolithic Django architecture with a single `invoices` app containing all business logic, with clear separation between views, services, and models. It's optimized for deployment on Render with Gunicorn WSGI server.

### Invoice Status Workflow
Invoices follow a state machine with the following statuses and allowed transitions:
- **Draft** -> Sent, Unpaid
- **Sent** -> Unpaid, Paid, Overdue
- **Unpaid** -> Sent, Paid, Overdue  
- **Paid** -> (terminal state, no transitions)
- **Overdue** -> Paid, Sent

Status transitions are enforced via `InvoiceService.transition_status()` and logged to `InvoiceHistory` for audit purposes.

### Invoice History/Audit Log
The `InvoiceHistory` model tracks all invoice changes:
- Creation, updates, and deletions
- Status transitions with old/new values
- Line item changes
- Email and PDF generation events
- User who made the change and timestamp

### Automated Payment Reminders
Per-invoice configurable reminder system:
- **ReminderRule**: User-defined reminder templates (e.g., "3 days before due", "1 day after overdue")
- **ScheduledReminder**: Tracks individual reminder schedules per invoice
- **ReminderLog**: Audit trail of sent reminders with open/click tracking
- **ReminderFailureAlertService**: Emails users when reminders fail after max retries
- **Management command**: `python manage.py process_reminders` for scheduled processing

### Design System
Comprehensive CSS design system in `static/css/design-system.css`:
- **Design tokens**: Colors (primary, success, warning, error, slate), spacing, typography, shadows, transitions
- **Reusable components**: Buttons, cards, forms, badges, alerts, tables, modals, dropdowns, tabs
- **States**: Loading spinners, skeleton loaders, empty states, toast notifications
- **Micro-interactions**: Hover effects, focus states, reveal animations
- **Accessibility**: Skip links, focus-visible styles, ARIA support, screen reader utilities
- **Responsive utilities**: Mobile/tablet/desktop breakpoints, responsive grids

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

#### Payment Security Features
- **Webhook Signature Verification**: HMAC-SHA512 signature validation for all Paystack webhooks
- **Idempotency Keys**: Prevents duplicate payment processing via cached responses (24h TTL)
- **Replay Prevention**: ProcessedWebhook model tracks all processed events by event_id
- **Rate Limiting**: Configurable rate limits on webhook endpoints (default: 120 req/60s per IP)
- **Amount/Currency Validation**: Server-side verification of payment amounts against invoice totals
- **Atomic Transactions**: Payment and invoice updates happen in single database transactions with row locking
- **Reconciliation Service**: Automatic detection of payment state mismatches with recovery attempts

#### Payment Status Flow
1. Payment initialized -> Status: PENDING
2. Webhook received with charge.success -> Signature verified -> Amount validated
3. Payment marked SUCCESS atomically -> Invoice status updated to PAID
4. InvoiceHistory audit log created with payment details

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
├── pdf_service.py       # PDF generation
├── admin_service.py     # Platform admin statistics and user management
├── feedback_service.py  # Engagement metrics and user feedback
└── reminder_service.py  # Reminder rule management and tracking
```

### Layering Rules (Gate)
Every endpoint/view maps cleanly to service functions with no business logic in views or templates:
- **Views**: Only handle request parsing, authentication checks, permission validation, and response mapping
- **Services**: Contain all business logic, database transactions, and side effect orchestration
- **Models**: Define data structure and constraints only - no business methods
- **Templates**: Presentation only, no conditional business rules

### Validation and Error Handling
Centralized validation and error handling in `invoices/validation/`:
```
invoices/validation/
├── __init__.py           # Module exports
├── schemas.py            # Domain-specific validation schemas
├── errors.py             # Standardized error classes and format
├── middleware.py         # ErrorHandlingMiddleware for consistent responses
└── api_exceptions.py     # DRF custom exception handler
```

**Validation Schemas** (domain-specific rules):
- `InvoiceSchema` - Invoice creation/updates with line items
- `ClientSchema` - Client information validation
- `PaymentSchema` - Payment processing validation
- `RecurringSchema` - Recurring invoice configuration
- `LineItemSchema` - Invoice line item validation

**Error Response Format** (consistent across all endpoints):
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed. Please check your input.",
    "fields": [
      {"field": "client_email", "code": "FIELD_INVALID_FORMAT", "message": "Please enter a valid email address."}
    ]
  },
  "request_id": "uuid"
}
```

**HTTP Status Codes**:
- 400: Bad Request (validation errors)
- 401: Unauthorized (not authenticated)
- 403: Forbidden (not permitted)
- 404: Not Found
- 422: Unprocessable Entity (business rule violation)
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error

**Frontend Error Utilities** (`static/js/error-handler.js`):
- Toast notifications for transient errors
- Inline field error display
- `ErrorHandler.handleFetch()` for consistent API error handling

**API Endpoint**: `/api/v1/validation/constraints/` exposes validation rules for client-side mirroring

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