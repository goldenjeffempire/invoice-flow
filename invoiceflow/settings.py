"""
InvoiceFlow – Production-Ready Django Settings
Domain: https://invoiceflow.com.ng
"""

from pathlib import Path
import os
import sys
from typing import Any, cast
import environ

from .env_validation import validate_env

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))  # type: ignore[call-overload]

_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    environ.Env.read_env(_env_file)

validate_env()

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================
IS_RENDER: bool = bool(os.getenv("RENDER"))
IS_PRODUCTION: bool = os.getenv("PRODUCTION") == "true" and not os.getenv("REPL_ID")
RUNNING_TESTS: bool = "pytest" in sys.modules

DEBUG: bool = env.bool("DEBUG", False) if not IS_PRODUCTION else False

# =============================================================================
# DOMAIN
# =============================================================================
PRODUCTION_DOMAIN = "invoiceflow.com.ng"
PRODUCTION_URL = f"https://{PRODUCTION_DOMAIN}"

# =============================================================================
# SECURITY KEYS
# =============================================================================
SECRET_KEY: str = env.str("SECRET_KEY", "django-insecure-dev-only")
ENCRYPTION_SALT: str = env.str("ENCRYPTION_SALT", "dev-salt")

if IS_PRODUCTION:
    if SECRET_KEY.startswith("django-insecure"):
        raise RuntimeError("SECRET_KEY must be set securely in production")

    if ENCRYPTION_SALT == "dev-salt":
        raise RuntimeError("ENCRYPTION_SALT must be set in production")

# =============================================================================
# ALLOWED HOSTS / CSRF
# =============================================================================
_default_hosts: list[str]
if IS_PRODUCTION:
    _default_hosts = [PRODUCTION_DOMAIN, f"www.{PRODUCTION_DOMAIN}"]
else:
    _default_hosts = ["127.0.0.1", "localhost", "0.0.0.0", ".replit.dev"]
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=_default_hosts)  # type: ignore[arg-type]

# Ensure we support both the internal and external Replit domain formats
if "REPLIT_DEV_DOMAIN" in os.environ:
    ALLOWED_HOSTS.append(os.environ["REPLIT_DEV_DOMAIN"])
if "REPLIT_DOMAINS" in os.environ:
    for domain in os.environ["REPLIT_DOMAINS"].split(","):
        if domain not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(domain)
# Optional dev escape hatch (never enabled by default).
if not IS_PRODUCTION and env.bool("ALLOW_ALL_HOSTS_DEV", default=False):
    ALLOWED_HOSTS.append("*")

CSRF_TRUSTED_ORIGINS: list[str] = [
    f"https://{PRODUCTION_DOMAIN}",
    f"https://www.{PRODUCTION_DOMAIN}",
]

if not IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS += [
        "https://*.onrender.com",
        "https://*.replit.dev",
        "https://*.repl.co",
    ]

# Replit Specific CSRF Trusted Origins (non-production only)
if not IS_PRODUCTION and "REPLIT_DEV_DOMAIN" in os.environ:
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['REPLIT_DEV_DOMAIN']}")

csrf_origins_env = os.getenv("CSRF_TRUSTED_ORIGINS")
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS = [
        x.strip()
        for x in csrf_origins_env.split(",")
        if x.strip()
    ]

# =============================================================================
# SECURITY HEADERS (HARDENED)
# =============================================================================
SECURE_SSL_REDIRECT = False if RUNNING_TESTS else env.bool("SECURE_SSL_REDIRECT", IS_PRODUCTION)

