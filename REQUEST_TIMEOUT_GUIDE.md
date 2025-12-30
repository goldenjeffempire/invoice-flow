# Request Timeout & Performance Tuning Guide

InvoiceFlow is configured for production with specific timeout settings. This guide explains the configuration and how to optimize for your use case.

## Current Timeout Configuration

```
Gunicorn Timeout: 120 seconds (2 minutes)
  - Any request taking >120s will be killed and restarted
  
Graceful Shutdown: 30 seconds
  - Workers have 30s to finish in-flight requests during redeployment
  
HTTP Keepalive: 5 seconds
  - Client connections idle >5s are closed to free resources
```

## Why These Values?

### 120-Second Request Timeout
- **Appropriate for**: Invoice generation, PDF exports, email sending, data exports
- **Not appropriate for**: Long-running batch jobs, large data migrations
- **Rationale**: 
  - Prevents hanging requests from consuming resources indefinitely
  - Allows time for most invoice operations (PDF gen ~5-10s, email ~2-3s)
  - Triggers automatic recovery if code enters infinite loop
  - Matches Render's default timeout expectations

### 30-Second Graceful Shutdown
- Gives workers time to finish serving requests during deployment
- If request still in-flight after 30s, it's forcefully terminated
- Balances between safety and deployment speed

### 5-Second HTTP Keepalive
- Connection pooling optimization
- Reduces zombie connections
- Matches typical client keepalive settings

## Monitoring Request Duration

### Check for Slow Requests

**Via Logs** (Gunicorn access logs):
```
127.0.0.1 - - [29/Dec/2025:19:16:47 -0600] "POST /invoices/create/ HTTP/1.1" 200 4521 "-" "Mozilla/5.0" response_time=5234_us worker_id=<234>
                                                                                                                          ^^^^^^^^^^^ microseconds (5.2ms)
```

**Via Health Check** (realtime metrics):
```bash
curl https://invoiceflow.com.ng/health/detailed/ | jq '.metrics'
```

Response includes:
- Process CPU usage
- Memory usage
- Thread count
- Open connections

### Identify Slow Operations

**PDF Generation** (most common bottleneck)
```python
# Check PDF generation time
response_time = time.time() - start
if response_time > 10:
    logger.warning(f"Slow PDF generation: {response_time}s")
```

**Email Sending** (network I/O)
```python
# SendGrid typically takes 1-3 seconds
# If email sending >10s = network issue or SendGrid rate limiting
```

**Database Queries** (N+1 queries, missing indexes)
```bash
# Enable query logging in development
python manage.py runserver --debug-sql
```

## Performance Optimization Strategies

### 1. Asynchronous PDF Generation (Recommended)
Instead of generating PDFs synchronously:

```python
# BEFORE (slow, blocks request)
@view
def generate_pdf(request, invoice_id):
    pdf = generate_pdf_bytes(invoice)  # 5-10 seconds
    return FileResponse(pdf)

# AFTER (fast, delegates to background task)
@view
def generate_pdf(request, invoice_id):
    # Start async task
    task = pdf_generation_task.delay(invoice_id)
    return JsonResponse({"task_id": task.id, "status": "processing"})
```

### 2. Database Query Optimization
Profile slow queries:

```python
# settings.py - Enable logging for slow queries >500ms
LOGGING = {
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

Common issues:
- [ ] N+1 queries in list views → Use `select_related()`, `prefetch_related()`
- [ ] Missing indexes → Check PostgreSQL slow query log
- [ ] Large result sets → Add pagination, use `.values()` for specific columns
- [ ] Inefficient aggregate queries → Use `annotate()` with database functions

### 3. Caching Strategy
Optimize frequently-accessed data:

```python
# Cache dashboard stats for 60 seconds
CACHE_TIMEOUT_DASHBOARD = 60

# Cache analytics for 120 seconds
CACHE_TIMEOUT_ANALYTICS = 120

# Invalidate cache when invoice changes
AnalyticsService.invalidate_user_cache(user_id)
```

### 4. Response Streaming
For large exports, stream instead of buffering:

```python
# BEFORE (buffers entire file in memory)
def export_csv(request):
    data = generate_large_csv()  # Big memory spike
    return HttpResponse(data, content_type='text/csv')

# AFTER (streams chunks, constant memory)
def export_csv(request):
    response = StreamingHttpResponse(
        csv_generator(),
        content_type='text/csv'
    )
    return response
