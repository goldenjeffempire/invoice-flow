# InvoiceFlow API Quick Start Guide

Fast introduction to the InvoiceFlow REST API.

---

## API Overview

**Base URL:** `https://yourdomain.com/api/v1/`

**Authentication:** Token-based (Bearer token)

**Response Format:** JSON

---

## Getting Started

### 1. Get Your API Token

In Django Admin (`/admin/`):
1. Go to **Invoices > API Tokens**
2. Create new token
3. Copy the token (keep it secret!)

Or via shell:
```bash
python manage.py shell << 'EOF'
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

user = User.objects.get(username='your_username')
token = Token.objects.create(user=user)
print(f"Token: {token.key}")
EOF
```

### 2. Make Your First Request

```bash
curl -X GET https://yourdomain.com/api/v1/invoices/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Core Endpoints

### Invoices

**List Invoices**
```
GET /api/v1/invoices/
Authorization: Bearer TOKEN
```

Response:
```json
{
  "count": 42,
  "results": [
    {
      "id": 1,
      "invoice_id": "INV-001",
      "client_name": "Acme Corp",
      "amount": "1500.00",
      "status": "sent",
      "due_date": "2025-01-22"
    }
  ]
}
```

**Create Invoice**
```
POST /api/v1/invoices/
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "client_name": "Client Name",
  "client_email": "client@example.com",
  "amount": "1000.00",
  "currency": "USD",
  "due_date": "2025-01-22",
  "line_items": [
    {
      "description": "Service",
      "quantity": 1,
      "unit_price": "1000.00"
    }
  ]
}
```

**Get Invoice**
```
GET /api/v1/invoices/{id}/
Authorization: Bearer TOKEN
```

**Update Invoice**
```
PUT /api/v1/invoices/{id}/
Authorization: Bearer TOKEN

{
  "status": "sent",
  "amount": "1200.00"
}
```

**Delete Invoice**
```
DELETE /api/v1/invoices/{id}/
Authorization: Bearer TOKEN
```

---

### Payments

**List Payments**
```
GET /api/v1/payments/
Authorization: Bearer TOKEN
```

**Record Payment**
```
POST /api/v1/payments/
Authorization: Bearer TOKEN

{
  "invoice_id": 1,
  "amount_paid": "1000.00",
  "payment_method": "bank_transfer",
  "transaction_id": "TXN123456"
}
```

**Get Payment**
```
GET /api/v1/payments/{id}/
Authorization: Bearer TOKEN
```

---

### Line Items

**List Line Items**
```
GET /api/v1/line-items/?invoice_id=1
Authorization: Bearer TOKEN
```

**Add Line Item**
```
POST /api/v1/line-items/
Authorization: Bearer TOKEN

{
  "invoice_id": 1,
  "description": "Consulting Services",
  "quantity": 10,
  "unit_price": "100.00"
}
```

---

### User Profile

**Get Your Profile**
```
GET /api/v1/profile/
Authorization: Bearer TOKEN
```

Response:
```json
{
  "user_id": 1,
  "company_name": "Your Company",
  "business_email": "billing@yourcompany.com",
  "default_currency": "USD",
  "default_tax_rate": "10.00",
  "timezone": "UTC"
}
```

**Update Profile**
```
PUT /api/v1/profile/
Authorization: Bearer TOKEN

{
  "company_name": "New Company Name",
  "default_tax_rate": "15.00"
}
```

---

## Query Parameters

### Filter Results

```bash
# Filter by status
GET /api/v1/invoices/?status=sent

# Filter by date range
GET /api/v1/invoices/?created_after=2025-01-01&created_before=2025-01-31

# Filter by client
GET /api/v1/invoices/?client_name=Acme

# Combine filters
GET /api/v1/invoices/?status=paid&created_after=2025-01-01
```

### Pagination

```bash
# List with pagination
GET /api/v1/invoices/?page=2&page_size=50

# Default page size: 20
# Max page size: 100
```

### Ordering

```bash
# Sort by date (newest first)
GET /api/v1/invoices/?ordering=-created_at

# Sort by amount
GET /api/v1/invoices/?ordering=amount
```

### Searching

```bash
# Search invoices
GET /api/v1/invoices/?search=client_name

