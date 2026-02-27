"""Caching strategies for optimal performance."""

from django.core.cache import cache
from django.utils.decorators import method_decorator
from functools import wraps
from typing import Any, Callable, Optional
import hashlib
import json


class CacheHelper:
    """Cache management utilities."""
    
    @staticmethod
    def make_key(prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from parameters."""
        key_data = f"{prefix}:" + ":".join(str(a) for a in args)
        if kwargs:
            key_data += ":" + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def cached(timeout: int = 300, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = CacheHelper.make_key(
                    key_prefix or func.__name__,
                    *args,
                    **kwargs
                )
                
                # Try to get from cache
                result = cache.get(cache_key)
                if result is not None:
                    return result
                
                # Compute and cache
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate_pattern(pattern: str) -> None:
        """Invalidate cache keys matching pattern."""
        from django.core.cache import caches
        try:
            # Try to get analytics cache, fallback to default
            try:
                cache_backend = caches["analytics"]
            except Exception:
                from django.core.cache import cache as cache_backend
            
            if hasattr(cache_backend, "delete_pattern"):
                cache_backend.delete_pattern(pattern)
            elif hasattr(cache_backend, "_cache"):
                # Fallback for locmem
                keys_to_delete = [k for k in cache_backend._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    cache_backend.delete(k)
        except Exception:
            pass


class UserCacheManager:
    """Manage caching for user-specific data."""
    
    USER_INVOICE_COUNT_KEY = "user:invoices:count:{user_id}"
    USER_REVENUE_KEY = "user:revenue:{user_id}"
    USER_UNPAID_KEY = "user:unpaid:{user_id}"
    
    @staticmethod
    def get_invoice_count(user_id: int) -> int:
        """Get cached invoice count."""
        from invoices.models import Invoice
        key = UserCacheManager.USER_INVOICE_COUNT_KEY.format(user_id=user_id)
        count = cache.get(key)
        if count is None:
            count = Invoice.objects.filter(user_id=user_id).count()
            cache.set(key, count, 3600)  # 1 hour
        return count
    
    @staticmethod
    def invalidate_invoice_cache(user_id: int) -> None:
        """Invalidate user invoice caches."""
        cache.delete(UserCacheManager.USER_INVOICE_COUNT_KEY.format(user_id=user_id))
        cache.delete(UserCacheManager.USER_REVENUE_KEY.format(user_id=user_id))
        cache.delete(UserCacheManager.USER_UNPAID_KEY.format(user_id=user_id))
    
    @staticmethod
    def get_revenue(user_id: int) -> float:
        """Get cached total revenue."""
        from invoices.models import Invoice
        from django.db.models import Sum
        
        key = UserCacheManager.USER_REVENUE_KEY.format(user_id=user_id)
        revenue = cache.get(key)
        if revenue is None:
            agg = Invoice.objects.filter(user_id=user_id, status='paid').aggregate(Sum('total'))
            revenue = float(agg['total__sum'] or 0)
            cache.set(key, revenue, 3600)
        return revenue


class QueryOptimization:
    """Optimize database queries with select_related and prefetch_related."""
    
    @staticmethod
    def optimize_invoice_list(queryset):
        """Optimize invoice list queries."""
        return queryset.select_related('user').prefetch_related('line_items', 'payments')
    
    @staticmethod
    def optimize_payment_list(queryset):
        """Optimize payment list queries."""
        return queryset.select_related('user', 'invoice')
    
    @staticmethod
    def optimize_user_profile(queryset):
        """Optimize user profile queries."""
        return queryset.select_related('user').prefetch_related('invoice_templates')


class BulkOperationHelper:
    """Helpers for bulk operations with performance optimization."""
    
    @staticmethod
    def bulk_create_invoices(invoice_data_list: list, user_id: int):
        """Bulk create invoices with optimizations."""
        from invoices.models import Invoice
        
        invoices = [
            Invoice(user_id=user_id, **data)
            for data in invoice_data_list
        ]
        created = Invoice.objects.bulk_create(invoices, batch_size=100)
        
        # Invalidate cache
        UserCacheManager.invalidate_invoice_cache(user_id)
        
        return created
    
    @staticmethod
    def bulk_update_status(invoice_ids: list, status: str):
        """Bulk update invoice status."""
        from invoices.models import Invoice
        
        Invoice.objects.filter(id__in=invoice_ids).update(status=status)
        
        # Invalidate caches for all affected users
        users = Invoice.objects.filter(id__in=invoice_ids).values_list('user_id', flat=True).distinct()
        for user_id in users:
            UserCacheManager.invalidate_invoice_cache(user_id)
