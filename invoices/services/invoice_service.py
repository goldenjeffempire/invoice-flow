"""
Invoice Service - Business logic for invoice lifecycle management.

Responsibilities:
- Create, update, delete invoices
- Status transitions
- Line item management
- Invoice validation
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.shortcuts import get_object_or_404

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import Invoice
    from invoices.forms import InvoiceForm

logger = logging.getLogger(__name__)


class InvoiceService:
    """Centralized service for Invoice lifecycle management."""

    @staticmethod
    @transaction.atomic
    def create_invoice(
        user: "User",
        invoice_data: Dict[str, Any],
        line_items_data: List[Dict[str, Any]],
    ) -> Tuple[Optional["Invoice"], Any]:
        """
        Create a new invoice with line items.
        
        Args:
            user: The user creating the invoice
            invoice_data: Dictionary of invoice field values
            line_items_data: List of line item dictionaries
            
        Returns:
            Tuple of (invoice, form) - invoice is None if validation failed
        """
        from invoices.forms import InvoiceForm
        from invoices.models import Invoice, LineItem
        from invoices.validators import InvoiceBusinessRules
        from .analytics_service import AnalyticsService

        form = InvoiceForm(invoice_data)
        if not form.is_valid():
            return None, form

        invoice = form.save(commit=False)
        invoice.user = user
        invoice.save()

        try:
            InvoiceBusinessRules.validate_line_items(line_items_data)
        except Exception as exc:
            form.add_error(None, str(exc))
            return None, form

        for item in line_items_data:
            if item.get("description"):
                LineItem.objects.create(
                    invoice=invoice,
                    description=item["description"],
                    quantity=Decimal(str(item.get("quantity", 1))),
                    unit_price=Decimal(str(item.get("unit_price", 0))),
                )

        from invoices.models import InvoiceHistory
        InvoiceHistory.log(
            invoice=invoice,
            action=InvoiceHistory.ActionType.CREATED,
            user=user,
            new_value={"invoice_id": invoice.invoice_id, "client_name": invoice.client_name},
            description=f"Invoice {invoice.invoice_id} created",
        )

        AnalyticsService.invalidate_user_cache(user.id)
        logger.info(f"Invoice {invoice.invoice_id} created for user {user.id}")
        return invoice, form

    @staticmethod
    @transaction.atomic
    def update_invoice(
        invoice: "Invoice",
        invoice_data: Dict[str, Any],
        line_items_data: List[Dict[str, Any]],
    ) -> Tuple[Optional["Invoice"], Any]:
        """
        Update an existing invoice with new data and line items.
        
        Args:
            invoice: The invoice to update
            invoice_data: Dictionary of invoice field values
            line_items_data: List of line item dictionaries
            
        Returns:
            Tuple of (invoice, form) - invoice is None if validation failed
        """
        from invoices.forms import InvoiceForm
        from invoices.models import LineItem
        from invoices.validators import InvoiceBusinessRules
        from .analytics_service import AnalyticsService

        invoice_form = InvoiceForm(invoice_data, instance=invoice)
        if not invoice_form.is_valid():
            return None, invoice_form

        try:
            InvoiceBusinessRules.validate_line_items(line_items_data)
        except Exception as exc:
            invoice_form.add_error(None, str(exc))
            return None, invoice_form

        invoice = invoice_form.save()

        new_items = []
        for item_data in line_items_data:
            desc = item_data.get("description")
            if not desc:
                continue

            qty = Decimal(str(item_data.get("quantity", 1)))
            price = Decimal(str(item_data.get("unit_price", 0)))

            new_items.append(
                LineItem(
                    invoice=invoice,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                )
            )

        invoice.line_items.all().delete()
        LineItem.objects.bulk_create(new_items)

        from invoices.models import InvoiceHistory
        InvoiceHistory.log(
            invoice=invoice,
            action=InvoiceHistory.ActionType.UPDATED,
            user=invoice.user,
            description=f"Invoice {invoice.invoice_id} updated",
        )

        AnalyticsService.invalidate_user_cache(invoice.user_id)
        logger.info(f"Invoice {invoice.invoice_id} updated")
        return invoice, invoice_form

    @staticmethod
    @transaction.atomic
    def delete_invoice(user: "User", invoice_id: str) -> bool:
        """
        Delete an invoice.
        
        Args:
            user: The user who owns the invoice
            invoice_id: The invoice ID to delete
            
        Returns:
            True if deletion was successful
        """
        from invoices.models import Invoice
        from .analytics_service import AnalyticsService

        invoice = get_object_or_404(Invoice, invoice_id=invoice_id, user=user)
        invoice_id_str = invoice.invoice_id
        invoice.delete()
        AnalyticsService.invalidate_user_cache(user.id)
        logger.info(f"Invoice {invoice_id_str} deleted by user {user.id}")
        return True

    @staticmethod
    @transaction.atomic
    def transition_status(
        invoice: "Invoice",
        new_status: str,
        user=None,
        force: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Safely transition invoice status with validation.
        
        Args:
            invoice: The invoice to update
            new_status: The new status value
            user: The user performing the transition (for audit log)
            force: If True, skip transition validation (admin override)
            
        Returns:
            Tuple of (success, error_message) - error_message is None if successful
        """
        from invoices.models import Invoice, InvoiceHistory
        from .analytics_service import AnalyticsService

        if new_status not in dict(Invoice.Status.choices):
            return False, f"Invalid status: {new_status}"

        old_status = invoice.status
        
        if old_status == new_status:
            return True, None

        if not force and not invoice.can_transition_to(new_status):
            allowed = invoice.get_available_transitions()
            return False, f"Cannot transition from '{old_status}' to '{new_status}'. Allowed: {allowed}"
        
        if new_status == Invoice.Status.PAID:
            InvoiceService._mark_as_paid(invoice)
        elif new_status == Invoice.Status.OVERDUE:
            InvoiceService._mark_as_overdue(invoice)
        elif new_status == Invoice.Status.SENT:
            InvoiceService._mark_as_sent(invoice)
        else:
            invoice.status = new_status
            invoice.save(update_fields=["status", "updated_at"])

        InvoiceHistory.log(
            invoice=invoice,
            action=InvoiceHistory.ActionType.STATUS_CHANGED,
            user=user,
            old_value={"status": old_status},
            new_value={"status": new_status},
            description=f"Status changed from {old_status} to {new_status}",
        )

        AnalyticsService.invalidate_user_cache(invoice.user_id)
        logger.info(f"Invoice {invoice.invoice_id} status: {old_status} -> {new_status}")
        return True, None

    @staticmethod
    def _mark_as_paid(invoice: "Invoice") -> None:
        """Internal method to mark invoice as paid with side effects."""
        from django.utils import timezone
        from invoices.models import Invoice
        from .email_service import EmailService

        if invoice.status == Invoice.Status.PAID:
            return

        with transaction.atomic():
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=["status", "updated_at"])

            invoice.payments.filter(status="pending").update(
                status="success",
                paid_at=timezone.now(),
                updated_at=timezone.now(),
            )

        try:
            successful_payment = (
                invoice.payments.filter(status="success").order_by("-paid_at").first()
            )
            if successful_payment:
                EmailService.send_receipt(successful_payment)
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")

    @staticmethod
    def _mark_as_overdue(invoice: "Invoice") -> None:
        """Internal method to mark invoice as overdue."""
        from invoices.models import Invoice

        if invoice.status in [Invoice.Status.UNPAID, Invoice.Status.SENT]:
            invoice.status = Invoice.Status.OVERDUE
            invoice.save(update_fields=["status", "updated_at"])

    @staticmethod
    def _mark_as_sent(invoice: "Invoice") -> None:
        """Internal method to mark invoice as sent."""
        from invoices.models import Invoice

        if invoice.status in [Invoice.Status.DRAFT, Invoice.Status.UNPAID, Invoice.Status.OVERDUE]:
            invoice.status = Invoice.Status.SENT
            invoice.save(update_fields=["status", "updated_at"])

    @staticmethod
    def get_user_invoices(
        user: "User",
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List["Invoice"]:
        """
        Get invoices for a user with optional filtering.
        
        Args:
            user: The user whose invoices to retrieve
            status: Optional status filter
            limit: Optional limit on number of results
            
        Returns:
            List of invoices
        """
        from invoices.models import Invoice

        queryset = Invoice.objects.filter(user=user).prefetch_related("line_items")
        
        if status:
            queryset = queryset.filter(status=status)
            
        queryset = queryset.order_by("-created_at")
        
        if limit:
            queryset = queryset[:limit]
            
        return list(queryset)

    @staticmethod
    def get_invoice_by_id(user: "User", invoice_id: str) -> Optional["Invoice"]:
        """
        Get a specific invoice by ID for a user.
        
        Args:
            user: The user who owns the invoice
            invoice_id: The invoice ID
            
        Returns:
            Invoice or None if not found
        """
        from invoices.models import Invoice

        try:
            return Invoice.objects.prefetch_related("line_items").get(
                invoice_id=invoice_id, user=user
            )
        except Invoice.DoesNotExist:
            return None
