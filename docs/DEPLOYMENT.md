# InvoiceFlow Deployment Guide

## Overview
InvoiceFlow is a Django-based invoicing platform with a PostgreSQL backend. This guide covers deploying to Replit and production environments.

## Prerequisites
- Python 3.11+
- PostgreSQL database
- Environment variables configured
- SendGrid account (for email functionality)

## Deployment to Replit

### 1. Environment Setup
Ensure all environment variables are set in the Replit Secrets tab:
- `DATABASE_URL` - PostgreSQL connection string (auto-generated)
- `SECRET_KEY` - Django secret key
- `SENDGRID_API_KEY` - SendGrid API key for email delivery
- `DEBUG` - Set to False in production
- `ALLOWED_HOSTS` - Comma-separated list of allowed domains

### 2. Database Migrations
```bash
python manage.py migrate
```

### 3. Static Files
```bash
python manage.py collectstatic --noinput
```

### 4. Running the Server
The project is configured to run on port 5000:
```bash
python manage.py runserver 0.0.0.0:5000
```

## Production Deployment with Gunicorn

### Setup
```bash
gunicorn invoiceflow.wsgi:application \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --worker-class sync \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### Configuration
1. Set `DEBUG=False` in environment variables
2. Configure `ALLOWED_HOSTS` with your domain
3. Enable HTTPS/SSL (Replit auto-handles this)
4. Set secure cookies and CSRF settings

## Database Backups
- Replit automatically creates PostgreSQL backups
- Manual backups: Use `pg_dump` command
- Restore: Use `psql` with backup file

## Monitoring & Logs
- View logs in Replit's Logs tab
- Monitor performance using Django debug toolbar (development only)
- Use Sentry integration (if configured) for error tracking

## Health Checks
The application provides a health endpoint:
- `GET /health/` - Returns 200 if system is operational

## Scaling Considerations
- Use database connection pooling for high traffic
- Consider caching with Redis for performance
- Enable WhiteNoise for efficient static file serving (already configured)
- Monitor CPU and memory usage

## Rollback Procedure
1. Revert code changes via git
2. Run migrations in reverse (if needed):
   ```bash
   python manage.py migrate invoices 0022
   ```
3. Restart the application

## Support
For deployment issues, refer to:
- Django documentation: https://docs.djangoproject.com/en/5.2/howto/deployment/
- Replit documentation: https://replit.com/docs
- Project README: See root directory
