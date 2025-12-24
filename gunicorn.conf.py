"""
InvoiceFlow Production Gunicorn Configuration
Enterprise-Grade Server Setup - Rebuilt from Scratch
Version: 2.0.0 | November 2025

Features:
- Dynamic worker scaling based on CPU cores
- Optimized thread configuration for gthread workers
- Production-ready security settings
- Comprehensive logging with structured output
- Graceful shutdown handling
- Request timeout protection
"""

import multiprocessing
import os

# =============================================================================
# SERVER BINDING
# =============================================================================

bind = "0.0.0.0:5000"

# HTTPS support - can be overridden with --certfile and --keyfile flags
certfile = os.getenv("SSL_CERTFILE", None)
keyfile = os.getenv("SSL_KEYFILE", None)

# =============================================================================
# WORKER CONFIGURATION
# =============================================================================


def calculate_workers():
    """Calculate optimal worker count based on CPU cores."""
    cpu_count = multiprocessing.cpu_count()
    recommended = (cpu_count * 2) + 1
    max_workers = 17
    min_workers = 2
    return max(min_workers, min(recommended, max_workers))


workers = int(os.getenv("WEB_CONCURRENCY", calculate_workers()))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", 4))
worker_connections = 1000

# Connection pooling for database (Django's CONN_MAX_AGE should handle this)
# but we set reasonable TCP limits here
tcp_keepalives_idle = 5
tcp_keepalives_intvl = 1
tcp_keepalives_probes = 3

# =============================================================================
# TIMEOUTS & LIMITS
# =============================================================================

timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# =============================================================================
# APPLICATION LOADING
# =============================================================================

preload_app = True
reload = os.getenv("GUNICORN_RELOAD", "false").lower() == "true"
reload_engine = "auto"

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "*")
proxy_protocol = os.getenv("PROXY_PROTOCOL", "false").lower() == "true"

secure_scheme_headers = {
    "X-FORWARDED-PROTO": "https",
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
capture_output = True
enable_stdio_inheritance = True

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# =============================================================================
# PROCESS NAMING
# =============================================================================

proc_name = "invoiceflow"

# =============================================================================
# SERVER HOOKS
# =============================================================================


def on_starting(server):
    """Called just before the master process is initialized."""
    print("[InvoiceFlow] Starting Gunicorn server...")
    print(f"[InvoiceFlow] Workers: {workers} | Threads: {threads} | Worker Class: {worker_class}")


def on_reload(server):
    """Called when receiving SIGHUP for reloading."""
    print("[InvoiceFlow] Reloading server configuration...")


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    print(f"[InvoiceFlow] Worker {worker.pid} interrupted")


def worker_abort(worker):
    """Called when a worker receives SIGABRT."""
    print(f"[InvoiceFlow] Worker {worker.pid} aborted")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker is forked."""
    print(f"[InvoiceFlow] Worker {worker.pid} spawned")


def post_worker_init(worker):
    """Called just after a worker has initialized."""
    pass


def child_exit(server, worker):
    """Called when a worker exits."""
    print(f"[InvoiceFlow] Worker {worker.pid} exited")


def worker_exit(server, worker):
    """Called when a worker has been exited from the master process."""
    pass


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers is changed."""
    print(f"[InvoiceFlow] Worker count changed: {old_value} -> {new_value}")


def on_exit(server):
    """Called just before exiting gunicorn."""
    print("[InvoiceFlow] Server shutting down gracefully...")
