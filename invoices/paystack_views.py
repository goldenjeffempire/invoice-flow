
import json
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from invoiceflow.mfa import require_mfa

from .auth_services import require_verified_email
from .models import Payment, ProcessedWebhook
from .paystack_service import (
    PaystackService,
    finalize_payment_from_verification,
)


# ---------------------------------------------------------------------
# INITIALIZE PAYMENT
# ---------------------------------------------------------------------

@require_POST
def initialize_payment(request):
    user = request.user
    require_verified_email(user)
    require_mfa(user)

    invoice_id = request.POST.get("invoice_id")
    amount = Decimal(request.POST.get("amount", "0"))

    if not invoice_id or amount <= 0:
        return JsonResponse({"error": "Invalid payment request"}, status=400)

    reference = f"inv_{invoice_id}_{user.id}"

    payment, created = Payment.objects.get_or_create(
        reference=reference,
        defaults={
            "user": user,
            "invoice_id": invoice_id,
            "amount": amount,
        },
    )

    if not created:
        return JsonResponse(
            {"error": "Payment already initialized"}, status=400
        )

    service = PaystackService()
    result = service.initialize_payment(
        email=user.email,
        amount=amount,
        reference=reference,
        callback_url=settings.PAYSTACK_CALLBACK_URL,
        metadata={
            "invoice_id": invoice_id,
            "user_id": user.id,
        },
    )

    return JsonResponse(result, status=200 if result.get("status") == "success" else 400)


# ---------------------------------------------------------------------
# PAYSTACK WEBHOOK
# ---------------------------------------------------------------------

@csrf_exempt
@require_POST
def paystack_webhook(request):
    service = PaystackService()

    signature = request.headers.get("X-Paystack-Signature", "")
    payload = request.body

    # Verify webhook signature
    if not service.verify_webhook_signature(payload, signature):
        return HttpResponse(status=400)

    event = json.loads(payload.decode("utf-8"))
    event_id = str(event.get("data", {}).get("id"))

    if not event_id:
        return HttpResponse(status=400)

    # Idempotency check
    if service.is_webhook_processed(event_id):
        return HttpResponse(status=200)

    reference = event.get("data", {}).get("reference")
    if not reference:
        return HttpResponse(status=400)

    with transaction.atomic():
        service.mark_webhook_processed(event_id)

        try:
            payment = Payment.objects.select_for_update().get(
                reference=reference
            )
        except Payment.DoesNotExist:
            return HttpResponse(status=404)

        # Skip already verified payments
        if payment.verified:
            return HttpResponse(status=200)

        verification = service.verify_transaction(reference)

        if not verification.get("verified"):
            return HttpResponse(status=200)

        # Amount validation (anti-tampering)
        if verification["amount"] != payment.amount:
            return HttpResponse(status=400)

        finalize_payment_from_verification(
            payment=payment,
            verification=verification,
        )

    return HttpResponse(status=200)
