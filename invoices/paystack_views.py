"""
Paystack Payment Views for InvoiceFlow.
Handles payment initiation, callbacks, and webhooks.
"""

import hashlib
import json
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from .email_services import PaymentEmailService
from .models import Invoice, ProcessedWebhook
from .paystack_service import get_paystack_service

logger = logging.getLogger(__name__)


@login_required
@require_POST
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def initiate_invoice_payment(request, invoice_id):
    """Initiate payment for an invoice."""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    if invoice.status == "paid":
        messages.info(request, "This invoice has already been paid.")
        return redirect("invoice_detail", invoice_id=invoice.id)
    
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        messages.error(request, "Payment processing is not configured. Please contact support.")
        return redirect("invoice_detail", invoice_id=invoice.id)
    
    callback_url = request.build_absolute_uri(f"/payments/callback/{invoice.id}/")
    if callback_url.startswith("http://") and "localhost" not in callback_url:
        callback_url = callback_url.replace("http://", "https://", 1)
    
    reference = f"INV-{invoice.invoice_id}-{uuid.uuid4().hex[:8]}"
    
    subaccount_code = None
    
    try:
        profile = request.user.profile
        if profile.has_payment_setup():
            subaccount_code = profile.paystack_subaccount_code
            logger.info(f"Using subaccount {subaccount_code} for invoice {invoice.id}")
        else:
            messages.error(
                request, 
                "Payment receiving is not configured. Please set up your bank account in Payment Settings first."
            )
            logger.warning(f"Payment blocked for invoice {invoice.id}: User {request.user.id} has no subaccount configured")
            return redirect("payment_settings")
    except Exception as e:
        messages.error(request, "Payment setup is incomplete. Please configure your payment settings.")
        logger.error(f"Payment blocked for invoice {invoice.id}: Profile error - {e}")
        return redirect("payment_settings")
    
    result = paystack.initialize_payment(
        email=invoice.client_email or invoice.business_email,
        amount=invoice.total,
        currency=invoice.currency if invoice.currency in ["NGN", "USD", "GHS", "ZAR", "KES"] else "NGN",
        reference=reference,
        callback_url=callback_url,
        metadata={
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_id,
            "client_name": invoice.client_name,
            "business_name": invoice.business_name,
            "subaccount": subaccount_code,
        },
        subaccount_code=subaccount_code,
    )
    
    if result["status"] == "success":
        invoice.payment_reference = reference
        invoice.save(update_fields=["payment_reference"])
        return redirect(result["authorization_url"])
    else:
        messages.error(request, f"Could not initialize payment: {result.get('message', 'Unknown error')}")
        return redirect("invoice_detail", invoice_id=invoice.id)


