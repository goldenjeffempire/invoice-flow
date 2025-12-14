"""
InvoiceFlow Django Settings
Production-ready configuration for https://invoiceflow.com.ng
"""

import os
from pathlib import Path

import environ

env = environ.Env(DEBUG=(bool, False))

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# =============================================================================
# PRODUCTION DOMAIN CONFIGURATION
# =============================================================================
PRODUCTION_DOMAIN = "invoiceflow.com.ng"
PRODUCTION_URL = f"https://{PRODUCTION_DOMAIN}"

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================
IS_REPLIT = os.environ.get("REPL_ID") is not None or os.environ.get("REPLIT") is not None
IS_RENDER = os.environ.get("RENDER") is not None

# Production flag takes precedence - allows production mode on Replit
IS_PRODUCTION = os.environ.get("PRODUCTION") == "true"

# DEBUG mode: False if explicitly in production, otherwise check environment
if IS_PRODUCTION:
    DEBUG = False  # Production mode always disables debug
elif IS_REPLIT:
    DEBUG = env.bool("DEBUG", default=True)  # type: ignore  # Replit dev defaults to True
else:
    DEBUG = env.bool("DEBUG", default=False)  # type: ignore

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-CHANGE-IN-PRODUCTION")  # type: ignore

# Encryption salt for field-level encryption (bank account numbers, etc.)
ENCRYPTION_SALT = env("ENCRYPTION_SALT", default="dev-salt-only-for-local-testing")  # type: ignore

# PRODUCTION SAFETY GUARDS - enforced when IS_PRODUCTION is true
if IS_PRODUCTION:
    if SECRET_KEY.startswith("django-insecure-"):
        raise ValueError(
            "PRODUCTION ERROR: You must set a secure SECRET_KEY environment variable! "
            'Generate one with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )

    if ENCRYPTION_SALT == "dev-salt-only-for-local-testing":
        raise ValueError(
            "PRODUCTION ERROR: You must set a secure ENCRYPTION_SALT environment variable! "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )

# =============================================================================
# ALLOWED HOSTS & CSRF CONFIGURATION
# =============================================================================
if IS_PRODUCTION:
    # Production: strict allowed hosts
    allowed_hosts = env.list("ALLOWED_HOSTS", default=[PRODUCTION_DOMAIN, f".{PRODUCTION_DOMAIN}", "www." + PRODUCTION_DOMAIN])  # type: ignore
    ALLOWED_HOSTS = allowed_hosts
else:
    # Development: allow configured hosts, Replit domains, and localhost
    # Using explicit wildcard and common dev domains for reliability
    ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1", ".replit.dev", ".picard.replit.dev", ".spock.replit.dev", ".repl.co"]  # type: ignore

# CSRF Trusted Origins - Production domain first
CSRF_TRUSTED_ORIGINS = [
    f"https://{PRODUCTION_DOMAIN}",
    f"https://www.{PRODUCTION_DOMAIN}",
]

# Add development origins if in dev mode
if DEBUG or IS_REPLIT:
    CSRF_TRUSTED_ORIGINS.extend(
        [
            "https://*.replit.dev",
            "https://*.repl.co",
        ]
    )

if IS_RENDER:
    CSRF_TRUSTED_ORIGINS.extend(
        [
            "https://*.onrender.com",
            "https://*.render.com",
        ]
    )

# Override from environment if provided
_csrf_env = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if _csrf_env:
    CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf_env.split(",") if x.strip()]

# =============================================================================
# SSL & SECURITY HEADERS
# =============================================================================
# Check for SSL certificate files
HAS_SSL_CERTS = os.path.exists("/tmp/invoiceflow-certs/certificate.pem") and os.path.exists(
    "/tmp/invoiceflow-certs/private-key-rsa.pem"
)

if IS_PRODUCTION:
    # Production security hardening
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"
elif HAS_SSL_CERTS:
    # SSL certs available - enable secure settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    # Development mode - no SSL enforcement
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = "SAMEORIGIN"  # Allow iframe embedding in Replit

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
    "drf_spectacular",
    "csp",
    "invoices",
]

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "EXCEPTION_HANDLER": "invoices.api.exception_handlers.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "InvoiceFlow API",
    "DESCRIPTION": "Professional invoice management platform API for creating, managing, and tracking invoices.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
    "ENUM_NAME_OVERRIDES": {
        "InvoiceStatusEnum": "invoices.models.Invoice.STATUS_CHOICES",
        "RecurringInvoiceStatusEnum": "invoices.models.RecurringInvoice.STATUS_CHOICES",
        "ContactSubmissionStatusEnum": "invoices.models.ContactSubmission.STATUS_CHOICES",
        "StatusE4aEnum": "invoices.models.Invoice.STATUS_CHOICES",
    },
    "POSTPROCESSING_HOOKS": [],
}