# Search by invoice ID
GET /api/v1/invoices/?search=INV-001
```

---

## Request Examples

### Create Complete Invoice

```bash
curl -X POST https://yourdomain.com/api/v1/invoices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "ABC Corporation",
    "client_email": "billing@abc.com",
    "client_phone": "+1-555-123-4567",
    "currency": "USD",
    "tax_rate": "10",
    "amount": "5000.00",
    "due_date": "2025-02-22",
    "notes": "Thank you for your business!",
    "line_items": [
      {
        "description": "Consulting Services - January",
        "quantity": "40",
        "unit_price": "100.00"
      },
      {
        "description": "Support & Maintenance",
        "quantity": "1",
        "unit_price": "1000.00"
      }
    ]
  }'
```

### Send Invoice Email

```bash
curl -X POST https://yourdomain.com/api/v1/invoices/1/send/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "client@example.com",
    "subject": "Invoice from Your Company",
    "message": "Please find attached your invoice. Thank you!"
  }'
```

### Get Invoice Statistics

```bash
curl -X GET https://yourdomain.com/api/v1/invoices/stats/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "total_invoices": 150,
  "total_amount": "450000.00",
  "paid_amount": "425000.00",
  "outstanding_amount": "25000.00",
  "average_days_to_payment": 12
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid data",
  "details": {
    "amount": ["This field is required."]
  }
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication failed",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "error": "Permission denied",
  "message": "You don't have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "error": "Not found",
  "message": "Invoice with id 999 not found"
}
```

### 500 Server Error
```json
{
  "error": "Internal server error",
  "message": "Something went wrong. Please contact support."
}
```

---

## Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Successful deletion
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate resource
- `429 Too Many Requests` - Rate limit exceeded
- `500 Server Error` - Server error

---

## Rate Limiting

- **Limit:** 100 requests per minute per token
- **Remaining:** Check `X-RateLimit-Remaining` header
- **Reset:** Check `X-RateLimit-Reset` header

---

## Common Use Cases

### Bulk Invoice Creation

```python
import requests
import json

BASE_URL = "https://yourdomain.com/api/v1"
TOKEN = "your_api_token"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

invoices_data = [
    {
        "client_name": "Client A",
        "client_email": "a@example.com",
        "amount": "1000.00",
        "due_date": "2025-02-22"
    },
    {
        "client_name": "Client B",
        "client_email": "b@example.com",
        "amount": "2000.00",
        "due_date": "2025-02-22"
    }
]

for invoice in invoices_data:
    response = requests.post(
        f"{BASE_URL}/invoices/",
        headers=HEADERS,
        json=invoice
    )
    print(f"Created: {response.json()['invoice_id']}")
```

### Get Monthly Revenue

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "https://yourdomain.com/api/v1"
TOKEN = "your_api_token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Get last 30 days of paid invoices
start_date = (datetime.now() - timedelta(days=30)).isoformat()
response = requests.get(
    f"{BASE_URL}/invoices/",
    headers=HEADERS,
    params={
        "status": "paid",
        "created_after": start_date
    }
)

invoices = response.json()["results"]
revenue = sum(float(inv["amount"]) for inv in invoices)
print(f"Monthly Revenue: ${revenue:,.2f}")
```

### Sync with Accounting Software

```python
# Export to CSV
import csv
import requests

BASE_URL = "https://yourdomain.com/api/v1"
TOKEN = "your_api_token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

response = requests.get(
    f"{BASE_URL}/invoices/?page_size=1000",
    headers=HEADERS
)

with open("invoices.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["ID", "Client", "Amount", "Status", "Date"])
    
    for inv in response.json()["results"]:
        writer.writerow([
            inv["invoice_id"],
            inv["client_name"],
            inv["amount"],
            inv["status"],
            inv["created_at"]
        ])
```

---

## Documentation

Full API documentation available at:
- **Schema:** `/api/schema/`
- **Swagger UI:** `/api/schema/swagger-ui/`
- **ReDoc:** `/api/schema/redoc/`

---

## Support

For API help:
1. Check this guide
2. Review full docs at `/api/schema/`
3. Contact support: support@yourdomain.com

---

**Last Updated:** December 22, 2025
