# InvoiceFlow - Production-Grade Full-Stack Platform

## Overview
InvoiceFlow is a production-grade professional invoicing platform designed to streamline financial operations for freelancers, agencies, small teams, and service-based businesses. It offers a comprehensive suite of features including PDF generation, multi-channel invoice sharing (email/WhatsApp), payment tracking, recurring invoices, customizable templates, and an analytics dashboard for financial reporting. The platform emphasizes enterprise-grade security and a modern, intuitive user experience. The business vision is to provide a robust, scalable solution that saves users time, accelerates payments, and drives revenue growth.

## User Preferences
- Preserve Django backend while rebuilding frontend
- Execute phases sequentially with artifact reporting
- Modern, professional UI/UX aligned with component showcase
- Comprehensive documentation at each phase

## System Architecture
### UI/UX Decisions
The platform features a modern, professional UI/UX with a focus on clean light themes, professional business aesthetics, and responsive design. Key design elements include:
- **Design System Foundation**: Professional light theme design tokens, indigo primary colors (#4f46e5), emerald accents (#10b981), clean white backgrounds, subtle gray accents, modern shadow system, and an 8pt grid spacing scale.
- **Typography**: Modern Inter font family.
- **Animations**: Advanced animation system with shimmer, bounce, slide-in, fade-in, wiggle effects, scroll reveals, parallax, and confetti for user feedback. Supports `prefers-reduced-motion`.
- **Component Library**: Modular CSS for buttons, cards, forms, navigation, modals, skeleton loaders, and toast notifications.
- **Responsive Design**: Comprehensive mobile-first approach with CSS breakpoints, including mobile navigation, collapsible dashboard sidebar, and responsive tables.
- **Interactive Elements**: Hover effects, 3D tilt interactions, animated counters, floating labels, and live form validation.

### Technical Implementations
- **Backend**: Django 5.2.9 with Python 3.12.11 and PostgreSQL.
- **Frontend**: Primarily HTML/CSS with JavaScript for interactive elements. Tailwind CSS for utility-first styling.
- **Email Service**: SendGrid integration.
- **PDF Generation**: WeasyPrint.
- **Security**: Comprehensive measures including CSRF protection, XSS prevention, SQL injection prevention, modern security headers (CSP, HSTS), rate limiting, honeypot spam protection, secure session management, and Two-Factor Authentication (TOTP MFA).
- **Performance**: Gunicorn with multiple workers, database connection pooling, static file compression (Brotli), asset hashing, and lazy loading.
- **Health Checks**: Dedicated `/health/`, `/health/ready/`, and `/health/live/` endpoints for monitoring.
- **SEO**: robots.txt, sitemap.xml, Open Graph, Twitter Card meta tags, and JSON-LD structured data.

### Feature Specifications
- **Invoice Management**: Create, edit, delete, track, and export invoices (CSV, PDF), including recurring invoices.
- **Multi-channel Sharing**: Share invoices via email and WhatsApp.
- **Payment Tracking**: Record and track invoice payments.
- **Customization**: Customizable invoice templates with branding options.
- **Analytics Dashboard**: Visualizations for revenue, payment status, and other key metrics.
- **User Authentication**: Secure login, signup, and password reset.
- **Contact Management**: Contact forms with admin panel management.

### System Design Choices
- **Micro-interactions**: Subtle animations and feedback for user actions.
- **Error Handling**: Robust error handling with user-friendly toast notifications and validation.
- **Accessibility**: ARIA attributes, labeled form inputs, descriptive alt texts, keyboard navigation, and focus indicators.
- **Deployment**: Production-ready Gunicorn configuration, integrated with Render for autoscale deployments, including SSL.
- **Logging**: Structured JSON logging with request context propagation.
- **Compliance**: GDPR compliance with cookie consent and comprehensive Privacy Policy/Terms of Service.

## Recent Enhancements (December 2025)

### Complete Light Theme Redesign (December 2025)
All authenticated pages have been completely rebuilt with a modern, premium light-only design system:

**Core Design System:**
- `static/css/dashboard-light.css` - Comprehensive light theme stylesheet with 2000+ lines
- Modern design tokens: indigo primary (#6366f1), emerald success (#10b981), amber warning
- Clean white backgrounds with subtle shadows and gradients
- Consistent 8pt grid spacing, Inter font family

**Rebuilt Pages:**
- **Dashboard**: Modern stat cards, revenue charts, recent invoices table, activity feed
- **Invoice List**: Card-based layout with filters, search, bulk actions
- **Create/Edit Invoice**: Modern form design with line item management
- **Invoice Detail**: Professional invoice preview with action buttons
- **Analytics**: Charts, metrics cards, revenue visualizations
- **Settings Pages**: Profile, Business, Security, Notifications, Billing - all with consistent light theme
- **Templates**: Card-based template gallery with preview
- **Recurring**: Recurring invoice management with status badges

**Shared Components:**
- `templates/components/sidebar-light.html` - Reusable navigation sidebar with user info and logout
- All authenticated pages use the shared sidebar component for consistency

**Key Features:**
- Fully responsive design (mobile, tablet, desktop)
- Glassmorphism effects with subtle backdrop blur
- Smooth hover transitions and micro-interactions
- No dark mode elements - pure light theme throughout
- Premium SaaS-style aesthetics

### Comprehensive Responsive Design System (December 2025)
A unified mobile-first responsive framework for both landing pages and authenticated dashboard:

**Core CSS (`static/css/responsive-system.css` - 1120 lines):**
- Mobile-first breakpoints: xs (0), sm (480px), md (768px), lg (1024px), xl (1280px), 2xl (1536px)
- CSS custom properties for sidebar widths, spacing, transitions, z-index layers
- Responsive container system with adaptive padding
- Dashboard layout with collapsible sidebar (full, collapsed, icon-only, off-canvas states)
- Landing page navigation with scroll behavior and mobile slide menu
- Responsive grid utilities (r-grid-1 to r-grid-4)
- Print styles and accessibility features (focus rings, reduced motion, touch targets)

**JavaScript (`static/js/responsive-nav.js`):**
- Sidebar toggle for mobile (off-canvas) and desktop (collapse)
- Mobile navigation toggle with ARIA attributes
- Scroll behavior for navbar (adds `is-scrolled` class)
- Keyboard navigation (Escape to close menus)
- Focus trapping for accessibility compliance
- localStorage persistence for sidebar collapsed state
- Resize handler to close mobile menus on larger screens

**Template Integration:**
- `templates/base/layout-light.html` - Landing pages use `nav-landing` and `mobile-nav` classes
- `templates/components/sidebar-light.html` - Dashboard sidebar with `dashboard-sidebar` class
- All dashboard templates use `dashboard-layout` and `dashboard-main` classes

**Accessibility:**
- Proper ARIA attributes (aria-expanded, aria-hidden, aria-label)
- Focus management and focus trapping
- Keyboard navigation support
- Screen reader compatibility

## Recent Enhancements (December 2025)

### Professional Navbar & Hero Redesign
- **New Navbar**: `static/css/navbar-hero.css` - Modern fixed navbar with glass blur effect
  - Sticky header with scroll detection
  - Responsive mobile menu with overlay and focus trap
  - Smooth hamburger animation on mobile
  - Proper ARIA attributes for accessibility
- **New Hero Section**: Split-layout design with gradient backgrounds
  - Animated badge, gradient text titles, floating cards
  - Dashboard mockup with browser chrome styling
  - Stats bar with key metrics
  - Full responsive design (desktop, tablet, mobile)
- **Template Updates**: `templates/base/layout.html`, `templates/pages/home.html`

### Modern JavaScript Architecture
- **ES6+ Modules**: Modular architecture with separate utility modules
  - `static/js/modules/utils.js` - Utility functions (debounce, throttle, formatters)
  - `static/js/modules/toast.js` - Modern toast notification system
  - `static/js/modules/forms.js` - Real-time form validation with accessibility
  - `static/js/modules/command-palette.js` - Quick navigation (Ctrl+K)

### Progressive Web App (PWA) Support
- **Service Worker**: `static/js/sw.js` with caching strategies
- **Manifest**: `static/manifest.json` for installable app experience
- **Offline Page**: `templates/pages/offline.html` fallback

### Enhanced CSS Features
- **Modern CSS**: `static/css/enhancements-v2.css` with container queries, `:has()` selector
- **Skeleton Loading**: Built-in loading state styles
- **Improved Animations**: Spring-based easing, reduced motion support
- **Toast System**: Multi-position, accessible notifications

### Command Palette
- Trigger with `Ctrl+K` or `Cmd+K`
- Quick navigation to all major sections
- Keyboard-driven interface with arrow key navigation

### OAuth & Payment Integrations (December 2025)
The platform now includes full OAuth social login and payment processing integrations:

**Social Login (OAuth 2.0):**
- **Google OAuth**: Full implementation in `invoices/oauth_views.py`
- **GitHub OAuth**: Full implementation in `invoices/github_oauth_views.py`
- Both integrate with the `SocialAccount` model for linking accounts
- Login/signup templates updated with working social login buttons

**Payment Processing (Paystack):**
- **Payment Service**: `invoices/paystack_service.py` - Full Paystack API integration
- **Payment Views**: `invoices/paystack_views.py` - Invoice payment initiation, callbacks, webhooks
- Supports NGN, USD, GHS, ZAR, KES currencies
- Webhook signature verification for secure payment notifications

**Environment Configuration:**
- `PRODUCTION=true` (production) / `PRODUCTION=false` (development)
- Production mode enables: SSL redirect, HSTS, secure cookies, strict security headers

**Required Secrets (for full functionality):**
- `SENDGRID_API_KEY` - Email functionality
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` - Google login
- `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET` - GitHub login
- `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` - Payment processing

### Enterprise Authentication System Rebuild (December 2025)
The authentication system has been completely rebuilt with a modern, enterprise-ready design:

**Design Features:**
- Split-screen layout with animated branding panel and glassmorphism form card
- Dark theme with gradient orbs background animation
- Social login placeholders (Google, GitHub) with "Coming Soon" badges
- Professional typography with gradient text effects
- Responsive design with mobile-first approach

**Security & Validation:**
- Real-time password strength meter (5-point criteria: length, lowercase, uppercase, number, special)
- Minimum 12-character password requirement enforced client-side
- Password confirmation matching validation
- CSRF protection on all forms
- MFA/2FA support with TOTP (authenticator apps)
- Recovery codes with download/copy/print functionality

**Accessibility (WCAG Compliance):**
- Semantic HTML structure with proper ARIA attributes
- Screen reader support with live regions for error messages
- Keyboard navigation with visible focus states
- `prefers-reduced-motion` media query for animation control
- Color contrast ratios meeting WCAG AA standards

**Templates:**
- `templates/auth/login.html` - Modern login with split-screen design
- `templates/auth/signup.html` - Enhanced signup with password strength
- `templates/auth/mfa_verify.html` - MFA code entry with recovery option
- `templates/auth/mfa_setup.html` - Step-by-step MFA setup with QR code
- `templates/auth/mfa_setup_complete.html` - Recovery codes display

**CSS & JavaScript:**
- `static/css/auth.css` - Comprehensive auth styling (1600+ lines)
- `static/js/modules/auth-validation.js` - Real-time form validation

## Production Configuration (December 2025)

### Management Commands
- `python manage.py test_email --check-only` - Validate SendGrid configuration
- `python manage.py test_email --to=email@example.com` - Send test email
- `python manage.py test_payments` - Validate Paystack API connectivity
- `python manage.py test_sentry` - Check Sentry error monitoring
- `python manage.py health_check` - Comprehensive system health check

### Environment Variables (Required)
- `SECRET_KEY` - Django secret key (production-safe)
- `DATABASE_URL` - PostgreSQL connection URL
- `SENDGRID_API_KEY` - SendGrid API key for emails
- `SENDGRID_FROM_EMAIL` - Verified sender email
- `PAYSTACK_SECRET_KEY` - Paystack secret key
- `PAYSTACK_PUBLIC_KEY` - Paystack public key
- `SENTRY_DSN` - Sentry error tracking DSN
- `ENCRYPTION_SALT` - Field-level encryption salt
- `PRODUCTION=true` - Enable production mode

### Deployment
- **Target**: Autoscale deployment on Replit
- **Build**: `python manage.py collectstatic --noinput`
- **Run**: `gunicorn --bind=0.0.0.0:5000 --workers=2 --threads=4 --worker-class=gthread --timeout=120 invoiceflow.wsgi:application`

## External Dependencies
- **Database**: PostgreSQL
- **Web Server**: Gunicorn
- **Static Files Serving**: WhiteNoise
- **Email Service**: SendGrid (configured and tested)
- **PDF Generation**: WeasyPrint
- **Payment Processing**: Paystack (configured and tested)
- **Error Tracking**: Sentry (configured)
- **Frontend Frameworks/Libraries**: Tailwind CSS, PostCSS, Node.js (for asset compilation)

## File Structure (Key Additions)
```
static/
├── js/
│   ├── modules/
│   │   ├── utils.js          # ES6+ utilities
│   │   ├── toast.js          # Toast notifications
│   │   ├── forms.js          # Form validation
│   │   ├── command-palette.js # Quick navigation
│   │   └── auth-validation.js # Auth form validation & password strength
│   ├── sw.js                 # Service worker
│   ├── app.js                # Main application
│   └── landing.js            # Landing page interactions
├── css/
│   ├── auth.css              # Enterprise auth styling (1600+ lines)
│   ├── enhancements-v2.css   # Modern CSS features
│   └── ...                   # Existing CSS files
└── manifest.json             # PWA manifest

templates/
├── auth/
│   ├── login.html            # Modern split-screen login
│   ├── signup.html           # Enhanced signup with password strength
│   ├── mfa_verify.html       # MFA verification with recovery
│   ├── mfa_setup.html        # MFA setup wizard
│   └── mfa_setup_complete.html # Recovery codes display
```