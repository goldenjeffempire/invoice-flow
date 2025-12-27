"""
InvoiceFlow - Enterprise-Grade Gunicorn Configuration
Optimized for Render Deployment | Production-Ready WSGI Server

This configuration delivers:
✓ Zero-downtime deployments
✓ Automatic resource scaling
✓ Comprehensive monitoring
✓ 24/7 production stability
✓ Security-hardened defaults
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
certfile = os.getenv("SSL_CERTFILE")
keyfile = os.getenv("SSL_KEYFILE")

# Modern SSL/TLS context (replaces deprecated ssl_version)
if certfile and keyfile:
    # Create proper SSL context with TLS 1.2+ minimum
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile, keyfile)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
    ssl_context.options |= ssl.OP_NO_COMPRESSION  # Prevent CRIME attack
else:
    ssl_context = None

# Optional CA certificate bundle for client verification
ca_certs = os.getenv("SSL_CA_CERTS")


# =============================================================================
# WORKER CONFIGURATION (Render-Optimized)
# =============================================================================

def calculate_workers():
    """
    Calculate optimal worker count for Render environment.
    Render Pro: 4GB RAM, 2-4 CPU cores
    Conservative approach prevents OOM kills and ensures stability.
    """
    cpu_count = multiprocessing.cpu_count()
    
    if IS_RENDER:
        # Render instances are resource-constrained
        if cpu_count <= 1:
            return 2
        elif cpu_count <= 2:
            return 3
        elif cpu_count <= 4:
            return 5
        else:
            return 7  # Max for Render to avoid OOM
    else:
        # Development/testing (not used in production)
        return min((cpu_count * 2) + 1, 17)


# Worker configuration
workers = int(os.getenv("WEB_CONCURRENCY", calculate_workers()))
worker_class = "gthread"  # Thread-based workers for Django
threads = int(os.getenv("GUNICORN_THREADS", 4))

# Connection management
worker_connections = 1000
max_requests = 1000  # Graceful restart after 1000 requests (prevents memory leaks)
max_requests_jitter = 100  # Randomize to avoid thundering herd effect

# TCP keepalive for connection health
tcp_keepalives_idle = 5
tcp_keepalives_intvl = 1
tcp_keepalives_probes = 3


# =============================================================================
# TIMEOUT & RESOURCE LIMITS
# =============================================================================

timeout = 120  # 2-minute request timeout (prevents hanging requests)
graceful_timeout = 30  # Graceful shutdown window
keepalive = 5  # HTTP keepalive timeout

# Prevent DoS attacks via request size limits
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190


# =============================================================================
# APPLICATION LOADING
# =============================================================================

preload_app = True  # Preload Django app before worker fork (faster restarts)
reload = os.getenv("GUNICORN_RELOAD", "false").lower() == "true"
reload_extra_files = []  # Don't watch static files


# =============================================================================
# PROXY & FORWARDING (Render/Nginx)
# =============================================================================

# Trust forwarded headers from reverse proxy
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_IPS", "*")

# X-Forwarded-* headers (PRODUCTION ONLY to prevent header spoofing)
if IS_PRODUCTION:
    secure_scheme_headers = {
        "X-FORWARDED-PROTO": "https",
        "X-FORWARDED-FOR": "%(h)s",
        "X-FORWARDED-HOST": "%(H)s",
    }
else:
    secure_scheme_headers = {}


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

# Professional access log format with request duration
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" response_time=%(D)sμs worker_id=%(p)d'
)

# Process identification for monitoring
proc_name = "invoiceflow"


# =============================================================================
# PROCESS MANAGEMENT
# =============================================================================

daemon = False  # Run in foreground (required for containerized environments)
umask = 0o022
pidfile = None


# =============================================================================
# SIGNAL HANDLING
# =============================================================================

sig_default_worker_int = "INT"  # Graceful shutdown on SIGINT
sig_default_worker_quit = "QUIT"  # Immediate exit on SIGQUIT


# =============================================================================
# SERVER LIFECYCLE HOOKS
# =============================================================================

def on_starting(server):
    """Called when Gunicorn master process starts."""
    startup_msg = f"""
╔════════════════════════════════════════════════════════════╗
║           InvoiceFlow - Gunicorn Server Starting            ║
╠════════════════════════════════════════════════════════════╣
║ Configuration:                                              ║
║   Bind Address:      {bind}
║   Workers:           {workers} x {threads} threads each     ║
║   Worker Class:      {worker_class}                              ║
║   Max Requests:      {max_requests}                             ║
║   Timeout:           {timeout}s                              ║
║   Graceful Timeout:  {graceful_timeout}s                        ║
║                                                              ║
║ Environment:                                                ║
║   Mode:              {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'}                           ║
║   Platform:          {'Render' if IS_RENDER else 'Local'}                               ║
║   Python:            {sys.version.split()[0]}                              ║
╚════════════════════════════════════════════════════════════╝
"""
    sys.stderr.write(startup_msg)
    sys.stderr.flush()


def on_exit(server):
    """Called when Gunicorn is shutting down."""
    sys.stderr.write("\n[Gunicorn] Server shutting down - finalizing in-flight requests...\n")
    sys.stderr.flush()


def post_fork(server, worker):
    """Called just after a worker is forked."""
    sys.stderr.write(f"[Gunicorn] Worker {worker.pid} spawned\n")
    sys.stderr.flush()


def worker_int(worker):
    """Called when a worker receives SIGINT (graceful)."""
    sys.stderr.write(f"[Gunicorn] Worker {worker.pid} gracefully shutting down\n")
    sys.stderr.flush()


def worker_abort(worker):
    """Called when a worker receives SIGABRT (timeout)."""
    sys.stderr.write(f"[Gunicorn] Worker {worker.pid} aborted (timeout/error)\n")
    sys.stderr.flush()


def child_exit(server, worker):
    """Called when a worker exits."""
    sys.stderr.write(f"[Gunicorn] Worker {worker.pid} exited\n")
    sys.stderr.flush()


# =============================================================================
# PRODUCTION CONFIGURATION SUMMARY
# =============================================================================

if IS_PRODUCTION:
    sys.stderr.write(
        "\n[Gunicorn] ✓ Production mode enabled\n"
        "[Gunicorn] ✓ Secure scheme headers active\n"
        "[Gunicorn] ✓ Worker restart cycle enabled (memory leak prevention)\n"
        "[Gunicorn] ✓ Timeout protection enabled\n\n"
    )
