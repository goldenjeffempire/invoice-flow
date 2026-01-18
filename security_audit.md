# InvoiceFlow Baseline Inventory & Scope Mapping

## 1. Inventory
### Apps & Modules
- **invoices**: Core application containing models, views, and logic for invoicing, payments, and reminders.
- **invoiceflow**: Project configuration and settings.
- **api**: REST API endpoints within `invoices/api`.
- **enterprise**: Enterprise-level features within `invoices/enterprise_*.py`.

### Templates & Static Assets
- **templates/**:
  - `base/`: Layout files.
  - `pages/`: Individual page templates.
  - `pages/auth/`: Authentication-related templates.
- **static/**:
  - `stock_images/`: Visual assets for the frontend.

### Configuration Files
- `manage.py`: Django entry point.
- `invoiceflow/settings.py`: Main configuration.
- `requirements.txt`: Python dependencies.
- `pyproject.toml`: Tooling configuration (Black, Ruff, Pytest).
- `.env.example`: Environment variable template.

## 2. Major Flows
- **Onboarding**: Signup flow with email verification.
- **Auth**: Login, MFA (TOTP), password reset, and session management.
- **Invoicing**: Creation, editing, deletion, and PDF generation.
- **Payments**: Paystack integration for invoice settlement.
- **Reminders**: Automated email reminders for overdue invoices.
- **Dashboards**: Analytics and overview for users.

## 3. Dependency Matrix
| Dependency | Version | Risk |
|------------|---------|------|
| Django | 5.2.9 | Stable, but new version. |
| DRF | 3.15.2 | Standard for Django APIs. |
| Paystack (via requests) | N/A | External API dependency. |
| WeasyPrint | 66.0 | System library dependencies (Pango, Cairo). |
| django-csp | 4.0 | Critical for security (CSP). |

---

# Phase 1 — Security, Compliance & Risk Audit

## 1. Security Checklist
- [x] CSRF Protection enabled.
- [x] Hardened Security Headers (HSTS, Content-Type-Options, X-Frame-Options).
- [x] MFA Support (TOTP).
- [x] Rate Limiting on APIs.
- [x] Environment Validation on startup.

## 2. Risk Severity List
| Risk | Severity | Description |
|------|----------|-------------|
| Missing Webhook Signatures | High | If Paystack webhooks aren't properly validated, payments could be forged. |
| PII in Logs | Medium | Ensure sensitive user data isn't leaked to console or file logs. |
| Local Memory Cache | Low | In production, a shared cache like Redis should be used for scalability. |

## 3. Fix Plan
1. **Webhook Validation**: Audit `paystack_webhook` view to ensure signature verification is active.
2. **PII Scrubbing**: Review custom `JsonFormatter` to ensure sensitive fields are masked.
3. **Session Hardening**: Ensure `SESSION_COOKIE_SECURE` is always true in production.
