"""
InvoiceFlow – Production-Ready Django Settings
Domain: https://invoiceflow.com.ng
"""

from pathlib import Path
import os
import re
import environ
import dj_database_url

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

IS_PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# =============================================================================
# ENVIRONMENT VALIDATION (FAIL-FAST)
# =============================================================================
from invoiceflow.env_validation import validate_env
validate_env()

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-in-production")

# Build ALLOWED_HOSTS based on environment
if IS_PRODUCTION:
    PRODUCTION_DOMAIN = "invoiceflow.com.ng"
    ALLOWED_HOSTS = [PRODUCTION_DOMAIN, f"www.{PRODUCTION_DOMAIN}", "localhost", "127.0.0.1"]
    render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if render_hostname:
        ALLOWED_HOSTS.append(render_hostname)
    # Allow all Replit preview/deploy domains
    ALLOWED_HOSTS += [
        ".replit.dev",
        ".repl.co",
        ".replit.app",
        ".riker.replit.dev",
    ]
else:
    ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS
    if "*" not in host and not host.startswith(".")
]
CSRF_TRUSTED_ORIGINS += [
    "https://*.replit.dev",
    "https://*.repl.co",
    "https://*.replit.app",
    "https://*.riker.replit.dev",
]

# Handle proxy HTTPS
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
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_SAVE_EVERY_REQUEST = True
CSRF_USE_SESSIONS = True

# Detect Replit environment (proxy handles HTTPS termination)
IS_REPLIT = bool(os.getenv("REPLIT_DOMAINS") or os.getenv("REPL_ID") or os.getenv("REPLIT_DEV_DOMAIN"))

# Production Security Headers
if IS_PRODUCTION:
    # Replit terminates SSL at the proxy — don't redirect internally
    SECURE_SSL_REDIRECT = not IS_REPLIT
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

    # Hardened CSP (django-csp 4.0+ format)
    CONTENT_SECURITY_POLICY = {
        "DIRECTIVES": {
            "default-src": ("'self'",),
            "style-src": ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"),
            "script-src": ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"),
            "font-src": ("'self'", "https://fonts.gstatic.com"),
            "img-src": ("'self'", "data:", "https:"),
        }
    }

    SILENCED_SYSTEM_CHECKS = ["security.W001", "security.W004", "security.W008", "security.W012", "security.W018", "security.W009"]
else:
    DEBUG = True
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_REDIRECT_EXEMPT = [r'.*']

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_EXEMPT_PATHS = os.getenv("RATE_LIMIT_EXEMPT_PATHS", "/static/,/media/").split(",")

RATELIMIT_ENABLE = RATE_LIMIT_ENABLED
RATELIMIT_USE_CACHE = 'default'
ACCOUNT_LOCKOUT_THRESHOLD = int(os.getenv("ACCOUNT_LOCKOUT_THRESHOLD", "5"))
ACCOUNT_LOCKOUT_DURATION = int(os.getenv("ACCOUNT_LOCKOUT_DURATION", "900")) # 15 mins

# Password Policy
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

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
            '()': 'invoiceflow.middleware.RequestIDFilter',
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
        'level': 'WARNING' if IS_PRODUCTION else 'INFO',
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
    "csp",
    "invoices.apps.InvoicesConfig",
]

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=IS_PRODUCTION
    )
}

if DATABASE_URL and IS_PRODUCTION:
    # Strip unsupported params for production PostgreSQL (e.g. Neon)
    clean_url = re.sub(r'[?&]channel_binding=[^&]+', '', DATABASE_URL).replace('?&', '?').rstrip('&')
    DATABASES["default"] = dj_database_url.parse(
        clean_url,
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True
    )
    DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10, "sslmode": "require"}

# =============================================================================
# CACHING & PERFORMANCE
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

if IS_PRODUCTION:
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        CACHES["default"] = {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
            }
        }

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
    "csp.middleware.CSPMiddleware",
    "invoiceflow.middleware.RequestIDMiddleware",
    "invoices.validation.middleware.ErrorHandlingMiddleware",
]

ROOT_URLCONF = "invoiceflow.urls"

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
                "invoices.context_processors.workspace_context",
            ],
        },
    }
]

# =============================================================================
# WSGI / ASGI
# =============================================================================
WSGI_APPLICATION = "invoiceflow.wsgi.application"
ASGI_APPLICATION = "invoiceflow.asgi.application"

# =============================================================================
# INTERNATIONALISATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# =============================================================================
# EMAIL
# =============================================================================
if IS_PRODUCTION:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "apikey")
    EMAIL_HOST_PASSWORD = os.getenv("SENDGRID_API_KEY", "")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "InvoiceFlow <noreply@invoiceflow.com.ng>")
    SERVER_EMAIL = os.getenv("SERVER_EMAIL", "errors@invoiceflow.com.ng")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "InvoiceFlow Dev <dev@localhost>"

EMAIL_TIMEOUT = 10  # seconds before giving up on SMTP

# =============================================================================
# MEDIA FILES (user uploads – receipts, logos, etc.)
# =============================================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Hard limits for uploads (prevent DoS via oversized files)
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024    # 5 MB (in-memory threshold)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB (total POST body)
FILE_UPLOAD_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"]

# =============================================================================
# SENTRY (Error Monitoring)
# =============================================================================
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN and IS_PRODUCTION:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    import logging as _logging

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            LoggingIntegration(
                level=_logging.WARNING,
                event_level=_logging.ERROR,
            ),
        ],
        traces_sample_rate=0.1,    # 10 % of transactions for performance monitoring
        profiles_sample_rate=0.05,  # 5 % profiling
        send_default_pii=False,
        environment="production",
        release=os.getenv("APP_VERSION", "1.0.0"),
        before_send=lambda event, hint: event,
    )

# =============================================================================
# INTERNAL IPS (Django Debug Toolbar etc.)
# =============================================================================
INTERNAL_IPS = ["127.0.0.1", "::1"]

# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "EXCEPTION_HANDLER": "invoices.validation.api_exceptions.custom_exception_handler",
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# AUTH REDIRECTS
# =============================================================================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/invoices/"
LOGOUT_REDIRECT_URL = "/"
