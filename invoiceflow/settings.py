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
IS_PRODUCTION: bool = os.getenv("PRODUCTION") == "true"
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
ALLOWED_HOSTS.append("*")  # Temporarily allow all for replit preview if needed, but we should be specific

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
else:
    CSRF_TRUSTED_ORIGINS += [
        "https://*.onrender.com",
        "https://*.replit.dev",
        "https://*.repl.co",
    ]

# Replit Specific CSRF Trusted Origins
if "REPLIT_DEV_DOMAIN" in os.environ:
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
SESSION_COOKIE_SECURE = False if RUNNING_TESTS else env.bool("SESSION_COOKIE_SECURE", IS_PRODUCTION)
CSRF_COOKIE_SECURE = False if RUNNING_TESTS else env.bool("CSRF_COOKIE_SECURE", IS_PRODUCTION)

# HttpOnly always enabled (no JavaScript access to cookies)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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
if IS_PRODUCTION and not _redis_url:
    raise RuntimeError("REDIS_URL must be set in production for shared caching.")
if _redis_url:
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
else:
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
    "tailwind",
    "theme",
    "invoices.apps.InvoicesConfig",
]

TAILWIND_APP_NAME = 'theme'

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
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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
                "csp.context_processors.nonce",
                "invoiceflow.context_processors.assets_config",
            ],
        },
    }
]

# =============================================================================
# AUTH & PASSWORD SECURITY
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "invoiceflow.password_validators.ComplexityValidator"},
    {"NAME": "invoiceflow.password_validators.BreachedPasswordValidator"},
]

LOGIN_URL = "invoices:login"
LOGIN_REDIRECT_URL = "invoices:dashboard"
LOGOUT_REDIRECT_URL = "invoices:home"

# =============================================================================
# ACCOUNT LOCKOUT / MFA
# =============================================================================
ACCOUNT_LOCKOUT_THRESHOLD = env.int("ACCOUNT_LOCKOUT_THRESHOLD", 5)
ACCOUNT_LOCKOUT_DURATION = env.int("ACCOUNT_LOCKOUT_DURATION", 900)

MFA_ENABLED = env.bool("MFA_ENABLED", False)
MFA_ISSUER_NAME = env.str("MFA_ISSUER_NAME", "InvoiceFlow")
MFA_RECOVERY_CODES_COUNT = env.int("MFA_RECOVERY_CODES_COUNT", 10)

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_REQUESTS = env.int("RATE_LIMIT_REQUESTS", 120)
RATE_LIMIT_WINDOW = env.int("RATE_LIMIT_WINDOW", 60)
PAYSTACK_WEBHOOK_RATE_LIMIT = env.int("PAYSTACK_WEBHOOK_RATE_LIMIT", 120)
PAYSTACK_WEBHOOK_RATE_WINDOW = env.int("PAYSTACK_WEBHOOK_RATE_WINDOW", 60)

# =============================================================================
# SESSION SECURITY
# =============================================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_NAME = "invoiceflow_session"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# =============================================================================
# STATIC / MEDIA
# =============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Enhanced WhiteNoise Configuration for Caching
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_IMMUTABLE_FILE_SUPPORT = not DEBUG
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "invoices.api.rate_limiting.AnonBurstThrottle",
        "invoices.api.rate_limiting.UserBurstThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user_burst": "100/hour",
        "user_sustained": "1000/day",
        "anon_burst": "20/hour",
        "payment": "5/hour",
        "public_invoice": "30/hour",
    },
    "EXCEPTION_HANDLER": "invoices.api.exception_handlers.custom_exception_handler",
}

# =============================================================================
# DJANGO REST FRAMEWORK SPECTACULAR (API SCHEMA)
# =============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "InvoiceFlow API",
    "DESCRIPTION": "Professional invoicing platform API",
    "VERSION": "1.0.0",
    "SKIP_VIEW_PERMISSIONS": True,
    "SKIP_VALIDATION": True,
    "COERCE_DECIMAL_TO_STRING": True,
    "ENABLE_SPECTACULAR_DEFAULTS": True,
    "PREFER_HTTPS": not DEBUG,
    "ENUM_MAPPING_FAIL_SAFE": True,
    "DISABLE_ENUM_COERCION": True,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]",
    "SCHEMA_EXEMPT_VIEWS": [
        "django.views.static.serve",
        "rest_framework.decorators.api_view",
    ],
    "ALLOWED_HOSTS": ALLOWED_HOSTS,
    "AUTHENTICATION_FLOWS": {
        "basicAuth": {
            "type": "http",
            "scheme": "basic",
        },
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
        },
    },
    "OPERATION_ID_BASE": "openapi_auto_schema",
    "DEFAULT_GENERATOR_CLASS": "drf_spectacular.generators.SchemaGenerator",
    "ENUM_NAME_OVERRIDES": {},
    "POSTPROCESSING_HOOKS": ["invoiceflow.spectacular_hooks.postprocess_schema_enums"],
}

# =============================================================================
# LOGGING
# =============================================================================
os.makedirs(BASE_DIR / "logs", exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "invoiceflow.logging_config.RequestContextFilter",
        },
        "pii_scrubber": {
            "()": "invoiceflow.logging_config.PiiScrubberFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "json": {
            "()": "invoiceflow.logging_config.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if IS_PRODUCTION else "verbose",
            "filters": ["request_context", "pii_scrubber"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/django.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "formatter": "json",
            "filters": ["request_context", "pii_scrubber"],
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

# =============================================================================
# CONTENT SECURITY POLICY
# =============================================================================
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'", "https:"),
        "script-src": ("'self'", "'unsafe-inline'", "'unsafe-eval'", "https:", "https://unpkg.com"),
        "style-src": ("'self'", "'unsafe-inline'", "https:", "https://fonts.googleapis.com"),
        "img-src": ("'self'", "data:", "https:"),
        "font-src": ("'self'", "data:", "https:", "https://fonts.gstatic.com"),
        "connect-src": ("'self'", "https:"),
        "frame-src": ("'self'", "https:"),
        "object-src": ("'none'",),
    },
    "INCLUDE_NONCE_IN": ["script-src", "style-src"],
}

# =============================================================================
# EMAIL
# =============================================================================
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = env.str("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT: int = env.int("EMAIL_PORT", 587)
EMAIL_USE_TLS: bool = True
EMAIL_HOST_USER: str = env.str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = env.str("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL: str = f"noreply@{PRODUCTION_DOMAIN}"

# =============================================================================
# THIRD-PARTY
# =============================================================================
HCAPTCHA_SITEKEY: str = env.str("HCAPTCHA_SITEKEY", "")
HCAPTCHA_SECRET: str = env.str("HCAPTCHA_SECRET", "")
HCAPTCHA_ENABLED: bool = bool(HCAPTCHA_SITEKEY and HCAPTCHA_SECRET)

# =============================================================================
# API / WEBHOOKS
# =============================================================================
API_BASE_URL: str = env.str("API_BASE_URL", PRODUCTION_URL)
WEBHOOK_BASE_URL: str = env.str("WEBHOOK_BASE_URL", PRODUCTION_URL)
SITE_URL: str = env.str("SITE_URL", PRODUCTION_URL)
