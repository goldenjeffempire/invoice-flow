# InvoiceFlow - Professional Invoicing Platform

## Overview
InvoiceFlow is a production-ready professional invoicing platform designed to enable users to create, manage, and send professional invoices. Key capabilities include PDF generation, email and WhatsApp distribution, multi-currency support, recurring invoices, and integrated payment processing. The platform features robust security with password breach detection, suspicious login detection, device and session management, and comprehensive security event logging. It also includes an automated payment reminder system and a detailed invoice history/audit log. The public-facing marketing website and authentication UI are built with a unified, modern design system.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend
The platform is built on **Django 5.2.9** with a monolithic architecture, employing a strict layered approach separating models, services, views, and templates. Business logic resides in service classes. **Gunicorn** serves as the WSGI server, and **WhiteNoise** handles static files. An **Async Email Service** handles email sending in the background to prevent blocking.

### Database
**PostgreSQL** is the primary database.

### Authentication & Security
A production-grade authentication system is implemented with:
- **User Management**: Sign up with strong password validation, login with rate limiting, email verification, secure password reset, workspace invitations.
- **Multi-Factor Authentication (MFA)**: TOTP-based 2FA with backup codes.
- **Proactive Security**: Password breach detection (Have I Been Pwned API), suspicious login detection, device/session management.
- **Auditing & Resilience**: Comprehensive security event logging, IP-based rate limiting, CSRF protection, and a resilience middleware stack for database, redirect, and session issues.

### Payment Processing
- **Paystack**: Primary payment gateway for online payments.
  - Webhook: `/webhooks/paystack/`
  - Integration: Verified signatures, idempotency, and automatic reconciliation.
- **Offline Payments**: Support for cash and bank transfers with audit trails.
- **Security**: HMACS signature validation for all webhooks.

### Email Services
**SendGrid** is used for all transactional emails.

### PDF Generation
**WeasyPrint** is used for HTML-to-PDF invoice generation.

### Frontend
The frontend uses **Tailwind CSS** for styling with server-side rendered Django templates. It features a comprehensive design system, responsive layouts, and accessibility compliance. The authentication UI incorporates glass morphism effects, real-time password strength indicators, and staggered animations. An 8-step onboarding flow guides users through setup, including business profile, branding, tax, payments, and team invitations.

### Caching
**Django-Redis** provides the caching layer.

### API Architecture
**Django REST Framework** is used for API endpoints, with **drf-spectacular** for OpenAPI schema generation, versioning at `/api/v1/`, and standardized error handling.

### Background Tasks
A **ThreadPoolExecutor-based system** handles asynchronous tasks with retry logic.

### Dashboard & Analytics
- **Financial Insights**: Real-time KPI widgets for total revenue, monthly performance, overdue totals, and pending receivables.
- **Export Engine**: CSV export functionality for all critical data including Transactions and Client lists for external accounting.

### Client Management
- **CRM Lite**: Comprehensive client profiles with billing/shipping management, financial summaries, internal notes, and automated activity tracking.

### Monitoring & Observability
Structured JSON logging, health check endpoints, performance monitoring middleware, and **Sentry** integration are in place.

### Key Design Patterns
- **Strict Layered Architecture**: Models, Services, Views, Templates separation.
- **Service Layer**: Centralizes business logic.
- **Repository Pattern**: Custom model managers.
- **Decorator Pattern**: For authentication, rate limiting, monitoring.
- **Middleware Stack**: For security headers, logging, MFA enforcement.

### Validation and Error Handling
Centralized validation with domain-specific schemas, standardized error responses, and frontend error utilities.

### Invoice Lifecycle
A comprehensive invoice lifecycle system supports:
- **Status Tracking**: Draft, sent, viewed, part_paid, paid (with overdue/void/write-off states).
- **Features**: Multi-currency, tax modes (exclusive/inclusive), per-line and global discounts, recurring invoices, delivery tracking, payment reminders, public sharing via unique token, and version control.
- **Supporting Models**: `LineItem`, `InvoiceActivity` (audit trail), `InvoiceAttachment`, `InvoicePayment`.
- **State Machine**: Enforces status transitions via `InvoiceService`.
- **Views**: List, builder, detail, preview, PDF generation, share link, record payment, void, duplicate, CSV export, and public invoice viewing.

## External Dependencies

### Payment Gateway
- **Paystack API**

### Email Service
- **SendGrid API**

### OAuth Providers
- **Google OAuth**
- **GitHub OAuth**

### CAPTCHA
- **hCaptcha**

### Database
- **PostgreSQL**

### Caching
- **Redis**

### Error Monitoring
- **Sentry**

### Deployment Platform
- **Replit** (development)
- **Render** (production)