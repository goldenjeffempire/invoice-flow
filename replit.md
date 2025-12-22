# InvoiceFlow - Production-Grade Full-Stack Platform

## Overview
InvoiceFlow is a production-grade professional invoicing platform designed to streamline financial operations for freelancers, agencies, small teams, and service-based businesses. It offers comprehensive features including PDF generation, multi-channel invoice sharing, payment tracking, recurring invoices, customizable templates, and an analytics dashboard. The platform emphasizes enterprise-grade security and a modern, intuitive user experience, aiming to provide a robust, scalable solution that saves users time, accelerates payments, and drives revenue growth.

## User Preferences
- Preserve Django backend while rebuilding frontend
- Execute phases sequentially with artifact reporting
- Modern, professional UI/UX aligned with component showcase
- Comprehensive documentation at each phase

## System Architecture
### UI/UX Decisions
The platform features a modern, professional UI/UX with a focus on clean light themes, professional business aesthetics, and responsive design. Key elements include a design system foundation with indigo primary colors, emerald accents, and an 8pt grid; the Inter font family; advanced animations supporting `prefers-reduced-motion`; a modular component library; comprehensive mobile-first responsive design; and interactive elements like hover effects and live form validation.

### Technical Implementations
The backend is built with Django 5.2.9, Python 3.12.11, and PostgreSQL. The frontend uses HTML/CSS with JavaScript, styled using Tailwind CSS. Email services are integrated via SendGrid, and PDF generation uses WeasyPrint. Security measures include CSRF, XSS, SQL injection prevention, modern security headers, rate limiting, secure session management, and TOTP MFA. Performance is optimized with Gunicorn, database connection pooling, static file compression, and lazy loading. The system also includes dedicated health check endpoints, SEO features, and PWA support with service workers and a manifest. Environment variable validation is enforced, and HTTP security headers are strictly applied.

### Feature Specifications
Core features include comprehensive invoice management (create, edit, track, export, recurring), multi-channel sharing (email, WhatsApp), payment tracking, customizable invoice templates, an analytics dashboard, secure user authentication, and contact management. User-configurable settings and audit logging are also included. Payment operations require email verification, MFA completion, and identity verification for high-value transactions. Recurring invoice generation includes idempotency and execution locks, and public invoice access is secured via token-based authentication with access logging.

### System Design Choices
The architecture incorporates micro-interactions, robust error handling with user-friendly notifications, and extensive accessibility features. Deployment is configured for production-ready Gunicorn on Render with autoscale and SSL. Logging is structured JSON, and the platform aims for GDPR compliance. Enterprise-grade authentication includes real-time password strength validation, MFA/2FA with recovery codes, and social login integrations. Payment processing is integrated via Paystack, supporting multiple currencies with secure webhook verification, idempotency, reconciliation services, and automatic recovery for failed payments. Session rotation is implemented to prevent fixation attacks.

### API Layer, Email Delivery & Testing Infrastructure (December 22, 2025)
#### API Response Standardization
- **APIResponse Wrapper** (invoices/api/response.py): Consistent response format across all endpoints
  - Success responses: `{"success": true, "message": "...", "data": {...}, "meta": {...}}`
  - Error responses: `{"success": false, "error": {"code": "...", "message": "...", "details": {...}}}`
  - Paginated responses with metadata (page, page_size, total, total_pages)
  - Built-in support for error codes (VALIDATION_ERROR, AUTHENTICATION_REQUIRED, etc.)
- **Exception Handlers**: Custom exception handler for DRF (exception_handlers.py)
  - Standardized error codes for all API exceptions
  - Request ID tracking for debugging
  - Detailed validation error formatting

#### Email Delivery Tracking & Retry Queue
- **EmailDeliveryLog Model**: Complete email delivery tracking
  - Email types: Verification, Invoice Ready, Payment Reminder, Payment Receipt, Recurring Notification, Security Alert, Password Reset
  - Status tracking: PENDING, SENT, BOUNCED, FAILED, QUEUED
  - Bounce type and reason logging for failed deliveries
  - Related invoice linking for audit trail
  - Message ID tracking (SendGrid integration)
- **EmailRetryQueue Model**: Intelligent retry strategy with exponential backoff
  - Max retries configurable (default 5)
  - Retry strategies: EXPONENTIAL, LINEAR, IMMEDIATE
  - Next retry scheduling
  - Error message logging for debugging
  - Active status flag for pause/resume

#### Database Migrations
- **Migration 0023**: Added EmailDeliveryLog and EmailRetryQueue models
  - Proper indexes for efficient status/email/type queries
  - Cascade delete for referential integrity

#### Testing Infrastructure
- **Test Scaffold**: Basic test structure created for comprehensive coverage
  - test_email_delivery.py: Email delivery and retry queue tests
  - test_api.py: API endpoint tests (existing)
  - test_views.py: View tests (existing)
  - test_models.py: Model tests (existing)
  - conftest.py: Shared fixtures and setup (existing)

#### Infrastructure Completed
- ✅ Standardized API response format (wrapper created)
- ✅ Email delivery tracking with bounce handling
- ✅ Retry queue with exponential backoff strategy
- ✅ Exception handling with error codes
- ✅ Test scaffolding for email, payment, MFA coverage

#### Remaining Work (Requires Full Autonomous Mode):
1. **Complete Permission Matrix**:
   - Permission decorators and classes across all views
   - Role-based access control (admin, user, client)
   - Object-level permissions for invoices/payments

2. **Rate Limiting & API Abuse Protection**:
   - Per-endpoint rate limits
   - User-based throttling
   - IP-based throttling
   - Integration with existing rate limit middleware

3. **Comprehensive Test Suite**:
   - End-to-end payment flow tests
   - Webhook security and replay attack tests
   - MFA enforcement tests
   - Recurring invoice duplicate prevention tests
   - Email retry queue execution tests
   - Regression test coverage
   - CI/CD configuration

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid (Replit Integration)
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js