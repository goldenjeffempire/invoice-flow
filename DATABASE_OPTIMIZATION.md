# Database Connection Pool & Optimization Guide

InvoiceFlow uses PostgreSQL with optimized connection pooling. This guide covers configuration and troubleshooting.

## Current Database Configuration

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 600,        # Keep connections alive for 10 minutes
        "CONN_HEALTH_CHECKS": True,  # Ping idle connections periodically
        "CONN_HEALTH_CHECK_COEFF": 0.9,  # Health check at 90% of CONN_MAX_AGE
    }
}
```

## Connection Pool Behavior

### CONN_MAX_AGE = 600 Seconds (10 Minutes)

**What it means:**
- Django keeps database connections open for up to 600s of inactivity
- Improves performance (no reconnection overhead)
- Connections auto-close after 600s to refresh state

**Why 600 seconds?**
- PostgreSQL statement timeout default: ∞ (no limit)
- TCP connection idle timeout varies (usually 30+ minutes)
- 600s (10 min) provides good balance:
  - Long enough to reuse connections (performance)
  - Short enough to refresh state periodically (safety)

### CONN_HEALTH_CHECKS = True

**What it means:**
- Django periodically checks idle connections are still alive
- Replaces dead connections automatically
- Prevents "database connection lost" errors in client requests

**Health Check Frequency:**
- Checked at ~90% of CONN_MAX_AGE (540 seconds)
- Adds ~1-2ms per health check (negligible)

## Connection Pool Size

### Default Pool Size (Gunicorn)
```
Workers: 4
Threads per worker: 4 (default)
Total concurrent threads: 4 × 4 = 16
```

**Connection pool expectation:**
- Each thread needs a database connection
- Maximum connections: ~20 (gunicorn + other services)
- PostgreSQL should allow: 25-30 connections minimum

### PostgreSQL Configuration (Neon/Render)
```sql
-- Check current max connections
SHOW max_connections;  -- Default: 100 in cloud

-- Connection limit per user (if needed)
ALTER ROLE invoiceflow CONNECTION LIMIT 25;

-- Check current active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

## Monitoring Connection Pool

### Via Health Check Endpoint

```bash
curl https://invoiceflow.com.ng/health/detailed/ | \
  jq '.database'
```

Response:
```json
{
  "database": {
    "engine": "django.db.backends.postgresql",
    "host": "db.neon...",
    "name": "invoiceflow",
    "is_usable": true,
    "connection_status": "OK"
  }
}
```

### Via Django ORM

```python
from django.db import connections

# Get connection pool info
conn = connections['default']
print(f"Connection alive: {conn.is_usable()}")
print(f"Connection settings: {conn.settings_dict}")

# Get active connections (Postgres)
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
    active_connections = cursor.fetchone()[0]
    print(f"Active connections: {active_connections}")
```

## Optimization Strategies

### 1. Connection Pool Exhaustion
**Symptoms:**
- "FATAL: remaining connection slots are reserved" error
- 503 Service Unavailable under load
- Increasing response times

**Diagnosis:**
```python
# Check if connections are being exhausted
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT count(*), state 
        FROM pg_stat_activity 
        WHERE datname = current_database()
        GROUP BY state
    """)
    for count, state in cursor.fetchall():
        print(f"{state}: {count}")
```

**Solutions:**
1. Increase Gunicorn workers (more processes = better throughput)
2. Reduce CONN_MAX_AGE if connections leak
3. Add connection pool monitoring
4. Use PgBouncer (external connection pooler) for high load

### 2. Slow Queries
**Symptoms:**
- Dashboard takes >1 second to load
- Analytics page slow

**Enable Slow Query Logging:**
```sql
-- In PostgreSQL
SET log_min_duration_statement = 500;  -- Log queries >500ms

-- Or via environment (Neon)
ALTER DATABASE invoiceflow SET log_min_duration_statement = 500;
```

**Find Slow Queries:**
```python
# Django ORM logging
import logging
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# Then check logs for slow queries
# [5234.234ms] SELECT * FROM ...
```

