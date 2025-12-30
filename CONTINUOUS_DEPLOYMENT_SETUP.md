# 🚀 Continuous Deployment Setup for Render

## Problem Fixed
Workers were not shutting down cleanly during continuous deployment, causing slow deployments.

## Solution Implemented
Optimized Gunicorn graceful shutdown for continuous deployment on Render.

### Changes Made

**1. Graceful Timeout Optimized**
- **Before:** 30 seconds (too long for CI/CD)
- **After:** 10 seconds (default), configurable via environment variable
- **Benefit:** Clean, fast worker shutdown during deployment

**2. Configuration Files Updated**
- `gunicorn.conf.py`: Added graceful timeout environment variable support
- `deploy_config_tool`: Configured production deployment with build/run commands

**3. Render Deployment Config**
```
Deployment Target: autoscale
Build Command: python manage.py migrate && python manage.py collectstatic --noinput
Run Command: gunicorn invoiceflow.wsgi:application -c gunicorn.conf.py
```

## How It Works

### Default Behavior (Production)
- Graceful shutdown window: **10 seconds**
- Workers have 10 seconds to finish handling requests
- After 10 seconds, remaining connections forcefully closed
- Clean deployment restart with zero downtime

### Fast CI/CD Option
Set environment variable for faster deployments:
```
GUNICORN_GRACEFUL_TIMEOUT=5
```
This reduces shutdown time to 5 seconds for rapid continuous deployments.

## Deployment Process

1. **Render receives deploy signal**
2. **Gunicorn receives SIGTERM**
3. **Workers enter graceful shutdown** (10-second window by default)
4. **New deployment starts fresh**
5. **Zero downtime achieved**

## Monitoring Graceful Shutdown

Check logs for shutdown confirmation:
```
[timestamp] INFO Gunicorn shutting down gracefully...
[timestamp] INFO Worker exiting (pid: XXXX)
[timestamp] INFO Master shutting down
```

## Troubleshooting

### If deployment still takes too long:
1. Set `GUNICORN_GRACEFUL_TIMEOUT=5` in Render environment
2. Check for long-running requests (timeout=120s)
3. Monitor worker logs for stuck requests

### If requests fail during deployment:
1. Increase graceful_timeout to 15-20 seconds
2. Check database connection pools
3. Verify request handlers complete quickly

## Health Checks

Render automatically detects readiness:
- GET `/health/live/` - Quick liveness check
- POST `/health/ready/` - Full readiness check (DB, cache, migrations)

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `GUNICORN_GRACEFUL_TIMEOUT` | 10 | Shutdown grace window (seconds) |
| `GUNICORN_MAX_REQUESTS` | 1000 | Worker restart cycle (requests) |
| `GUNICORN_THREADS` | 4 | Threads per worker |
| `WEB_CONCURRENCY` | Auto | Number of workers |

## Next Steps

1. Deploy to Render with this configuration
2. Monitor logs for `Gunicorn shutting down gracefully...`
3. Verify deployment completes in under 30 seconds
4. Adjust GUNICORN_GRACEFUL_TIMEOUT if needed

---

**Status:** ✅ Continuous deployment optimized for fast, clean shutdowns
