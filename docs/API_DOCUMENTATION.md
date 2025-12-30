# InvoiceFlow API Documentation

Modern RESTful API for professional invoicing operations.

## Base URL

```
https://invoiceflow.co/api/v1
```

## Authentication

All API endpoints require Bearer token authentication in the `Authorization` header:

```
Authorization: Bearer <your_api_token>
```

## Response Format

All API responses follow a standardized format:

### Success Response
```json
{
  "status": "success",
  "code": 200,
  "message": "Operation completed",
  "data": {...},
  "timestamp": "2025-12-23T00:05:00"
}
```

### Error Response
```json
{
  "status": "error",
  "code": 400,
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid input",
  "details": {...},
  "timestamp": "2025-12-23T00:05:00"
}
```

### Paginated Response
```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "timestamp": "2025-12-23T00:05:00"
}
```

## Endpoints

### Invoices

#### List Invoices
```
GET /invoices/
```

Query Parameters:
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20)
- `status` (string): Filter by status (paid/unpaid)
- `search` (string): Search by client name or invoice ID
- `ordering` (string): Sort field (-created_at, due_date, etc.)

Response: Paginated invoice list

#### Get Invoice
```
GET /invoices/{id}/
```

Response: Complete invoice details with line items

#### Create Invoice
```
POST /invoices/
```

Request Body:
```json
{
  "client_name": "John Doe",
  "client_email": "john@example.com",
  "amount": 1000.00,
  "currency": "USD",
  "due_date": "2025-01-23",
  "description": "Professional Services",
  "line_items": [
    {
      "description": "Consulting",
      "quantity": 10,
      "rate": 100.00
    }
  ]
}
```

#### Update Invoice
```
PATCH /invoices/{id}/
```

Request Body: Same as create (partial updates supported)

#### Delete Invoice
```
DELETE /invoices/{id}/
```

#### Update Invoice Status
```
POST /invoices/{id}/status/
```

Request Body:
```json
{
  "status": "paid"
}
```

### User Profile

#### Get Profile
```
GET /user/profile/
```

#### Update Profile
```
PATCH /user/profile/
```

Request Body:
```json
{
  "company_name": "Acme Inc",
  "business_email": "hello@acme.com",
  "default_currency": "USD",
  "invoice_prefix": "INV"
}
```

### Analytics

#### Get Dashboard Analytics
```
GET /analytics/dashboard/
```

Response: Monthly trends, revenue metrics, client count

#### Get Revenue Forecast
```
GET /analytics/forecast/
```

Parameters:
- `months` (int): Number of months to forecast (default: 6)

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `UNAUTHORIZED` | Missing or invalid authentication |
| `FORBIDDEN` | User lacks permissions |
| `NOT_FOUND` | Resource not found |
| `CONFLICT` | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

## Rate Limiting

- **Limit**: 100 requests per minute per user
- **Headers**: 
  - `X-RateLimit-Limit`: Total allowed requests
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Pagination

Default page size is 20 items. Maximum is 100.

```
GET /invoices/?page=2&page_size=50
```

## Filtering & Search

Combine multiple filters:
```
GET /invoices/?status=unpaid&currency=USD&search=client_name
```

## Examples

### Create and Send Invoice
```bash
curl -X POST https://invoiceflow.co/api/v1/invoices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "John Doe",
    "client_email": "john@example.com",
    "amount": 1000.00,
    "currency": "USD",
    "due_date": "2025-01-23",
    "description": "Web Development Services"
  }'
```

### Get Invoice Details
```bash
curl https://invoiceflow.co/api/v1/invoices/123/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Invoice Status to Paid
```bash
curl -X POST https://invoiceflow.co/api/v1/invoices/123/status/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "paid"}'
```

## SDK Examples

### Python
```python
import requests

headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}

# Create invoice
response = requests.post(
    "https://invoiceflow.co/api/v1/invoices/",
    headers=headers,
    json={
        "client_name": "John Doe",
        "client_email": "john@example.com",
        "amount": 1000.00
    }
)
```

### JavaScript
```javascript
const headers = {
  "Authorization": `Bearer YOUR_TOKEN`,
  "Content-Type": "application/json"
};

fetch("https://invoiceflow.co/api/v1/invoices/", {
  method: "POST",
  headers,
  body: JSON.stringify({
    client_name: "John Doe",
    client_email: "john@example.com",
    amount: 1000.00
  })
})
.then(r => r.json())
.then(data => console.log(data));
```

## Webhooks

Register webhooks to receive real-time notifications:

```
POST /webhooks/
```

Supported events:
- `invoice.created`
- `invoice.updated`
- `invoice.deleted`
- `payment.received`
- `invoice.overdue`

## Support

For API support: api-support@invoiceflow.co
