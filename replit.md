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

### Invoice Creator v2.0 - Complete Modern Rebuild (December 15, 2025)
- Built entirely from scratch with advanced modern UX
- New template: templates/invoices/create_invoice.html
- New CSS: static/css/invoice-creator-modern.css (comprehensive styling)
- New JS: static/js/invoice-creator-modern.js (full functionality)
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

### Payment Settings Page Modernization (December 15, 2025)
- Complete UI overhaul with modern card-based design
- Enhanced bank account verification workflow
- Payment methods display (Cards, Bank Transfer, USSD, Mobile Money)
- Toggle switch for enabling/disabling direct payments
- Status badges showing active/inactive state
- Step-by-step "How It Works" guide
- Improved error/success messaging with icons

### Payment System Audit (December 15, 2025)
- Verified security measures:
  - Rate limiting on payment initiation (10/min)
  - HMAC-SHA512 webhook signature verification
  - Amount and currency validation on callbacks
  - Invoice ID verification in payment metadata
- Paystack subaccount support for direct merchant payouts
- Comprehensive logging for payment events
- Required secrets: PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY (not yet configured)

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
- Removed unused CSS: static/css/create-invoice.css (replaced by invoice-creator-modern.css)
- Security verified: Production guards enforce secure SECRET_KEY and ENCRYPTION_SALT
- Services verified: SendGrid email with Replit fallback, Paystack payments with subaccount support
- Analytics: Database-level SQL aggregations with cache invalidation
- All core pages verified: Landing, Signup, Login pages rendering correctly

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js