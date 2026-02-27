"""
Complete Admin Management System for InvoiceFlow.
Provides comprehensive platform administration with user, payment, and invoice management.

Views layer responsibilities:
- Request parsing and validation
- Authentication and authorization checks
- Response mapping and rendering
- All business logic delegated to AdminService
"""

import logging
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .services import AdminService

logger = logging.getLogger(__name__)


def staff_required(view_func):
    """Decorator requiring staff/admin access."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in.")
            return redirect("invoices:login")
        if not (request.user.is_active and request.user.is_staff):
            messages.error(request, "Admin access required.")
            return redirect("invoices:home")
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
@require_GET
def admin_dashboard(request):
    """Admin dashboard with platform statistics and KPIs."""
    context = AdminService.get_platform_stats()
    return render(request, "admin/dashboard.html", context)


@staff_required
@require_http_methods(["GET", "POST"])
def admin_users(request):
    """Manage platform users with search, filtering, and bulk actions."""
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")

    result = AdminService.get_users_list(
        search_query=search_query,
        status_filter=status_filter,
    )

    context = {
        "users": result["users"],
        "search_query": search_query,
        "status_filter": status_filter,
        "total_count": result["total_count"],
    }
    return render(request, "admin/users.html", context)


@staff_required
@require_GET
def admin_payments(request):
    """Monitor payment transactions and gateway activity."""
    status_filter = request.GET.get("status", "")

    context = {
        "payments": AdminService.get_payments_list(status_filter=status_filter),
        "stats": AdminService.get_payments_stats(),
        "status_filter": status_filter,
    }
    return render(request, "admin/payments.html", context)


@staff_required
@require_GET
def admin_invoices(request):
    """Monitor invoices across all users."""
    status_filter = request.GET.get("status", "")

    context = {
        "invoices": AdminService.get_invoices_list(status_filter=status_filter),
        "stats": AdminService.get_invoices_stats(),
        "status_filter": status_filter,
    }
    return render(request, "admin/invoices.html", context)


@staff_required
@require_GET
def admin_contacts(request):
    """Manage contact form submissions."""
    status_filter = request.GET.get("status", "")

    context = {
        "submissions": AdminService.get_contacts_list(status_filter=status_filter),
        "stats": AdminService.get_contacts_stats(),
        "status_filter": status_filter,
    }
    return render(request, "admin/contacts.html", context)


@staff_required
@require_http_methods(["POST"])
def update_contact_status(request, submission_id):
    """Update contact submission status."""
    new_status = request.POST.get("status", "new")

    success, message = AdminService.update_contact_status(submission_id, new_status)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("admin_contacts")


@staff_required
@require_GET
def admin_settings(request):
    """System and platform settings management."""
    from django.contrib.auth.models import User

    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
    }
    return render(request, "admin/settings.html", context)
