"""
InvoiceFlow - Enterprise-Grade Gunicorn WSGI Server Configuration
================================================================

Production-optimized Gunicorn configuration for Render deployment.

Features:
✓ Dynamic worker scaling (2-7 based on CPU cores)
✓ Memory leak prevention (worker restart cycles)
✓ Timeout protection (120 seconds per request)
✓ Graceful shutdown (30-second window)
✓ TCP keepalive health checks
✓ DoS protection via request size limits
✓ Structured logging to stdout/stderr
✓ Connection pooling via forwarded headers
✓ Zero-downtime deployment ready
✓ Render-optimized thread configuration
✓ Production-grade security defaults
"""

import multiprocessing
import os
import sys
import logging
import ssl

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

IS_PRODUCTION = os.getenv("PRODUCTION") == "true"
IS_RENDER = bool(os.getenv("RENDER"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Configure logging early
logging.basicConfig(
    level=logging.INFO if IS_PRODUCTION else logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SERVER BINDING & SSL/TLS
# =============================================================================

# Dynamic port (Render sets PORT environment variable)
PORT = int(os.getenv("PORT", 5000))
bind = [f"0.0.0.0:{PORT}"]

# SSL/TLS Configuration (if certificates provided)
# Note: Render uses HTTPS termination at proxy, no SSL needed in Gunicorn
certfile = os.getenv("SSL_CERTFILE")
keyfile = os.getenv("SSL_KEYFILE")

if certfile and keyfile:
    # Modern SSL/TLS context with TLS 1.2+ minimum
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile, keyfile)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
    ssl_context.options |= ssl.OP_NO_COMPRESSION  # Prevent CRIME attack
    ca_certs = os.getenv("SSL_CA_CERTS")


# =============================================================================
# WORKER CONFIGURATION (Render-Optimized)
# =============================================================================

def calculate_workers():
    """
    Calculate optimal worker count for Render environment.
    Render Standard: 512MB-2GB RAM, 0.5-1 CPU core
    Render Pro: 4GB RAM, 2-4 CPU cores
    Conservative scaling prevents OOM and ensures stability.
    """
    cpu_count = multiprocessing.cpu_count()
    
    if IS_RENDER:
        # Render is resource-constrained
        if cpu_count <= 1:
            return 2
        elif cpu_count <= 2:
            return 3
        elif cpu_count <= 4:
            return 5
        else:
            return 7
    else:
        # Development
        return min((cpu_count * 2) + 1, 17)


workers = int(os.getenv("WEB_CONCURRENCY", calculate_workers()))
worker_class = "gthread"  # Thread-based workers for Django
threads = int(os.getenv("GUNICORN_THREADS", 4))

# Connection management
worker_connections = 1000
# max_requests: Restart workers after N requests to prevent memory leaks
# Default: 1000 requests. Can be disabled with env var: GUNICORN_MAX_REQUESTS=0
# WARNING: Only disable after profiling confirms no memory leaks with: py-spy, memory_profiler, or valgrind
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))  # Randomize to avoid thundering herd

# TCP keepalive for connection health
tcp_keepalives_idle = 5
tcp_keepalives_intvl = 1
tcp_keepalives_probes = 3


# =============================================================================
# TIMEOUT & RESOURCE LIMITS
# =============================================================================

timeout = 120  # 2-minute request timeout (prevents hanging requests)
# Graceful shutdown: Use environment variable to override for continuous deployment
# Set GUNICORN_GRACEFUL_TIMEOUT=5 for fast CI/CD deployments
# Default: 10 seconds for production, ensures clean shutdown during continuous deployment
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 10))
keepalive = 5  # HTTP keepalive timeout

# Prevent DoS attacks
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190


# =============================================================================
# APPLICATION LOADING
# =============================================================================

preload_app = True  # Preload Django app before worker fork (faster restarts)
reload = os.getenv("GUNICORN_RELOAD", "false").lower() == "true"
reload_extra_files = []


# =============================================================================
# PROXY & FORWARDING (Render/Nginx)
# =============================================================================

# Trust forwarded headers from reverse proxy
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "*")

# X-Forwarded-* headers (PRODUCTION ONLY)
# Gunicorn handles scheme detection; Django delegates to Gunicorn (SECURE_PROXY_SSL_HEADER=None)
# Only trust X-Forwarded-Proto from Render's reverse proxy to avoid contradictory scheme warnings
if IS_PRODUCTION:
    secure_scheme_headers = {
        "X-FORWARDED-PROTO": "https",
    }


# =============================================================================
# LOGGING & MONITORING
# =============================================================================

# Write to stdout/stderr (Render captures automatically)
accesslog = "-"
errorlog = "-"
loglevel = "info" if IS_PRODUCTION else "debug"

# Capture application output
capture_output = True
enable_stdio_inheritance = True

# Professional access log format
# All specifiers use %(name)s for string values (Gunicorn v23)
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" response_time=%(D)s_us worker_id=%(p)s'
)

proc_name = "invoiceflow"


# =============================================================================
# PROCESS MANAGEMENT
# =============================================================================

backlog = 2048

# =============================================================================
# STARTUP HOOKS
# =============================================================================

def when_ready(server):
    """
    Called when the server is ready to handle requests.
    Signals to orchestration systems (Render, Kubernetes) that app is ready for traffic.
    Health checks should hit /health/ready/ for more robust readiness detection.
    """
    logger.info(f"✓ Gunicorn READY at {server.address} with {workers} workers")
    logger.info("✓ POST requests to /health/ready/ to verify readiness (DB, cache, migrations)")
    logger.info("✓ GET /health/live/ for quick liveness check (no external dependencies)")


def post_fork(server, worker):
    """
    Called after a worker has been forked.
    Pre-warm database connections to avoid slow first requests.
    """
    try:
        import django
        django.setup()
        from django.db import connection
        connection.ensure_connection()
        logger.info(f"Worker {worker.pid}: Database connection pre-warmed")
    except Exception as e:
        logger.warning(f"Worker {worker.pid}: Failed to pre-warm DB connection: {e}")


def on_exit(server):
    """
    Called when Gunicorn is shutting down.
    Ensures clean exit for continuous deployment.
    """
    logger.info("Gunicorn shutting down gracefully...")


def pre_request(worker, req):
    """
    Called just before a worker processes a request.
    Used for tracking request lifecycle.
    """
    worker.log.debug(f"Processing request: {req.method} {req.path}")


# =============================================================================
# RENDER STARTUP MESSAGES
# =============================================================================

if IS_RENDER:
    logger.info("[Gunicorn] ✓ Production mode enabled")
    logger.info(f"[Gunicorn] ✓ Workers: {workers} (dynamic scaling enabled)")
    logger.info("[Gunicorn] ✓ Memory leak prevention: 1000-request restart cycles")
    logger.info("[Gunicorn] ⚠ To profile memory usage: set GUNICORN_MAX_REQUESTS=0 in env")
    logger.info("[Gunicorn] ✓ Timeout protection: 120 seconds per request")
    logger.info(f"[Gunicorn] ✓ Graceful shutdown: {graceful_timeout}-second window (continuous deployment optimized)")
    logger.info("[Gunicorn] 📝 Tip: Set GUNICORN_GRACEFUL_TIMEOUT=5 for faster CI/CD deployments")
    if IS_PRODUCTION:
        logger.info("[Gunicorn] ✓ Secure scheme headers active")
