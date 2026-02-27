"""
InvoiceFlow - Production WSGI Application
Enterprise-Grade Configuration for Gunicorn Deployment

This module:
- Initializes Django settings for production
- Validates environment configuration
- Applies WSGI middleware optimizations
- Handles graceful error handling
"""

import os
import sys
import logging

# Configure logging early for startup diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# DJANGO INITIALIZATION
# =============================================================================

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoiceflow.settings")

# Import and validate environment before creating WSGI app
try:
    from invoiceflow.env_validation import validate_env
    validate_env()
    # Validation logger already outputs; WSGI just notes success
except Exception as e:
    logger.critical(f"Environment validation failed: {e}")
    sys.exit(1)

# Get WSGI application
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    logger.critical(f"Failed to initialize Django WSGI: {e}")
    sys.exit(1)

# =============================================================================
# WSGI MIDDLEWARE STACK (Optional enhancements)
# =============================================================================

# The application is ready for production deployment via Gunicorn
# All Django middleware is configured via settings.py

if __name__ == "__main__":
    logger.warning("Running WSGI app directly (should use Gunicorn in production)")
