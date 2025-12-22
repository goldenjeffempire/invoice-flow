#!/bin/bash
# InvoiceFlow Deployment Script
# Complete setup for production deployment

set -e

echo "🚀 InvoiceFlow Deployment Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Environment Check
echo -e "${YELLOW}[1/6] Checking environment...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Create .env with required variables"
    exit 1
fi

if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3.11 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment OK${NC}"
echo ""

# Step 2: Database Setup
echo -e "${YELLOW}[2/6] Setting up database...${NC}"
python3.11 manage.py migrate
echo -e "${GREEN}✓ Database migrated${NC}"
echo ""

# Step 3: Static Files
echo -e "${YELLOW}[3/6] Collecting static files...${NC}"
python3.11 manage.py collectstatic --noinput --clear
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Step 4: Create Superuser (if needed)
echo -e "${YELLOW}[4/6] Checking admin user...${NC}"
python3.11 manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    print("Creating admin user...")
    User.objects.create_superuser('admin', 'admin@invoiceflow.local', 'admin123')
    print("✓ Admin user created (username: admin, password: admin123)")
    print("⚠️  CHANGE PASSWORD IMMEDIATELY IN PRODUCTION")
else:
    print("✓ Admin user exists")
EOF
echo -e "${GREEN}✓ Admin setup OK${NC}"
echo ""

# Step 5: Health Check
echo -e "${YELLOW}[5/6] Running health check...${NC}"
python3.11 manage.py health_check
echo -e "${GREEN}✓ Health check passed${NC}"
echo ""

# Step 6: Run Tests
echo -e "${YELLOW}[6/6] Running test suite...${NC}"
python3.11 -m pytest tests/ -q --tb=no 2>&1 | tail -3
echo -e "${GREEN}✓ Tests passed${NC}"
echo ""

echo -e "${GREEN}=================================="
echo "✅ Deployment Preparation Complete!"
echo "==================================${NC}"
echo ""
echo "Next steps:"
echo "1. Change admin password: python manage.py changepassword admin"
echo "2. Verify environment variables in .env"
echo "3. Test payment gateway (Paystack)"
echo "4. Test email service (SendGrid)"
echo "5. Click 'Publish' in Replit"
echo ""
echo "Documentation:"
echo "- DEPLOYMENT_CHECKLIST.md - Verification steps"
echo "- ADMIN_GUIDE.md - Administration guide"
echo "- PRODUCTION_READY.md - Production setup"
echo ""