# Secure cookies only in production (prevents conflicts with HTTP in development)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_HSTS_SECONDS = 0 if RUNNING_TESTS else env.int("SECURE_HSTS_SECONDS", 31536000 if IS_PRODUCTION else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False if RUNNING_TESTS else env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", IS_PRODUCTION)
SECURE_HSTS_PRELOAD = False if RUNNING_TESTS else env.bool("SECURE_HSTS_PRELOAD", IS_PRODUCTION)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Proxy SSL header detection
# Note: Gunicorn handles X-Forwarded-Proto via secure_scheme_headers in production
# Do NOT duplicate this in Django to avoid contradictory scheme headers warnings
# Setting this to None lets Gunicorn's secure_scheme_headers handle the detection
SECURE_PROXY_SSL_HEADER = None

X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_EMBEDDER_POLICY = "require-corp"

# =============================================================================
# TIMEZONE
# =============================================================================
TIME_ZONE = "UTC"
USE_TZ = True

PERMISSIONS_POLICY = {
    "accelerometer": "():",
    "camera": "():",
    "geolocation": "():",
    "gyroscope": "():",
    "magnetometer": "():",
    "microphone": "():",
    "payment": "():",
    "usb": "():",
}

# =============================================================================
# CACHING (Optimized for Production)
# =============================================================================
_redis_url = env.str("REDIS_URL", "")
# On Replit, we use local memory cache if Redis is not configured
if not _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        },
        "analytics": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "analytics-data",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        },
        "analytics": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{_redis_url}/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "TIMEOUT": 300,
        }
    }

# =============================================================================
# RATE LIMITING
# =============================================================================
RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", True)
RATELIMIT_USE_CACHE = "default"
RATELIMIT_DEFAULT_LIMIT = env.str("RATELIMIT_DEFAULT_LIMIT", "100/m")
CACHE_TIMEOUT_DASHBOARD = env.int("CACHE_TIMEOUT_DASHBOARD", 300)
CACHE_TIMEOUT_ANALYTICS = env.int("CACHE_TIMEOUT_ANALYTICS", 600)
CACHE_TIMEOUT_TOP_CLIENTS = env.int("CACHE_TIMEOUT_TOP_CLIENTS", 1800)

# =============================================================================
# INSTALLED APPS
# =============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",

    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "csp",
    "invoices.apps.InvoicesConfig",
]

INTERNAL_IPS = ["127.0.0.1"]

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "invoiceflow.unified_middleware.UnifiedMiddleware",
    "invoiceflow.performance_middleware.PerformanceMonitoringMiddleware",
    "invoiceflow.unified_middleware.OptimizedRateLimitMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "invoiceflow.mfa_middleware.MFAEnforcementMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "invoiceflow.urls"
WSGI_APPLICATION = "invoiceflow.wsgi.application"

# Silence RuntimeWarnings for model re-registration (common in dev environments with reloaders)
SILENCED_SYSTEM_CHECKS = ["models.W001", "models.W036", "models.W035"]

# Disable ETag generation to prevent 304 issues during development and ensure consistent production behavior
USE_ETAGS = False

# Cache Headers Control
# In development (DEBUG=True), we disable aggressive caching to allow immediate updates
# In production, we use 1 year for immutable assets
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0
# Static asset handling optimization
WHITENOISE_KEEP_ONLY_HASHED_FILES = not DEBUG
WHITENOISE_MANIFEST_STRICT = not DEBUG
# =============================================================================
# DATABASE
# =============================================================================
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# =============================================================================
# CSRF TRUSTED ORIGINS
# =============================================================================
CSRF_TRUSTED_ORIGINS: list[str] = [
    f"https://{PRODUCTION_DOMAIN}",
    f"https://www.{PRODUCTION_DOMAIN}",
]

if not IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS += [
        "https://*.onrender.com",
        "https://*.replit.dev",
        "https://*.repl.co",
    ]

# Replit Specific CSRF Trusted Origins (non-production only)
if "REPLIT_DEV_DOMAIN" in os.environ:
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['REPLIT_DEV_DOMAIN']}")
if "REPLIT_DOMAINS" in os.environ:
    for domain in os.environ["REPLIT_DOMAINS"].split(","):
        CSRF_TRUSTED_ORIGINS.append(f"https://{domain}")
