# InvoiceFlow

A production-ready Django invoicing application for freelancers and small businesses.

## Features
- Invoice creation, management, and PDF generation
- Client management
- Payment tracking (Paystack integration)
- Recurring billing/scheduling
- Expense tracking
- Estimates
- Multi-workspace support
- MFA authentication
- Admin panel
- REST API (DRF)
- Email notifications (SendGrid)
- Email marketing (newsletter subscribers + campaign management)
- Reports (revenue, aging, cashflow, profitability, tax, forecast)

## Architecture

- **Framework:** Django 6.x with Django REST Framework
- **Database:** PostgreSQL (Replit built-in via `DATABASE_URL`)
- **Cache:** In-memory (LocMemCache) in dev, Redis in production
- **Static Files:** WhiteNoise for serving static assets
- **Templates:** Django templates with Tailwind CSS (CDN), Alpine.js (CDN), Chart.js (CDN)
- **UI System:** App shell (layout_app.html). CSS-variable-driven collapsible sidebar (256px ↔ 64px icon-only mode with tooltips), mobile off-canvas drawer with overlay, sticky topbar, workspace switcher dropdown, user profile footer menu, notification dropdown, dark mode toggle. **Global search** — ⌘K keyboard shortcut + search button in topbar opens an Alpine.js modal overlay calling `/api/search/` with real-time results for invoices, clients, expenses, and estimates. **Dashboard fully rebuilt (production-grade)** — `invoices/views/dashboard_views.py` and `templates/pages/dashboard.html` completely rewritten. Features: two rows of KPI cards (MTD revenue + trend %, outstanding, overdue, expenses MTD + trend %, net profit, collection rate, total clients, draft count), 6-month revenue-vs-expenses Chart.js line chart with gradient fills, invoice status doughnut chart with legend, recent invoices table with status badges and inline due amounts, recent payments feed, due-this-week sidebar, top clients by paid revenue, 6 quick action tiles, overdue aging analysis (0-30/31-60/61-90/90+ day buckets with progress bars — only shown when overdue invoices exist). All sections have proper empty states. Fully responsive. Dark mode supported. `LOGIN_REDIRECT_URL = '/dashboard/'`. Client detail page (`pages/clients/detail.html`) enhanced with a 12-month per-client revenue bar chart. All report pages include Chart.js visualizations. **Wallet** (`/wallet/`) — balance dashboard showing total payments received vs. payouts with net balance KPI cards and transaction history. **System Monitoring** (`/monitoring/`) — live dashboard showing DB/cache/migration health checks, process memory/CPU metrics, uptime, runtime info, and health API endpoint reference. **Invoice Templates** (`/invoice-templates/`) — visual template selector (modern, classic, minimal, professional, bold) saved per workspace.
- **Page Consistency Pass (Mar 2026):** All authenticated pages standardized with: (1) `{% block page_title %}` breadcrumb blocks so the topbar displays the correct page name, (2) `page-in` animation wrapper div for entrance animations, (3) `.page-hdr` / `.page-title` / `.page-sub` / `.page-hdr-actions` CSS classes replacing inline styles for page headers. Pages updated: Invoices list, Invoice detail, Invoice builder, Estimates list, Estimate detail, Estimate builder, Clients list, Client detail, Expenses list, Payments overview, Transactions list, Payment detail, Recurring schedules list, Recurring schedule detail, Reports home. Modal backdrops added with blur overlay to invoice detail modals (Send, Void). Settings page sidebar nav refactored to use `.nav-item` CSS class instead of inline JS hover handlers.
- **Dashboard v2 Complete Rebuild (Mar 2026):** Dashboard completely rebuilt from scratch with premium SaaS-grade UI/UX. New architecture: `invoices/views/dashboard_views.py` (full rewrite with net profit chart data, 6-month cashflow trend, smart insights engine, collection rate, estimate conversion stats) + `templates/pages/dashboard.html` (entirely new template) + `static/css/app-enhanced.css` (700+ lines of new dashboard CSS) + `invoices/templatetags/invoice_filters.py` (new `dict_get` and `abs_value` custom filters). New layout: (1) **Header** — user avatar, time-aware greeting, workspace name, refresh button (R shortcut), Create Invoice CTA; (2) **Quick Actions row** — 6 branded action cards (Create Invoice, Add Client, Record Payment, New Estimate, Log Expense, View Reports); (3) **KPI grid** — 6 cards (Revenue MTD + trend%, Outstanding, Overdue with danger highlight, Expenses MTD + trend%, Net Profit with color coding, Total Clients + new count badge); (4) **Smart Insights banners** — contextual alerts for overdue/due-soon/revenue-trend/collection-rate; (5) **Charts row** — Revenue vs Expenses bar chart + Net Profit line overlay (6-month trend), Invoice Status doughnut with animated progress bars; (6) **Main tabbed table** — single card with 3 tabs (Recent Invoices / Recent Payments / Overdue) with view-all links; (7) **Due Soon card** — surfaces invoices due within 7 days; (8) **Sidebar** — Business Overview stats, Top Clients by revenue, Timeline Activity Feed with live indicator. 4 JSON API endpoints: `GET /api/dashboard/summary`, `GET /api/invoices/recent`, `GET /api/payments/recent`, `GET /api/analytics/revenue-expenses`. Alpine.js live refresh (silent background polling every 5 min), keyboard shortcut R. Full dark mode + responsive breakpoints. `getCsrfToken()` helper in `app.js` for CSRF-safe AJAX.
- **PDF Generation:** WeasyPrint + ReportLab
- **Email:** SendGrid
- **Auth:** Enterprise-grade rebuild — AuthService, SessionService, PasswordValidator (HIBP breach check), SecurityService. No email verification required. MFA (TOTP via pyotp) preserved for existing users.
- **Deployment:** Render `standard` plan (Always On, 2 GB RAM, 1 CPU). Gunicorn gthread workers. Zero-downtime deploys via `preDeployCommand` migrations. Replit configured as `vm` (Always On). Sentry optional via `SENTRY_DSN` env var.
- **Bug Fixes (Mar 2026):** 5 production bugs fixed: (1) `PaymentAuditLog` field mismatch — `payment_views.py` corrected `order_by('-timestamp')` to `order_by('-created_at')`; (2) Revenue report `NoReverseMatch` — guarded `client_detail` URL against empty `client__id` in `revenue.html`; (3) Recurring schedule detail `TypeError: RecurringSchedule is not JSON serializable` — fixed `Invoice.objects.filter(recurring_schedule=schedule)` which was filtering on a JSONField; now queries via `ScheduleExecution` FK; (4) Exports hub `ProgrammingError` — created migration `0019_fix_reportexport_schema` to add missing `report_params`, `export_format`, `file_name`, `file_size` columns to `invoices_reportexport` table; (5) Workspace settings `AttributeError` — replaced non-existent `profile.terms_conditions` with existing `profile.payment_instructions` field, and fixed `bank_sort_code` template/form to use the existing `bank_swift_code` field.
- **Payment View Rebuild (Mar 2026):** `payment_views.py` fully rebuilt with: workspace safety guard helper, proper Decimal arithmetic, month-over-month stats, pending amount/count, payment method breakdown, active dispute count. `payment_overview.html` now shows 4 KPI cards (total collected, this-month vs last-month with MoM% badge, pending amount+count, active disputes), method breakdown sidebar, disputes panel, quick actions. `payment_list.html` (transactions page) rebuilt with search, status tabs, date-range filter, sortable columns, paginator. `invoice_send` view fixed: status saved before email attempt, `delivery_email_sent` flag tracked via `update_fields`. `client_autocomplete` URL registered at `clients/autocomplete/` (view was defined in `client_views.py` but missing from `urls.py`).
- **Encryption:** cryptography library with ENCRYPTION_SALT env var

