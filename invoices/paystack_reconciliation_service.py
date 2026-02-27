"""
Payment Reconciliation & Recovery Service
Ensures payment state consistency between Paystack and InvoiceFlow.
Detects lost/interrupted payments and triggers automatic recovery.
"""

from decimal import Decimal
from typing import Any, Optional
from django.utils import timezone
from django.db import transaction
import logging

from .models import (
    Payment,
    PaymentReconciliation,
    PaymentRecovery,
    UserIdentityVerification,
)
from .paystack_service import get_paystack_service

logger = logging.getLogger(__name__)


class PaymentReconciliationService:
    """
    Core reconciliation service:
    1. Verifies payment state with Paystack
    2. Detects mismatches (amount, currency, status)
    3. Triggers recovery for failed/missing payments
    4. Prevents double-charging and fraud
    """

    def __init__(self):
        self.paystack = get_paystack_service()

    @transaction.atomic
    def reconcile_payment(
        self,
        payment: Payment,
    ) -> PaymentReconciliation:
        """
        Reconcile a single payment against Paystack.
        """
        try:
            reconciliation = PaymentReconciliation.objects.get(
                payment=payment,
            )
        except PaymentReconciliation.DoesNotExist:
            reconciliation = PaymentReconciliation(
                payment=payment,
                user=payment.user,
                local_status=payment.status,
            )

        reconciliation.status = PaymentReconciliation.ReconciliationStatus.IN_PROGRESS
        reconciliation.last_attempt = timezone.now()
        reconciliation.save()

        try:
            verification = self.paystack.verify_payment(
                reference=payment.reference,
            )

            paystack_status = verification.get("status", "unknown")
            paystack_verified = verification.get("verified", False)

            reconciliation.paystack_status = paystack_status
            reconciliation.local_status = payment.status

            # Check for mismatches
            amount_match = (
                Decimal(str(verification.get("amount", 0))) / 100
                == payment.amount
            )
            currency_match = (
                verification.get("currency", "").upper() == payment.currency
            )

            if paystack_verified and payment.status == Payment.Status.SUCCESS:
                status_match = True
            elif not paystack_verified and payment.status == Payment.Status.PENDING:
                status_match = True
            else:
                status_match = False

            reconciliation.amount_match = amount_match
            reconciliation.currency_match = currency_match
            reconciliation.status_match = status_match

            # Determine reconciliation outcome
            if amount_match and currency_match and status_match:
                reconciliation.status = (
                    PaymentReconciliation.ReconciliationStatus.VERIFIED
                )
                reconciliation.verified_at = timezone.now()
            else:
                reconciliation.status = (
                    PaymentReconciliation.ReconciliationStatus.MISMATCH
                )
                self._trigger_recovery(
                    payment=payment,
                    error_reason="State mismatch detected",
                )

        except Exception as e:
            reconciliation.status = PaymentReconciliation.ReconciliationStatus.FAILED
            reconciliation.last_error = str(e)
            logger.error(f"Reconciliation failed for {payment.reference}: {e}")

            if reconciliation.retry_count < 3:
                reconciliation.retry_count += 1
                self._trigger_recovery(
                    payment=payment,
                    error_reason=f"Reconciliation error: {str(e)}",
                )

        reconciliation.save()
        return reconciliation

    def _trigger_recovery(
        self,
        payment: Payment,
        error_reason: str,
    ) -> PaymentRecovery:
        """
        Trigger payment recovery for failed/mismatched payments.
        """
        latest_recovery = (
            PaymentRecovery.objects
            .filter(payment=payment)
            .order_by("-attempt_number")
            .first()
        )

        attempt_number = (latest_recovery.attempt_number + 1
                         if latest_recovery else 1)

        if attempt_number > 3:
            logger.error(
                f"Payment {payment.reference} exceeded max recovery attempts"
            )
            return None

        recovery = PaymentRecovery.objects.create(
            payment=payment,
            user=payment.user,
            strategy=PaymentRecovery.RecoveryStrategy.WEBHOOK_RETRY,
            attempt_number=attempt_number,
            error_reason=error_reason,
            next_retry_at=timezone.now() + timezone.timedelta(seconds=30),
        )

        logger.info(
            f"Recovery triggered for {payment.reference} "
            f"(attempt {attempt_number}): {error_reason}"
        )

        return recovery

    def process_pending_recoveries(self) -> dict[str, int]:
        """
        Process all pending payment recoveries (scheduled retries).
        Returns count of successful/failed recoveries.
        """
        now = timezone.now()
        pending = PaymentRecovery.objects.filter(
            next_retry_at__lte=now,
            is_successful=False,
            attempt_number__lt=3,
        )

        stats = {"attempted": 0, "successful": 0, "failed": 0}

        for recovery in pending:
            stats["attempted"] += 1
            try:
                result = self.paystack.verify_payment(
                    reference=recovery.payment.reference,
                )

                if result.get("verified"):
                    recovery.is_successful = True
                    recovery.completed_at = timezone.now()
                    recovery.payment.status = Payment.Status.SUCCESS
                    recovery.payment.verified = True
                    recovery.payment.paid_at = timezone.now()
                    recovery.payment.save()

                    PaymentReconciliation.objects.filter(
                        payment=recovery.payment,
                    ).update(
                        status=PaymentReconciliation.ReconciliationStatus.RECOVERED,
                        verified_at=timezone.now(),
                    )

                    stats["successful"] += 1
                    logger.info(
                        f"Payment recovery successful for "
                        f"{recovery.payment.reference}"
                    )
                else:
                    recovery.error_code = "NOT_VERIFIED"
                    recovery.error_reason = "Payment not verified by Paystack"
                    stats["failed"] += 1

            except Exception as e:
                recovery.error_code = "RECOVERY_ERROR"
                recovery.error_reason = str(e)
                stats["failed"] += 1
                logger.error(f"Recovery process error: {e}")

            recovery.save()

        return stats


