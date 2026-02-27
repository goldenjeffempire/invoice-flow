"""
Cookie Consent Management for InvoiceFlow.
GDPR-compliant cookie consent handling with explicit opt-in.
"""

import json
import logging
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)

CONSENT_COOKIE_NAME = "invoiceflow_cookie_consent"
CONSENT_COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year


@csrf_protect
@require_POST
def set_cookie_consent(request):
    """
    Handle cookie consent submission.
    Stores consent preferences in a secure cookie.
    """
    try:
        data = json.loads(request.body)

        consent_data = {
            "essential": True,  # Always required
            "analytics": data.get("analytics", False),
            "marketing": data.get("marketing", False),
            "preferences": data.get("preferences", False),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        response = JsonResponse(
            {
                "success": True,
                "message": "Cookie preferences saved successfully.",
                "consent": consent_data,
            }
        )

        # Set secure cookie with consent preferences
        is_secure = request.is_secure() or getattr(settings, "IS_PRODUCTION", False)

        response.set_cookie(
            CONSENT_COOKIE_NAME,
            json.dumps(consent_data),
            max_age=CONSENT_COOKIE_MAX_AGE,
            secure=is_secure,
            httponly=True,
            samesite="Lax",
        )

        logger.info(
            f"Cookie consent set: analytics={consent_data['analytics']}, marketing={consent_data['marketing']}"
        )

        return response

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid request data.",
            },
            status=400,
        )
    except Exception as e:
        logger.error(f"Cookie consent error: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred saving preferences.",
            },
            status=500,
        )


@require_GET
def get_cookie_consent(request):
    """
    Get current cookie consent status.
    """
    consent_cookie = request.COOKIES.get(CONSENT_COOKIE_NAME, "")

    if consent_cookie:
        try:
            consent_data = json.loads(consent_cookie)
            return JsonResponse(
                {
                    "success": True,
                    "hasConsent": True,
                    "consent": consent_data,
                }
            )
        except json.JSONDecodeError:
            pass

    return JsonResponse(
        {
            "success": True,
            "hasConsent": False,
            "consent": {
                "essential": True,
                "analytics": False,
                "marketing": False,
                "preferences": False,
            },
        }
    )


@csrf_protect
@require_POST
def withdraw_cookie_consent(request):
    """
    Handle cookie consent withdrawal (GDPR right to withdraw).
    Removes all non-essential cookies and resets consent.
    """
    try:
        response = JsonResponse(
            {
                "success": True,
                "message": "Cookie consent withdrawn. Non-essential cookies have been removed.",
            }
        )

        # Delete consent cookie
        response.delete_cookie(CONSENT_COOKIE_NAME)

        # Delete any analytics/marketing cookies
        non_essential_cookies = [
            "_ga",
            "_gid",
            "_gat",  # Google Analytics
            "_fbp",
            "_fbc",  # Facebook
            "hubspotutk",  # HubSpot
        ]

        for cookie_name in non_essential_cookies:
            response.delete_cookie(cookie_name)

        logger.info("Cookie consent withdrawn")

        return response

    except Exception as e:
        logger.error(f"Cookie consent withdrawal error: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred withdrawing consent.",
            },
            status=500,
        )
