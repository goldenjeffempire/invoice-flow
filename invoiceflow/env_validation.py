import os
from django.core.exceptions import ImproperlyConfigured

REQUIRED_PRODUCTION_ENV_VARS = [
    "SECRET_KEY",
    "DATABASE_URL",
]

def validate_env():
    is_production = os.getenv("PRODUCTION") == "true"
    
    if not is_production:
        return
    
    missing = []
    for var in REQUIRED_PRODUCTION_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise ImproperlyConfigured(
            f"Missing required environment variables: {', '.join(missing)}"
        )