class IdentityVerificationService:
    """
    KYC (Know Your Customer) service for payout enablement.
    Ensures strong identity verification before enabling transfers.
    """

    def __init__(self):
        self.paystack = get_paystack_service()

    def verify_identity(
        self,
        user_id: int,
        document_type: str,
        document_number: str,
    ) -> tuple[bool, str]:
        """
        Verify user identity via Paystack KYC.
        """
        try:
            verification = UserIdentityVerification.objects.get(
                user_id=user_id,
            )
        except UserIdentityVerification.DoesNotExist:
            verification = UserIdentityVerification(
                user_id=user_id,
                status=UserIdentityVerification.VerificationStatus.PENDING,
            )

        verification.document_type = document_type
        verification.document_number = document_number

        try:
            result = self.paystack.verify_bvn(
                bvn=document_number,
            )

            if result.get("verified"):
                verification.status = (
                    UserIdentityVerification.VerificationStatus.VERIFIED
                )
                verification.verified_at = timezone.now()
                verification.verified_by = "Paystack KYC"
                verification.expires_at = (
                    timezone.now() + timezone.timedelta(days=365)
                )

                verification.save()
                return True, "Identity verified successfully"
            else:
                verification.status = (
                    UserIdentityVerification.VerificationStatus.REJECTED
                )
                verification.rejection_reason = "KYC verification failed"
                verification.save()
                return False, "Identity verification failed"

        except Exception as e:
            verification.status = (
                UserIdentityVerification.VerificationStatus.PENDING
            )
            verification.rejection_reason = str(e)
            verification.save()
            return False, f"Verification error: {str(e)}"

    def can_process_payout(self, user_id: int) -> tuple[bool, str]:
        """
        Check if user can process payouts based on identity verification.
        """
        try:
            verification = UserIdentityVerification.objects.get(
                user_id=user_id,
            )

            if not verification.is_verified():
                return (
                    False,
                    "Identity verification required before payout",
                )

            return True, "User can process payouts"

        except UserIdentityVerification.DoesNotExist:
            return (
                False,
                "Please complete identity verification first",
            )


def get_reconciliation_service() -> PaymentReconciliationService:
    """Factory function for reconciliation service."""
    return PaymentReconciliationService()


def get_identity_service() -> IdentityVerificationService:
    """Factory function for identity verification service."""
    return IdentityVerificationService()