## Project Structure

```
invoiceflow/        - Django project settings and configuration
invoices/           - Main app with models, views, forms, API
  api/              - REST API views and serializers
  migrations/       - Database migrations
  management/       - Custom management commands
  validation/       - Input validation and error handling
  services/         - Business logic services
  views/            - View modules
templates/          - HTML templates
static/             - Static assets (CSS, JS)
staticfiles/        - Collected static files (generated)
tests/              - Test suite
```

## Development

The app runs on port 5000 with `python manage.py runserver 0.0.0.0:5000`.

### Environment Variables
- `SECRET_KEY` - Django secret key (defaults to insecure dev key if not set)
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Replit)
- `DEBUG` - Set to "false" for production (default "true")
- `PRODUCTION` - Set to "true" for production mode
- `ENCRYPTION_SALT` - Required in production for data encryption
- `SENDGRID_API_KEY` - For email delivery
- `SENTRY_DSN` - For error monitoring

### Migration Notes
Migration 0006 had a bug where it tried to modify the `invoices_payment` table after it was dropped by migration 0003's raw SQL. Fixed by adding a `CreateModel` for Payment in migration 0006 before the RemoveField operations.

## Recent Improvements (2026-03)

### New Public Pages
- `templates/pages/support.html` — Full support centre with search, help topic cards, contact channels, and live platform status indicator.
- `templates/pages/blog.html` — Blog listing with featured article, article grid, tag badges, and newsletter subscription form.
- `templates/pages/careers.html` — Careers page with company values, open roles listing, and step-by-step hiring process.
- `templates/pages/workspace/create.html` — Workspace creation form served by the existing `workspace_create` view.