```

## Adjusting Timeout Settings

### Scenario 1: PDF Generation Consistently >120s
**Cause**: Large invoices with complex layouts

**Solution 1 (Recommended)**: Use async task queue
```python
# Task queue handles long operations
pdf_task = generate_pdf_async.delay(invoice_id)
```

**Solution 2**: Increase timeout (careful!)
```python
# gunicorn.conf.py
timeout = 180  # Increase to 3 minutes
```

⚠️ **Warning**: Increasing timeout means:
- Slow requests tie up worker threads longer
- Can reduce throughput under load
- Doesn't solve root cause (inefficient PDF generation)

### Scenario 2: Email Sending Timeouts
**Cause**: SendGrid rate limiting or network issues

**Solution**:
```python
# Use async email sending
send_invoice_email.delay(invoice_id)  # Doesn't block request
```

### Scenario 3: Database Timeouts
**Cause**: Long-running queries (missing indexes, full table scans)

**Solutions**:
1. Add database indexes on frequently-queried columns
2. Optimize query (use `explain()` in PostgreSQL)
3. Archive old data to separate table
4. Use read replicas for heavy queries

```sql
-- Example: Add index on created_at for analytics queries
CREATE INDEX idx_invoices_user_created 
ON invoices(user_id, created_at DESC);
```

## Testing Timeout Behavior

### Simulate Slow Request
```python
# Add to a view temporarily for testing
import time

@view
def slow_endpoint(request):
    time.sleep(130)  # 130 seconds > 120s timeout
    return HttpResponse("Done")
```

Expected behavior:
- Request gets killed after 120s
- Worker restarts
- Client receives 503 Service Unavailable or connection reset

### Monitor Worker Restarts
```bash
# Check Render logs for worker restarts
# Look for: "[PID] [INFO] Booting worker with pid: [NEW_PID]"

# This indicates previous worker was killed due to timeout
```

## Production Checklist

- [ ] **PDF Generation**: <10 seconds per invoice
  - If slower, consider async generation
- [ ] **Email Sending**: <5 seconds per email
  - Use background tasks if >5s
- [ ] **Dashboard Load**: <1 second (cached)
  - Check `/health/detailed/` response time
- [ ] **Database Queries**: All <500ms
  - Use Django Debug Toolbar in development
  - Check PostgreSQL slow query log
- [ ] **Error Rate**: <1% of requests timing out
  - Monitor via logs, Render metrics
  - If higher, investigate performance

## Monitoring & Alerts

### Key Metrics to Track

1. **P95 Response Time** (95th percentile)
   - Should be <5 seconds
   - If trending upward = load increasing or query regression

2. **Timeout Rate** 
   - Should be 0
   - Any timeouts = investigate cause

3. **Worker Restart Rate**
   - Should be <1 per hour (due to max_requests cycle)
   - Higher = memory leak or frequent crashes

4. **Memory Growth Over Time**
   - Should plateau after 10 minutes
   - Continuous growth = memory leak

### Using Health Check for Monitoring

```bash
# Script to alert if response time >1000ms
curl -w "\nResponse time: %{time_total}s\n" \
  https://invoiceflow.com.ng/health/detailed/

# Parse JSON to check specific latencies
curl -s https://invoiceflow.com.ng/health/detailed/ | \
  jq '.details.database_latency_ms, .details.cache_latency_ms'
```

## FAQ

**Q: What happens if a request exceeds 120s?**
A: Gunicorn terminates the worker process and restarts it. The client receives an error (503 or connection reset).

**Q: Can I increase timeout indefinitely?**
A: You can, but it's not recommended. Better to:
1. Optimize the slow operation
2. Move to async task queue
3. Profile to find bottleneck

**Q: How do I know if a request timed out?**
A: Check Gunicorn logs for "Worker timeout" or "Booting worker" messages.

**Q: What's the difference between Gunicorn timeout and request timeout?**
A: Same thing in this context. Gunicorn's `timeout` setting applies per request.

**Q: Can I have different timeouts for different endpoints?**
A: Not directly with Gunicorn. Use middleware to skip timeout for specific paths:
```python
# Requires custom middleware
# Not recommended - better to use async tasks instead
```

## References

- [Gunicorn Timeout Documentation](https://docs.gunicorn.org/en/stable/source/gunicorn.settings.html#timeout)
- [Django Async Tasks (Celery/APScheduler)](https://docs.djangoproject.com/en/5.2/topics/async/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
