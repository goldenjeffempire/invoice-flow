"""
InvoiceFlow – Production-Ready Django Settings
Domain: https://invoiceflow.com.ng
"""

from pathlib import Path
import os
from typing import Any, cast
import environ

from .env_validation import validate_env

# =============================================================================
# BASE SETUP
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))  # type: ignore[call-overload]

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
validate_env()

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================
IS_REPLIT: bool = bool(os.getenv("REPL_ID") or os.getenv("REPLIT"))
IS_RENDER: bool = bool(os.getenv("RENDER"))
IS_PRODUCTION: bool = os.getenv("PRODUCTION") == "true"

DEBUG: bool = False if IS_PRODUCTION else env.bool("DEBUG", default=IS_REPLIT)  # type: ignore[arg-type]

# =============================================================================
# DOMAIN
# =============================================================================
PRODUCTION_DOMAIN = "invoiceflow.com.ng"
PRODUCTION_URL = f"https://{PRODUCTION_DOMAIN}"

# =============================================================================
# SECURITY KEYS
# =============================================================================
SECRET_KEY: str = env("SECRET_KEY", default="django-insecure-dev-only")  # type: ignore[arg-type]
ENCRYPTION_SALT: str = env("ENCRYPTION_SALT", default="dev-salt")  # type: ignore[arg-type]

if IS_PRODUCTION:
    if SECRET_KEY.startswith("django-insecure"):
        raise RuntimeError("SECRET_KEY must be set securely in production")

    if ENCRYPTION_SALT == "dev-salt":
        raise RuntimeError("ENCRYPTION_SALT must be set in production")

# =============================================================================
# ALLOWED HOSTS / CSRF
# =============================================================================
_default_hosts: list[str] = (
    [
        PRODUCTION_DOMAIN,
        f".{PRODUCTION_DOMAIN}",
        f"www.{PRODUCTION_DOMAIN}",
        "*.onrender.com",
        "*.replit.dev",
        "*.repl.co",
    ]
    if IS_PRODUCTION
    else ["*"]
)
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=_default_hosts)  # type: ignore[arg-type]

CSRF_TRUSTED_ORIGINS: list[str] = [
    f"https://{PRODUCTION_DOMAIN}",
    f"https://www.{PRODUCTION_DOMAIN}",
]

if not IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS += [
        "https://*.replit.dev",
        "https://*.repl.co",
        "https://*.onrender.com",
    ]
else:
    CSRF_TRUSTED_ORIGINS += [
        "https://*.onrender.com",
    ]

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
SECURE_SSL_REDIRECT = IS_PRODUCTION
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_HSTS_PRELOAD = IS_PRODUCTION

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if IS_PRODUCTION else None

X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_EMBEDDER_POLICY = "require-corp"

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

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "invoiceflow.unified_middleware.UnifiedMiddleware",
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

# =============================================================================
# DATABASE
# =============================================================================
database_url = env("DATABASE_URL", default=None)  # type: ignore[arg-type]
if database_url:
    DATABASES: dict[str, dict[str, Any]] = {
        "default": {
            **env.db(),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
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

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

# =============================================================================
# SESSION SECURITY
# =============================================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
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
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
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
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/django.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "formatter": "json",
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
        "default-src": ("'self'",),
        "script-src": ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://js.hcaptcha.com"),
        "style-src": ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com"),
        "img-src": ("'self'", "data:", "https:"),
        "font-src": ("'self'", "https://fonts.gstatic.com"),
        "connect-src": ("'self'", PRODUCTION_URL),
        "frame-src": ("https://hcaptcha.com",),
        "object-src": ("'none'",),
    },
    "INCLUDE_NONCE_IN": ["script-src", "style-src"],
}

# =============================================================================
# EMAIL
# =============================================================================
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = env("EMAIL_HOST", default="smtp.gmail.com")  # type: ignore[arg-type]
EMAIL_PORT: int = env.int("EMAIL_PORT", default=587)  # type: ignore[arg-type]
EMAIL_USE_TLS: bool = True
EMAIL_HOST_USER: str = env("EMAIL_HOST_USER", default="")  # type: ignore[arg-type]
EMAIL_HOST_PASSWORD: str = env("EMAIL_HOST_PASSWORD", default="")  # type: ignore[arg-type]
DEFAULT_FROM_EMAIL: str = f"noreply@{PRODUCTION_DOMAIN}"

# =============================================================================
# THIRD-PARTY
# =============================================================================
HCAPTCHA_SITEKEY: str = env("HCAPTCHA_SITEKEY", default="")  # type: ignore[arg-type]
HCAPTCHA_SECRET: str = env("HCAPTCHA_SECRET", default="")  # type: ignore[arg-type]
HCAPTCHA_ENABLED: bool = bool(HCAPTCHA_SITEKEY and HCAPTCHA_SECRET)

# =============================================================================
# API / WEBHOOKS
# =============================================================================
API_BASE_URL: str = env("API_BASE_URL", default=PRODUCTION_URL)  # type: ignore[arg-type]
WEBHOOK_BASE_URL: str = env("WEBHOOK_BASE_URL", default=PRODUCTION_URL)  # type: ignore[arg-type]
