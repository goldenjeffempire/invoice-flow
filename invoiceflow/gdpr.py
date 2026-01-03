"""
GDPR Compliance Endpoints for InvoiceFlow.
Implements Subject Access Request (SAR), data export, and deletion.
All requests are persisted to database for audit trail and compliance tracking.
"""

import json
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)
User = get_user_model()


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def send_gdpr_email(subject, message, recipient_list, gdpr_request=None):
    """
    Send GDPR-related email with error tracking.
    Returns True if successful, False otherwise.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        if gdpr_request:
            gdpr_request.email_sent = True
            gdpr_request.save(update_fields=["email_sent"])
        return True
    except Exception as e:
        logger.error(f"GDPR email delivery failed: {e}")
        if gdpr_request:
            gdpr_request.email_error = str(e)
            gdpr_request.save(update_fields=["email_error"])
        return False


@login_required
@require_GET
def export_user_data(request):
    """
    GDPR Article 20 - Right to Data Portability.
    Export all user data in machine-readable format (JSON).
    """
    from django.apps import apps
    GDPRRequest = apps.get_model('invoices', 'GDPRRequest')

    try:
        user = request.user

        gdpr_request = GDPRRequest.objects.create(
            user=user,
            user_email=user.email,
            user_username=user.username,
            request_type="data_export",
            status="completed",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        user_data = {
            "personal_information": {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "format_version": "1.0",
                "platform": "InvoiceFlow",
                "request_id": gdpr_request.id,
            },
        }

        try:
            Invoice = apps.get_model('invoices', 'Invoice')
            UserProfile = apps.get_model('invoices', 'UserProfile')

            profile = UserProfile.objects.filter(user=user).first()
            if profile:
                user_data["business_profile"] = {
                    "company_name": profile.company_name or "",
                    "company_address": profile.business_address or "",
                    "phone": profile.business_phone or "",
                    "website": "",
                    "tax_number": "",
                }

            invoices = Invoice.objects.filter(user=user)
            user_data["invoices"] = [
                {
                    "invoice_number": inv.invoice_number,
                    "client_name": inv.client_name,
                    "client_email": inv.client_email,
                    "amount": str(inv.total_amount) if hasattr(inv, "total_amount") else "0",
                    "status": inv.status,
                    "created_at": inv.created_at.isoformat(),
                }
                for inv in invoices
            ]

        except ImportError:
            pass

        response = HttpResponse(
            json.dumps(user_data, indent=2).encode("utf-8"),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="invoiceflow_data_export_{user.username}_{datetime.now().strftime("%Y%m%d")}.json"'
        )

        logger.info(f"Data export completed for user: {user.username} (request_id={gdpr_request.id})")

        return response

    except Exception as e:
        logger.error(f"Data export error: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred exporting your data.",
            },
            status=500,
        )


@login_required
@csrf_protect
@require_POST
def request_data_deletion(request):
    """
    GDPR Article 17 - Right to Erasure (Right to be Forgotten).
    Submit a request to delete all user data.
    Request is persisted to database before email notification.
    """
    from django.apps import apps
    GDPRRequest = apps.get_model('invoices', 'GDPRRequest')

    try:
        user = request.user

        gdpr_request = GDPRRequest.objects.create(
            user=user,
            user_email=user.email,
            user_username=user.username,
            request_type="data_deletion",
            status="pending",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        user_email_sent = send_gdpr_email(
            subject="[InvoiceFlow] Data Deletion Request Received",
            message=f"""
Dear {user.first_name or user.username},

We have received your request to delete your InvoiceFlow account and associated data.

Request Details:
- Request ID: {gdpr_request.id}
- Account: {user.email}
- Requested: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

We will process your request within 30 days as required by GDPR. You will receive a confirmation email once the deletion is complete.

If you did not make this request, please contact us immediately at privacy@invoiceflow.com.ng

Best regards,
The InvoiceFlow Team
            """,
            recipient_list=[user.email],
            gdpr_request=gdpr_request,
        )

        admin_email_sent = send_gdpr_email(
            subject=f"[InvoiceFlow Admin] Data Deletion Request - {user.username}",
            message=f"""
Data Deletion Request Received

Request ID: {gdpr_request.id}
User: {user.username}
Email: {user.email}
Requested: {datetime.utcnow().isoformat()}

Please process this request within 30 days as required by GDPR.
View in admin: /admin/invoices/gdprrequest/{gdpr_request.id}/
            """,
            recipient_list=["privacy@invoiceflow.com.ng"],
        )

        if not user_email_sent:
            logger.warning(f"User notification email failed for deletion request {gdpr_request.id}")

        if not admin_email_sent:
            logger.warning(f"Admin notification email failed for deletion request {gdpr_request.id}")

        logger.info(f"Data deletion requested by user: {user.username} (request_id={gdpr_request.id})")

        return JsonResponse(
            {
                "success": True,
                "message": "Your data deletion request has been submitted and recorded. You will receive a confirmation email shortly.",
                "request_id": gdpr_request.id,
            }
        )

    except Exception as e:
        logger.error(f"Data deletion request error: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred submitting your request.",
            },
            status=500,
        )


@login_required
@csrf_protect
@require_POST
def submit_sar(request):
    """
    GDPR Article 15 - Right of Access (Subject Access Request).
    Submit a formal SAR for comprehensive data disclosure.
    Request is persisted to database before email notification.
    """
    from django.apps import apps
    GDPRRequest = apps.get_model('invoices', 'GDPRRequest')

    try:
        user = request.user
        data = json.loads(request.body) if request.body else {}

        request_details = data.get("details", "Full data access request")

        gdpr_request = GDPRRequest.objects.create(
            user=user,
            user_email=user.email,
            user_username=user.username,
            request_type="subject_access",
            status="pending",
            details=request_details,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        user_email_sent = send_gdpr_email(
            subject="[InvoiceFlow] Subject Access Request Received",
            message=f"""
Dear {user.first_name or user.username},

We have received your Subject Access Request (SAR) under GDPR Article 15.

Request Details:
- Request ID: {gdpr_request.id}
- Account: {user.email}
- Request: {request_details}
- Submitted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

We will respond to your request within 30 days. If you need immediate access to your data, you can use the "Export My Data" feature in your account settings.

Best regards,
The InvoiceFlow Team
            """,
            recipient_list=[user.email],
            gdpr_request=gdpr_request,
        )

        admin_email_sent = send_gdpr_email(
            subject=f"[InvoiceFlow Admin] SAR Request - {user.username}",
            message=f"""
Subject Access Request Received

Request ID: {gdpr_request.id}
User: {user.username}
Email: {user.email}
Request: {request_details}
Submitted: {datetime.utcnow().isoformat()}

Please respond within 30 days as required by GDPR Article 15.
View in admin: /admin/invoices/gdprrequest/{gdpr_request.id}/
            """,
            recipient_list=["privacy@invoiceflow.com.ng"],
        )

        if not user_email_sent:
            logger.warning(f"User notification email failed for SAR request {gdpr_request.id}")

        if not admin_email_sent:
            logger.warning(f"Admin notification email failed for SAR request {gdpr_request.id}")

        logger.info(f"SAR submitted by user: {user.username} (request_id={gdpr_request.id})")

        return JsonResponse(
            {
                "success": True,
                "message": "Your Subject Access Request has been submitted and recorded. You will receive a response within 30 days.",
                "request_id": gdpr_request.id,
            }
        )

    except Exception as e:
        logger.error(f"SAR submission error: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": "An error occurred submitting your request.",
            },
            status=500,
        )
