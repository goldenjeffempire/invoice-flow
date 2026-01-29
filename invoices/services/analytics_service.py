"""
Analytics Service - Business logic for analytics and reporting.

Responsibilities:
- Dashboard statistics calculation
- Revenue analytics
- Client analytics
- Cache management
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import caches
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Handles analytics calculations with optimized database-level SQL aggregations.

    Performance Optimizations:
    - Uses Django's annotate() for database-level aggregations
    - Calculates invoice totals using SUM(quantity * unit_price) at DB level
    - Reduces N+1 queries by aggregating in single queries
    - Implements database caching for multi-worker environments
    """

    CACHE_PREFIX_DASHBOARD = "analytics:dashboard"
    CACHE_PREFIX_STATS = "analytics:stats"
    CACHE_PREFIX_TOP_CLIENTS = "analytics:top_clients"

    _executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()

    @classmethod
    def _get_cache(cls):
        """Get the analytics cache backend."""
        try:
            return caches["analytics"]
        except Exception:
            return caches["default"]

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """Get or create thread pool executor for async operations."""
        if cls._executor is None:
            with cls._executor_lock:
                if cls._executor is None:
                    cls._executor = ThreadPoolExecutor(max_workers=2)
        return cls._executor

    @staticmethod
    def _make_cache_key(prefix: str, user_id: int) -> str:
        """Generate a cache key for a user's analytics data."""
        return f"{prefix}:{user_id}"

    @classmethod
    def invalidate_user_cache(cls, user_id: int) -> None:
        """
        Invalidate all cached analytics data for a user.
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

    @classmethod
    def get_user_dashboard_stats(cls, user: "User") -> Dict[str, Any]:
        """
        Calculate dashboard statistics using optimized database-level aggregations.
        
        Returns cached data if available, otherwise computes and caches.
        Target response time: <100ms (cached), <250ms (uncached)
        """
        from invoices.models import Invoice, LineItem

        cache = cls._get_cache()
        cache_key = cls._make_cache_key(cls.CACHE_PREFIX_DASHBOARD, user.id)
        timeout = getattr(settings, "CACHE_TIMEOUT_DASHBOARD", 60)

        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats

        invoices = Invoice.objects.filter(user=user)

        stats = invoices.aggregate(
            total_invoices=Count("id"),
            paid_count=Count("id", filter=Q(status="paid")),
            unpaid_count=Count("id", filter=Q(status="unpaid")),
            unique_clients=Count("client_email", distinct=True),
        )

        revenue_data = LineItem.objects.filter(invoice__user=user).aggregate(
            paid_revenue=Coalesce(
                Sum(F("quantity") * F("unit_price"), filter=Q(invoice__status="paid")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            unpaid_revenue=Coalesce(
                Sum(F("quantity") * F("unit_price"), filter=Q(invoice__status="unpaid")),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )

        result = {
            "total_invoices": stats["total_invoices"] or 0,
            "paid_count": stats["paid_count"] or 0,
            "unpaid_count": stats["unpaid_count"] or 0,
            "total_revenue": revenue_data["paid_revenue"],
            "unpaid_revenue": revenue_data["unpaid_revenue"],
            "unique_clients": stats["unique_clients"] or 0,
            "last_updated": timezone.now().isoformat(),
        }

        try:
            cache.set(cache_key, result, timeout)
        except Exception as e:
            logger.warning(f"Failed to cache dashboard stats: {e}")

        return result

    @classmethod
    def get_user_analytics_stats(cls, user: "User") -> Dict[str, Any]:
        """
        Calculate comprehensive analytics using database-level aggregations.
        
        Returns cached numeric stats with fresh invoice list.
        """
        from datetime import datetime
        from invoices.models import Invoice, LineItem

        cache = cls._get_cache()
        cache_key = cls._make_cache_key(cls.CACHE_PREFIX_STATS, user.id)
        timeout = getattr(settings, "CACHE_TIMEOUT_ANALYTICS", 120)

        cached_stats = cache.get(cache_key)
        invoices = Invoice.objects.filter(user=user)

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

        revenue_stats = LineItem.objects.filter(invoice__user=user).aggregate(
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

        all_invoices_list = list(
            invoices.prefetch_related("line_items").order_by("-created_at")
        )

        return {
            **cacheable_stats,
            "all_invoices": all_invoices_list,
        }

    @classmethod
    def get_top_clients(cls, user: "User", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Calculate top clients with database-level aggregations.
        
        Groups by client_name with revenue and count calculations in SQL.
        """
        from invoices.models import Invoice, LineItem

        cache = cls._get_cache()
        cache_key = f"{cls._make_cache_key(cls.CACHE_PREFIX_TOP_CLIENTS, user.id)}:{limit}"
        timeout = getattr(settings, "CACHE_TIMEOUT_TOP_CLIENTS", 300)

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        clients = (
            Invoice.objects.filter(user=user)
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
            LineItem.objects.filter(invoice__user=user)
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

    @classmethod
    def warm_user_cache(cls, user_id: int) -> None:
        """
        Warm user cache asynchronously (non-blocking).
        Called on user login to pre-populate dashboard caches.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            executor = cls._get_executor()
            
            def warm():
                try:
                    user = User.objects.get(id=user_id)
                    cls.get_user_dashboard_stats(user)
                    cls.get_user_analytics_stats(user)
                except Exception as e:
                    logger.warning(f"Cache warming failed for user {user_id}: {e}")

            executor.submit(warm)
        except Exception as e:
            logger.warning(f"Failed to submit cache warming task: {e}")
