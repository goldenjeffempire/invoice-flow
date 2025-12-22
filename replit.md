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
The backend is built with Django 5.2.9, Python 3.12.11, and PostgreSQL. The frontend uses HTML/CSS with JavaScript, styled using Tailwind CSS. Email services are integrated via SendGrid, and PDF generation uses WeasyPrint. Security measures include CSRF, XSS, SQL injection prevention, modern security headers, rate limiting, secure session management, and TOTP MFA. Performance is optimized with Gunicorn, database connection pooling, static file compression, and lazy loading. The system also includes dedicated health check endpoints, SEO features, and PWA support with service workers and a manifest.

### Feature Specifications
Core features include comprehensive invoice management (create, edit, track, export, recurring), multi-channel sharing (email, WhatsApp), payment tracking, customizable invoice templates, an analytics dashboard, secure user authentication, and contact management.

### System Design Choices
The architecture incorporates micro-interactions, robust error handling with user-friendly notifications, and extensive accessibility features (ARIA attributes, keyboard navigation, focus indicators). Deployment is configured for production-ready Gunicorn on Render with autoscale and SSL. Logging is structured JSON, and the platform aims for GDPR compliance. Enterprise-grade authentication includes real-time password strength validation, MFA/2FA with recovery codes, and social login integrations (Google, GitHub). Payment processing is integrated via Paystack, supporting multiple currencies with secure webhook verification.

## Recent Changes (December 2025)

### Payment System Hardening & Idempotency (December 22, 2025)
- **Idempotency Key Model**: Added IdempotencyKey model to prevent duplicate payment processing
  - Caches responses for 24 hours using unique idempotency keys
  - Request hash tracking for integrity verification
  - HTTP status code caching for proper error handling
  - Automatic expiration of old keys
- **Enhanced Webhook Security**: Hardened paystack_webhook with comprehensive validation
  - Improved error logging for audit trails and debugging
  - JSON parsing error handling
  - Replay attack prevention via ProcessedWebhook model
  - Amount validation to prevent tampering
  - Currency validation with mismatch detection
  - Server-to-server Paystack verification (not relying on client-side data)
  - Atomic transaction handling to prevent race conditions
- **Idempotent Payment Initialization**: Updated initialize_payment view
  - Required idempotency key parameter to prevent duplicate charges
  - Integration with IdempotencyKey service layer
  - Proper error responses for missing idempotency keys
  - Cached response replay for retry scenarios
- **MFA & Email Verification Enforcement**: Views now require both:
  - require_verified_email(user) - enforces email verification
  - require_mfa(user) - enforces MFA completion before payment
  - Protects payment endpoints from unverified users

### Security Audit & Hardening (December 18, 2025)
- **Webhook Replay Protection**: Added ProcessedWebhook model to prevent payment webhook replay attacks
  - Tracks event_id, payload_hash, provider, and processing timestamp
  - Duplicate detection before processing webhooks
  - Automatic cleanup of old records (30+ days)
  - IP address logging for audit trails
- **API Security**: DRF throttling configured (100/hour anon, 1000/hour authenticated)
- **Database Migration**: Migration 0018 added for ProcessedWebhook model
- **Configuration Validation**: Enhanced startup checks for required environment variables
- **Code Quality**: Fixed LSP type annotation issues in paystack_service.py

### Comprehensive Platform Audit & Optimization (December 18, 2025)
- **Database**: PostgreSQL provisioned, all 18 migrations applied successfully
- **Cache**: Django database cache tables created and verified working
- **Health Checks**: All 4 endpoints verified working (/health/, /health/ready/, /health/live/, /health/detailed/)
- **Type Safety**: Fixed LSP diagnostics in invoices/api/views.py (proper type casting for validated_data)
- **Dependencies**: All Python packages installed and verified
- **Configuration**: Core environment variables set (SECRET_KEY, ENCRYPTION_SALT, DATABASE_URL)
- **Server Status**: Gunicorn running with gthread workers, 120s timeout
- **Security**: Production security guards in place (HSTS, CSRF, secure cookies when PRODUCTION=true)
- **Email**: SendGrid integration code complete - requires SENDGRID_API_KEY or Replit connector
- **Payments**: Paystack integration code complete - requires PAYSTACK_SECRET_KEY to enable
- **Remaining**: To fully enable payments and email, add the respective API keys in Secrets

### Public Invoice Payment System - Direct Client Payments (December 18, 2025)
- **Public Payment Page**: New `/pay/<invoice_id>/` endpoint for unauthenticated clients
- **Templates**: templates/invoices/public_invoice.html with professional dark-mode UI
- **Features**:
  - Clean, professional invoice display without login requirement
  - Real-time payment status badges (Paid/Unpaid/Overdue)
  - Bank transfer details section
  - Secure "Pay Now" button with Paystack integration
  - Responsive design for all devices
  - Invoice preview with all details (items, dates, totals, notes)
