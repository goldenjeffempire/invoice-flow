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

### Email Service Consolidation (December 15, 2025)
- Unified all email functionality under SendGridEmailService
- Added send_verification_email method to SendGridEmailService
- Migrated authentication emails (signup verification, password reset) to SendGrid
- Removed redundant email_service.py (was using Django's send_mail)
- All emails now route through single SendGrid service with Replit integration support

### Create Invoice Page Complete Rebuild (December 15, 2025)
- Completely rebuilt from scratch with professional modern design
- Two-column layout: main form + sticky sidebar with invoice summary
- External CSS stylesheet (static/css/create-invoice.css) for maintainability
- Mobile-first responsive design with breakpoints at 480px, 768px, 1024px
- Desktop: table-based line items; Mobile: card-based layout
- Real-time calculations with currency symbol updates across all inputs
- Drag-and-drop line item reordering with visual feedback
- Keyboard shortcuts: Enter to add new item, Ctrl+D to duplicate, Tab navigation
- Auto-save with debounced localStorage persistence (7-day expiry)
- Inline form validation with ARIA live regions for accessibility
- Clean CSS custom properties for consistent theming
- Reduced motion support for accessibility compliance

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

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js