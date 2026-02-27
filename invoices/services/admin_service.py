"""
Admin Service - Business logic for admin dashboard and platform management.

Responsibilities:
- Platform-wide statistics
- User management analytics
- Payment monitoring
- Invoice monitoring
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum

if TYPE_CHECKING:
    from invoices.models import Invoice, Payment, UserProfile, ContactSubmission

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin dashboard and platform management."""

    @staticmethod
    def get_platform_stats() -> Dict[str, Any]:
        """
        Get platform-wide statistics for admin dashboard.
        
        Returns:
            Dictionary with platform statistics
        """
        from invoices.models import Invoice, Payment, ContactSubmission

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(status="paid").count()

        paid_invoices_qs = Invoice.objects.filter(status="paid").prefetch_related("line_items")
        total_revenue = sum(inv.total for inv in paid_invoices_qs) if paid_invoices_qs.exists() else Decimal("0")

        pending_invoices = Invoice.objects.filter(status="unpaid").count()
        total_payments = Payment.objects.count()
        successful_payments = Payment.objects.filter(status="success").count()

        contact_submissions = ContactSubmission.objects.filter(status="new").count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
            "pending_invoices": pending_invoices,
            "total_revenue": total_revenue,
            "payment_rate": (paid_invoices / total_invoices * 100) if total_invoices > 0 else 0,
            "total_payments": total_payments,
            "successful_payments": successful_payments,
            "contact_submissions": contact_submissions,
        }

    @staticmethod
    def get_users_list(
        search_query: str = "",
        status_filter: str = "",
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get users list with search and filtering.
        
        Args:
            search_query: Search term for username, email, or name
            status_filter: Filter by status (active, inactive, staff)
            limit: Maximum number of users to return
            
        Returns:
            Dictionary with users list and total count
        """
        from invoices.models import Invoice, Payment, UserProfile

        users = User.objects.all().order_by("-date_joined")

        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )

        if status_filter == "active":
            users = users.filter(is_active=True)
        elif status_filter == "inactive":
            users = users.filter(is_active=False)
        elif status_filter == "staff":
            users = users.filter(is_staff=True)

        total_count = users.count()

        user_list = []
        for user in users[:limit]:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            invoice_count = Invoice.objects.filter(user=user).count()
            payment_count = Payment.objects.filter(user=user).count()

            user_list.append({
                "user": user,
                "profile": profile,
                "invoices": invoice_count,
                "payments": payment_count,
            })

        return {
            "users": user_list,
            "total_count": total_count,
        }

    @staticmethod
    def get_payments_stats() -> Dict[str, Any]:
        """
        Get payment statistics for admin monitoring.
        
        Returns:
            Dictionary with payment statistics
        """
        from invoices.models import Payment

        return {
            "total_payments": Payment.objects.count(),
            "successful": Payment.objects.filter(status="success").count(),
            "pending": Payment.objects.filter(status="pending").count(),
            "failed": Payment.objects.filter(status="failed").count(),
            "total_amount": sum(p.amount for p in Payment.objects.filter(status="success")) or Decimal("0"),
        }

    @staticmethod
    def get_payments_list(status_filter: str = "", limit: int = 100) -> List[Any]:
        """
        Get filtered payments list.
        
        Args:
            status_filter: Filter by payment status
            limit: Maximum number of payments to return
            
        Returns:
            List of payment objects
        """
        from invoices.models import Payment

        payments = Payment.objects.select_related("invoice", "user").order_by("-created_at")

        if status_filter:
            payments = payments.filter(status=status_filter)

        return list(payments[:limit])

    @staticmethod
    def get_invoices_stats() -> Dict[str, Any]:
        """
        Get invoice statistics for admin monitoring.
        
        Returns:
            Dictionary with invoice statistics
        """
        from invoices.models import Invoice

        return {
            "total": Invoice.objects.count(),
            "paid": Invoice.objects.filter(status="paid").count(),
            "unpaid": Invoice.objects.filter(status="unpaid").count(),
            "total_value": sum(inv.total for inv in Invoice.objects.prefetch_related("line_items")) or Decimal("0"),
        }

    @staticmethod
    def get_invoices_list(status_filter: str = "", limit: int = 100) -> List[Any]:
        """
        Get filtered invoices list.
        
        Args:
            status_filter: Filter by invoice status
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice objects
        """
        from invoices.models import Invoice

        invoices = Invoice.objects.select_related("user").prefetch_related("line_items").order_by("-created_at")

        if status_filter:
            invoices = invoices.filter(status=status_filter)

        return list(invoices[:limit])

    @staticmethod
    def get_contacts_stats() -> Dict[str, Any]:
        """
        Get contact submission statistics.
        
        Returns:
            Dictionary with contact statistics
        """
        from invoices.models import ContactSubmission

        return {
            "total": ContactSubmission.objects.count(),
            "new": ContactSubmission.objects.filter(status="new").count(),
            "in_progress": ContactSubmission.objects.filter(status="in_progress").count(),
            "resolved": ContactSubmission.objects.filter(status="resolved").count(),
        }

    @staticmethod
    def get_contacts_list(status_filter: str = "") -> List[Any]:
        """
        Get filtered contact submissions list.
        
        Args:
            status_filter: Filter by submission status
            
        Returns:
            List of contact submission objects
        """
        from invoices.models import ContactSubmission

        submissions = ContactSubmission.objects.order_by("-submitted_at")

        if status_filter:
            submissions = submissions.filter(status=status_filter)

        return list(submissions)

    @staticmethod
    def update_contact_status(submission_id: int, new_status: str) -> tuple[bool, str]:
        """
        Update contact submission status.
        
        Args:
            submission_id: ID of the submission to update
            new_status: New status value
            
        Returns:
            Tuple of (success, message)
        """
        from invoices.models import ContactSubmission

        try:
            submission = ContactSubmission.objects.get(id=submission_id)
        except ContactSubmission.DoesNotExist:
            return False, "Submission not found."

        if new_status not in dict(ContactSubmission.Status.choices):
            return False, "Invalid status."

        submission.status = new_status
        submission.save()
        logger.info(f"Contact submission {submission_id} status updated to {new_status}")
        return True, f"Contact status updated to {submission.get_status_display()}."
