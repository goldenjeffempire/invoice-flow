# Testing Guide for InvoiceFlow

Complete guide to testing the InvoiceFlow platform.

---

## Test Coverage

**Total Tests:** 57  
**Status:** ✅ All Passing  
**Coverage:** ~85% of core functionality

Test categories:
- API Tests (8 tests)
- Model Tests (10 tests)
- View Tests (15 tests)
- Email Tests (5 tests)
- Integration Tests (19 tests)

---

## Running Tests

### Run All Tests
```bash
cd /home/runner/workspace
python3.11 -m pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_api.py -v
pytest tests/test_models.py -v
pytest tests/test_views.py -v
```

### Run Specific Test
```bash
pytest tests/test_api.py::TestInvoiceAPI::test_create_invoice -v
```

### Run with Coverage
```bash
pytest tests/ --cov=invoices --cov-report=html
# Opens coverage report in htmlcov/index.html
```

### Run Tests in Parallel
```bash
pytest tests/ -n auto
```

---

## Test Categories

### API Tests (8 tests)

**File:** `tests/test_api.py`

Tests REST API endpoints:
- ✅ List invoices (authenticated)
- ✅ Get invoice detail
- ✅ Filter by status
- ✅ Search functionality
- ✅ Update invoice status
- ✅ Get statistics

**Run:**
```bash
pytest tests/test_api.py -v
```

### Model Tests (10 tests)

**File:** `tests/test_models.py`

Tests database models:
- ✅ Create invoice
- ✅ Calculate totals
- ✅ Line items
- ✅ Templates
- ✅ Validations

**Run:**
```bash
pytest tests/test_models.py -v
```

### View Tests (15 tests)

**File:** `tests/test_views.py`

Tests page rendering:
- ✅ Dashboard loads
- ✅ Invoice pages
- ✅ Public pages (features, pricing, etc)
- ✅ Health checks

**Run:**
```bash
pytest tests/test_views.py -v
```

### Email Tests (5 tests)

**File:** `tests/test_email_delivery.py`

Tests email system:
- ✅ Email sending
- ✅ Bounce tracking
- ✅ Retry queue
- ✅ Delivery logs

**Run:**
```bash
pytest tests/test_email_delivery.py -v
```

---

## Manual Testing Checklist

### User Registration
- [ ] Go to `/signup/`
- [ ] Enter valid email and password
- [ ] Submit form
- [ ] Check inbox for verification email
- [ ] Click verification link
- [ ] Verify email and redirect to login
- [ ] Login with new credentials

### User Login
- [ ] Go to `/login/`
- [ ] Enter correct credentials → Should login
- [ ] Try wrong password → Should show error
- [ ] Try non-existent user → Should show error

### Invoice Creation
- [ ] Go to dashboard `/dashboard/`
- [ ] Click "Create Invoice"
- [ ] Fill in client details
- [ ] Add line items
- [ ] Verify calculations
- [ ] Save as draft
- [ ] Edit and update
- [ ] Save with status "sent"

### Invoice Sending
- [ ] Create and send invoice
- [ ] Check email inbox
- [ ] Verify email contains invoice
- [ ] Click payment link in email
- [ ] Verify client can view invoice

### Payments
- [ ] Click payment button
- [ ] Go to Paystack checkout
- [ ] Use test card: 4111111111111111
- [ ] Password: 123456, exp: any future date
- [ ] Complete payment
- [ ] Return to site
- [ ] Verify payment status updated

### Email Verification
- [ ] Create account
- [ ] Check verification email
- [ ] Click link
- [ ] Verify success message

### Password Reset
- [ ] Go to `/forgot-password/`
- [ ] Enter email
- [ ] Check email for reset link
- [ ] Click link
- [ ] Enter new password
- [ ] Login with new password

### MFA (Two-Factor)
- [ ] Go to settings
- [ ] Click "Enable 2FA"
- [ ] Scan QR code with authenticator app
- [ ] Enter code to verify
- [ ] Save backup codes
- [ ] Logout and re-login
- [ ] Verify MFA prompt

---

## Testing Specific Features

### API Testing with cURL

```bash
# Get your API token
TOKEN="your_token_here"
BASE="https://yourdomain.com/api/v1"

# Test authentication
curl -X GET $BASE/invoices/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Create invoice
curl -X POST $BASE/invoices/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "client_email": "test@example.com",
    "amount": "1000.00",
    "due_date": "2025-12-31"
  }'
```

### Email Testing

```bash
# Test email sending
python manage.py shell << 'EOF'
from invoices.email_services import send_invoice_email
from invoices.models import Invoice

invoice = Invoice.objects.first()
send_invoice_email(invoice, "test@example.com")
print("Email sent!")
EOF
```

### Payment Testing