- **New Views**: public_invoice_view, public_initiate_payment, public_payment_callback
- **URLs**: /pay/<invoice_id>/, /pay/<invoice_id>/checkout/, /pay/<invoice_id>/callback/
- **Security Enhancements**:
  - Webhook signature verification (HMAC-SHA512)
  - Payment reference validation to prevent replay attacks
  - Amount and currency verification on callbacks
  - Invoice ownership validation (invoice.user check)
  - Explicit reference matching between payment initiation and webhook events

### Paystack Security Hardening (December 18, 2025)
- Enhanced webhook handler with comprehensive payment validation
- Added reference mismatch detection (prevents payment hijacking)
- Requires invoice.payment_reference exists before webhook processing
- Amount tolerance validation (0.01 currency units)
- Currency validation with logging of mismatches
- Structured error responses for invalid webhooks
- Rate limiting on payment initiation (10/min per user)
- Payload validation before processing
- Comprehensive logging for audit trails

### API Security Improvement (December 18, 2025)
- Changed InvoiceViewSet base queryset from Invoice.objects.all() to Invoice.objects.none()
- Ensures DRF always calls get_queryset() which filters by authenticated user
- Eliminates risk of incomplete queryset filtering
- Added proper type hints to API methods (Optional[int], Optional[str])
- Fixed return type hint for get_serializer_class()

### Invoice Detail UI Enhancement (December 18, 2025)
- Added "Client Payment Link" section in invoice detail page
- Copy-to-clipboard functionality for payment link
- Shows full public URL for easy client sharing
- Green visual indicator for payment link section
- Integrates with existing sharing methods

### Invoice Creator v2.0 - Complete Modern Rebuild (December 15, 2025)
- Built entirely from scratch with advanced modern UX
- New template: templates/invoices/create_invoice.html
- New CSS: static/css/invoice-creator-v3.css (comprehensive styling)
- New JS: static/js/invoice-creator-v3.js (full functionality)
- Features:
  - Collapsible form sections with gradient icons
  - Real-time invoice preview modal
  - Sticky sidebar with live calculations
  - Desktop: inline editable table rows
  - Mobile: card-based item layout
  - Drag-and-drop reordering
  - Auto-save to localStorage with visual indicators
  - Keyboard shortcuts (Enter, Tab navigation)
  - Full ARIA accessibility
  - Smooth animations and transitions

### Comprehensive Payment System Enhancement (December 15, 2025)
- **Payment Models**: Created Payment, PaymentRecipient, PaymentPayout, PaymentCard, PaymentSettings models with proper user ownership fields and database indexes
- **Payment Settings Views**: Implemented payment_settings_dashboard, payment_preferences, setup_subaccount, manage_recipients, saved_cards, payment_history, payout_history views
- **Security Features**:
  - Rate limiting on all POST endpoints (5-10 requests/minute using django-ratelimit)
  - Server-side bank account verification via Paystack API
  - CSRF protection on all forms
  - User ownership scoping on all payment queries
- **PaystackTransferService**: Enhanced with transfer/payout capabilities including create_transfer_recipient, initiate_transfer, verify_transfer, list_transfers, verify_account_number, get_balance
- **Direct Payments**: Paystack subaccount support with percentage_charge=0 for direct user payouts
- **Management Command**: test_payments command for verifying payment system functionality
- **Templates**: 7+ payment management templates with modern UI
- **URLs**: Complete routing for payment settings endpoints

### Payment Settings Page Modernization (December 15, 2025)
- Complete UI overhaul with modern card-based design
- Enhanced bank account verification workflow
- Payment methods display (Cards, Bank Transfer, USSD, Mobile Money)
- Toggle switch for enabling/disabling direct payments
- Status badges showing active/inactive state
- Step-by-step "How It Works" guide
- Improved error/success messaging with icons

### Email Service Consolidation (December 15, 2025)
- Unified all email functionality under SendGridEmailService
- Added send_verification_email method to SendGridEmailService
- Migrated authentication emails (signup verification, password reset) to SendGrid
- Removed redundant email_service.py (was using Django's send_mail)
- All emails now route through single SendGrid service with Replit integration support

### Dashboard Footer Enhancement
- Modernized with cleaner, more professional design
- Improved responsiveness across all device sizes

### Landing Page Optimization
- Removed redundant CTA section to streamline conversion flow
- Now has single focused call-to-action at end of page

### Platform Cleanup
- Cleaned up requirements.txt (removed massive duplicates, 265 to 60 lines)
- Removed unnecessary flow-venv/ directory
- Removed duplicate email_service.py after SendGrid consolidation

### End-to-End Platform Audit (December 15, 2025)
- Database: All 16 migrations applied successfully, PostgreSQL healthy
- Static assets: Created missing favicon-32x32.png, favicon-16x16.png, apple-touch-icon.png, og-image.jpg
- Removed unused CSS: static/css/create-invoice.css (replaced by invoice-creator-v3.css)
- Security verified: Production guards enforce secure SECRET_KEY and ENCRYPTION_SALT
- Services verified: SendGrid email with Replit fallback, Paystack payments with subaccount support
- Analytics: Database-level SQL aggregations with cache invalidation
- All core pages verified: Landing, Signup, Login pages rendering correctly

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid (Replit Integration)
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js