# =============================================================================
# MIDDLEWARE - Optimized for Performance
# =============================================================================
# Consolidated middleware chain reduces overhead from 11+ custom middleware to 4
# See invoiceflow/unified_middleware.py for implementation details
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "invoiceflow.unified_middleware.UnifiedMiddleware",
    "invoiceflow.unified_middleware.OptimizedRateLimitMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "invoiceflow.unified_middleware.CookieConsentMiddleware",
    "invoiceflow.mfa_middleware.MFAEnforcementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
                "django.template.context_processors.media",
                "invoiceflow.context_processors.assets_config",
                "csp.context_processors.nonce",
            ],
            "builtins": [
                "django.template.defaulttags",
                "django.template.defaultfilters",
                "django.template.loader_tags",
            ],
        },
    },
]

WSGI_APPLICATION = "invoiceflow.wsgi.application"

# =============================================================================
# DATABASE
# =============================================================================
if env("DATABASE_URL", default=None):  # type: ignore
    DATABASES = {"default": env.db()}
    DATABASES["default"]["CONN_MAX_AGE"] = 600
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    DATABASES["default"]["OPTIONS"] = {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# =============================================================================
# PASSWORD VALIDATION - Enhanced Security (Phase 1)
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"max_similarity": 0.6},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},  # Increased from default 8
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {
        "NAME": "invoiceflow.password_validators.BreachedPasswordValidator",
    },
    {
        "NAME": "invoiceflow.password_validators.ComplexityValidator",
    },
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
USE_MINIFIED_ASSETS = not DEBUG

# =============================================================================
# MEDIA FILES
# =============================================================================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# AUTHENTICATION
# =============================================================================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

# =============================================================================
# SESSION SECURITY - Phase 1 Security Hardening
# =============================================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 1 week
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_NAME = "invoiceflow_session"
SESSION_COOKIE_SAMESITE = "Strict"  # Strict CSRF protection
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on every request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Secure cookies in production
if not DEBUG or IS_REPLIT:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Strict"

# =============================================================================
# ACCOUNT SECURITY SETTINGS
# =============================================================================
ACCOUNT_LOCKOUT_THRESHOLD = 5  # Lock after 5 failed attempts
ACCOUNT_LOCKOUT_DURATION = 15 * 60  # 15 minutes lockout
LOGIN_RATE_LIMIT_MAX = 10  # Max login attempts per window
LOGIN_RATE_LIMIT_WINDOW = 15 * 60  # 15 minute window
SIGNUP_RATE_LIMIT_MAX = 3  # Max signups per IP
SIGNUP_RATE_LIMIT_WINDOW = 60 * 60  # 1 hour window

# MFA Configuration
MFA_ENABLED = env.bool("MFA_ENABLED", default=True)  # type: ignore
MFA_ISSUER_NAME = "InvoiceFlow"
MFA_RECOVERY_CODES_COUNT = 10

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")  # type: ignore
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # type: ignore
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # type: ignore
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # type: ignore
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # type: ignore
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"noreply@{PRODUCTION_DOMAIN}")  # type: ignore

