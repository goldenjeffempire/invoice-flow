# InvoiceFlow - Professional Invoicing Platform

## Overview

InvoiceFlow is a production-ready professional invoicing platform designed to enable users to create, manage, and send professional invoices. Key capabilities include PDF generation, email and WhatsApp distribution, multi-currency support, recurring invoices, and integrated payment processing via Paystack. The platform features a robust security system with password breach detection, suspicious login detection, device and session management, and comprehensive security event logging. It also includes an automated payment reminder system and a detailed invoice history/audit log. The public-facing marketing website has been rebuilt with a unified design system and narrative-driven content.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend
The platform is built on **Django 5.2.9** following a monolithic architecture with a single `invoices` app. It employs a **strict layered architecture** separating models, services, views, and templates, with all business logic residing in service classes. **Gunicorn** serves as the WSGI server, and **WhiteNoise** handles static files.

### Database
**PostgreSQL** is the primary database, utilizing Django's ORM.

### Authentication & Security
**Production-grade authentication system rebuilt on January 31, 2026** with the following features:
- **Sign Up**: User registration with strong password validation (min 8 chars, uppercase, lowercase, numbers, special characters)
- **Login**: Username or email authentication with rate limiting and account lockout protection
- **Email Verification**: Token-based verification with 24-hour expiry and resend functionality
- **Password Reset**: Secure token-based reset with 1-hour expiry
- **Multi-Factor Authentication (MFA)**: TOTP-based 2FA with QR code setup and 10 backup recovery codes
- **Password Breach Detection**: Integration with Have I Been Pwned API (k-anonymity model)
- **Suspicious Login Detection**: Detects new devices, new locations, unusual times, and failed attempt patterns
- **Device/Session Management**: Track and revoke active sessions, trusted device management
- **Workspace Invitations**: Token-based invitations with role assignment and email-based acceptance
- **Security Event Logging**: Comprehensive audit log for all authentication events
- **Rate Limiting**: IP-based rate limiting on login, signup, and password reset endpoints
- **CSRF Protection**: Django's built-in CSRF protection on all forms

Service classes: `AuthService`, `MFAService`, `SessionService`, `SecurityService`, `EmailService`, `InvitationService`

### Payment Processing
**Paystack** is the primary payment gateway, featuring a payment reconciliation service, idempotency keys, webhook handling with signature verification, and atomic transactions.

### Email Services
**SendGrid** is used for transactional emails, including invoice delivery, reminders, and verification.

### PDF Generation
**WeasyPrint** is used for HTML-to-PDF invoice generation, with **ReportLab** as an alternative.

### Frontend
The frontend uses **Tailwind CSS** for styling, with server-side rendered Django templates. It includes a comprehensive design system with reusable components, states, micro-interactions, and accessibility features. The public-facing website features a modern design with a fixed header, mobile menu, and a narrative-driven layout with scroll-triggered animations.

**Authentication UI (Enhanced January 31, 2026)**: All authentication pages feature modern SaaS-grade design with:
- Glass morphism card effects with blur and shadows
- Real-time password strength indicators with visual checklists
- Password visibility toggles
- Staggered animations and micro-interactions
- Full reduced-motion accessibility support
- Semantic HTML with ARIA attributes for screen readers
- MFA code auto-formatting (6-digit TOTP or 8-char recovery codes)
- Form submission loading states
- Responsive layouts for mobile/desktop

Key files: `static/css/auth-enhanced.css`, `static/js/auth-interactions.js`

### Caching
**Django-Redis** provides the caching layer for performance optimization.

### API Architecture
**Django REST Framework** is used for API endpoints, with **drf-spectacular** for OpenAPI schema generation, versioning at `/api/v1/`, and standardized error handling.

### Background Tasks
A **ThreadPoolExecutor-based system** handles asynchronous tasks with retry logic.

### Monitoring & Observability
Structured JSON logging, health check endpoints, performance monitoring middleware, and **Sentry** integration are in place for error tracking.

### Key Design Patterns
- **Strict Layered Architecture**: Models, Services, Views, Templates separation.
- **Service Layer**: Centralizes all business logic in modular service classes (e.g., `InvoiceService`, `PaymentService`).
- **Repository Pattern**: Custom model managers for query encapsulation.
- **Decorator Pattern**: Used for authentication, rate limiting, and monitoring.
- **Middleware Stack**: For security headers, request logging, and MFA enforcement.

