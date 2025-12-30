# InvoiceFlow - Production-Ready Deployment Platform

## Overview
InvoiceFlow is a Django SaaS invoicing platform designed for secure, scalable, and reliable invoicing. It offers secure payment processing, robust API validation, optimized database performance, and enhanced security features. The platform is production-hardened and configured for 24/7 operation with a 99.9% uptime SLA, making it suitable for thousands of users. Key capabilities include a rebuilt "Create Invoice" page with real-time calculations, a comprehensive "Settings" page, and an enhanced "Invoice List/Dashboard" with bulk actions and advanced filtering.

## User Preferences
I prefer detailed explanations and iterative development. Ask before making major changes. I value clear, concise communication and prefer if the agent focuses on high-level feature implementation rather than granular code details unless specifically asked.

## System Architecture

### Deployment Stack
The platform is deployed on Render, utilizing a Python 3.13 web service with Gunicorn for WSGI. It uses PostgreSQL 15 for the database (Render-managed with daily backups and 99.9% uptime). Static files are served via WhiteNoise, and caching is handled by Django's database cache. Health checks are performed every 30 seconds via `/api/health/`, and logs are captured automatically.

### UI/UX Decisions
The UI/UX prioritizes a fast, responsive user experience with secure payment processing. It includes multi-currency support, real-time payment status tracking, production-grade validation, error handling, and professional styling across all pages. The "Create Invoice" page features dynamic line items and real-time calculations. The "Settings" page is a tabbed interface with six organized sections.

### Technical Implementations
Key technical implementations include strict API validation using Decimal types for financial accuracy, idempotent payment handling with `IdempotencyKey`, and HMAC verification for webhook security. Database optimization is achieved through strategic indexing and PostgreSQL with connection pooling. Security features include 12 middleware layers, CSP, HSTS preload, rate limiting, field encryption, and structured JSON logging. All forms feature comprehensive client-side and server-side validation.

### Feature Specifications
Core features include a professional "Create Invoice" form with real-time calculations and currency support, an "Invoice List" with bulk actions and advanced filtering, and a unified "Settings" interface. The platform also supports comprehensive API documentation, health check endpoints, structured JSON logging, multi-currency support, recurring invoice automation, an admin interface, hCaptcha form protection, SendGrid email integration, and role-based access control.

### Template System Architecture & Implementation Strategy
The project maintains dual template systems for flexibility and stability:

**Create Invoice Page:**
- **Primary System**: Multi-step workflow (4 steps) via `invoice_create_views.py`
  - Step 1: Invoice details (`/invoices/create/`)
  - Step 2: Line items (`/invoices/create/items/`)
  - Step 3: Taxes & discounts (`/invoices/create/taxes/`)
  - Step 4: Review & confirm (`/invoices/create/review/`)
- **Alternative System**: Single-page form via `views.create_invoice()` (fallback compatibility)
- **Status**: Both operational, multi-step is production-primary

**Settings Page:**
- **Primary System**: Unified tabbed interface via `settings_views.settings_unified()`
  - Tabs: Profile, Business, Security, Payments, Notifications, Billing
  - Single unified template: `pages/settings-unified.html`
- **Alternative System**: Individual feature pages (profile, business, security, etc.)
- **Status**: Both operational, unified is production-primary

**Decision**: Dual systems maintained for flexibility. Primary systems are fully tested and production-ready. Alternative systems available for feature-specific optimization and gradual migration.

### System Design Choices
The architecture emphasizes security-by-default, with idempotent payment processing and webhook deduplication. Performance is optimized through database indexing and efficient server configurations. The system is designed for scalability and maintainability, ensuring clear separation of concerns.

## External Dependencies

- **Database**: PostgreSQL 15
- **Payment Gateway**: Paystack
- **Email Service**: SendGrid
- **Deployment Platform**: Render
- **Domain Registrar**: DomainKing (for custom domain configuration)
- **Static Files**: WhiteNoise
- **Form Protection**: hCaptcha