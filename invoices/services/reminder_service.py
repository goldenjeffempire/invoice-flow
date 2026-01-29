"""
Reminder Service - Business logic for reminder rule management and tracking.

Responsibilities:
- Managing reminder rules
- Tracking reminder interactions
- Recording clicks and opens
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import ReminderRule, ReminderLog

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminder rules and tracking."""

    @staticmethod
    def get_user_reminder_rules(user: "User") -> List["ReminderRule"]:
        """
        Get all reminder rules for a user.
        
        Args:
            user: The user whose rules to retrieve
            
        Returns:
            QuerySet of reminder rules
        """
        from invoices.models import ReminderRule

        return list(ReminderRule.objects.filter(user=user).order_by("trigger_type", "days_delta"))

    @staticmethod
    @transaction.atomic
    def create_reminder_rule(
        user: "User",
        trigger_type: str,
        days_delta: int,
        is_active: bool = True,
        email_subject: str = "",
        email_template: str = "",
    ) -> Tuple[bool, str, Optional["ReminderRule"]]:
        """
        Create a new reminder rule.
        
        Args:
            user: The user creating the rule
            trigger_type: Type of trigger (before_due, on_due, after_due)
            days_delta: Days offset from trigger
            is_active: Whether the rule is active
            email_subject: Subject line for reminder emails
            email_template: Template for reminder emails
            
        Returns:
            Tuple of (success, message, rule)
        """
        from invoices.models import ReminderRule

        rule = ReminderRule.objects.create(
            user=user,
            trigger_type=trigger_type,
            days_delta=days_delta,
            is_active=is_active,
            email_subject=email_subject,
            email_template=email_template,
        )

        logger.info(f"Reminder rule created: {rule.id} for user {user.id}")
        return True, "Reminder rule created.", rule

    @staticmethod
    @transaction.atomic
    def update_reminder_rule(
        rule_id: int,
        user: "User",
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Optional["ReminderRule"]]:
        """
        Update an existing reminder rule.
        
        Args:
            rule_id: ID of the rule to update
            user: The user who owns the rule
            data: Dictionary of field values to update
            
        Returns:
            Tuple of (success, message, rule)
        """
        from invoices.models import ReminderRule

        try:
            rule = ReminderRule.objects.get(id=rule_id, user=user)
        except ReminderRule.DoesNotExist:
            return False, "Reminder rule not found.", None

        for field in ["trigger_type", "days_delta", "is_active", "email_subject", "email_template"]:
            if field in data:
                setattr(rule, field, data[field])

        rule.save()
        logger.info(f"Reminder rule updated: {rule.id}")
        return True, "Reminder rule updated.", rule

    @staticmethod
    @transaction.atomic
    def delete_reminder_rule(rule_id: int, user: "User") -> Tuple[bool, str]:
        """
        Delete a reminder rule.
        
        Args:
            rule_id: ID of the rule to delete
            user: The user who owns the rule
            
        Returns:
            Tuple of (success, message)
        """
        from invoices.models import ReminderRule

        try:
            rule = ReminderRule.objects.get(id=rule_id, user=user)
        except ReminderRule.DoesNotExist:
            return False, "Reminder rule not found."

        rule.delete()
        logger.info(f"Reminder rule deleted: {rule_id}")
        return True, "Reminder rule deleted."

    @staticmethod
    @transaction.atomic
    def record_reminder_click(log_id: int) -> Tuple[bool, Optional[str]]:
        """
        Record a click on a reminder link.
        
        Args:
            log_id: ID of the reminder log entry
            
        Returns:
            Tuple of (success, invoice_id or None)
        """
        from invoices.models import ReminderLog

        try:
            reminder_log = ReminderLog.objects.select_related("invoice").get(id=log_id)
        except ReminderLog.DoesNotExist:
            return False, None

        if reminder_log.clicked_at is None:
            reminder_log.clicked_at = timezone.now()
            reminder_log.save(update_fields=["clicked_at"])
            logger.info(f"Reminder click recorded: {log_id}")

        return True, reminder_log.invoice.invoice_id

    @staticmethod
    @transaction.atomic
    def record_reminder_open(log_id: int) -> bool:
        """
        Record an open event for a reminder email.
        
        Args:
            log_id: ID of the reminder log entry
            
        Returns:
            Whether the open was recorded
        """
        from invoices.models import ReminderLog

        try:
            reminder_log = ReminderLog.objects.get(id=log_id)
        except ReminderLog.DoesNotExist:
            return False

        if reminder_log.opened_at is None:
            reminder_log.opened_at = timezone.now()
            reminder_log.save(update_fields=["opened_at"])
            logger.info(f"Reminder open recorded: {log_id}")

        return True
