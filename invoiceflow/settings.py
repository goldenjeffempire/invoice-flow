"""
InvoiceFlow – Production-Ready Django Settings
Domain: https://invoiceflow.com.ng
"""

from pathlib import Path
import os
import sys
from typing import Any, cast
import environ
import dj_database_url

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))

_env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_file):
    environ.Env.read_env(_env_file)

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================
IS_PRODUCTION = os.getenv("PRODUCTION") == "true" and not os.getenv("REPL_ID")
DEBUG = env.bool("DEBUG", not IS_PRODUCTION)

# =============================================================================
# DOMAIN
# =============================================================================
PRODUCTION_DOMAIN = "invoiceflow.com.ng"
PRODUCTION_URL = f"https://{PRODUCTION_DOMAIN}"

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = env.str("SECRET_KEY", "django-insecure-dev-only")
DEBUG = env.bool("DEBUG", False)

ALLOWED_HOSTS = [
    "invoiceflow.com.ng",
    "*.replit.dev",
    "*.repl.co",
    "0.0.0.0",
    "localhost",
    "127.0.0.1",
]

if os.getenv("REPLIT_DEV_DOMAIN"):
    ALLOWED_HOSTS.append(os.getenv("REPLIT_DEV_DOMAIN"))

CSRF_TRUSTED_ORIGINS = [
    "https://*.replit.dev",
    "https://*.repl.co",
    f"https://{PRODUCTION_DOMAIN}",
]
if os.getenv("REPLIT_DEV_DOMAIN"):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['REPLIT_DEV_DOMAIN']}")

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
    "tailwind",
    "theme",
]

# Tailwind Configuration
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ["127.0.0.1"]

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
    "invoiceflow.performance_middleware.PerformanceMonitoringMiddleware",
    "invoiceflow.unified_middleware.UnifiedMiddleware",
    "invoiceflow.unified_middleware.OptimizedRateLimitMiddleware",
    "invoiceflow.mfa_middleware.MFAEnforcementMiddleware",
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
if os.getenv("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=False)

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
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "invoices:login"
LOGIN_REDIRECT_URL = "invoices:dashboard"
LOGOUT_REDIRECT_URL = "invoices:home"
