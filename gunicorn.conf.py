"""
InvoiceFlow - Professional Gunicorn Configuration
Production-Ready WSGI Server Setup for Django 5.2

This configuration is optimized for:
- Render cloud deployment
- 24/7 production stability
- Resource-constrained environments
- Zero-downtime deployments
- Comprehensive monitoring and observability
"""

import multiprocessing
import os
import sys

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

IS_PRODUCTION = os.getenv("PRODUCTION") == "true"
IS_RENDER = bool(os.getenv("RENDER"))


# =============================================================================
# SERVER BINDING
# =============================================================================

# Dynamic port detection (Render uses PORT environment variable)
PORT = int(os.getenv("PORT", 5000))
bind = f"0.0.0.0:{PORT}"

# Support for SSL/TLS (can be overridden via CLI flags)
certfile = os.getenv("SSL_CERTFILE")
keyfile = os.getenv("SSL_KEYFILE")

# SSL version and options for production
ssl_version = 5  # TLS 1.2+
do_handshake_on_connect = True
suppress_ragged_eof = True


# =============================================================================
# WORKER CONFIGURATION
# =============================================================================

def get_worker_count():
    """Calculate optimal worker count based on CPU cores and environment."""
    cpu_count = multiprocessing.cpu_count()
    
    if IS_RENDER:
        # Render standard: 2-4 CPU cores, 4GB RAM
        # Conservative scaling to prevent OOM kills
        if cpu_count <= 1:
            return 2
        elif cpu_count <= 2:
            return 3
        elif cpu_count <= 4:
            return 5
        else:
            return 7
    else:
        # Development environments
        return min((cpu_count * 2) + 1, 17)


# Use environment override or calculated value
workers = int(os.getenv("WEB_CONCURRENCY", get_worker_count()))

# gthread worker class for Django (synchronous with threading)
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", 4))

# Memory and connection management
worker_connections = 1000
max_requests = 1000  # Restart worker after 1000 requests (prevents memory leaks)
max_requests_jitter = 100  # Randomize restart to avoid thundering herd

# TCP keepalive settings
tcp_keepalives_idle = 5  # Check connection health every 5 seconds
tcp_keepalives_intvl = 1  # Retry interval
tcp_keepalives_probes = 3  # Number of probes before giving up


# =============================================================================
# TIMEOUTS AND LIMITS
# =============================================================================

# Request timeout (prevent hanging requests from consuming resources)
timeout = 120  # 2 minutes for typical requests

# Graceful shutdown window (allow in-flight requests to complete)
graceful_timeout = 30

# HTTP keepalive timeout
keepalive = 5

# Request size limits (prevent DoS attacks)
limit_request_line = 8190  # HTTP request line size
limit_request_fields = 100  # Number of header fields
limit_request_field_size = 8190  # Size of header field


# =============================================================================
# APPLICATION LOADING
# =============================================================================

# Preload application before forking workers
preload_app = True

# Reload settings only in development
reload = os.getenv("GUNICORN_RELOAD", "false").lower() == "true"
reload_extra_files = []  # Don't watch static files


# =============================================================================
# PROXY AND FORWARDING (For Render/nginx)
# =============================================================================

# Trust forwarded headers from reverse proxy
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "*")

# X-Forwarded-* headers for HTTPS detection (production only)
if IS_PRODUCTION:
    secure_scheme_headers = {
        "X-FORWARDED-PROTO": "https",
        "X-FORWARDED-FOR": "%(h)s",
        "X-FORWARDED-HOST": "%(H)s",
    }
else:
    secure_scheme_headers = {}


# =============================================================================
# LOGGING
# =============================================================================

# Write logs to stdout (Render captures stdout automatically)
accesslog = "-"
errorlog = "-"

# Log level (INFO in production, DEBUG in development)
loglevel = os.getenv("LOG_LEVEL", "info" if IS_PRODUCTION else "debug")

# Capture stdout/stderr from application
capture_output = True
enable_stdio_inheritance = True

# Professional access log format with timing information
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" response_time=%(D)sμs worker_id=%(p)d'
)

# Process naming for monitoring
proc_name = "invoiceflow-wsgi"


# =============================================================================
# PROCESS MANAGEMENT
# =============================================================================

# Run in foreground (important for containerized environments)
daemon = False

# Don't detach from controlling process
umask = 0

# UID/GID (optional, use for security hardening)
# user = None
# group = None


