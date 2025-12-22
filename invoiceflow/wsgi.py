"""
WSGI config for invoiceflow project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoiceflow.settings")

from django.conf import settings

from invoiceflow.env_validation import validate_env

validate_env()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
