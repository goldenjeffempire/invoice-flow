# Architecture & Refactor Plan

This document outlines the next refactor milestones needed to normalize service boundaries, improve API consistency, and harden payment flows.

## Service Boundaries
- Move payment initialization, verification, and reconciliation out of views into a dedicated payment service layer.
- Centralize cross-cutting concerns (idempotency, audit logging, rate-limit helpers) in reusable service utilities.
- Keep views thin: request parsing + service orchestration only.

## API Consistency
- Standardize pagination, ordering, and filtering across all DRF viewsets (shared mixin).
- Enforce consistent error envelopes for all API responses.
- Add test fixtures for API consumers (token auth, pagination, error formats).

## Validation & Data Integrity
- Reuse InvoiceBusinessRules across forms, services, and serializers.
- Introduce shared validators for payment references and status transitions.
- Add tests to cover invoice totals, line items, and payment state transitions.

## Performance & Caching
- Require shared cache (Redis) in production.
- Review cache keys and timeouts for analytics endpoints.
- Add instrumentation around cache hit ratios and error rates.

## Testing Plan
- Unit tests for PaymentService (webhooks, idempotency, signature validation).
- Integration tests for payment initialization + reconciliation.
- API contract tests for pagination, filters, and error shapes.