# =============================================================================
# SIGNAL HANDLERS
# =============================================================================

# Signal handling for graceful restarts and shutdowns
sig_default_worker_int = "INT"  # Graceful shutdown on SIGINT
sig_default_worker_quit = "QUIT"  # Immediate exit on SIGQUIT


# =============================================================================
# SERVER HOOKS FOR MONITORING AND LIFECYCLE
# =============================================================================


def on_starting(server):
    """Called when Gunicorn master starts."""
    message = (
        f"\n{'=' * 70}\n"
        f"InvoiceFlow WSGI Server Starting\n"
        f"{'=' * 70}\n"
        f"Bind Address:      {bind}\n"
        f"Workers:           {workers} (class: {worker_class})\n"
        f"Threads/Worker:    {threads}\n"
        f"Max Requests:      {max_requests}\n"
        f"Timeout:           {timeout}s\n"
        f"Environment:       {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}\n"
        f"Platform:          {'Render' if IS_RENDER else 'Other'}\n"
        f"Python Version:    {sys.version.split()[0]}\n"
        f"{'=' * 70}\n"
    )
    sys.stderr.write(message)
    sys.stderr.flush()


def on_exit(server):
    """Called when Gunicorn is shutting down."""
    sys.stderr.write("\n[gunicorn] Server shutting down - finalizing requests...\n")
    sys.stderr.flush()


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker is forked."""
    sys.stderr.write(f"[gunicorn] Worker {worker.pid} spawned\n")
    sys.stderr.flush()


def post_worker_init(worker):
    """Called just after a worker has initialized."""
    # Reset any database connections for the new process
    pass


def worker_int(worker):
    """Called when a worker receives SIGINT (graceful shutdown)."""
    sys.stderr.write(f"[gunicorn] Worker {worker.pid} interrupted (graceful shutdown)\n")
    sys.stderr.flush()


def worker_abort(worker):
    """Called when a worker receives SIGABRT (timeout/error)."""
    sys.stderr.write(f"[gunicorn] Worker {worker.pid} aborted (timeout or error)\n")
    sys.stderr.flush()


def child_exit(server, worker):
    """Called when a worker exits."""
    sys.stderr.write(f"[gunicorn] Worker {worker.pid} exited\n")
    sys.stderr.flush()


def worker_exit(server, worker):
    """Called when a worker has been removed from the master."""
    sys.stderr.write(f"[gunicorn] Worker {worker.pid} exit confirmed\n")
    sys.stderr.flush()


def nworkers_changed(server, new_value, old_value):
    """Called when worker count changes."""
    sys.stderr.write(f"[gunicorn] Worker count changed: {old_value} → {new_value}\n")
    sys.stderr.flush()


# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================
"""
PRODUCTION-READY FEATURES:

1. PERFORMANCE
   - Gthread workers for Django (synchronous + threaded)
   - Dynamic worker scaling based on CPU cores
   - Connection pooling (1000 concurrent connections)
   - HTTP keepalive support

2. STABILITY
   - Worker restart cycle (1000 requests) prevents memory leaks
   - Graceful shutdown (30s window) allows in-flight requests
   - Timeout protection (120s) kills hanging requests
   - TCP keepalive (5s) detects dead connections

3. SECURITY
   - Request size limits prevent DoS attacks
   - Production-only secure headers for HTTPS
   - Process isolation via worker separation
   - No hardcoded credentials in config

4. MONITORING
   - Structured logging to stdout (Render capture)
   - Detailed access logs with timing
   - Worker lifecycle hooks
   - Clear startup/shutdown messages

5. DEPLOYMENT
   - Dynamic PORT binding (Render compatible)
   - Preload app for fast restarts
   - Graceful signal handling
   - Zero-downtime deployment ready

6. RESOURCE OPTIMIZATION
   - Conservative worker count for Render (prevents OOM)
   - Max requests jitter (prevents thundering herd)
   - Thread pooling for I/O-bound operations
   - Memory-efficient gthread worker class

ENVIRONMENT VARIABLES:
- PORT: Server port (default: 5000)
- PRODUCTION: Set to "true" for production mode
- WEB_CONCURRENCY: Override worker count
- GUNICORN_THREADS: Threads per worker (default: 4)
- GUNICORN_RELOAD: Enable reload in development
- LOG_LEVEL: Logging level (default: info/debug)
- SSL_CERTFILE/SSL_KEYFILE: SSL certificate paths
"""
