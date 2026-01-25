# InvoiceFlow - Professional Invoicing Platform

## Overview
InvoiceFlow is a professional invoicing platform built with Django. It allows businesses to create, send, and track invoices with automated payment reminders and real-time analytics.

## Project Structure
```
invoiceflow/
├── invoices/           # Main Django app
│   ├── views.py        # Views including landing page, auth, invoices
│   ├── urls.py         # URL routing
│   ├── models.py       # Database models
│   └── api/            # REST API endpoints
├── templates/
│   ├── base/           # Base layout templates
│   ├── pages/          # Page templates (landing, auth, dashboard)
│   ├── payments/       # Payment-related templates
│   └── admin/          # Admin panel templates
├── static/
│   ├── css/            # Stylesheets (landing_v2.css)
│   ├── js/             # JavaScript (landing_v2.js)
│   └── images/         # Image assets
└── invoiceflow/        # Django project settings
```

## Recent Changes
- **Jan 2026**: Complete landing page redesign with:
  - Three-slide intro animation (Welcome, Core Value, Priming)
  - Premium hero section with CTAs
  - Value proposition and features sections
  - Problem-solution storytelling
  - Product mockups and workflow diagrams
  - Dynamic FAQ loaded from API (/api/faq/)
  - Contact form section
  - Multiple CTA blocks
  - Smooth scrolling and scroll-triggered animations
  - WCAG accessibility (keyboard nav, focus states, reduced-motion)
  - Responsive design (mobile/tablet/desktop/ultrawide)

## Key Features
- Professional invoice creation and management
- Automated payment reminders
- Real-time analytics dashboard
- Online payments via Paystack integration
- MFA support for security
- PDF invoice export

## Development
- Run with: `python manage.py runserver 0.0.0.0:5000`
- Database: PostgreSQL (DATABASE_URL environment variable)
- Static files served with WhiteNoise

## Production Notes
Production deployments should use **Render** (or another production platform) with:
- `DEBUG=False`
- strict `ALLOWED_HOSTS`
- strict `CSRF_TRUSTED_ORIGINS`
- a managed Postgres database
- proper secrets set via environment variables

If you use Replit, do not commit secrets. Configure them in Replit's Secrets UI.
