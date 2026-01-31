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
    raise ImproperlyConfigured("DATABASE_URL environment variable is required.")

IS_PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

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
    # In development, prioritize Replit domains for correctness
    ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if "*" not in host]
if not IS_PRODUCTION:
    # Explicitly trust Replit origins for CSRF
    CSRF_TRUSTED_ORIGINS.extend(["https://*.replit.dev", "https://*.repl.co", "https://*.replit.app"])

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

# Security Headers & Rotation
SESSION_SAVE_EVERY_REQUEST = True  # Facilitates session rotation on some level
CSRF_USE_SESSIONS = True           # Store CSRF token in session instead of cookie for extra security
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# Email Configuration
if IS_PRODUCTION:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "apikey")
    EMAIL_HOST_PASSWORD = os.getenv("SENDGRID_API_KEY")
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@invoiceflow.com.ng")
else:
    # Use console backend for development
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "noreply@invoiceflow.replit.dev"

# Replit Mail Integration (if available)
REPLIT_MAIL_ENABLED = True

# Rate Limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
ACCOUNT_LOCKOUT_THRESHOLD = 5
ACCOUNT_LOCKOUT_DURATION = 900 # 15 minutes

# Password Policy and Hashing
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

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
    "invoices.validation.middleware.ErrorHandlingMiddleware",
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

# Only use PostgreSQL
if DATABASE_URL:
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
            ssl_require=IS_PRODUCTION  # Only require SSL in production
        )
        if db_config:
            # Fix for dj_database_url returning empty string engine or mismatched engine
            if not db_config.get('ENGINE') or db_config['ENGINE'] == 'django.db.backends.':
                db_config['ENGINE'] = 'django.db.backends.postgresql'
            DATABASES["default"] = dict(db_config)
    except Exception as e:
        # Fallback to default postgres engine if parsing succeeds but something is off
        try:
            db_config = dj_database_url.config(default=_db_url, conn_max_age=600, ssl_require=IS_PRODUCTION)
            if db_config:
                if not db_config.get('ENGINE') or db_config['ENGINE'] == 'django.db.backends.':
                    db_config['ENGINE'] = 'django.db.backends.postgresql'
                DATABASES["default"] = dict(db_config)
            else:
                raise e
        except:
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

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "invoices.validation.api_exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "NON_FIELD_ERRORS_KEY": "__all__",
}

# =============================================================================
# ENVIRONMENT VALIDATION (FAIL-FAST)
# =============================================================================
# Run validation at the end of settings to ensure all required vars are set
from invoiceflow.env_validation import validate_env
validate_env()
