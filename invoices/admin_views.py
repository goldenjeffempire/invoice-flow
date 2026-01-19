"""
Complete Admin Management System for InvoiceFlow.
Provides comprehensive platform administration with user, payment, and invoice management.
"""

import logging
from functools import wraps
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.db.models import Count, Sum, Q
from django.utils import timezone
from decimal import Decimal

from .models import Invoice, Payment, UserProfile, PaymentSettings, ContactSubmission

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
    
    context = {
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
    return render(request, "admin/dashboard.html", context)


@staff_required
@require_http_methods(["GET", "POST"])
def admin_users(request):
    """Manage platform users with search, filtering, and bulk actions."""
    users = User.objects.all().order_by("-date_joined")
    
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")
    
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
    
    # Get user statistics for each
    user_list = []
    for user in users[:100]:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        invoice_count = Invoice.objects.filter(user=user).count()
        payment_count = Payment.objects.filter(user=user).count()
        
        user_list.append({
            "user": user,
            "profile": profile,
            "invoices": invoice_count,
            "payments": payment_count,
        })
    
    context = {
        "users": user_list,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_count": users.count(),
    }
    return render(request, "admin/users.html", context)


@staff_required
@require_GET
def admin_payments(request):
    """Monitor payment transactions and gateway activity."""
    payments = Payment.objects.select_related("invoice", "user").order_by("-created_at")
    
    status_filter = request.GET.get("status", "")
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    stats = {
        "total_payments": Payment.objects.count(),
        "successful": Payment.objects.filter(status="success").count(),
        "pending": Payment.objects.filter(status="pending").count(),
        "failed": Payment.objects.filter(status="failed").count(),
        "total_amount": sum(p.amount for p in Payment.objects.filter(status="success")) or Decimal("0"),
    }
    
    context = {
        "payments": payments[:100],
        "stats": stats,
        "status_filter": status_filter,
    }
    return render(request, "admin/payments.html", context)


@staff_required
@require_GET
def admin_invoices(request):
    """Monitor invoices across all users."""
    invoices = Invoice.objects.select_related("user").prefetch_related("line_items").order_by("-created_at")
    
    status_filter = request.GET.get("status", "")
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    stats = {
        "total": Invoice.objects.count(),
        "paid": Invoice.objects.filter(status="paid").count(),
        "unpaid": Invoice.objects.filter(status="unpaid").count(),
        "total_value": sum(inv.total for inv in Invoice.objects.prefetch_related("line_items")) or Decimal("0"),
    }
    
    context = {
        "invoices": invoices[:100],
        "stats": stats,
        "status_filter": status_filter,
    }
    return render(request, "admin/invoices.html", context)


@staff_required
@require_GET
def admin_contacts(request):
    """Manage contact form submissions."""
    submissions = ContactSubmission.objects.order_by("-submitted_at")
    
    status_filter = request.GET.get("status", "")
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    stats = {
        "total": ContactSubmission.objects.count(),
        "new": ContactSubmission.objects.filter(status="new").count(),
        "in_progress": ContactSubmission.objects.filter(status="in_progress").count(),
        "resolved": ContactSubmission.objects.filter(status="resolved").count(),
    }
    
    context = {
        "submissions": submissions,
        "stats": stats,
        "status_filter": status_filter,
    }
    return render(request, "admin/contacts.html", context)


@staff_required
@require_http_methods(["POST"])
def update_contact_status(request, submission_id):
    """Update contact submission status."""
    submission = get_object_or_404(ContactSubmission, id=submission_id)
    new_status = request.POST.get("status", "new")
    
    if new_status in dict(ContactSubmission.Status.choices):
        submission.status = new_status
        submission.save()
        messages.success(request, f"Contact status updated to {submission.get_status_display()}.")
    else:
        messages.error(request, "Invalid status.")
    
    return redirect("admin_contacts")


@staff_required
@require_GET
def admin_settings(request):
    """System and platform settings management."""
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    context = {
        "total_users": total_users,
        "active_users": active_users,
    }
    return render(request, "admin/settings.html", context)
