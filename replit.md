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

### Reports & Analytics
A production-grade SaaS reporting module with comprehensive financial analysis:
- **ReportsService**: Centralized service class with 7 report types, KPI calculations, date-range filtering (13 presets), trend analysis, and forecasting.
- **Report Types**: Revenue, A/R Aging, Cashflow, Client Profitability, Tax Summary, Expense Analysis, Forecast.
- **KPI Dashboard**: Total revenue, outstanding balance, overdue amount, collection rate, average invoice value, invoice counts, trend indicators.
- **Date Range System**: 13 presets (today, yesterday, this_week, last_week, this_month, last_month, this_quarter, last_quarter, this_year, last_year, last_30/90/365_days, all_time) plus custom ranges.
- **Exports Hub**: 9 export types with CSV generation, export history tracking, and row count logging.
- **Shared Report Links**: Create shareable links with optional password protection (SHA256 hash), expiration dates, and access audit logging.
- **Audit Logging**: Full access tracking for shared links including IP address, user agent, and timestamps.
- **Models**: `SharedReportLink`, `ReportAccessLog`, `ReportExport`.
- **Views**: Reports home, individual report views, CSV export handlers, shared link management, public shared report viewing.
- **Workspace-Based**: All reports are filtered by workspace for multi-tenant isolation.

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

### Recurring Billing System
A production-grade recurring billing and subscription management system:
- **Models**: `RecurringSchedule`, `ScheduleExecution`, `PaymentAttempt`, `RecurringScheduleAuditLog`.
- **Interval Types**: Weekly, biweekly, monthly, quarterly, yearly, and custom day intervals.
- **Features**: Proration support, timezone-aware scheduling, anchor day billing, configurable payment terms.
- **Retry Logic**: Exponential backoff with configurable max attempts and interval multiplier.
- **Idempotent Generation**: Prevents duplicate invoices via compound idempotency keys (schedule_id + date).
- **Failure Notifications**: Email alerts when payment retries are exhausted.
- **Audit Logging**: Complete audit trail of all schedule actions, invoice generation, and payment attempts.
- **Views**: Schedule list, create, detail (with execution history), edit, pause/resume, and cancel.
- **Management Command**: `process_recurring_schedules` for automated scheduled processing.
- **Service Layer**: `RecurringBillingService` handles all business logic including invoice generation, payment processing, and retry orchestration.

### Expenses & Cost Tracking
A comprehensive expense management and cost tracking module:
- **Models**: `Expense`, `ExpenseCategory`, `Vendor`, `ExpenseAttachment`, `ExpenseAuditLog`.
- **Expense Workflow**: Draft → Pending Approval → Approved/Rejected → Reimbursed or Billed to Client.
- **Categories**: Hierarchical categories with color coding, GL account codes, and tax deductibility flags.
- **Vendors**: Full vendor management with contact info, payment terms, and expense totals tracking.
- **Receipt Attachments**: Secure file upload with type validation (images, PDFs), size limits (10MB).
- **Billable Expenses**: Mark expenses as billable, assign to clients with optional markup, add to invoices.
- **Multi-Currency**: Full currency support with exchange rates and base currency conversion.
- **Tax Handling**: Per-expense tax rates with automatic tax amount calculation.
- **Filtering & Search**: Filter by status, category, vendor, client, date range, billable status.
- **P&L Reports**: Revenue vs expenses analysis with category breakdown and monthly trends.
- **CSV Export**: Export filtered expense data for external accounting systems.
- **Audit Logging**: Complete audit trail of all expense actions.
- **Views**: Expense list, create/edit, detail, categories, vendors, P&L report, billable expense selection.
- **Service Layer**: `ExpenseService`, `ExpenseCategoryService`, `VendorService` for business logic.

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