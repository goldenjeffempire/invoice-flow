# InvoiceFlow

A production-ready Django invoicing application for freelancers and small businesses.

## Features
- Invoice creation, management, and PDF generation
- Client management
- Payment tracking (Paystack integration)
- Recurring billing/scheduling
- Expense tracking
- Estimates
- Multi-workspace support
- MFA authentication
- Admin dashboard
- REST API (DRF)
- Email notifications (SendGrid)

## Architecture

- **Framework:** Django 6.x with Django REST Framework
- **Database:** PostgreSQL (Replit built-in via `DATABASE_URL`)
- **Cache:** In-memory (LocMemCache) in dev, Redis in production
- **Static Files:** WhiteNoise for serving static assets
- **Templates:** Django templates with Tailwind CSS
- **PDF Generation:** WeasyPrint + ReportLab
- **Email:** SendGrid
- **Auth:** Enterprise-grade rebuild — AuthService, SessionService, PasswordValidator (HIBP breach check), SecurityService. No email verification required. MFA (TOTP via pyotp) preserved for existing users.
- **Encryption:** cryptography library with ENCRYPTION_SALT env var

## Project Structure

```
invoiceflow/        - Django project settings and configuration
invoices/           - Main app with models, views, forms, API
  api/              - REST API views and serializers
  migrations/       - Database migrations
  management/       - Custom management commands
  validation/       - Input validation and error handling
  services/         - Business logic services
  views/            - View modules
templates/          - HTML templates
static/             - Static assets (CSS, JS)
staticfiles/        - Collected static files (generated)
tests/              - Test suite
```

## Development

The app runs on port 5000 with `python manage.py runserver 0.0.0.0:5000`.

### Environment Variables
- `SECRET_KEY` - Django secret key (defaults to insecure dev key if not set)
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Replit)
- `DEBUG` - Set to "false" for production (default "true")
- `PRODUCTION` - Set to "true" for production mode
- `ENCRYPTION_SALT` - Required in production for data encryption
- `SENDGRID_API_KEY` - For email delivery
- `SENTRY_DSN` - For error monitoring

### Migration Notes
Migration 0006 had a bug where it tried to modify the `invoices_payment` table after it was dropped by migration 0003's raw SQL. Fixed by adding a `CreateModel` for Payment in migration 0006 before the RemoveField operations.

## Deployment

Uses Gunicorn with `gunicorn.conf.py` for production. Build step runs migrations and collectstatic.
