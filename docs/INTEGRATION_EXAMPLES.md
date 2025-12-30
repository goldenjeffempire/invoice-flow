# InvoiceFlow Integration Examples

Professional examples for integrating with InvoiceFlow API.

## Authentication

### API Key Authentication
```python
import requests

API_KEY = "sk_your_api_key_here"
BASE_URL = "https://invoiceflow.co/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.get(f"{BASE_URL}/invoices/", headers=headers)
```

### Session Token Authentication
```python
# Login to get token
login_response = requests.post(
    f"{BASE_URL}/auth/login/",
    json={"username": "user", "password": "pass"}
)
token = login_response.json()["token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/invoices/", headers=headers)
```

## Python SDK Example

```python
from invoiceflow_sdk import InvoiceFlow

client = InvoiceFlow(api_key="sk_...")

# Create invoice
invoice = client.invoices.create(
    client_name="John Doe",
    client_email="john@example.com",
    amount=1000.00,
    currency="USD",
    due_date="2025-01-23"
)

# Send invoice
client.invoices.send_email(
    invoice_id=invoice['id'],
    message="Please review and pay"
)

# Track payment
payment = client.payments.get(invoice_id=invoice['id'])

# Create recurring invoice
recurring = client.recurring_invoices.create(
    client_name="Acme Corp",
    amount=5000.00,
    frequency="monthly",
    start_date="2025-01-01"
)
```

## JavaScript/Node.js Example

```javascript
const invoiceflow = require('invoiceflow-sdk');

const client = invoiceflow.create({
  apiKey: 'sk_...'
});

// Create invoice
const invoice = await client.invoices.create({
  clientName: 'John Doe',
  clientEmail: 'john@example.com',
  amount: 1000.00,
  currency: 'USD',
  dueDate: '2025-01-23'
});

// Send invoice
await client.invoices.sendEmail(invoice.id, {
  message: 'Please review and pay'
});

// Fetch invoices with filters
const invoices = await client.invoices.list({
  status: 'unpaid',
  currency: 'USD',
  amountMin: 500,
  amountMax: 5000
});

// Get analytics
const analytics = await client.analytics.getDashboard();
console.log(`Revenue: $${analytics.total_revenue}`);
```

## Webhook Integration

### Register Webhook
```python
response = requests.post(
    f"{BASE_URL}/webhooks/",
    headers=headers,
    json={
        "url": "https://your-app.com/webhooks/invoiceflow",
        "events": ["invoice.created", "payment.received"]
    }
)
webhook_id = response.json()["id"]
```

### Handle Webhook Events
```python
from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)

@app.route('/webhooks/invoiceflow', methods=['POST'])
def handle_webhook():
    data = request.json
    signature = request.headers.get('X-InvoiceFlow-Signature')
    
    # Verify signature
    expected_sig = hmac.new(
        b'your_webhook_secret',
        request.data,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_sig):
        return {'error': 'Invalid signature'}, 403
    
    event_type = data['event_type']
    event_data = data['data']
    
    if event_type == 'invoice.created':
        print(f"New invoice: {event_data['invoice_id']}")
    elif event_type == 'payment.received':
        print(f"Payment received: ${event_data['amount']}")
    
    return {'status': 'ok'}, 200
```

## Background Tasks

### Enqueue Task
```python
from invoices.enterprise_tasks import TaskQueue

# Queue email sending task
task = TaskQueue.enqueue(
    task_type="send_email",
    data={
        "invoice_id": 123,
        "recipient": "customer@example.com",
        "message": "Invoice for your review"
    },
    user=user_instance
)

# Check task status
task.refresh_from_db()
print(f"Status: {task.status}")
if task.status == "completed":
    print(f"Result: {task.result}")
```

### Scheduled Tasks
```python
from invoices.enterprise_tasks import ScheduledTask

# Create daily reconciliation task
ScheduledTask.objects.create(
    name="Daily Payment Reconciliation",
    task_type="reconcile_payments",
    frequency="daily",
    next_run=timezone.now() + timedelta(days=1)
)
```

## Advanced Search

```python
from invoices.enterprise_search import FilterBuilder, AdvancedSearch
from invoices.models import Invoice

# Build filters from query params
filters = FilterBuilder.build_invoice_filters({
    'search': 'acme',
    'status': 'unpaid',
    'date_from': '2025-01-01',
    'amount_min': '1000',
    'amount_max': '10000'
})

# Apply filters to queryset
queryset = Invoice.objects.filter(user=user)
results = AdvancedSearch.search_invoices(queryset, filters)

for invoice in results:
    print(f"{invoice.invoice_id}: {invoice.total} {invoice.currency}")
```

## API Key Management

```python
from invoices.enterprise_auth import APIKey

# Create API key
key, api_key_obj = APIKey.create_key(
    user=user,
    name="Mobile App Integration",
    scopes=['invoices:read', 'invoices:write', 'payments:read'],
    expires_days=90
)

print(f"API Key: {key}")  # Share with app securely
print(f"Expires: {api_key_obj.expires_at}")

# Later: Authenticate with key
user, api_key = APIKey.authenticate(key)
if user:
    print(f"Authenticated as: {user.username}")
    print(f"Scopes: {api_key.scopes}")
```

## Error Handling

```python
from invoices.enterprise_errors import ValidationError, AuthorizationError

try:
    # Create invoice
    invoice_data = {...}
    ErrorHandler.validate_required_fields(
        invoice_data,
        ['client_name', 'amount', 'due_date']
    )
    # Process invoice
except ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Context: {e.context}")
except AuthorizationError as e:
    print(f"Permission denied: {e.message}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Monitoring

```python
from invoices.monitoring import HealthChecker, RateLimitMonitor

# Check system health
health = HealthChecker.get_full_health()
if health['status'] == 'healthy':
    print("All systems operational")

# Check rate limits
from invoices.enterprise_auth import APIKey
user, api_key = APIKey.authenticate(key)
if api_key:
    requests_remaining = 100 - RateLimitMonitor.get_user_requests(user.id)
    print(f"Requests remaining: {requests_remaining}")
```

## TypeScript Example (Advanced)

```typescript
import { InvoiceFlow, Invoice, CreateInvoiceDto } from 'invoiceflow-sdk';

const client = new InvoiceFlow({
  apiKey: process.env.INVOICEFLOW_API_KEY,
  baseUrl: 'https://invoiceflow.co/api/v1'
});

async function createAndSendInvoice(data: CreateInvoiceDto) {
  try {
    // Create invoice
    const invoice: Invoice = await client.invoices.create(data);
    
    // Send via email
    await client.invoices.sendEmail(invoice.id, {
      message: 'Invoice attached. Please pay by due date.',
      cc: ['finance@company.com']
    });
    
    // Track in analytics
    const analytics = await client.analytics.getDashboard();
    
    return {
      invoiceId: invoice.id,
      status: 'sent',
      totalRevenue: analytics.total_revenue
    };
  } catch (error) {
    if (error.code === 'AUTHORIZATION_FAILED') {
      console.error('Invalid API key or insufficient permissions');
    }
    throw error;
  }
}
```

---

**For complete API documentation, see `API_DOCUMENTATION.md`**
