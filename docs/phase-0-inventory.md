# Phase 0 — Inventory & Scope Map

## Project layout snapshot
- **Backend framework:** Django project configuration lives under `invoiceflow/`, including settings, middleware, and REST configuration.【F:invoiceflow/settings.py†L1-L430】
- **Core domain app:** `invoices/` contains authentication services, payment flows, email/PDF services, and business models.【F:invoices/auth_services.py†L1-L200】【F:invoices/paystack_views.py†L1-L200】【F:invoices/sendgrid_service.py†L1-L200】【F:invoices/models.py†L120-L207】
- **API surface:** DRF router exposes invoice and template viewsets under `/api/` endpoints.【F:invoices/api/urls.py†L1-L7】
- **Templates & static assets:** Templates are served from the `templates/` directory and static assets from `static/`, as configured in Django settings.【F:invoiceflow/settings.py†L300-L341】
- **Runtime config:** Replit-specific configuration files are no longer present in the repo after cleanup.

## Feature map (high-level)
- **Authentication & account security:** MFA enforcement and login protection are implemented in middleware and auth services.【F:invoiceflow/mfa_middleware.py†L1-L111】【F:invoices/auth_services.py†L1-L200】
- **Payments:** Paystack initialization, callbacks, and webhooks are handled in `paystack_views.py` with supporting service logic in `paystack_service.py`.【F:invoices/paystack_views.py†L1-L200】【F:invoices/paystack_service.py†L260-L360】
- **Payment providers:** User profiles store Stripe and Paystack configuration fields, indicating multi-provider support at the data layer.【F:invoices/models.py†L139-L158】
- **Email + PDF workflows:** SendGrid service uses HTML templates and WeasyPrint for PDF rendering/attachments.【F:invoices/sendgrid_service.py†L1-L200】
- **OAuth integrations:** Google and GitHub OAuth flows are implemented in dedicated view modules.【F:invoices/oauth_views.py†L1-L120】【F:invoices/github_oauth_views.py†L1-L120】

## Entry points & configuration
- **Django settings:** Security headers, REST framework defaults, and middleware stack are centralized in `invoiceflow/settings.py`.【F:invoiceflow/settings.py†L1-L430】
- **REST framework defaults:** Session-based authentication, throttling, and exception handling are configured globally in settings.【F:invoiceflow/settings.py†L373-L404】

## Next inventory steps
1. Enumerate all templates and static assets for UX/UI modernization scope.
2. Catalog all endpoints and views (web + API) for functional coverage.
3. Map all background/async tasks and scheduled jobs for reliability review.