# =============================================================================
# LOGGING
# =============================================================================
os.makedirs(BASE_DIR / "logs", exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
        "json": {
            "()": "invoiceflow.logging_config.JsonFormatter",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        "request_context": {"()": "invoiceflow.logging_config.RequestContextFilter"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
            "filters": ["request_context"],
        },
        "file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR / "logs" / "django.log"),
            "maxBytes": 1024 * 1024 * 15,
            "backupCount": 10,
            "formatter": "json",
            "filters": ["request_context"],
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console", "file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "invoices": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# CONTENT SECURITY POLICY
# =============================================================================
if IS_PRODUCTION:
    # Production: Strict CSP with nonces
    CONTENT_SECURITY_POLICY = {
        "DIRECTIVES": {
            "default-src": ("'self'",),
            "script-src": (
                "'self'",
                "https://fonts.googleapis.com",
                "https://js.hcaptcha.com",
                "https://cdn.jsdelivr.net",
            ),
            "style-src": (
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
                "https://hcaptcha.com",
            ),
            "img-src": ("'self'", "data:", "https:", "https://ui-avatars.com"),
            "font-src": ("'self'", "https://fonts.gstatic.com", "data:"),
            "connect-src": (
                "'self'",
                PRODUCTION_URL,
                "https://hcaptcha.com",
                "https://api.hcaptcha.com",
            ),
            "frame-src": ("https://hcaptcha.com", "https://newassets.hcaptcha.com"),
            "frame-ancestors": ("'none'",),
            "base-uri": ("'self'",),
            "form-action": ("'self'",),
            "object-src": ("'none'",),
            "upgrade-insecure-requests": True,
            "block-all-mixed-content": True,
        },
        "INCLUDE_NONCE_IN": ["script-src"],
    }
else:
    # Development: More permissive CSP for Replit iframe environment
    CONTENT_SECURITY_POLICY = {
        "DIRECTIVES": {
            "default-src": ("'self'",),
            "script-src": (
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
                "https://js.hcaptcha.com",
                "https://cdn.jsdelivr.net",
            ),
            "style-src": (
                "'self'",
                "'unsafe-inline'",
                "https://fonts.googleapis.com",
                "https://hcaptcha.com",
            ),
            "img-src": ("'self'", "data:", "https:", "https://ui-avatars.com"),
            "font-src": ("'self'", "https://fonts.gstatic.com", "data:"),
            "connect-src": (
                "'self'",
                PRODUCTION_URL,
                "https://*.replit.dev",
                "https://*.repl.co",
                "https://hcaptcha.com",
                "https://api.hcaptcha.com",
            ),
            "frame-src": ("https://hcaptcha.com", "https://newassets.hcaptcha.com", "'self'"),
            "frame-ancestors": ("'self'", "https://*.replit.dev", "https://*.repl.co"),
            "base-uri": ("'self'",),
            "form-action": ("'self'",),
            "object-src": ("'none'",),
        },
        "INCLUDE_NONCE_IN": ["script-src"],
    }

# =============================================================================
# RATE LIMITING
# =============================================================================
RATELIMIT_ENABLE = not DEBUG
RATELIMIT_USE_CACHE = "default"
RATELIMIT_VIEW = "django_ratelimit.decorators.ratelimit"

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================
# Use database cache for multi-worker support (Gunicorn with 2 workers)
# Database cache is shared across workers unlike LocMemCache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "OPTIONS": {"MAX_ENTRIES": 10000},
        "TIMEOUT": 300,  # 5 minutes default
    },
    "analytics": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_analytics",
        "OPTIONS": {"MAX_ENTRIES": 5000},
        "TIMEOUT": 60,  # 1 minute for analytics (balance freshness vs performance)
    },
}

# Cache timeout settings (in seconds)
CACHE_TIMEOUT_DASHBOARD = 60  # Dashboard stats: 1 minute
CACHE_TIMEOUT_ANALYTICS = 120  # Analytics page: 2 minutes
CACHE_TIMEOUT_TOP_CLIENTS = 300  # Top clients: 5 minutes

# =============================================================================
# SESSION SECURITY (Phase 1 requirements)
# =============================================================================
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"  # Phase 1: Strict for CSRF protection
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # Extend session on activity

# =============================================================================
# CSRF SECURITY
# =============================================================================
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"  # Phase 1: Strict for enhanced security
CSRF_USE_SESSIONS = False

# =============================================================================
# HCAPTCHA CONFIGURATION (Phase 0: Contact form protection)
# =============================================================================
HCAPTCHA_SITEKEY = env("HCAPTCHA_SITEKEY", default="")  # type: ignore
HCAPTCHA_SECRET = env("HCAPTCHA_SECRET", default="")  # type: ignore
HCAPTCHA_ENABLED = bool(HCAPTCHA_SITEKEY and HCAPTCHA_SECRET)

# =============================================================================
# SENTRY ERROR TRACKING
# =============================================================================
SENTRY_DSN = env("SENTRY_DSN", default="")  # type: ignore
if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production" if IS_PRODUCTION else "development",
    )

# =============================================================================
# WEBHOOK & API CONFIGURATION
# =============================================================================
WEBHOOK_BASE_URL = env("WEBHOOK_BASE_URL", default=PRODUCTION_URL)  # type: ignore
API_BASE_URL = env("API_BASE_URL", default=PRODUCTION_URL)  # type: ignore
