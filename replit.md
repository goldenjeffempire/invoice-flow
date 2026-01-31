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
Django's built-in authentication is extended with **Multi-Factor Authentication (MFA)** using TOTP, email verification, and **OAuth integration** for Google and GitHub. Custom password validators include breach detection, and sensitive data uses field-level encryption with Fernet (AES-256). Security features encompass suspicious login detection, device and session management, and a comprehensive security event logging system. Workspace invitations with role assignment are also supported.

### Payment Processing
**Paystack** is the primary payment gateway, featuring a payment reconciliation service, idempotency keys, webhook handling with signature verification, and atomic transactions.

### Email Services
**SendGrid** is used for transactional emails, including invoice delivery, reminders, and verification.

### PDF Generation
**WeasyPrint** is used for HTML-to-PDF invoice generation, with **ReportLab** as an alternative.

### Frontend
The frontend uses **Tailwind CSS** for styling, with server-side rendered Django templates. It includes a comprehensive design system with reusable components, states, micro-interactions, and accessibility features. The public-facing website features a modern design with a fixed header, mobile menu, and a narrative-driven layout with scroll-triggered animations.

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
- **Render**: Primary deployment target with autoscaling and health checks.