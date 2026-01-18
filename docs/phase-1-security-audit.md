# Phase 1 — Security & Risk Review (Initial)

## Existing security controls (observed)
- **Hardened headers & cookies:** HSTS, secure cookies, and referrer/frame protections are configured in settings.【F:invoiceflow/settings.py†L95-L123】【F:invoiceflow/settings.py†L344-L352】
- **Password policy:** Password validators enforce length, complexity, and breached-password checks.【F:invoiceflow/settings.py†L318-L332】
- **MFA enforcement:** Middleware enforces MFA for authenticated users with explicit exemptions for login and recovery flows.【F:invoiceflow/mfa_middleware.py†L1-L111】
- **Login rate limiting:** Authentication service tracks failed attempts by IP/user and locks out excessive failures.【F:invoices/auth_services.py†L45-L132】
- **API throttling:** DRF throttles per-user and anonymous requests for API endpoints.【F:invoiceflow/settings.py†L379-L401】
- **Webhook verification:** Paystack webhook signatures are verified using constant-time comparison and processed with idempotency guards.【F:invoices/paystack_views.py†L118-L199】【F:invoices/paystack_service.py†L304-L353】

## Risks & follow-up verification items
1. **Non-production host laxness:** Non-production defaults allow `ALLOWED_HOSTS = ["*"]`, which is acceptable for local dev but should never be reused in production-like environments.【F:invoiceflow/settings.py†L57-L70】
2. **Session-based API auth:** DRF is configured for `SessionAuthentication`. Ensure all API clients use CSRF tokens or introduce token-based auth for external integrations if required.【F:invoiceflow/settings.py†L373-L386】
3. **MFA and email verification enforcement scope:** MFA and email verification are enforced in specific flows (middleware/auth service). Confirm all sensitive endpoints and payment operations are covered, especially any API endpoints outside the standard web session flow.【F:invoiceflow/mfa_middleware.py†L1-L111】【F:invoices/auth_services.py†L17-L63】

## Immediate Phase 2 security goals
- Enumerate every endpoint and classify it by authentication and risk level.
- Add tests that confirm CSRF, MFA, and email-verification constraints across critical flows.
- Review logging for sensitive data exposure and adjust log levels/filters.