@require_GET
def payment_callback(request, invoice_id):
    """Handle Paystack payment callback."""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    reference = request.GET.get("reference")
    
    if not reference:
        messages.error(request, "Invalid payment callback.")
        return redirect("invoice_detail", invoice_id=invoice.id)
    
    if invoice.payment_reference and invoice.payment_reference != reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("invoice_detail", invoice_id=invoice.id)
    
    paystack = get_paystack_service()
    result = paystack.verify_payment(reference)
    
    if result["status"] == "success" and result.get("verified"):
        metadata = result.get("raw_data", {}).get("metadata", {})
        if str(metadata.get("invoice_id")) != str(invoice.id):
            logger.warning(
                "Payment verification failed: Invoice mismatch. "
                f"Expected invoice_id={invoice.id}, got metadata invoice_id={metadata.get('invoice_id')}"
            )
            messages.error(request, "Payment verification failed: Invoice mismatch.")
            return redirect("invoice_detail", invoice_id=invoice.id)
        
        paid_amount = result.get("amount", Decimal("0"))
        paid_currency = result.get("currency", "").upper()
        expected_amount = invoice.total
        expected_currency = invoice.currency.upper() if invoice.currency else "NGN"
        
        amount_tolerance = Decimal("0.01")
        amount_difference = abs(paid_amount - expected_amount)
        
        if amount_difference > amount_tolerance:
            logger.warning(
                f"Payment amount mismatch for invoice {invoice.id}. "
                f"Expected {expected_amount}, received {paid_amount}. Reference: {reference}"
            )
            messages.error(
                request, 
                f"Payment amount mismatch: Expected {expected_amount}, received {paid_amount}. "
                "Please contact support."
            )
            return redirect("invoice_detail", invoice_id=invoice.id)
        
        if paid_currency and paid_currency != expected_currency:
            logger.warning(
                f"Payment currency mismatch for invoice {invoice.id}. "
                f"Expected {expected_currency}, received {paid_currency}. Reference: {reference}"
            )
            messages.error(
                request, 
                f"Payment currency mismatch: Expected {expected_currency}, received {paid_currency}. "
                "Please contact support."
            )
            return redirect("invoice_detail", invoice_id=invoice.id)
        
        invoice.status = "paid"
        invoice.payment_reference = reference
        invoice.save(update_fields=["status", "payment_reference"])
        
        logger.info(f"Payment successful for invoice {invoice.id}. Amount: {paid_amount}, Reference: {reference}")
        messages.success(request, "Payment successful! Thank you for your payment.")
    else:
        logger.warning(f"Payment verification failed for invoice {invoice.id}. Result: {result}")
        messages.error(request, f"Payment verification failed: {result.get('message', 'Unknown error')}")
    
    return redirect("invoice_detail", invoice_id=invoice.id)


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook events with replay protection.
    
    Security:
    - Validates HMAC-SHA512 signature with Paystack secret key
    - Prevents replay attacks using ProcessedWebhook model
    - Logs all webhook attempts for audit trail
    - Returns consistent responses to prevent timing attacks
    """
    paystack = get_paystack_service()
    
    signature = request.headers.get("X-Paystack-Signature", "")
    client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    if not paystack.verify_webhook_signature(request.body, signature):
        logger.warning(f"Paystack webhook: Invalid signature received from IP {client_ip}")
        return HttpResponse(status=400)
    
    try:
        from django.db import transaction as db_transaction
        
        payload = json.loads(request.body)
        event = payload.get("event")
        data = payload.get("data", {})
        
        # Generate unique event ID for replay protection
        reference = data.get("reference", "")
        event_id = f"{event}:{reference}:{data.get('id', '')}"
        payload_hash = hashlib.sha256(request.body).hexdigest()
        
        # Check for replay attack
        if ProcessedWebhook.is_duplicate(event_id):
            logger.warning(f"Paystack webhook: Duplicate event detected - {event_id}")
            return HttpResponse(status=200)  # Return 200 to prevent retries
        
        # Get client IP for audit logging
        client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        
        logger.info(f"Paystack webhook received: event={event}, reference={reference}")
        
        if event == "charge.success":
            with db_transaction.atomic():  # Ensure payment status update is atomic
                reference = data.get("reference")
                metadata = data.get("metadata", {})
                invoice_id = metadata.get("invoice_id")
                paid_amount = Decimal(data.get("amount", 0)) / 100
                
                if not reference:
                    logger.warning("Webhook: No reference provided in charge.success event")
                    return HttpResponse(status=400)
                
                if invoice_id:
                    try:
                        invoice = Invoice.objects.select_for_update().get(id=invoice_id)
                        
                        if not invoice.payment_reference:
                            logger.warning(
                                f"Webhook: No payment initiated for invoice {invoice_id}. "
                                f"Rejecting webhook with reference {reference}"
                            )
                            return HttpResponse(status=400)
                        
                        if invoice.payment_reference != reference:
                            logger.warning(
                                f"Webhook: Reference mismatch for invoice {invoice_id}. "
                                f"Expected {invoice.payment_reference}, got {reference}"
                            )
                            return HttpResponse(status=400)
                        
                        if invoice.status != "paid":
                            expected_amount = invoice.total
                            expected_currency = (invoice.currency or "NGN").upper()
                            paid_currency = data.get("currency", "").upper()
                            amount_tolerance = Decimal("0.01")
                            amount_difference = abs(paid_amount - expected_amount)
                            
                            logger.info(
                                f"Webhook payment verification: invoice={invoice_id}, "
                                f"expected={expected_amount}, paid={paid_amount}, "
                                f"difference={amount_difference}, tolerance={amount_tolerance}"
                            )
                            
                            if amount_difference > amount_tolerance:
                                logger.warning(
                                    f"Webhook: Payment amount mismatch for invoice {invoice_id}. "
                                    f"Expected {expected_amount}, received {paid_amount}. Reference: {reference}"
                                )
                            elif paid_currency and paid_currency != expected_currency:
                                logger.warning(
                                    f"Webhook: Payment currency mismatch for invoice {invoice_id}. "
                                    f"Expected {expected_currency}, received {paid_currency}. Reference: {reference}"
                                )
                            else:
                                invoice.status = "paid"
                                invoice.payment_reference = reference
                                invoice.save(update_fields=["status", "payment_reference"])
                                
                                logger.info(
                                    f"Webhook: Invoice {invoice_id} marked as paid. "
                                    f"Amount: {paid_amount}, Currency: {paid_currency}, Reference: {reference}"
                                )
                                
                                PaymentEmailService.send_payment_success_notification(
                                    invoice_id=invoice.invoice_id,
                                    client_email=invoice.client_email,
                                    client_name=invoice.client_name,
                                    business_name=invoice.business_name,
                                    amount=str(paid_amount),
                                    currency=paid_currency,
                                    reference=reference,
                                    business_email=invoice.business_email,
                                )
                                
                                PaymentEmailService.send_seller_payment_received(
                                    invoice_id=invoice.invoice_id,
                                    seller_email=invoice.user.email,
                                    seller_name=invoice.business_name,
                                    client_name=invoice.client_name,
                                    amount=str(paid_amount),
                                    currency=paid_currency,
                                    reference=reference,
                                )
                        else:
                            logger.info(f"Webhook: Invoice {invoice_id} already marked as paid")
                    except Invoice.DoesNotExist:  # type: ignore[attr-defined]
                        logger.error(f"Webhook: Invoice not found for id={invoice_id}, reference={reference}")
                else:
                    logger.warning(f"Webhook: No invoice_id in metadata for reference={reference}")
        
        elif event == "charge.failed":
            reference = data.get("reference")
            metadata = data.get("metadata", {})
            invoice_id = metadata.get("invoice_id")
            failure_message = data.get("gateway_response", "Unknown failure")
            
            logger.warning(
                f"Webhook: Payment failed for invoice {invoice_id}. "
                f"Reference: {reference}, Reason: {failure_message}"
            )
            
            if invoice_id:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)
                    amount = data.get("amount", 0)
                    if isinstance(amount, (int, float)):
                        amount = Decimal(amount) / 100
                    
                    PaymentEmailService.send_payment_failure_notification(
                        invoice_id=invoice.invoice_id,
                        client_email=invoice.client_email,
                        client_name=invoice.client_name,
                        business_name=invoice.business_name,
                        amount=str(amount),
                        currency=invoice.currency or "NGN",
                        failure_reason=failure_message,
                        reference=reference,
                        business_email=invoice.business_email,
                    )
                    
                    logger.info(
                        f"Webhook: Failure notification sent for invoice {invoice_id}"
                    )
                except Invoice.DoesNotExist:  # type: ignore[attr-defined]
                    logger.error(
                        f"Webhook: Invoice not found for charge.failed event: {invoice_id}"
                    )
        
        # Record the webhook to prevent replay attacks
        try:
            ProcessedWebhook.record_webhook(
                event_id=event_id,
                event_type=event,
                reference=reference,
                payload_hash=payload_hash,
                provider="paystack",
                ip_address=client_ip if client_ip else None,
            )
        except Exception as record_error:
            logger.error(f"Failed to record webhook: {record_error}")
        
        return HttpResponse(status=200)
    
    except json.JSONDecodeError as e:
        logger.error(f"Paystack webhook: Invalid JSON payload. Error: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception(f"Paystack webhook: Unexpected error processing webhook. Error: {str(e)}")
        return HttpResponse(status=500)


@login_required
def payment_status(request, invoice_id):
    """Check payment status for an invoice."""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    if not invoice.payment_reference:
        return JsonResponse({
            "status": "no_payment",
            "message": "No payment initiated for this invoice.",
        })
    
    paystack = get_paystack_service()
    result = paystack.verify_payment(invoice.payment_reference)
    
    return JsonResponse({
        "status": result.get("status"),
        "verified": result.get("verified", False),
        "invoice_status": invoice.status,
        "paid_at": result.get("paid_at"),
    })


@ratelimit(key='ip', rate='20/m', method='GET', block=True)
def public_invoice_view(request, invoice_id):
    """Public invoice view for clients to view and pay invoices.
    
    Rate limiting: 20 requests per minute per IP to prevent abuse.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    paystack = get_paystack_service()
    payment_enabled = paystack.is_configured
    
    subaccount_enabled = False
    try:
        profile = invoice.user.profile
        subaccount_enabled = profile.has_payment_setup()
    except Exception:
        pass
    
    context = {
        "invoice": invoice,
        "payment_enabled": payment_enabled and subaccount_enabled,
        "is_public_view": True,
    }
    
    return render(request, "invoices/public_invoice.html", context)


