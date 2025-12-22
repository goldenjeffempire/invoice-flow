# Paystack Integration Setup Guide

## Overview
This guide provides step-by-step instructions to integrate Paystack payment gateway into InvoiceFlow for accepting payments in Nigeria and other supported countries.

## Prerequisites
- Paystack account (create at https://dashboard.paystack.com)
- API keys (Public Key and Secret Key)
- Django application with payment models configured

## Step 1: Get Your Paystack API Keys

### For Testing (Sandbox)
1. Log in to https://dashboard.paystack.com
2. Navigate to **Settings** → **API Keys & Webhooks**
3. Copy your **Test Public Key** and **Test Secret Key**
4. Use email: `test@example.com`, password: `12345678` for test transactions

### For Production
1. Verify your business account (KYC verification required)
2. Activate your **Live Keys** in API Keys section
3. Update all configuration to use Live Public and Secret keys

## Step 2: Configure Environment Variables

Add these to your Replit Secrets:

```
PAYSTACK_PUBLIC_KEY=pk_live_xxxxxxxxxxxxx  (or pk_test_xxxxxxxxxxxxx for testing)
PAYSTACK_SECRET_KEY=sk_live_xxxxxxxxxxxxx  (or sk_test_xxxxxxxxxxxxx for testing)
PAYSTACK_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

## Step 3: Install Required Packages

```bash
pip install paystack
```

The package should already be in requirements.txt.

## Step 4: Create Payment Views

### Payment Initialization
```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import requests

@require_http_methods(["POST"])
def initiate_payment(request):
    invoice_id = request.POST.get('invoice_id')
    amount = request.POST.get('amount')  # Amount in kobo (1 naira = 100 kobo)
    email = request.POST.get('email')
    
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "amount": int(float(amount) * 100),  # Convert to kobo
        "email": email,
        "metadata": {
            "invoice_id": invoice_id,
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    return JsonResponse(response.json())
```

### Payment Verification
```python
def verify_payment(request):
    reference = request.GET.get('reference')
    
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    
    response = requests.get(url, headers=headers)
    result = response.json()
    
    if result['status'] and result['data']['status'] == 'success':
        # Update payment status in database
        invoice = Invoice.objects.get(id=result['data']['metadata']['invoice_id'])
        invoice.payment_status = 'paid'
        invoice.save()
        return redirect('payment_success')
    
    return redirect('payment_failed')
```

## Step 5: Set Up Webhook Handler

### Add Webhook URL
1. Go to **Settings** → **API Keys & Webhooks**
2. Add Webhook URL: `https://yourdomain.com/webhooks/paystack/`
3. Save configuration

### Handle Webhook
```python
from django.views.decorators.csrf import csrf_exempt
import hmac
import hashlib

@csrf_exempt
def paystack_webhook(request):
    if request.method == 'POST':
        # Verify webhook signature
        payload = request.body
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        
        hash_obj = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha512
        )
        computed_hash = hash_obj.hexdigest()
        
        if signature == computed_hash:
            event_data = json.loads(payload)
            
            if event_data['event'] == 'charge.success':
                invoice_id = event_data['data']['metadata']['invoice_id']
                invoice = Invoice.objects.get(id=invoice_id)
                invoice.payment_status = 'paid'
                invoice.save()
                
                return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'failed'}, status=400)
```

## Step 6: Frontend Integration

### Paystack JS Library
```html
<script src="https://js.paystack.co/v1/inline.js"></script>

<script>
function initatePayment(invoiceId, email, amount) {
    fetch('/api/payment/initialize/', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `invoice_id=${invoiceId}&email=${email}&amount=${amount}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.status) {
            PaystackPop.setup({
                key: '{{ PAYSTACK_PUBLIC_KEY }}',
                email: email,
                amount: amount * 100,
                ref: data.data.reference,
                onClose: function() {
                    alert('Payment window closed.');
                },
                onSuccess: function(response) {
                    window.location.href = '/payment/verify/?reference=' + response.reference;
                }
            });
            PaystackPop.openIframe();
        }
    });
}
</script>
```

## Step 7: Testing

### Test Cards
| Card Number | Expiry | CVV |
|-------------|--------|-----|
| 4111 1111 1111 1111 | 01/25 | 123 |
| 5555 5555 5555 4444 | 01/25 | 123 |

### Test Transactions
1. Initialize payment with test amounts
2. Use test card numbers
3. Verify webhook delivery in Paystack dashboard
4. Check database for payment status updates

## Step 8: Go Live

1. Replace `pk_test_*` with `pk_live_*` in PAYSTACK_PUBLIC_KEY
2. Replace `sk_test_*` with `sk_live_*` in PAYSTACK_SECRET_KEY
3. Test with real payments using test business accounts
4. Monitor transactions in Paystack dashboard

## Troubleshooting

### Payment Not Processing
- Verify API keys are correct
- Check webhook signature validation
- Review error logs in Paystack dashboard
- Ensure email is valid and verified

### Webhook Not Received
- Confirm webhook URL is publicly accessible
- Check IP whitelist in Paystack settings
- Verify webhook secret is correct
- Review logs for timeout issues

## Support & Resources
- Paystack Documentation: https://paystack.com/docs
- API Reference: https://paystack.com/docs/api/
- Community: https://slack.paystack.com
- Support Email: support@paystack.com
