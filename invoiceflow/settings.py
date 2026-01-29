"""
InvoiceFlow – Production-Ready Django Settings
Domain: https://invoiceflow.com.ng
"""

from pathlib import Path
import os
import sys
from typing import Any, cast, Dict
import environ
import dj_database_url

from django.core.exceptions import ImproperlyConfigured

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

# Fail-fast environment validation
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.strip():
    if os.getenv("PRODUCTION") == "true":
        raise ImproperlyConfigured("DATABASE_URL is required and cannot be empty in production.")

IS_PRODUCTION = os.getenv("PRODUCTION") == "true" and not os.getenv("REPL_ID")
_debug_default = "false" if IS_PRODUCTION else "true"
DEBUG = os.getenv("DEBUG", _debug_default).lower() == "true"

# =============================================================================
# DOMAIN
# =============================================================================
PRODUCTION_DOMAIN = "invoiceflow.com.ng"
PRODUCTION_URL = f"https://{PRODUCTION_DOMAIN}"
SITE_URL = PRODUCTION_URL if IS_PRODUCTION else "http://localhost:5000"

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY and IS_PRODUCTION:
    raise ImproperlyConfigured("SECRET_KEY is required in production.")
SECRET_KEY = SECRET_KEY or "django-insecure-dev-only-change-in-production"

# Build ALLOWED_HOSTS based on environment
if IS_PRODUCTION:
    ALLOWED_HOSTS = [PRODUCTION_DOMAIN, f"www.{PRODUCTION_DOMAIN}"]
    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if render_hostname:
        ALLOWED_HOSTS.append(render_hostname)
else:
    ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if "*" not in host]
if not IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS.extend(["https://*.replit.dev", "https://*.repl.co"])

# Handle Replit proxy HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Security Hardening
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 1209600 # 2 weeks
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Production Security Headers
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
else:
    # Disable redirect and secure cookies in development to avoid proxy issues
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    # Allow insecure requests for the development server behind Replit proxy
    SECURE_REDIRECT_EXEMPT = [r'.*']

# Structured Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] [request_id=%(request_id)s] %(message)s',
        },
    },
    'filters': {
        'request_id': {
            '()': 'invoiceflow.logging_filters.RequestIDFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
            'filters': ['request_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

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
    "rest_framework",
    "invoices.apps.InvoicesConfig",
]

# Analytics Cache Settings
CACHE_TIMEOUT_DASHBOARD = 60
CACHE_TIMEOUT_ANALYTICS = 120
CACHE_TIMEOUT_TOP_CLIENTS = 300

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "invoiceflow.unified_middleware.UnifiedMiddleware",
    "invoiceflow.unified_middleware.OptimizedRateLimitMiddleware",
    "invoiceflow.mfa_middleware.MFAEnforcementMiddleware",
    "invoiceflow.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "invoiceflow.urls"

# =============================================================================
# TEMPLATES
# =============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

# MFA Settings
MFA_ENABLED = True
MFA_ISSUER_NAME = "InvoiceFlow"

# =============================================================================
# DATABASE
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# PostgreSQL connection using the provisioned DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Production requires a valid DATABASE_URL
if IS_PRODUCTION:
    if not DATABASE_URL:
        raise ImproperlyConfigured(
            "DATABASE_URL environment variable is required in production. "
            "Ensure exactly one non-empty DATABASE_URL is set in Render environment settings."
        )

# Only use PostgreSQL in production, use SQLite for development
if DATABASE_URL and IS_PRODUCTION:
    # Remove unsupported parameters from the connection string if they exist
    _db_url = DATABASE_URL
    if "channel_binding=" in _db_url:
        import re
        _db_url = re.sub(r'[?&]channel_binding=[^&]+', '', _db_url)
        # Fix possible leading/trailing &
        _db_url = _db_url.replace('?&', '?').rstrip('&')
    
    try:
        # Parse database URL with production-ready settings
        db_config = dj_database_url.parse(
            _db_url,
            conn_max_age=600,
            ssl_require=True
        )
        if db_config:
            # Use standard postgresql backend - Django will auto-detect psycopg version
            db_config['ENGINE'] = 'django.db.backends.postgresql'
            DATABASES["default"] = db_config
    except Exception as e:
        raise ImproperlyConfigured(f"Failed to configure database from DATABASE_URL: {e}")

# =============================================================================
# STATIC / MEDIA
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "invoices:login"
LOGIN_REDIRECT_URL = "invoices:dashboard"
LOGOUT_REDIRECT_URL = "invoices:home"
