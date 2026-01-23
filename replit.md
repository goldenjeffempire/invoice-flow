# Replit (Development Only)

This repository can be run on Replit for **development previews**.

Production deployments should use **Render** (or another production platform) with:
- `DEBUG=False`
- strict `ALLOWED_HOSTS`
- strict `CSRF_TRUSTED_ORIGINS`
- a managed Postgres database
- proper secrets set via environment variables

If you use Replit, do not commit secrets. Configure them in Replit's Secrets UI.
