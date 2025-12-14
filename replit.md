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

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack
- **Error Tracking**: Sentry
- **Frontend Tooling**: Tailwind CSS, PostCSS, Node.js