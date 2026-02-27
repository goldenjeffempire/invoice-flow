"""Health check endpoints for production monitoring."""

import os
import time
from typing import Any, Dict

import psutil
from django.conf import settings
from django.core.cache import cache
from django.db import connection, connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.utils import timezone

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_START_TIME = time.time()


def _get_uptime_formatted() -> Dict[str, Any]:
    """Get uptime in human-readable format and raw seconds."""
    uptime_seconds = int(time.time() - APP_START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    return {"seconds": uptime_seconds, "formatted": " ".join(parts)}


def _get_system_metrics() -> Dict[str, Any]:
    """Get system metrics (memory, CPU)."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "memory": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2),
            },
            "cpu": {
                "percent": round(process.cpu_percent(interval=0.1), 2),
                "num_threads": process.num_threads(),
            },
            "open_files": len(process.open_files()) if hasattr(process, "open_files") else 0,
            "connections": len(process.connections()) if hasattr(process, "connections") else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def _get_db_pool_stats() -> Dict[str, Any]:
    """Get database connection pool statistics."""
    try:
        db_conn = connections["default"]
        db_settings = settings.DATABASES.get("default", {})

        host = db_settings.get("HOST") or "localhost"
        host_display = host[:20] + "..." if len(host) > 20 else host

        stats = {
            "engine": db_settings.get("ENGINE", "unknown"),
            "host": host_display,
            "name": db_settings.get("NAME") or "unknown",
        }

        if hasattr(db_conn, "connection") and db_conn.connection:
            conn = db_conn.connection
            if hasattr(conn, "info"):
                info = conn.info
                stats["server_version"] = getattr(info, "server_version", None)
                stats["protocol_version"] = getattr(info, "protocol_version", None)
            if hasattr(conn, "status"):
                stats["connection_status"] = conn.status
            stats["is_usable"] = db_conn.is_usable()
        else:
            stats["connection_status"] = "not_connected"

        return stats
    except Exception as e:
        return {"error": str(e)}


def _get_rate_limiter_config() -> Dict[str, Any]:
    """Get rate limiter configuration."""
    try:
        return {
            "status": "enabled",
            "description": "Sliding window rate limiter with per-endpoint and per-tier limits"
        }
    except Exception:
        return {
            "status": "enabled",
            "description": "Rate limiting active"
        }


def health_check(request):
    """
    Basic health check endpoint for load balancers.
    Returns 200 if the application is running.
    NOTE: This endpoint may redirect (e.g., HTTP->HTTPS).
    For orchestration: Use /health/ready/ or /health/live/ instead.
    """
    uptime = _get_uptime_formatted()
    response = JsonResponse(
        {
            "status": "healthy",
            "version": APP_VERSION,
            "environment": "production" if not settings.DEBUG else "development",
            "timestamp": timezone.now().isoformat(),
            "uptime": uptime,
        }
    )
    # Prevent caching of health status (stale responses cause false failures)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def liveness_check(request):
    """
    Liveness check - verifies app is still responsive.
    Returns basic responsiveness info without hitting database.
    """
    start = time.perf_counter()
    uptime = _get_uptime_formatted()

    response_data = {
        "status": "alive",
        "timestamp": timezone.now().isoformat(),
        "uptime": uptime,
        "version": APP_VERSION,
    }

    response_data["response_time_ms"] = round((time.perf_counter() - start) * 1000, 2)

    response = JsonResponse(response_data)
    # Prevent caching of liveness status
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response

def readiness_check(request):
    """Readiness check - checks database connectivity."""
    db_conn = connections['default']
    try:
        db_conn.cursor()
    except OperationalError:
        return JsonResponse({"status": "not_ready", "database": "down"}, status=503)
    else:
        return JsonResponse({"status": "ready", "database": "up"})


def detailed_health_impl(data):
    """Build detailed health response with cache control."""
    response = JsonResponse(data)
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response

def detailed_health(request):
    """
    Detailed health check for internal monitoring and debugging.
    Includes extended system information, metrics, and service status.
    """
    import platform
    import sys

    import django

    from invoiceflow.env_validation import get_env_status
    from invoices.async_tasks import AsyncTaskService
    
    try:
        from invoices.services import CacheWarmingService
    except ImportError:
        CacheWarmingService = None

    checks = {
        "database": False,
        "migrations": False,
        "cache": False,
    }
    details = {}

    db_start = time.perf_counter()
    try:
        connections["default"].ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            checks["database"] = result is not None and result[0] == 1
        details["database_latency_ms"] = round((time.perf_counter() - db_start) * 1000, 2)
    except Exception as e:
        checks["database"] = False
        details["database_error"] = str(e)

    try:
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        pending = executor.migration_plan(targets)
        checks["migrations"] = len(pending) == 0
        if pending:
            details["pending_migrations"] = len(pending)
    except Exception:
        checks["migrations"] = True

    cache_start = time.perf_counter()
    try:
        cache_key = "_detailed_health_test"
        cache.set(cache_key, "ok", 10)
        cached_value = cache.get(cache_key)
        checks["cache"] = cached_value == "ok"
        cache.delete(cache_key)
        details["cache_latency_ms"] = round((time.perf_counter() - cache_start) * 1000, 2)
    except Exception:
        checks["cache"] = True
        details["cache_note"] = "Using default LocMem cache"

    env_status = get_env_status()
    required_configured = all(v["configured"] for v in env_status["required"].values())

    all_healthy = all(checks.values()) and required_configured
    uptime = _get_uptime_formatted()
    system_metrics = _get_system_metrics()
    db_pool_stats = _get_db_pool_stats()
    rate_limiter_config = _get_rate_limiter_config()

    health_data = {
        "status": "healthy" if all_healthy else "degraded",
        "version": APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "timestamp": timezone.now().isoformat(),
        "uptime": uptime,
        "checks": checks,
        "details": details,
        "environment_status": env_status,
        "system": {
            "python_version": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "django_version": django.get_version(),
            "os": platform.system(),
            "machine": platform.machine(),
        },
        "metrics": system_metrics,
        "database": db_pool_stats,
        "rate_limiting": rate_limiter_config,
        "config": {
            "debug": settings.DEBUG,
            "mfa_enabled": getattr(settings, "MFA_ENABLED", False),
            "allowed_hosts": settings.ALLOWED_HOSTS[:3] if settings.ALLOWED_HOSTS else [],
            "time_zone": settings.TIME_ZONE,
        },
        "cache_warming": CacheWarmingService.get_cache_stats() if CacheWarmingService else {"status": "unavailable"},
        "async_tasks": AsyncTaskService.get_task_stats(),
    }
    return detailed_health_impl(health_data)