### Navigation & Footer
- Resources nav dropdown now includes Blog and Support Centre links (desktop + mobile).
- Footer updated to include Blog, Support, Careers, and Security in appropriate columns.

### View Fixes
- `settings_page` — Was a redirect stub; now `@login_required` and renders `pages/settings.html` with profile + workspace context.
- `payment_settings_update_ajax` — Was a stub; now fully updates `accept_card_payments`, `accept_bank_transfers`, `accept_mobile_money`, and `payment_instructions` on the user profile.
- `security_update_ajax` — Was a stub; now `@login_required` + `@require_POST`, updates security notification preferences.
- `reminder_dashboard` — Added `@login_required` decorator.
- `faq_api` — Now returns real FAQ data with optional search filtering via `?q=` query param.
- `security_activity` — Added missing `@login_required` decorator (was accessible to anonymous users, causing a crash on `request.user`).

### Critical Bug Fixes (2026-03-16)
- **`invoices/encryption.py`** — Fixed broken import: `PBKDF2` was removed from the `cryptography` library; replaced with `PBKDF2HMAC`. Full encrypt/decrypt round-trip now verified working.
- **`invoiceflow/settings.py`** — Added `ENCRYPTION_SALT = os.getenv("ENCRYPTION_SALT", ...)` so `settings.ENCRYPTION_SALT` resolves correctly (previously caused `AttributeError` at runtime).
- **`invoices/services/pdf_service.py`** — Replaced all uses of `invoice.invoice_id` (non-existent attribute) with `invoice.invoice_number` (lines 72, 75, 89). Affects PDF generation log messages and the generated filename.
- **`invoices/services/payment_service.py`** — Removed `tip_amount=tip_amount` from `Payment.objects.create()` call; `tip_amount` is not a model field. The value is now stored in the `metadata` JSON field instead.

### Template & URL Audit Fixes (2026-03-16 continued)
- **`templates/pages/reports/home.html`** — Corrected 7 broken URL references: `report_cashflow/aging/expense/profitability/tax/forecast/exports` → correct names `cashflow_report`, `aging_report`, `expense_analysis`, `profitability_report`, `tax_report`, `forecast_report`, `exports_hub`. All report cards now link correctly.
- **`invoices/views/expense_views.py`** — Added missing `expense_delete` view (`@require_POST`, workspace-scoped, protects billed/reimbursed expenses from deletion).
- **`invoices/urls.py`** — Added `expenses/<int:expense_id>/delete/` URL pattern (`name="expense_delete"`) wiring up the new view. Resolves the broken delete action in `expense_detail.html`.
- **`invoiceflow/settings.py`** — Added `django.contrib.humanize` to `INSTALLED_APPS` (required by expense, forecast, and profitability templates that use `{% load humanize %}`).
- **`templates/pages/workspace/settings.html`** — Fixed double `{% endblock %}` syntax error.
- All template URL names validated against defined patterns — zero mismatches remain.

## Template Rewrites (2026-03-27)

### Settings Pages — CSS Architecture Fix
All authenticated settings pages were rewritten to use the app's inline-style design system (no Tailwind utility classes). `layout_app.html` only loads `app.css` + `app-enhanced.css`, so all pages must use CSS variables and component classes:
- `templates/pages/settings.html` — Tabbed sidebar (Profile, Business, Branding, Notifications) with Alpine.js toggles and color pickers
- `templates/pages/workspace/settings.html` — Team Members, Payment Methods, General config
- `templates/pages/auth/security_settings.html` — Change Password with show/hide toggle + match validation, 2FA card, Active Sessions table with per-session revoke and "Sign Out Others"

