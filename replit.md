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
- Admin panel
- REST API (DRF)
- Email notifications (SendGrid)
- Email marketing (newsletter subscribers + campaign management)
- Reports (revenue, aging, cashflow, profitability, tax, forecast)

## Architecture

- **Framework:** Django 6.x with Django REST Framework
- **Database:** PostgreSQL (Replit built-in via `DATABASE_URL`)
- **Cache:** In-memory (LocMemCache) in dev, Redis in production
- **Static Files:** WhiteNoise for serving static assets
- **Templates:** Django templates with Tailwind CSS (CDN), Alpine.js (CDN), Chart.js (CDN)
- **UI System:** App shell (layout_app.html). CSS-variable-driven collapsible sidebar (256px ↔ 64px icon-only mode with tooltips), mobile off-canvas drawer with overlay, sticky topbar, workspace switcher dropdown, user profile footer menu, notification dropdown, dark mode toggle, ⌘K global search palette. **Dashboard fully rebuilt (production-grade)** — `invoices/views/dashboard_views.py` and `templates/pages/dashboard.html` completely rewritten. Features: two rows of KPI cards (MTD revenue + trend %, outstanding, overdue, expenses MTD + trend %, net profit, collection rate, total clients, draft count), 6-month revenue-vs-expenses Chart.js line chart with gradient fills, invoice status doughnut chart with legend, recent invoices table with status badges and inline due amounts, recent payments feed, due-this-week sidebar, top clients by paid revenue, 6 quick action tiles, overdue aging analysis (0-30/31-60/61-90/90+ day buckets with progress bars — only shown when overdue invoices exist). All sections have proper empty states. Fully responsive. Dark mode supported. `LOGIN_REDIRECT_URL = '/dashboard/'`. Client detail page (`pages/clients/detail.html`) enhanced with a 12-month per-client revenue bar chart. All report pages include Chart.js visualizations.
- **PDF Generation:** WeasyPrint + ReportLab
- **Email:** SendGrid
- **Auth:** Enterprise-grade rebuild — AuthService, SessionService, PasswordValidator (HIBP breach check), SecurityService. No email verification required. MFA (TOTP via pyotp) preserved for existing users.
- **Deployment:** Render `standard` plan (Always On, 2 GB RAM, 1 CPU). Gunicorn gthread workers. Zero-downtime deploys via `preDeployCommand` migrations. Replit configured as `vm` (Always On). Sentry optional via `SENTRY_DSN` env var.
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

## Recent Improvements (2026-03)

### New Public Pages
- `templates/pages/support.html` — Full support centre with search, help topic cards, contact channels, and live platform status indicator.
- `templates/pages/blog.html` — Blog listing with featured article, article grid, tag badges, and newsletter subscription form.
- `templates/pages/careers.html` — Careers page with company values, open roles listing, and step-by-step hiring process.
- `templates/pages/workspace/create.html` — Workspace creation form served by the existing `workspace_create` view.

### Navigation & Footer
- Resources nav dropdown now includes Blog and Support Centre links (desktop + mobile).
- Footer updated to include Blog, Support, Careers, and Security in appropriate columns.

### View Fixes
- `settings_page` — Was a redirect stub; now `@login_required` and renders `pages/settings.html` with profile + workspace context.
- `payment_settings_update_ajax` — Was a stub; now fully updates `accept_card_payments`, `accept_bank_transfers`, `accept_mobile_money`, and `payment_instructions` on the user profile.
- `security_update_ajax` — Was a stub; now `@login_required` + `@require_POST`, updates security notification preferences.
- `reminder_dashboard` — Added `@login_required` decorator.
- `faq_api` — Now returns real FAQ data with optional search filtering via `?q=` query param.

## Deployment

Uses Gunicorn with `gunicorn.conf.py` for production. Build step runs migrations and collectstatic.
