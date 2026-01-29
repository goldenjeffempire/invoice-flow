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

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    environ.Env.read_env(_env_file)

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================
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
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-in-production")

ALLOWED_HOSTS = [
    "*",
    "invoiceflow.com.ng",
    "www.invoiceflow.com.ng",
    "*.replit.dev",
    "*.repl.co",
    "*.onrender.com",
    "0.0.0.0",
    "localhost",
    "127.0.0.1",
    "invoice-flow-7vu0.onrender.com",
]

if os.getenv("REPLIT_DEV_DOMAIN"):
    replit_domain = os.getenv("REPLIT_DEV_DOMAIN")
    if replit_domain:
        ALLOWED_HOSTS.append(replit_domain)

CSRF_TRUSTED_ORIGINS = [
    "https://*.replit.dev",
    "https://*.repl.co",
    "https://invoiceflow.com.ng",
    "https://www.invoiceflow.com.ng",
    "https://invoice-flow-7vu0.onrender.com",
]
if os.getenv("REPLIT_DEV_DOMAIN"):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['REPLIT_DEV_DOMAIN']}")

# Production Security Headers
if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    
    # CSP Settings
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "unpkg.com")
    CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
else:
    SECURE_SSL_REDIRECT = False

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
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.strip():
    import dj_database_url
    try:
        # Use conn_max_age to keep connections alive
        db_config = dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
        if db_config:
            # Check if psycopg2 or psycopg is available before setting engine
            try:
                import psycopg2
                db_config['ENGINE'] = 'django.db.backends.postgresql'
                DATABASES["default"] = db_config
            except ImportError:
                try:
                    import psycopg
                    db_config['ENGINE'] = 'django.db.backends.postgresql'
                    DATABASES["default"] = db_config
                except ImportError:
                    import sys
                    sys.stderr.write("WARNING: No PostgreSQL driver found. Falling back to SQLite.\n")
    except Exception as e:
        import sys
        sys.stderr.write(f"Warning: Failed to configure database from DATABASE_URL: {e}\n")

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
