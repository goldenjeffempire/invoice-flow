# Phase 2 — Backend Refactor & API Modernization Plan

## Target areas (current baseline)
- **Service layer:** Authentication and payment workflows live in `invoices/auth_services.py` and `invoices/paystack_service.py`, with view orchestration in `invoices/paystack_views.py`.【F:invoices/auth_services.py†L1-L200】【F:invoices/paystack_service.py†L260-L360】【F:invoices/paystack_views.py†L1-L200】
- **Data models:** The core business schema and payment provider fields are defined in `invoices/models.py`.【F:invoices/models.py†L120-L220】
- **API entry points:** DRF viewsets are registered in `invoices/api/urls.py` and use global DRF settings in `invoiceflow/settings.py`.【F:invoices/api/urls.py†L1-L7】【F:invoiceflow/settings.py†L373-L404】

## Refactor goals (Phase 2)
1. **Normalize service boundaries**
   - Separate transactional operations (payments, invoice status transitions) from view concerns.
   - Centralize cross-cutting concerns (idempotency, audit logging) into reusable helpers.
2. **API behavior consistency**
   - Standardize error response payloads and status codes for API endpoints.
   - Confirm pagination, filtering, and ordering across all DRF viewsets.
3. **Data integrity & validation**
   - Consolidate validation rules for invoices, line items, and payment references.
   - Add explicit domain methods for status transitions and invoice calculations.
4. **Observability**
   - Ensure error logging avoids sensitive data leaks.
   - Add structured log context for payment flows and webhook processing.

## Execution outline
1. **Model audit:** validate invoice total/tax/discount calculation logic and enforce invariant checks at the model or service layer.
2. **Service extraction:** move webhook processing and payment finalization logic into dedicated service functions with unit tests.
3. **API consolidation:** standardize DRF serializers and responses; ensure viewsets adhere to the same policy for errors.
4. **Performance review:** identify any N+1 queries in invoice list/detail endpoints; add select_related/prefetch_related where needed.

## Immediate next tasks (Phase 2.1)
- Produce an endpoint inventory (web + API) with authentication and risk classification.
- Draft unit tests for payment initialization and webhook processing.
- Align invoice calculations between model fields and derived totals.
