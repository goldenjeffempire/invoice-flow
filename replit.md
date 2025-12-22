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

### Authentication & Security Enforcement (December 22, 2025)
#### Session Rotation on Login
- **Session Fixation Prevention**: Invalidates all old sessions when user logs in
  - Prevents session hijacking and account takeover
  - Implemented in AuthenticationService.login_user()
  - Deletes previous UserSession records before creating new session
  
#### Email Verification Enforcement
- **Enforced on Payment Operations**: All payment initialization requires verified email
  - initialize_payment() now calls require_verified_email(user)
  - Returns 403 error with "EMAIL_NOT_VERIFIED" code if not verified
  - Prevents unverified accounts from initiating payments
  
#### MFA Enforcement for Sensitive Operations
- **Mandatory MFA for Payments**: Payment operations now require MFA completion
  - initialize_payment() checks request.session["mfa_verified"]
  - Returns 403 error with "MFA_NOT_VERIFIED" code if not completed
  - MFA enforcement middleware handles routing to MFA verification page
  - Added require_mfa_verified() function for sensitive operations
  
#### Identity Assurance on High-Value Payments
- **KYC Threshold**: Payments >100,000 require identity verification
  - initialize_payment() checks UserIdentityVerification.is_verified()
  - Returns 403 error with "IDENTITY_NOT_VERIFIED" if not verified
  - Implements defense-in-depth against fraud
  
#### Enhanced Error Responses
- **Structured Error Codes**: Payment operations return specific error codes
  - EMAIL_NOT_VERIFIED: User's email not verified
  - MFA_NOT_VERIFIED: MFA verification not completed
  - IDENTITY_NOT_VERIFIED: Identity verification not completed for high-value payments
  - Enables client-side UI to guide users to required verification steps
  
#### Service Layer Enhancements
- **auth_services.py**: 
  - Added MFANotVerifiedError exception class
  - Added require_mfa_verified() function
  - Enhanced login_user() to track email verification status in response
  - Session rotation via UserSession.objects.filter(user=user).delete()
  
- **mfa_middleware.py**: 
  - Added auth endpoints to exempt URLs (verify_email, verification_sent, resend_verification)
  - Ensures users can complete email verification before accessing dashboard
  
#### Security Flow Summary
1. **Login**: Sessions rotated, email & MFA status checked
2. **Email Verification**: Enforced before payment operations
3. **MFA**: Mandatory completion before sensitive operations
4. **Identity Verification**: Required for high-value payments (>100,000)
5. **Payment**: All three checks passed before processing

### Payment System Comprehensive Hardening (December 22, 2025)
#### Idempotency & Prevention of Double Charges
- **IdempotencyKey Model**: Prevents duplicate payment processing with 24-hour cache
  - Request hash tracking and integrity verification
  - HTTP status code caching for proper error replay
  - Automatic expiration of old keys
- **initialize_payment View**: Required idempotency key + integrated service layer
  - Proper error responses for missing idempotency keys
  - Cached response replay for retry scenarios

#### Webhook Security Hardening
- **paystack_webhook Validation**: Comprehensive checks preventing fraud
  - JSON parsing error handling with detailed logging
  - Replay attack prevention via ProcessedWebhook model
  - Amount & currency validation to prevent tampering
  - Server-to-server Paystack verification (not client-side data)
  - Atomic transactions preventing race conditions

#### Payment Reconciliation Service
- **PaymentReconciliation Model**: State machine for payment state consistency
  - Status tracking: PENDING → IN_PROGRESS → VERIFIED/MISMATCH/RECOVERED/FAILED
  - Amount, currency, and status mismatch detection
  - Retry tracking with automatic error logging
- **PaymentReconciliationService**: Verifies payments against Paystack
  - Detects lost/interrupted payments
  - Triggers automatic recovery for mismatches
  - Prevents double-charging and fraud
- **reconcile_payments Management Command**: Automatic reconciliation
  - Configurable time window (default: 7 days)
  - Status filtering (pending/failed/all)
  - Detailed reporting of verified/mismatched/failed payments

#### Automatic Recovery for Failed Payments
- **PaymentRecovery Model**: Tracks recovery attempts with retry logic
  - Strategy selection: IMMEDIATE_RETRY, SCHEDULED_RETRY, WEBHOOK_RETRY, MANUAL_VERIFICATION
  - Attempt tracking (max 3 attempts per payment)
  - Error reason and code logging
- **ReconciliationService.process_pending_recoveries()**: Automatic retry processing
  - Processes scheduled retries (30-second delay)
  - Re-verifies with Paystack
  - Updates Payment status on successful recovery
  - Creates reconciliation recovery records

#### Identity Verification (KYC) for Payout Enablement
- **UserIdentityVerification Model**: Strong identity verification before payouts
  - Status tracking: UNVERIFIED → PENDING → VERIFIED/REJECTED/EXPIRED
  - Document types: PASSPORT, NATIONAL_ID, DRIVERS_LICENSE, BVN
  - Personal info: name, DOB, phone, country
  - Document info: number, expiry, verification details
  - Expiration handling (annual renewal)
- **IdentityVerificationService**: KYC via Paystack
  - verify_identity() method with BVN verification
  - can_process_payout() enforcement
  - Prevents payout operations without verified identity
- **require_identity_verification Decorator**: Enforces KYC on payout views
  - Redirects unverified users to identity verification page
  - Blocks payout operations with warning messages

#### Service Layer Architecture
- **paystack_reconciliation_service.py** (new): Core services for reconciliation and identity
  - PaymentReconciliationService: Reconciliation, state machine, recovery triggering
  - IdentityVerificationService: KYC and payout eligibility checks
  - Factory functions: get_reconciliation_service(), get_identity_service()
- **paystack_service.py Enhancements**:
  - Added verify_payment() method (alias for verify_transaction)
  - Added verify_bvn() method for BVN/KYC verification
- **payment_settings_views.py Enhancements**:
  - Import UserIdentityVerification model and identity service
  - Added require_identity_verification decorator for payout views
  - Updated view comments to document KYC requirement

#### Database Migrations
- **Migration 0021**: Added PaymentReconciliation, PaymentRecovery, UserIdentityVerification models
  - Proper indexes for status queries and user filtering
  - Proper foreign keys with CASCADE delete for referential integrity

#### Security Enhancements Summary
- ✅ Prevents double charges (idempotency keys)
- ✅ Prevents payment hijacking (webhook security)
- ✅ Detects lost/interrupted payments (reconciliation)
- ✅ Automatic recovery with retry logic (payment recovery)
- ✅ Strong identity verification before payouts (KYC enforcement)
- ✅ Complete payment lifecycle tracking (state machine)
- ✅ Audit trail logging for fraud detection

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

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid (Replit Integration)
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js
