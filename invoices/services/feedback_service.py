"""
Feedback Service - Business logic for engagement metrics and user feedback.

Responsibilities:
- Recording engagement metrics
- Submitting user feedback
- Tracking user interactions
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from django.db import transaction

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from invoices.models import Invoice, EngagementMetric, UserFeedback

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for managing engagement metrics and user feedback."""

    @staticmethod
    @transaction.atomic
    def record_engagement(
        user: "User",
        metric_type: str,
        invoice: Optional["Invoice"] = None,
        element_id: str = "",
        value: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Record an engagement metric.
        
        Args:
            user: The user performing the action
            metric_type: Type of engagement metric
            invoice: Optional related invoice
            element_id: Optional element identifier
            value: Metric value
            metadata: Additional metadata
            
        Returns:
            Tuple of (success, message)
        """
        from invoices.models import EngagementMetric

        if metric_type not in dict(EngagementMetric.MetricType.choices):
            return False, "Invalid metric type."

        if metadata is None:
            metadata = {}
        elif isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {"raw": metadata}

        EngagementMetric.objects.create(
            user=user,
            invoice=invoice,
            metric_type=metric_type,
            element_id=element_id,
            value=value,
            metadata=metadata,
        )

        logger.info(f"Engagement recorded: {metric_type} for user {user.id}")
        return True, "Engagement recorded."

    @staticmethod
    @transaction.atomic
    def submit_feedback(
        rating: int,
        page_url: str,
        user: Optional["User"] = None,
        comment: str = "",
        user_agent: str = "",
        is_mobile: Optional[bool] = None,
    ) -> Tuple[bool, str]:
        """
        Submit user feedback.
        
        Args:
            rating: Rating from 1-5
            page_url: URL of the page being rated
            user: Optional authenticated user
            comment: Optional feedback comment
            user_agent: User agent string
            is_mobile: Whether the user is on mobile
            
        Returns:
            Tuple of (success, message)
        """
        from invoices.models import UserFeedback

        if rating not in range(1, 6):
            return False, "Rating must be between 1 and 5."

        if not page_url:
            return False, "Page URL is required."

        if is_mobile is None:
            is_mobile = "mobile" in user_agent.lower()

        UserFeedback.objects.create(
            user=user,
            rating=rating,
            comment=comment,
            page_url=page_url,
            user_agent=user_agent,
            is_mobile=bool(is_mobile),
        )

        logger.info(f"Feedback submitted: rating={rating} for {page_url}")
        return True, "Feedback received. Thank you!"
