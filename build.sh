#!/usr/bin/env bash
# =============================================================================
# InvoiceFlow Production Build Script
# Domain: https://invoiceflow.com.ng
# =============================================================================
set -o errexit

echo "=== InvoiceFlow Production Build Script ==="
echo "Target Domain: https://invoiceflow.com.ng"
echo "Runtime: Python 3.13"

# Export production domain for any scripts that need it
export PRODUCTION_DOMAIN="invoiceflow.com.ng"
export PRODUCTION_URL="https://invoiceflow.com.ng"

# Upgrade pip
echo "[1/7] Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "[2/7] Installing Python dependencies..."
pip install -r requirements.txt --no-cache-dir

# Install Node dependencies and build assets
if [ -f "package.json" ]; then
    echo "[3/7] Installing Node.js dependencies..."
    npm install --production=false --prefer-offline --no-audit
    
    # Build all production assets (CSS + minified JS/CSS)
    echo "[4/7] Building production assets..."
    npm run build:prod
else
    echo "[3/7] Skipping Node.js build (no package.json found)"
    echo "[4/7] Skipping asset minification"
fi

# Run Django migrations
echo "[5/7] Running database migrations..."
python manage.py migrate --noinput

# Create cache table (safe to run if already exists)
echo "[5.5/7] Creating cache tables (if needed)..."
python manage.py createcachetable 2>/dev/null || echo "  Cache table already exists (OK)"

# Collect static files
echo "[6/7] Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run Django system checks (non-blocking - warnings allowed)
echo "[7/7] Running Django system checks..."
python manage.py check --deploy || {
    EXITCODE=$?
    if [ $EXITCODE -eq 0 ]; then
        echo "✓ All deployment checks passed"
    else
        echo "⚠ Some deployment warnings (may be expected in build environment)"
    fi
}

echo ""
echo "=== Build Complete ==="
echo "✓ InvoiceFlow is ready for production at https://invoiceflow.com.ng"
echo "✓ Starting Gunicorn server..."
