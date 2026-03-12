#!/usr/bin/env bash
# InvoiceFlow – Render Build Script
# Runs during the BUILD phase (not deploy phase).
# Migrations are intentionally NOT here – they run in preDeployCommand
# (render.yaml) for zero-downtime deploys.
set -o errexit

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Build complete."