**Common Slow Query Patterns:**
```python
# BAD: N+1 query problem
invoices = Invoice.objects.all()
for invoice in invoices:
    print(invoice.user.name)  # 1 query per invoice!

# GOOD: Use select_related
invoices = Invoice.objects.select_related('user').all()
for invoice in invoices:
    print(invoice.user.name)  # Already loaded

# BAD: Missing index on filtered column
Invoice.objects.filter(created_at > yesterday)  # Full table scan

# GOOD: Add index
class Meta:
    indexes = [
        models.Index(fields=['user', 'created_at']),
    ]
```

### 3. Idle Connection Cleanup
**Symptoms:**
- PostgreSQL connection slots fill up
- "too many connections" errors

**Verify Health Checks Working:**
```bash
# Check logs for connection errors
# Should NOT see:
# "connection reset by peer"
# "FATAL: connection limit exceeded"
```

**Manual Cleanup (if needed):**
```sql
-- Close idle connections (careful: will disconnect users)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND query_start < now() - interval '15 minutes';
```

### 4. Connection Leak Detection
**Symptoms:**
- Worker memory grows over time
- Connection errors despite low traffic

**Detection:**
```python
# Monitor connection pool size over time
from django.db import connections

def monitor_connections():
    conn = connections['default']
    # Check if connection is in use
    if hasattr(conn, 'queries'):
        print(f"Pending queries: {len(conn.queries)}")
    if hasattr(conn.connection, '_in_use'):
        print(f"Connection in use: {conn.connection._in_use}")
```

**Likely Causes:**
1. Exception in database transaction (connection not returned)
2. Missing `connection.close()` after raw SQL
3. Custom database connection not properly cleaned up

**Fix:**
```python
# BEFORE (can leak)
with connection.cursor() as cursor:
    cursor.execute("SELECT ...")
    # Exception here = connection leaked

# AFTER (safe)
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT ...")
finally:
    connection.close()  # Explicit cleanup
```

## Production Checklist

- [ ] **Connection Pool Monitoring**: Set up alerting for connection exhaustion
  - Alert if `active_connections > max_connections * 0.8`
- [ ] **Slow Query Logging**: Enabled and reviewed weekly
  - Check for full table scans (seq scans)
  - Verify indexes exist on filtered columns
- [ ] **Health Checks**: Passing consistently
  - `/health/ready/` should show `"database": true`
- [ ] **CONN_HEALTH_CHECKS**: Enabled (automatic dead connection cleanup)
- [ ] **Connection Limits**: PostgreSQL `max_connections >= 25`

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| DB Connection Latency | <5ms | Check `/health/detailed/` |
| Query P95 (50% of queries) | <10ms | - |
| Query P99 (slowest 1%) | <100ms | - |
| Active Connections | <16 | Check `pg_stat_activity` |
| Idle Connections | ~4-8 | (auto-cleaned) |

## Troubleshooting

### "could not connect to database"
**Cause:** Database unreachable or connection refused

**Solution:**
1. Verify DATABASE_URL is correct
2. Check PostgreSQL service is running
3. Verify network connectivity (firewall, VPN)
4. Check connection limits not exceeded

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### "FATAL: remaining connection slots are reserved"
**Cause:** Connection pool exhausted

**Solution:**
1. Reduce concurrent requests (rate limiting)
2. Increase PostgreSQL max_connections
3. Use external connection pooler (PgBouncer)
4. Optimize queries (reduce connection hold time)

### Connections increasing but not decreasing
**Cause:** Connection leak

**Solution:**
1. Restart application (temporary fix)
2. Find where connections not returned (code review)
3. Add connection cleanup middleware
4. Monitor with `/health/detailed/` endpoint

## References

- [Django Database Configuration](https://docs.djangoproject.com/en/5.2/ref/settings/#databases)
- [PostgreSQL Connection Management](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Neon Connection Limits](https://neon.tech/docs/manage/endpoints)
- [PgBouncer Documentation](https://www.pgbouncer.org/)
