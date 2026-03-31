"""
NotificationService — central service for creating in-app notifications.
All notification creation flows should go through this service.
"""
from __future__ import annotations
import logging
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction

from invoices.models import Notification, Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    def _create(user: User, title: str, message: str,
                 notification_type: str = Notification.Type.INFO,
                 link: str = "",
                 workspace: Optional[Workspace] = None) -> Optional[Notification]:
        try:
            return Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link,
                workspace=workspace,
            )
        except Exception as e:
            logger.error("NotificationService._create error: %s", e)
            return None

    @staticmethod
    def notify_payment_received(payment, workspace: Workspace) -> None:
        """Notify workspace owner/admins when a payment is received."""
        try:
            amount = payment.amount
            invoice = payment.invoice
            client_name = invoice.client.name if invoice and invoice.client else "a client"
            sym = workspace.currency_symbol

            title = f"Payment received — {sym}{amount:,.2f}"
            message = (
                f"{client_name} paid {sym}{amount:,.2f} for invoice "
                f"{invoice.invoice_number if invoice else 'N/A'}."
            )
            link = f"/invoices/{invoice.id}/" if invoice else "/payments/"

            members = WorkspaceMember.objects.filter(
                workspace=workspace, role__in=["owner", "admin"]
            ).select_related("user")
            for m in members:
                NotificationService._create(
                    user=m.user,
                    title=title,
                    message=message,
                    notification_type=Notification.Type.PAYMENT,
                    link=link,
                    workspace=workspace,
                )
        except Exception as e:
            logger.error("notify_payment_received error: %s", e)

    @staticmethod
    def notify_invoice_viewed(invoice, workspace: Workspace) -> None:
        """Notify workspace members when an invoice is viewed by the client."""
        try:
            client_name = invoice.client.name if invoice.client else "Client"
            sym = workspace.currency_symbol

            title = f"Invoice viewed — {invoice.invoice_number}"
            message = (
                f"{client_name} viewed invoice {invoice.invoice_number} "
                f"({sym}{invoice.total_amount:,.2f})."
            )
            link = f"/invoices/{invoice.id}/"

            members = WorkspaceMember.objects.filter(
                workspace=workspace, role__in=["owner", "admin"]
            ).select_related("user")
            for m in members:
                NotificationService._create(
                    user=m.user,
                    title=title,
                    message=message,
                    notification_type=Notification.Type.INVOICE,
                    link=link,
                    workspace=workspace,
                )
        except Exception as e:
            logger.error("notify_invoice_viewed error: %s", e)

    @staticmethod
    def notify_invoice_overdue(invoice, workspace: Workspace) -> None:
        """Notify workspace members when an invoice becomes overdue."""
        try:
            client_name = invoice.client.name if invoice.client else "Client"
            sym = workspace.currency_symbol

            title = f"Overdue invoice — {invoice.invoice_number}"
            message = (
                f"Invoice {invoice.invoice_number} for {client_name} "
                f"({sym}{invoice.amount_due:,.2f}) is overdue."
            )
            link = f"/invoices/{invoice.id}/"

            members = WorkspaceMember.objects.filter(
                workspace=workspace, role__in=["owner", "admin"]
            ).select_related("user")
            for m in members:
                NotificationService._create(
                    user=m.user,
                    title=title,
                    message=message,
                    notification_type=Notification.Type.WARNING,
                    link=link,
                    workspace=workspace,
                )
        except Exception as e:
            logger.error("notify_invoice_overdue error: %s", e)

    @staticmethod
    def notify_estimate_responded(estimate, action: str, workspace: Workspace) -> None:
        """Notify when a client accepts or rejects an estimate."""
        try:
            client_name = estimate.client.name if estimate.client else "Client"
            sym = workspace.currency_symbol
            verb = "accepted" if action == "accepted" else "declined"

            title = f"Estimate {verb} — {estimate.estimate_number}"
            message = (
                f"{client_name} {verb} estimate {estimate.estimate_number} "
                f"({sym}{estimate.total_amount:,.2f})."
            )
            link = f"/estimates/{estimate.id}/"
            ntype = Notification.Type.SUCCESS if action == "accepted" else Notification.Type.WARNING

            members = WorkspaceMember.objects.filter(
                workspace=workspace, role__in=["owner", "admin"]
            ).select_related("user")
            for m in members:
                NotificationService._create(
                    user=m.user,
                    title=title,
                    message=message,
                    notification_type=ntype,
                    link=link,
                    workspace=workspace,
                )
        except Exception as e:
            logger.error("notify_estimate_responded error: %s", e)

    @staticmethod
    def notify_team_invite(invitee_user: User, workspace: Workspace,
                           inviter: User) -> None:
        """Notify a user they've been invited to a workspace."""
        try:
            NotificationService._create(
                user=invitee_user,
                title=f"You've been invited to join {workspace.name}",
                message=(
                    f"{inviter.get_full_name() or inviter.email} invited you to "
                    f"collaborate on {workspace.name} in InvoiceFlow."
                ),
                notification_type=Notification.Type.TEAM,
                link="/settings/workspace/",
                workspace=workspace,
            )
        except Exception as e:
            logger.error("notify_team_invite error: %s", e)

    @staticmethod
    def create_system_notification(user: User, title: str, message: str,
                                   link: str = "",
                                   workspace: Optional[Workspace] = None) -> None:
        """Create a general system notification for a user."""
        NotificationService._create(
            user=user,
            title=title,
            message=message,
            notification_type=Notification.Type.INFO,
            link=link,
            workspace=workspace,
        )
