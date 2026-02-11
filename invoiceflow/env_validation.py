import os
import logging
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Mandatory environment variables for production
REQUIRED_PRODUCTION_ENV_VARS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "ENCRYPTION_SALT",
]

def validate_env():
    """
    Validate critical environment variables for Django settings.
    Runs once per process; subsequent calls are idempotent.
    """
    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    
    # Check SECRET_KEY exists regardless of environment
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        if is_production:
            raise ImproperlyConfigured("CRITICAL: SECRET_KEY is required in production.")
        else:
            logger.warning("SECRET_KEY not set, using insecure default for development.")

    if is_production:
        missing = [var for var in REQUIRED_PRODUCTION_ENV_VARS if not os.getenv(var)]
        if missing:
            error_msg = f"CRITICAL: Missing required environment variables in production: {', '.join(missing)}"
            logger.critical(error_msg)
            raise ImproperlyConfigured(error_msg)

        # Enforce secure SECRET_KEY
        if secret_key and (secret_key.startswith("django-insecure") or len(secret_key) < 50):
            error_msg = "CRITICAL: SECRET_KEY must be a long, secure string in production"
            logger.critical(error_msg)
            raise ImproperlyConfigured(error_msg)
            
        # Enforce secure ENCRYPTION_SALT
        encryption_salt = os.getenv("ENCRYPTION_SALT", "")
        if encryption_salt in ["dev-salt", ""] or len(encryption_salt) < 32:
            error_msg = "CRITICAL: ENCRYPTION_SALT must be a long, secure string in production"
            logger.critical(error_msg)
            raise ImproperlyConfigured(error_msg)
    
    logger.info("Environment validation passed successfully")