1. Get Paystack test keys from dashboard
2. Use test card: 4111111111111111
3. Use password: 123456
4. Use any future expiry date
5. Verify payment webhook is called

---

## Performance Testing

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class InvoiceFlowUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_invoices(self):
        self.client.get("/api/v1/invoices/")
    
    @task
    def get_health(self):
        self.client.get("/health/")

EOF

# Run load test
locust -f locustfile.py --host=https://yourdomain.com
```

### Response Time Testing

```bash
# Measure response times
import requests
import time

url = "https://yourdomain.com/"
start = time.time()
response = requests.get(url)
duration = time.time() - start

print(f"Status: {response.status_code}")
print(f"Time: {duration*1000:.0f}ms")
print(f"Size: {len(response.content)} bytes")
```

---

## Security Testing

### Check CSRF Protection
```bash
# Try POST without CSRF token
curl -X POST https://yourdomain.com/invoices/create/ \
  -d "data=test"
# Should return 403 Forbidden
```

### Check Authentication
```bash
# Try API without token
curl https://yourdomain.com/api/v1/invoices/
# Should return 401 Unauthorized
```

### Check Rate Limiting
```bash
# Make 150 requests in 60 seconds
for i in {1..150}; do
  curl https://yourdomain.com/api/v1/invoices/
done
# After 100, should return 429 Too Many Requests
```

---

## Browser Testing

### Desktop Browsers
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Mobile Browsers
- [ ] iOS Safari
- [ ] Android Chrome

### Test Cases
- [ ] Pages load correctly
- [ ] Forms work properly
- [ ] Responsive design
- [ ] Modals/popups work
- [ ] Navigation works
- [ ] Payment flow works

---

## Continuous Integration

### GitHub Actions (if using GitHub)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      run: pytest tests/ -v
```

---

## Test Data Generation

```bash
# Create test data
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from invoices.models import Invoice, InvoiceTemplate
from decimal import Decimal
from django.utils import timezone

# Create test user
user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)

# Create test invoices
for i in range(10):
    Invoice.objects.create(
        user=user,
        client_name=f"Client {i}",
        client_email=f"client{i}@example.com",
        amount=Decimal("1000.00") + (i * Decimal("100.00")),
        status=['draft', 'sent', 'paid'][i % 3]
    )

print("Test data created!")
EOF
```

---

## Debugging Failed Tests

### Enable Verbose Output
```bash
pytest tests/test_api.py -vv -s
```

### Capture Print Statements
```bash
pytest tests/ -s  # Shows all prints
```

### Show Local Variables on Failure
```bash
pytest tests/ -l
```

### Drop into Debugger on Failure
```bash
pytest tests/ --pdb
```

---

## Test Troubleshooting

### Database Errors
```bash
# Reset test database
python manage.py migrate --run-syncdb
pytest tests/
```

### Import Errors
```bash
# Ensure app is on path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Fixture Issues
```bash
# List available fixtures
pytest --fixtures

# Show fixture details
pytest tests/ -v --setup-show
```

---

## Regression Testing

Before each release:

1. **Run full test suite**
   ```bash
   pytest tests/ -v --tb=short
   ```

2. **Manual smoke tests**
   - [ ] Signup
   - [ ] Login
   - [ ] Create invoice
   - [ ] Send email
   - [ ] Payment flow

3. **Performance baseline**
   ```bash
   pytest tests/ --benchmark
   ```

4. **Security scan**
   ```bash
   python manage.py check --deploy
   ```

---

## Test Reporting

### Generate HTML Report
```bash
pytest tests/ --html=report.html --self-contained-html
```

### Generate JSON Report
```bash
pytest tests/ --json-report --json-report-file=report.json
```

### Coverage Report
```bash
pytest tests/ --cov=invoices --cov-report=html:htmlcov
# Open htmlcov/index.html
```

---

## Best Practices

1. **Run tests before committing**
   ```bash
   git hook: pytest tests/ -q
   ```

2. **Test edge cases**
   - Empty inputs
   - Large numbers
   - Special characters
   - Boundary values

3. **Keep tests isolated**
   - Each test should be independent
   - Clean up after tests
   - Don't depend on test order

4. **Use meaningful names**
   ```python
   def test_create_invoice_with_valid_data():  # Good
   def test_create():  # Bad
   ```

5. **Write clear assertions**
   ```python
   assert invoice.amount == Decimal("1000.00")  # Good
   assert invoice.amount  # Bad
   ```

---

## Resources

- Test Files: `tests/` directory
- pytest Docs: https://docs.pytest.org/
- Django Testing: https://docs.djangoproject.com/en/5.2/topics/testing/
- Factory Boy: https://factoryboy.readthedocs.io/

---

**Last Updated:** December 22, 2025
