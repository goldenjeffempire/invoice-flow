# Production Profiling Guide

This guide covers profiling InvoiceFlow for memory leaks, performance bottlenecks, and optimization opportunities.

## Memory Leak Profiling

By default, Gunicorn restarts workers after 1000 requests to prevent memory leaks. To determine if actual leaks exist, profile the application:

### Option 1: Using py-spy (Recommended for Production)

```bash
# Install py-spy (non-intrusive, works in production)
pip install py-spy

# Profile for 60 seconds
python -m py_spy record -o profile.svg -- gunicorn invoiceflow.wsgi -c gunicorn.conf.py

# Set environment to disable restart cycles during profiling
GUNICORN_MAX_REQUESTS=0 python -m py_spy record -o profile_no_restart.svg -- gunicorn invoiceflow.wsgi -c gunicorn.conf.py
```

### Option 2: Using memory_profiler (Development/Staging)

```bash
pip install memory-profiler

# Add decorators to functions you suspect
from memory_profiler import profile

@profile
def my_function():
    # Your code here
    pass

# Run with profiling
python -m memory_profiler manage.py runserver
```

### Option 3: Using tracemalloc (Built-in Python)

```python
# In settings.py or a management command
import tracemalloc

tracemalloc.start()

# Your code here...

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f} MB; Peak: {peak / 1024 / 1024:.1f} MB")
```

## Disabling Max Requests During Profiling

To disable the 1000-request restart cycle for extended testing:

```bash
# In Render environment variables or .env
GUNICORN_MAX_REQUESTS=0
GUNICORN_MAX_REQUESTS_JITTER=0
```

Then restart the deployment. Gunicorn will no longer restart workers, allowing you to observe memory growth over time.

## Key Metrics to Monitor

1. **RSS Memory (Resident Set Size)**
   - Should plateau after initial request processing
   - If continuously growing = likely memory leak
   
2. **VMS Memory (Virtual Memory Size)**
   - May be higher than RSS but growth rate should match RSS
   
3. **Page Faults**
   - High page faults = memory pressure
   
4. **Request Latency**
   - Should not degrade over time
   - If latency increases = GC overhead or memory issues

## Health Check Endpoints

Use these endpoints to monitor application health during profiling:

- `/health/` - Basic health status
- `/health/ready/` - Readiness (includes DB, cache, migrations)
- `/health/live/` - Liveness (quick responsiveness check)
- `/health/detailed/` - Extended metrics (memory, system stats, environment)

Example:
```bash
curl https://invoiceflow.com.ng/health/detailed/ | jq '.metrics'
```

## After Profiling

If no memory leaks are found:
- Consider increasing `GUNICORN_MAX_REQUESTS` to a higher value (e.g., 5000)
- Or set to 0 to fully disable (not recommended without data)

If memory leaks are found:
- Use the profiling data to identify the culprit
- Common sources: circular references, cached data not cleared, event listeners not removed
- Add `# noqa` comments to the restart cycle comment in `gunicorn.conf.py` once justified

## Reference

- [py-spy Documentation](https://github.com/benfred/py-spy)
- [memory_profiler Documentation](https://github.com/pythonprofilers/memory_profiler)
- [Gunicorn Max Requests](https://docs.gunicorn.org/en/stable/source/gunicorn.workers.base.html#gunicorn.workers.base.Worker)