### Signal Bug Fix
- `invoices/signals.py` — `handle_invoice_save` was calling `reminder_service.ReminderSchedulingService` which imported the non-existent `ScheduledReminder` model, crashing every Invoice.objects.create(). Wrapped in try/except so it degrades gracefully.

### Demo Data Command
- `invoices/management/commands/create_demo_data.py` — Fully rewritten with correct model field names: `LineItem` (not `InvoiceItem`), `tax_total` (not `tax_amount`), `payment_method` (not `method`), `provider_reference`, `base_amount` + `idempotency_key` for `RecurringSchedule`, `ExpenseCategory` uses `name` not `slug`. Seeds: 8 clients, 15 invoices with line items + payments, 15 categorised expenses, 5 estimates with items, 4 recurring schedules.
- Run with: `python manage.py create_demo_data --username demo`
- Login: `username=demo`, `password=demo1234`

## Settings System Overhaul (2026-03-28)

Complete audit, repair, and upgrade of the Settings module:

### New Backend Endpoints
- `POST /settings/avatar/` (`avatar_upload`) — Validates file type via magic bytes, enforces 5 MB limit, stores to `media/avatars/`, returns JSON `{avatar_url}`.
- `POST /settings/email-change/` (`email_change_request`) — Requires `new_email` + `current_password`, authenticates via `authenticate()`, checks email uniqueness, writes `SecurityEvent`, returns JSON.

### Upgraded Existing Views (all now return JSON for AJAX and log SecurityEvents)
- `profile_update_ajax` — Validates full_name required, max 150 chars, updates first/last name, timezone, locale, logs `profile_updated` SecurityEvent.
- `settings_business_update` — Now saves `default_currency` and `tax_id_number` (previously ignored), validates business email format, logs `business_info_updated` SecurityEvent.
- `settings_branding_update` — Now saves `invoice_prefix` and `invoice_start_number` (previously ignored), validates hex color format with regex.
- `notifications_update_ajax` — Added `notify_invoice_created` toggle (was missing), all 6 notification preferences saved atomically.
- `security_update_ajax`, `payment_settings_update_ajax` — Now return JSON.

### settings.html Template Rewrite
- All 4 forms (Profile, Business, Branding, Notifications) use `fetch()` AJAX — zero page reloads on save.
- `Toast.show()` for every success and error response.
- Loading spinner states on all submit buttons.
- **Avatar upload** — `<input type="file">` with FileReader preview before upload, size/type client-side validation, uploads via AJAX to `/settings/avatar/`.
- **Email change modal** — Full modal with new email field + password confirmation field with show/hide toggle, client-side format validation, inline error display per field, updates displayed email without page reload.
- Notifications tab auto-saves on toggle click (600ms debounce) + manual Save button.
- Profile form shows "Change email →" link that opens the modal instead of disabled field with unhelpful message.
- Expanded timezone list (14 options covering major regions), currency selector (9 currencies).
- Color picker inputs now sync bidirectionally: hex text input updates picker and vice versa.
- Notification row "Invoice Created" added (was missing from UI despite model support).
- All forms prevented from native submit — fully JS-controlled.

### URL Changes
- `invoiceflow/urls.py` — Added `+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` for serving uploaded avatars in development.
- `invoices/urls.py` — Added `settings/avatar/` and `settings/email-change/` URL patterns.

### Security & Audit
- All new endpoints: `@login_required`, `@require_POST`, `@csrf_protect`.
- Email change authenticates password before updating, logs `email_changed` SecurityEvent with old/new email.
- Avatar upload validates file type via magic bytes (not just file extension), replacing the removed Python 3.13+ `imghdr` module with a custom `_detect_image_type()` helper.
- Business/profile updates logged to `SecurityEvent` model.

## Dashboard Production Bug Fixes (2026-03-28)

A comprehensive audit of the dashboard and app shell identified and fixed 5 production-impacting bugs:

