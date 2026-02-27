"""Enhanced monitoring and observability utilities."""

import logging
import time
from functools import wraps
from typing import Callable, Any
from django.core.cache import cache
from datetime import datetime, timedelta


logger = logging.getLogger("invoiceflow.monitoring")


class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    @staticmethod
    def track_operation(operation_name: str):
        """Decorator to track operation performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.info(f"Operation '{operation_name}' completed in {duration:.2f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"Operation '{operation_name}' failed after {duration:.2f}s: {str(e)}")
                    raise
            return wrapper
        return decorator


class RateLimitMonitor:
    """Monitor and manage rate limiting."""
    
    @staticmethod
    def get_user_requests(user_id: int, window_seconds: int = 60) -> int:
        """Get request count for user in time window."""
        cache_key = f"rate_limit:{user_id}:{int(time.time() // window_seconds)}"
        return cache.get(cache_key, 0)
    
    @staticmethod
    def increment_user_requests(user_id: int, window_seconds: int = 60) -> int:
        """Increment request count for user."""
        cache_key = f"rate_limit:{user_id}:{int(time.time() // window_seconds)}"
        count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, count, window_seconds)
        return count
    
    @staticmethod
    def is_rate_limited(user_id: int, limit: int = 100, window_seconds: int = 60) -> bool:
        """Check if user is rate limited."""
        count = RateLimitMonitor.get_user_requests(user_id, window_seconds)
        return count >= limit


class HealthChecker:
    """System health checks."""
    
    @staticmethod
    def check_database() -> dict:
        """Check database connectivity."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {"status": "healthy", "service": "database"}
        except Exception as e:
            return {"status": "unhealthy", "service": "database", "error": str(e)}
    
    @staticmethod
    def check_cache() -> dict:
        """Check cache connectivity."""
        try:
            cache.set("health_check", "ok", 10)
            value = cache.get("health_check")
            if value == "ok":
                return {"status": "healthy", "service": "cache"}
            else:
                return {"status": "unhealthy", "service": "cache", "error": "Cache read/write failed"}
        except Exception as e:
            return {"status": "unhealthy", "service": "cache", "error": str(e)}
    
    @staticmethod
    def get_full_health() -> dict:
        """Get full system health status."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": [
                HealthChecker.check_database(),
                HealthChecker.check_cache(),
            ]
        }


class MetricsCollector:
    """Collect and store metrics."""
    
    @staticmethod
    def record_invoice_metric(metric_type: str, user_id: int, value: Any) -> None:
        """Record invoice-related metric."""
        cache_key = f"metric:{metric_type}:{user_id}"
        metrics = cache.get(cache_key, {})
        metrics[datetime.utcnow().isoformat()] = value
        cache.set(cache_key, metrics, 86400 * 30)  # 30 days
    
    @staticmethod
    def get_daily_active_users() -> int:
        """Get count of daily active users."""
        from invoices.models import Invoice
        from django.utils import timezone
        today = timezone.now().date()
        return Invoice.objects.filter(
            created_at__date=today
        ).values("user").distinct().count()
    
    @staticmethod
    def get_payment_metrics(user_id: int) -> dict:
        """Get payment metrics for user."""
        from invoices.models import Payment
        from django.db.models import Sum, Count, Avg
        
        payments = Payment.objects.filter(invoice__user_id=user_id)
        
        return {
            "total_received": payments.aggregate(Sum("amount"))["amount__sum"] or 0,
            "payment_count": payments.count(),
            "average_payment": payments.aggregate(Avg("amount"))["amount__avg"] or 0,
            "success_rate": payments.filter(status="completed").count() / max(payments.count(), 1) * 100,
        }
