import os
from django.core.exceptions import ImproperlyConfigured

REQUIRED_ENV_VARS = [
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "EMAIL_HOST",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "DEFAULT_FROM_EMAIL",
    "ALLOWED_HOSTS",
]

def validate_env():
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise ImproperlyConfigured(
            f"Missing required environment variables: {', '.join(missing)}"
        )