### Bug 1 — CSRF Token Mismatch in `sendReminder()`
**Problem:** The dashboard's reminder button used `document.cookie.match(/csrftoken=/)` to get the CSRF token, but `CSRF_USE_SESSIONS = True` means there is no csrftoken cookie — the token lives in the session and is exposed via `<meta name="csrf-token">`. Every reminder POST silently sent an empty CSRF token, resulting in a 403 from Django.
**Fix:** Changed `sendReminder()` in `templates/pages/dashboard.html` to call `getCsrfToken()` (reads from the meta tag, defined in `app.js`).

### Bug 2 — Reminder Fetch Used Opaque Redirect Response
**Problem:** `send_manual_reminder` view returned an HTTP redirect, and the JS used `redirect: 'manual'`. This made the fetch resolve with an opaque response regardless of whether the server returned 403 or 200, so the UI always showed "Sent ✓" even on failure.
**Fix:** `send_manual_reminder` in `invoices/views/invoice_views.py` now returns `JsonResponse({'status': 'ok'})`. The JS checks `data.status === 'ok'` and shows proper error messages on failure. Also logs an `ActivityLog` entry so the reminder appears in the dashboard activity feed.

### Bug 3 — Chart Empty State Never Rendered
**Problem:** The template checked `{% if chart_revenue %}` to decide whether to show the chart or the "No revenue data yet" empty state. But `chart_revenue` is always a JSON string (`"[0.0, 0.0, ...]"`) — a non-empty string is always truthy in Django templates, so the empty state was never shown. Users would see a loading skeleton that disappeared, leaving a blank canvas.
**Fix:** Added `chart_has_data = any(v > 0 for v in chart_revenue)` to `dashboard_views.py` context. Template now uses `{% if chart_has_data %}`.

### Bug 4 — `mark_notification_read` Accepted GET Requests
**Problem:** The `mark_notification_read` view lacked a method check — any GET request to `/notifications/mark-read/<pk>/` would mark a notification as read without user intent, making it exploitable via link prefetching or crawlers.
**Fix:** Added `if request.method != 'POST': return JsonResponse({'status': 'error'}, status=405)`.

### Bug 5 — Duplicate Django Message Toast Handling
**Problem:** Both `app.js` and `app-enhanced.js` had `DOMContentLoaded` handlers that processed `[data-msg]` elements to show toast notifications. Since `app.js` ran first and removed the DOM elements, `app-enhanced.js`'s nicer toast system (with icons, close button, progress bar) was never triggered — Django messages appeared in the simpler legacy `Toast` UI.
**Fix:** Removed the `[data-msg]` processing from `app.js`'s DOMContentLoaded. Django messages are now exclusively handled by `app-enhanced.js`'s `initToastSystem()` which exposes `window.showToast` and uses the `#toast-container` div.

## Codebase Audit & Stabilization (2026-03-28)

A comprehensive full-codebase audit was completed covering all 80+ Python files, 130+ templates, all views, models, services, and URLs. Django system check passes with **0 issues (0 silenced)**.

### Bug Fix 1 — Invoice Detail Template: Fragile Status Check
**Problem:** `templates/pages/invoices/detail.html` line 56 used `{% if invoice.status not in 'paid,void,write_off' %}` — a substring check (Python `in` operator on strings) rather than list membership. While it happened to work by coincidence for the current status values, it was fragile and misleading. Additionally, the Invoice detail view already passes `can_void` as an explicit context variable for this exact purpose.
**Fix:** Replaced with `{% if can_void %}` which uses the proper `Invoice.can_void` model property via the view's context dictionary.

### Bug Fix 2 — Expense Views: Wrong Workspace Selected
**Problem:** `invoices/views/expense_views.py` had a `get_user_workspace()` helper that used `WorkspaceMember.objects.filter(user=user).first()` — returning the **first workspace by creation time** regardless of which workspace the user had switched to. All other views in the app correctly use `request.user.profile.current_workspace`. This caused users in multiple workspaces to always see expenses from their oldest workspace when visiting the expenses section.
**Fix:** Updated `get_user_workspace()` to check `profile.current_workspace_id` first (consistent with all other views), falling back to membership lookup only if no profile workspace is set.

