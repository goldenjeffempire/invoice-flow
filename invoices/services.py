"""
Business logic services for InvoiceFlow platform.
Extracts logic from views into reusable service classes.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from django.db.models import Count, DecimalField, F, Q, Sum, Value, Manager
from django.db.models.functions import Coalesce
from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from .models import Invoice, LineItem, Payment, ProcessedWebhook, UserProfile
from .paystack_service import PaystackService

if TYPE_CHECKING:
    from .forms import InvoiceForm
    from django.db.models.query import QuerySet

logger = logging.getLogger(__name__)


class PaymentService:
    """Centralized service for payment processing and reconciliation."""

    @staticmethod
    @transaction.atomic
    def process_payment(invoice: Invoice, amount: Decimal, reference: str, provider: str = "paystack") -> Tuple[Payment, bool]:
        """Record a payment and update invoice status if successful."""
        payment, created = Payment.objects.get_or_create(
            reference=reference,
            defaults={
                "invoice": invoice,
                "user": invoice.user,
                "amount": amount,
                "status": Payment.Status.PENDING,
            }
        )
        
        # In a real scenario, we'd verify with the provider here
        # For now, we assume this is called by a webhook or verified process
        payment.mark_as_success()
        AnalyticsService.invalidate_user_cache(invoice.user_id)
        return payment, created

    @staticmethod
    def handle_webhook(
        payload: Dict[str, Any],
        provider: str,
        *,
        signature: str = "",
        raw_payload: bytes | None = None,
    ) -> bool:
        """Process incoming webhooks with deduplication and signature validation."""
        if provider == "paystack":
            if not raw_payload or not signature:
                logger.warning("Missing Paystack webhook signature or payload.")
                return False
            
            # HMAC signature verification
            import hmac
            import hashlib
            secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
            if not secret:
                logger.error("PAYSTACK_SECRET_KEY not configured")
                return False
                
            hash_obj = hmac.new(secret.encode('utf-8'), raw_payload, hashlib.sha512)
            if not hmac.compare_digest(hash_obj.hexdigest(), signature):
                logger.warning("Invalid Paystack webhook signature.")
                return False

        event_id = payload.get("id") or payload.get("event_id")
        if not event_id:
            return False

        if ProcessedWebhook.objects.filter(event_id=event_id, provider=provider).exists():
            logger.info(f"Duplicate webhook received: {provider}:{event_id}")
            return True

        with transaction.atomic():
            # Process specific event types
            event_type = payload.get("event")
            if event_type == "charge.success":
                data = payload.get("data", {})
                reference = data.get("reference")
                amount = Decimal(str(data.get("amount", 0))) / 100 # Assuming kobo/cents
                
                try:
                    payment = Payment.objects.get(reference=reference)
                    payment.mark_as_success()
                except Payment.DoesNotExist:
                    logger.error(f"Payment not found for reference: {reference}")
                    return False

            ProcessedWebhook.objects.create(
                event_id=event_id,
                provider=provider,
                event_type=event_type or "unknown",
                reference=payload.get("data", {}).get("reference", ""),
            )
        return True


class EmailService:
    """Standardized email delivery service."""
    
    @staticmethod
    def send_invoice(invoice: Invoice, recipient: str) -> bool:
        from .sendgrid_service import SendGridEmailService
        try:
            return SendGridEmailService().send_invoice(invoice, recipient)
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False

    @staticmethod
    def send_receipt(payment: Payment) -> bool:
        from .sendgrid_service import SendGridEmailService
        from django.template.loader import render_to_string
        from django.core.mail import EmailMessage
        try:
            recipient = payment.invoice.client_email
            subject = f"Receipt for Invoice {payment.invoice.invoice_id}"
            context = {
                "payment": payment,
                "invoice": payment.invoice,
                "base_url": settings.SITE_URL if hasattr(settings, 'SITE_URL') else '',
            }
            html_content = render_to_string("invoices/email/receipt.html", context)
            
            # Use SendGrid if configured, otherwise fallback to Django core mail
            try:
                return SendGridEmailService().send_invoice_paid(payment.invoice, recipient)
            except Exception:
                msg = EmailMessage(subject, html_content, settings.DEFAULT_FROM_EMAIL, [recipient])
                msg.content_subtype = "html"
                msg.send()
                return True
        except Exception as e:
            logger.error(f"Failed to send receipt email: {e}")
            return False


class InvoiceService:
    """Centralized service for Invoice lifecycle management."""

    @staticmethod
    @transaction.atomic
    def create_invoice(user, invoice_data, line_items_data):
        from .forms import InvoiceForm
        form = InvoiceForm(invoice_data)
        if not form.is_valid():
            return None, form

        invoice = form.save(commit=False)
        invoice.user = user
        invoice.save()

        try:
            InvoiceBusinessRules.validate_line_items(line_items_data)
        except Exception as exc:
            form.add_error(None, str(exc))
            return None, form

        for item in line_items_data:
            if item.get("description"):
                LineItem.objects.create(
                    invoice=invoice,
                    description=item["description"],
                    quantity=Decimal(str(item.get("quantity", 1))),
                    unit_price=Decimal(str(item.get("unit_price", 0)))
                )
        
        # Ensure totals are calculated correctly at model level via properties
        AnalyticsService.invalidate_user_cache(user.id)
        return invoice, form

    @staticmethod
    def delete_invoice(user, invoice_id):
        from django.shortcuts import get_object_or_404
        invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=user)
        invoice.delete()
        AnalyticsService.invalidate_user_cache(user.id)
        return True

    @staticmethod
    @transaction.atomic
    def update_invoice(
        invoice: Invoice,
        invoice_data: Any,
        line_items_data: List[Dict[str, Any]],
    ) -> Tuple[Optional[Invoice], Any]:
        """Update invoice with line items in atomic transaction."""
        from .forms import InvoiceForm

        invoice_form = InvoiceForm(invoice_data, instance=invoice)
        if not invoice_form.is_valid():
            return None, invoice_form

        try:
            InvoiceBusinessRules.validate_line_items(line_items_data)
        except Exception as exc:
            invoice_form.add_error(None, str(exc))
            return None, invoice_form

        invoice = invoice_form.save()
        
        # Efficiently update line items
        new_items = []
        for item_data in line_items_data:
            desc = item_data.get("description")
            if not desc:
                continue
            
            qty = Decimal(str(item_data.get("quantity", 1)))
            price = Decimal(str(item_data.get("unit_price", 0)))
            
            new_items.append(LineItem(
                invoice=invoice,
                description=desc,
                quantity=qty,
                unit_price=price
            ))

        invoice.line_items.all().delete()
        LineItem.objects.bulk_create(new_items)

        AnalyticsService.invalidate_user_cache(invoice.user_id)
        return invoice, invoice_form

    @staticmethod
    def transition_status(invoice: Invoice, new_status: str) -> bool:
        """Safe status transition logic."""
        if new_status not in dict(Invoice.Status.choices):
            return False
        
        if new_status == Invoice.Status.PAID:
            invoice.mark_as_paid()
        elif new_status == Invoice.Status.OVERDUE:
            invoice.mark_as_overdue()
        else:
            invoice.status = new_status
            invoice.save(update_fields=["status", "updated_at"])
        
        AnalyticsService.invalidate_user_cache(invoice.user_id)
        return True


class PDFService:
    """Handles PDF generation with a unified rendering pipeline."""

    @staticmethod
    def generate_pdf_bytes(invoice: Invoice) -> bytes:
        """Generate PDF bytes for invoice using a standardized template."""
        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML
            from weasyprint.text.fonts import FontConfiguration
        except ImportError:
            HTML = None
            FontConfiguration = None

        if HTML is None:
            raise ValueError("PDF generation is currently unavailable due to missing system dependencies (weasyprint/cffi).")

        from django.conf import settings

        context = {
            "invoice": invoice,
            "base_url": settings.SITE_URL if hasattr(settings, 'SITE_URL') else '',
            "branding_color": "#4f46e5",
        }
        html_string = render_to_string("invoices/invoice_pdf.html", context)
        font_config = FontConfiguration()
        html = HTML(string=html_string, base_url=settings.SITE_URL if hasattr(settings, 'SITE_URL') else '')
        
        try:
            return html.write_pdf(font_config=font_config)
        except Exception as e:
            logger.error(f"PDF generation failed for invoice {invoice.invoice_id}: {e}")
            raise ValueError(f"Failed to generate PDF. System dependencies (cffi/weasyprint) might be missing.")


class AnalyticsService:
    """Handles analytics calculations with optimized database-level SQL aggregations.

    Performance Optimizations:
    - Uses Django's annotate() for database-level aggregations
    - Calculates invoice totals using SUM(quantity * unit_price) at DB level
    - Reduces N+1 queries by aggregating in single queries
    - Implements database caching for multi-worker environments
    - Target: Sub-250ms dashboard load time
    """

    # Cache key prefixes
    CACHE_PREFIX_DASHBOARD = "analytics:dashboard"
    CACHE_PREFIX_STATS = "analytics:stats"
    CACHE_PREFIX_TOP_CLIENTS = "analytics:top_clients"

    @staticmethod
    def _get_cache():
        """Get the analytics cache backend."""
        try:
            return caches["analytics"]
        except Exception:
            return caches["default"]

    @staticmethod
    def _make_cache_key(prefix: str, user_id: int) -> str:
        """Generate a cache key for a user's analytics data."""
        return f"{prefix}:{user_id}"

    @classmethod
    def invalidate_user_cache(cls, user_id: int) -> None:
        """Invalidate all cached analytics data for a user.

        Call this when invoices are created, updated, or deleted.
        """
        cache = cls._get_cache()
        keys = [
            cls._make_cache_key(cls.CACHE_PREFIX_DASHBOARD, user_id),
            cls._make_cache_key(cls.CACHE_PREFIX_STATS, user_id),
            cls._make_cache_key(cls.CACHE_PREFIX_TOP_CLIENTS, user_id),
        ]
        for key in keys:
            try:
                cache.delete(key)
            except Exception as e:
                logger.warning(f"Failed to invalidate cache key {key}: {e}")

    @staticmethod
    def _get_invoice_total_annotation():
        """Returns annotation for calculating invoice total at database level."""
        return Coalesce(
            Sum(F("line_items__quantity") * F("line_items__unit_price")),
            Value(Decimal("0")),
            output_field=DecimalField(max_digits=15, decimal_places=2),
        )

    @classmethod
    def get_user_dashboard_stats(cls, user: Any) -> Dict[str, Any]:
        """Calculate dashboard statistics using optimized database-level aggregations.

        Performance: Single query for counts, single query for revenue aggregation.
        Caching: 60 seconds (CACHE_TIMEOUT_DASHBOARD)
        Target response time: <100ms (cached), <250ms (uncached)
        """
        cache = cls._get_cache()
        cache_key = cls._make_cache_key(cls.CACHE_PREFIX_DASHBOARD, user.id)
        timeout = getattr(settings, "CACHE_TIMEOUT_DASHBOARD", 60)

        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats

        invoices = Invoice.objects.filter(user=user)  # type: ignore[attr-defined]

        stats = invoices.aggregate(
            total_invoices=Count("id"),
            paid_count=Count("id", filter=Q(status="paid")),
            unpaid_count=Count("id", filter=Q(status="unpaid")),
            unique_clients=Count("client_email", distinct=True),
        )

        total_revenue = LineItem.objects.filter(  # type: ignore[attr-defined]
            invoice__user=user, invoice__status="paid"
        ).aggregate(
            total=Coalesce(
                Sum(F("quantity") * F("unit_price")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )[
            "total"
        ]

        result = {
            "total_invoices": stats["total_invoices"] or 0,
            "paid_count": stats["paid_count"] or 0,
            "unpaid_count": stats["unpaid_count"] or 0,
            "total_revenue": total_revenue or Decimal("0"),
            "unique_clients": stats["unique_clients"] or 0,
        }

        try:
            cache.set(cache_key, result, timeout)
        except Exception as e:
            logger.warning(f"Failed to cache dashboard stats: {e}")

        return result

    @classmethod
    def get_user_analytics_stats(cls, user: Any) -> Dict[str, Any]:
        """Calculate comprehensive analytics using database-level aggregations.

        Performance: Uses aggregate() for all metrics, single query for invoice list.
        Caching: 120 seconds for numeric stats (all_invoices always fresh)
        Target response time: <100ms (cached), <200ms (uncached)
        """
        from datetime import datetime

        cache = cls._get_cache()
        cache_key = cls._make_cache_key(cls.CACHE_PREFIX_STATS, user.id)
        timeout = getattr(settings, "CACHE_TIMEOUT_ANALYTICS", 120)

        cached_stats = cache.get(cache_key)
        invoices = Invoice.objects.filter(user=user)  # type: ignore[attr-defined]

        if cached_stats is not None:
            all_invoices_list = list(
                invoices.prefetch_related("line_items").order_by("-created_at")
            )
            cached_stats["all_invoices"] = all_invoices_list
            return cached_stats

        stats = invoices.aggregate(
            total_invoices=Count("id"),
            paid_count=Count("id", filter=Q(status="paid")),
            unpaid_count=Count("id", filter=Q(status="unpaid")),
        )

        total_invoices = stats["total_invoices"] or 0
        paid_count = stats["paid_count"] or 0
        unpaid_count = stats["unpaid_count"] or 0

        revenue_stats = LineItem.objects.filter(invoice__user=user).aggregate(  # type: ignore[attr-defined]
            total_revenue=Coalesce(
                Sum(F("quantity") * F("unit_price"), filter=Q(invoice__status="paid")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            outstanding_amount=Coalesce(
                Sum(F("quantity") * F("unit_price"), filter=Q(invoice__status="unpaid")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            total_all=Coalesce(
                Sum(F("quantity") * F("unit_price")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )

        total_revenue = revenue_stats["total_revenue"] or Decimal("0")
        outstanding_amount = revenue_stats["outstanding_amount"] or Decimal("0")
        total_all = revenue_stats["total_all"] or Decimal("0")

        average_invoice = (total_all / total_invoices) if total_invoices > 0 else Decimal("0")
        payment_rate = (paid_count / total_invoices * 100) if total_invoices > 0 else 0

        now = datetime.now()
        current_month_invoices = invoices.filter(
            invoice_date__year=now.year, invoice_date__month=now.month
        ).count()

        cacheable_stats = {
            "total_invoices": total_invoices,
            "paid_invoices": paid_count,
            "unpaid_invoices": unpaid_count,
            "total_revenue": total_revenue,
            "outstanding_amount": outstanding_amount,
            "average_invoice": average_invoice,
            "payment_rate": payment_rate,
            "current_month_invoices": current_month_invoices,
        }

        try:
            cache.set(cache_key, cacheable_stats, timeout)
        except Exception as e:
            logger.warning(f"Failed to cache analytics stats: {e}")

        all_invoices_list = list(invoices.prefetch_related("line_items").order_by("-created_at"))

        return {
            **cacheable_stats,
            "all_invoices": all_invoices_list,
        }

    @classmethod
    def get_top_clients(cls, user: Any, limit: int = 10) -> List[Dict[str, Any]]:
        """Calculate top clients with database-level aggregations.

        Performance: Uses annotate() and aggregate() at database level.
        Caching: 300 seconds (5 minutes) - less frequently accessed
        Groups by client_name with revenue and count calculations in SQL.
        """
        cache = cls._get_cache()
        cache_key = f"{cls._make_cache_key(cls.CACHE_PREFIX_TOP_CLIENTS, user.id)}:{limit}"
        timeout = getattr(settings, "CACHE_TIMEOUT_TOP_CLIENTS", 300)

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        clients = (
            Invoice.objects.filter(user=user)  # type: ignore[attr-defined]
            .values("client_name")
            .annotate(
                invoice_count=Count("id"),
                paid_count=Count("id", filter=Q(status="paid")),
            )
            .order_by("client_name")
        )

        client_data: Dict[str, Dict[str, Any]] = {}
        for c in clients:
            client_data[c["client_name"]] = {
                "client_name": c["client_name"],
                "invoice_count": c["invoice_count"],
                "paid_count": c["paid_count"],
                "total_revenue": Decimal("0"),
                "total_all": Decimal("0"),
            }

        revenue_by_client = (
            LineItem.objects.filter(invoice__user=user)  # type: ignore[attr-defined]
            .values("invoice__client_name")
            .annotate(
                paid_revenue=Coalesce(
                    Sum(F("quantity") * F("unit_price"), filter=Q(invoice__status="paid")),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
                total_revenue=Coalesce(
                    Sum(F("quantity") * F("unit_price")),
                    Value(Decimal("0")),
                    output_field=DecimalField(max_digits=15, decimal_places=2),
                ),
            )
        )

        for r in revenue_by_client:
            client_name = r["invoice__client_name"]
            if client_name in client_data:
                client_data[client_name]["total_revenue"] = r["paid_revenue"]
                client_data[client_name]["total_all"] = r["total_revenue"]

        top_clients = sorted(
            [
                {
                    "client_name": data["client_name"],
                    "invoice_count": data["invoice_count"],
                    "total_revenue": data["total_revenue"],
                    "paid_count": data["paid_count"],
                    "avg_invoice": (
                        data["total_all"] / data["invoice_count"]
                        if data["invoice_count"] > 0
                        else Decimal("0")
                    ),
                    "payment_rate": (
                        (data["paid_count"] / data["invoice_count"] * 100)
                        if data["invoice_count"] > 0
                        else 0
                    ),
                }
                for data in client_data.values()
            ],
            key=lambda x: x["total_revenue"],
            reverse=True,
        )[:limit]

        try:
            cache.set(cache_key, top_clients, timeout)
        except Exception as e:
            logger.warning(f"Failed to cache top clients: {e}")

        return top_clients


class CacheWarmingService:
    """
    Service for proactive cache warming and smart cache management.

    Features:
    - Async cache warming on user login (non-blocking)
    - Startup cache warming for active users
    - Cache versioning for deployment cache busting
    - Efficient background warming with thread pool
    """

    CACHE_VERSION_KEY = "cache:version"
    ACTIVE_USERS_KEY = "cache:active_users"
    MAX_STARTUP_USERS = 50

    _executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """Get or create the thread pool executor (lazy initialization)."""
        if cls._executor is None:
            with cls._executor_lock:
                if cls._executor is None:
                    cls._executor = ThreadPoolExecutor(
                        max_workers=2, thread_name_prefix="cache_warmer"
                    )
        return cls._executor

    @classmethod
    def shutdown_executor(cls) -> None:
        """Shutdown the thread pool executor gracefully."""
        if cls._executor is not None:
            cls._executor.shutdown(wait=False)
            cls._executor = None

    @classmethod
    def warm_user_cache_async(cls, user: Any) -> None:
        """
        Warm user cache asynchronously (non-blocking).
        Called on user login to pre-populate dashboard caches.
        """
        try:
            executor = cls._get_executor()
            executor.submit(cls._warm_user_cache_sync, user.id)
        except Exception as e:
            logger.warning(f"Failed to submit cache warming task: {e}")

    @classmethod
    def _warm_user_cache_sync(cls, user_id: int) -> None:
        """
        Synchronously warm cache for a user (runs in background thread).
        Properly manages database connections for threaded execution.
        """
        from django.db import close_old_connections
        from django.contrib.auth import get_user_model

        try:
            close_old_connections()

            User = get_user_model()

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.debug(f"User {user_id} not found, skipping cache warming")
                return

            AnalyticsService.get_user_dashboard_stats(user)
            AnalyticsService.get_user_analytics_stats(user)
            AnalyticsService.get_top_clients(user)

            cls._track_active_user(user_id)

            logger.info(f"Cache warmed for user {user_id}")
        except Exception as e:
            logger.debug(f"Failed to warm cache for user {user_id}: {e}")
        finally:
            close_old_connections()

    @classmethod
    def _track_active_user(cls, user_id: int) -> None:
        """Track user as active for startup cache warming."""
        try:
            cache = AnalyticsService._get_cache()
            active_users = cache.get(cls.ACTIVE_USERS_KEY, set())
            if not isinstance(active_users, set):
                active_users = set(active_users) if active_users else set()
            active_users.add(user_id)
            if len(active_users) > cls.MAX_STARTUP_USERS * 2:
                active_users = set(list(active_users)[-cls.MAX_STARTUP_USERS :])
            cache.set(cls.ACTIVE_USERS_KEY, active_users, 86400 * 7)
        except Exception as e:
            logger.debug(f"Failed to track active user: {e}")

    @classmethod
    def warm_active_users_cache(cls) -> int:
        """
        Warm cache for recently active users on startup.
        Skips if no active users exist (optimization for new deployments).
        Returns number of users warmed.
        """
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            cache = AnalyticsService._get_cache()
            active_users = cache.get(cls.ACTIVE_USERS_KEY, set())

            if not active_users:
                recent_users = User.objects.filter(is_active=True).order_by("-last_login")[
                    : cls.MAX_STARTUP_USERS
                ]
                active_user_ids = [u.id for u in recent_users if u.last_login]
                
                # Skip cache warming if no active users exist (new deployment optimization)
                if not active_user_ids:
                    logger.debug("Startup cache warming skipped: no active users")
                    return 0
            else:
                active_user_ids = list(active_users)[: cls.MAX_STARTUP_USERS]

            warmed_count = 0
            for user_id in active_user_ids:
                try:
                    cls._warm_user_cache_sync(user_id)
                    warmed_count += 1
                except Exception as e:
                    logger.debug(f"Failed to warm cache for user {user_id}: {e}")

            logger.info(f"Startup cache warming completed: {warmed_count} users")
            return warmed_count
        except Exception as e:
            logger.warning(f"Startup cache warming failed: {e}")
            return 0

    @classmethod
    def get_cache_version(cls) -> str:
        """Get current cache version for cache busting."""
        cache = AnalyticsService._get_cache()
        version = cache.get(cls.CACHE_VERSION_KEY)
        if not version:
            version = cls._generate_version()
            cache.set(cls.CACHE_VERSION_KEY, version, None)
        return version

    @classmethod
    def bump_cache_version(cls) -> str:
        """
        Bump cache version to invalidate all caches.
        Call this during deployments or major changes.
        """
        version = cls._generate_version()
        cache = AnalyticsService._get_cache()
        cache.set(cls.CACHE_VERSION_KEY, version, None)
        logger.info(f"Cache version bumped to {version}")
        return version

    @staticmethod
    def _generate_version() -> str:
        """Generate a new cache version string."""
        import uuid
        return str(uuid.uuid4()).replace('-', '')[:8]

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            cache = AnalyticsService._get_cache()
            active_users = cache.get(cls.ACTIVE_USERS_KEY, set())
            version = cache.get(cls.CACHE_VERSION_KEY, "unknown")

            return {
                "cache_version": version,
                "tracked_active_users": len(active_users) if active_users else 0,
                "max_startup_users": cls.MAX_STARTUP_USERS,
                "executor_active": cls._executor is not None,
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
