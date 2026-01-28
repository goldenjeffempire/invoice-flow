# InvoiceFlow - Professional Invoicing Platform

## Overview
InvoiceFlow is an enterprise-grade invoicing platform built with Django. It provides a robust suite of features including secure authentication with MFA, automated payment reminders, and integrated Paystack payments.

## Project Structure
```
invoiceflow/            # Django project settings
invoices/               # Main Django app
├── api/                # REST API
├── management/         # Custom CLI commands
├── migrations/         # Database migrations
├── templates/          # App-specific templates
└── services.py         # Business logic services
static/                 # Visual assets and design system
templates/              # Project-wide templates
```

## Recent Changes
- **Jan 28, 2026**: Completed a full system audit and professional production-readiness cleanup.
  - Consolidated Django project settings to `invoiceflow/` for enterprise-grade modularity.
  - Fixed database connectivity for Neon PostgreSQL with reliable failover to SQLite.
  - Verified all core features: MFA, Paystack integration, and Analytics.
  - Optimized middleware stack for security and performance (CSP, SSL, Rate-limiting).
  - Synchronized all database migrations and collected static assets.

## Key Features
- **Enterprise Security**: Built-in MFA (TOTP), secure sessions, and CSP protection.
- **Payment Integration**: Native Paystack support for cards, transfers, and webhooks.
- **Automated Reminders**: Intelligent scheduling system for invoice follow-ups.
- **Real-time Analytics**: High-performance dashboard with SQL-level aggregations.

## Development
- Run with: `python manage.py runserver 0.0.0.0:5000`
- Database: Neon PostgreSQL via `DATABASE_URL` secret.

## Deployment
Production-ready for **Render** via `render.yaml`. Requires `DATABASE_URL`, `SECRET_KEY`, and `PAYSTACK_SECRET_KEY` environment variables.