### Bug Fix 3 — Missing UserProfile Auto-Creation Signal
**Problem:** No `post_save` signal existed to auto-create a `UserProfile` when a Django `User` was created. Only users who went through the full signup flow (via `AuthService.register_user`) got profiles. Admin-created users, management-command-created users, or any user created outside the auth flow would have no profile, causing `User.profile.RelatedObjectDoesNotExist` exceptions on nearly every authenticated view.
**Fix:** Added `@receiver(post_save, sender=settings.AUTH_USER_MODEL)` signal in `invoices/models.py` that calls `UserProfile.objects.get_or_create(user=instance)` on every new User creation. Verified working.

### Bug Fix 4 — Context Processor: Stale Session Workspace Key
**Problem:** `invoices/context_processors.py` had a workspace resolution path that checked `request.session.get('current_workspace_id')` before falling back to `request.user.profile.current_workspace`. However, no view in the codebase ever writes to `'current_workspace_id'` in the session — the `switch_workspace` view saves to `profile.current_workspace`. This session key was dead code that could theoretically serve stale workspace data if any old session had the key set.
**Fix:** Removed the session-based workspace lookup. Context processor now uses the canonical `request.user.profile.current_workspace` (or `request.workspace` if set by a view decorator, e.g. reports views).

## Bug Fixes (2026-03-28 Continued — View Audit)

A further targeted audit of all view files identified and fixed 3 additional bugs:

### Bug Fix 1 — Search: Wrong Currency Attribute on Workspace
**Problem:** `invoices/views/ux_views.py` line 77 called `workspace.default_currency` in the global search handler to look up the currency symbol for expense results. `default_currency` does not exist on the `Workspace` model — that field lives on `UserProfile`. The `Workspace` model uses `currency`. This caused an `AttributeError` whenever a search query matched any expenses in the workspace.
**Fix:** Changed to `workspace.currency`.

### Bug Fix 2 — Reports: Broken ORM Lookup for Non-Owner Workspace Members
**Problem:** `invoices/views/report_views.py` `get_user_workspace()` helper called `Workspace.objects.filter(members=user)`. The `members` field is a reverse FK to `WorkspaceMember` (not a direct M2M to `User`), so Django cannot filter by `members=<User instance>`. This raised an `FieldError` for any user who was a workspace member but not the owner, causing all report pages to break with an error for non-owner members.
**Fix:** Changed to `Workspace.objects.filter(members__user=user)` to traverse through the `WorkspaceMember` join table.

### Bug Fix 3 — Public Invoice: Dead Fragile Code Removed
**Problem:** `invoices/views/invoice_views.py` `public_invoice_view` computed `profile = invoice.workspace.members.first().user.profile if invoice.workspace.members.exists() else None` — a fragile N+1 chain accessing the first workspace member's user profile. This variable was passed as context but never used in `templates/payments/public_invoice.html` (the template uses `invoice.workspace.*` directly). The dead code introduced both an unnecessary DB query and a potential `AttributeError` if any link in the chain was None.
**Fix:** Removed the dead code entirely. The public invoice template now receives only the `invoice`, `is_public`, and `page_title` context variables.

## Session Audit & Fixes (2026-03-30)

Comprehensive full-system audit completed:

### Demo Data Fixes
- `create_demo_data.py` — Added `profile.email_verified = True` and `profile.onboarding_completed = True` to the profile setup section. Previously, demo users created via the management command had both flags as False, causing all login attempts to be redirected to the email verification page instead of the dashboard.
- Demo user name fixed: `first_name = 'Alex'`, `last_name = 'Johnson'` (was empty string from `get_or_create` default).

### Verified Working (Zero Issues)
- Django 6.0.3 system check: **0 issues, 0 silenced**
- All 130+ templates load correctly (verified via Django template loader)
- All URL name references in templates validated — **zero broken URL tags**
- All service modules import cleanly (`invoice_service`, `payment_service`, `expense_service`, `estimate_service`, `recurring_service`, `reports_service`, `pdf_service`, `email_service`, `auth_services`)
- Demo data: `demo`/`demo1234` → Johnson Consulting workspace, 16 invoices, 8 clients, 5 payments, 15 expenses, 5 estimates, 4 recurring schedules
- `auth_services.py` `register_user()` correctly sets `email_verified=True` for all new users going through the standard signup flow

## Deployment

Uses Gunicorn with `gunicorn.conf.py` for production. Build step runs migrations and collectstatic.