@require_POST
@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def public_initiate_payment(request, invoice_id):
    """Initiate payment for a public invoice (no login required).
    
    Rate limiting: 3 requests per minute per IP to prevent abuse.
    All payment attempts are logged for audit purposes.
    """
    client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    logger.info(f"Public payment initiation attempt for invoice {invoice_id} from IP {client_ip}")
    
    if invoice.status == "paid":
        messages.info(request, "This invoice has already been paid.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    paystack = get_paystack_service()
    
    if not paystack.is_configured:
        messages.error(request, "Payment processing is not configured. Please contact the invoice sender.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    subaccount_code = None
    try:
        profile = invoice.user.profile
        if profile.has_payment_setup():
            subaccount_code = profile.paystack_subaccount_code
            logger.info(f"Using subaccount {subaccount_code} for public payment on invoice {invoice.id}")
        else:
            messages.error(request, "Online payment is not enabled for this invoice. Please contact the invoice sender.")
            return redirect("public_invoice", invoice_id=invoice.id)
    except Exception:
        messages.error(request, "Payment setup is incomplete. Please contact the invoice sender.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    callback_url = request.build_absolute_uri(f"/pay/{invoice.id}/callback/")
    if callback_url.startswith("http://") and "localhost" not in callback_url:
        callback_url = callback_url.replace("http://", "https://", 1)
    
    reference = f"PAY-{invoice.invoice_id}-{uuid.uuid4().hex[:8]}"
    
    # Strict currency validation - only allow explicitly supported currencies
    SUPPORTED_CURRENCIES = {"NGN", "USD", "GHS", "ZAR", "KES"}
    payment_currency = invoice.currency.upper() if invoice.currency else "NGN"
    if payment_currency not in SUPPORTED_CURRENCIES:
        logger.warning(f"Unsupported currency attempted: {payment_currency}, defaulting to NGN for invoice {invoice.id}")
        payment_currency = "NGN"
    
    result = paystack.initialize_payment(
        email=invoice.client_email or "customer@example.com",
        amount=invoice.total,
        currency=payment_currency,
        reference=reference,
        callback_url=callback_url,
        metadata={
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_id,
            "client_name": invoice.client_name,
            "business_name": invoice.business_name,
            "payment_type": "public",
            "subaccount": subaccount_code,
        },
        subaccount_code=subaccount_code,
    )
    
    if result["status"] == "success":
        invoice.payment_reference = reference
        invoice.save(update_fields=["payment_reference"])
        return redirect(result["authorization_url"])
    else:
        messages.error(request, f"Could not initialize payment: {result.get('message', 'Unknown error')}")
        return redirect("public_invoice", invoice_id=invoice.id)


@require_GET
def public_payment_callback(request, invoice_id):
    """Handle Paystack payment callback for public payments."""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    reference = request.GET.get("reference")
    
    if not reference:
        messages.error(request, "Invalid payment callback.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    if invoice.payment_reference and invoice.payment_reference != reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("public_invoice", invoice_id=invoice.id)
    
    paystack = get_paystack_service()
    result = paystack.verify_payment(reference)
    
    if result["status"] == "success" and result.get("verified"):
        metadata = result.get("raw_data", {}).get("metadata", {})
        if str(metadata.get("invoice_id")) != str(invoice.id):
            logger.warning(
                "Public payment verification failed: Invoice mismatch. "
                f"Expected invoice_id={invoice.id}, got metadata invoice_id={metadata.get('invoice_id')}"
            )
            messages.error(request, "Payment verification failed: Invoice mismatch.")
            return redirect("public_invoice", invoice_id=invoice.id)
        
        paid_amount = result.get("amount", Decimal("0"))
        expected_amount = invoice.total
        amount_tolerance = Decimal("0.01")
        amount_difference = abs(paid_amount - expected_amount)
        
        if amount_difference > amount_tolerance:
            logger.warning(
                f"Public payment amount mismatch for invoice {invoice.id}. "
                f"Expected {expected_amount}, received {paid_amount}. Reference: {reference}"
            )
            messages.error(request, "Payment amount mismatch. Please contact support.")
            return redirect("public_invoice", invoice_id=invoice.id)
        
        invoice.status = "paid"
        invoice.payment_reference = reference
        invoice.save(update_fields=["status", "payment_reference"])
        
        logger.info(f"Public payment successful for invoice {invoice.id}. Amount: {paid_amount}, Reference: {reference}")
        messages.success(request, "Payment successful! Thank you for your payment.")
    else:
        logger.warning(f"Public payment verification failed for invoice {invoice.id}. Result: {result}")
        messages.error(request, f"Payment verification failed: {result.get('message', 'Unknown error')}")
    
    return redirect("public_invoice", invoice_id=invoice.id)