### Validation and Error Handling
Centralized validation using domain-specific schemas and standardized error responses with consistent HTTP status codes. Frontend error utilities provide toast notifications and inline field error display.

## External Dependencies

### Payment Gateway
- **Paystack API**: For payment processing.

### Email Service
- **SendGrid API**: For transactional email delivery.

### OAuth Providers
- **Google OAuth**
- **GitHub OAuth**

### CAPTCHA
- **hCaptcha**: For bot protection (optional).

### Database
- **PostgreSQL**: Primary data store.

### Caching
- **Redis**: For session and cache storage.

### Error Monitoring
- **Sentry**: For error tracking and performance monitoring.

### Deployment Platform
- **Replit**: Development environment with hot reload and instant previews.
- **Render**: Production deployment target with autoscaling and health checks (see render.yaml).

## Recent Changes

### February 1, 2026 - Signup Stability & Production Hardening
Comprehensive fixes to make the registration system production-grade:

**Key Improvements:**
- Deterministic UserProfile creation with 50+ fields and safe defaults via atomic transactions
- SendGrid email failures are now non-blocking (signup succeeds even if email API fails)
- HIBP password breach check uses ThreadPoolExecutor with 1-second timeout to prevent slow signups
- Database migrations synced with existing columns using fake-apply strategy
- Updated ProfileService and user_service.py with comprehensive defaults matching model structure

**Technical Details:**
- UserProfile model now includes: paystack_enabled, paystack_subaccount_code, paystack_subaccount_active, stripe_enabled, stripe_account_id, tax_id, tax_name, webhook_secret, and all notification preferences
- All get_or_create operations use explicit defaults dict for deterministic behavior
- Race conditions eliminated with atomic transaction wrappers

**Key Files Modified:**
- `invoices/models.py` - Updated UserProfile with payment gateway fields
- `invoices/auth_services.py` - Atomic profile creation with comprehensive defaults
- `invoices/services/user_service.py` - Safe get_or_create with defaults
- `invoices/migrations/0002_sync_model_with_db.py` - Database sync migration

### February 1, 2026 - Onboarding System Rebuild
Complete rebuild of the onboarding and workspace setup system to production-grade SaaS standards:

**8-Step Onboarding Flow:**
1. **Welcome**: Choose usage type (personal, small business, freelancer, agency, enterprise)
2. **Business Profile**: Company details, address, industry, size
3. **Branding**: Logo upload, color customization, tagline
4. **Tax & Compliance**: VAT/tax registration, tax ID, regional tax settings
5. **Payments**: Bank transfer details, card payments, mobile money (regional)
6. **Data Import**: Import customers, products, invoices from other platforms
7. **Templates**: Select and customize invoice template style
8. **Team**: Send team member invitations with role assignments

**Smart Features:**
- Region-based contextual defaults (Nigeria, US, UK, EU, South Africa, Ghana, Kenya)
- Automatic currency, locale, and tax configuration based on country
- Business-type suggestions for invoice numbering formats
- Progress tracking with completion percentage
- Time-to-first-invoice tracking for analytics
- Skip-able steps with smart defaults

**Technical Implementation:**
- `OnboardingService` class handles all business logic (service layer pattern)
- Extended `UserProfile` model with 38+ new fields for comprehensive onboarding data
- 9 responsive, accessible templates with stepper UI and mobile-first design
- WCAG accessibility compliance with proper ARIA labels and focus management
- CSRF protection on all forms, file upload validation (5MB limit, image types only)

**Key Files:**
- `invoices/services/onboarding_service.py` - Business logic
- `invoices/views/onboarding_views.py` - Thin controller views
- `invoices/templates/pages/onboarding/` - 9 template files
- `invoices/migrations/0004_onboarding_extended_fields.py` - Model changes

**Routes:**
- `/onboarding/` - Router (redirects to current step)
- `/onboarding/welcome/` through `/onboarding/team/` - Individual steps
- `/onboarding/complete/` - Completion celebration page
- `/api/onboarding/status/` - AJAX status endpoint