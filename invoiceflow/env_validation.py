import os
import logging
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

REQUIRED_PRODUCTION_ENV_VARS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
]

OPTIONAL_PRODUCTION_ENV_VARS = [
    "HCAPTCHA_SITEKEY",
    "HCAPTCHA_SECRET",
]

def validate_env():
    is_production = os.getenv("PRODUCTION") == "true"
    is_replit = bool(os.getenv("REPL_ID") or os.getenv("REPLIT"))
    
    missing = []
    for var in REQUIRED_PRODUCTION_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)

    if is_production and missing:
        error_msg = f"CRITICAL: Missing required environment variables in production: {', '.join(missing)}"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)
    
    if is_production:
        secret_key = os.getenv("SECRET_KEY", "")
        if secret_key.startswith("django-insecure"):
            error_msg = "CRITICAL: SECRET_KEY must not use insecure default in production"
            logger.critical(error_msg)
            raise ImproperlyConfigured(error_msg)
        
        encryption_salt = os.getenv("ENCRYPTION_SALT", "")
        if encryption_salt == "dev-salt" or not encryption_salt:
            error_msg = "CRITICAL: ENCRYPTION_SALT must be properly set in production"
            logger.critical(error_msg)
            raise ImproperlyConfigured(error_msg)
    
    if is_replit:
        logger.info("Running in Replit environment with relaxed validation")
    
    logger.info("Environment validation passed successfully")
