# InvoiceFlow - 24/7 Uptime Setup on Render

**Goal:** Configure InvoiceFlow for production-grade 24/7 reliability  
**Status:** Production-ready configuration guide  
**Estimated Setup Time:** 15 minutes

---

## 🎯 What You Need for 24/7 Uptime

### 1. **Render Paid Plan (REQUIRED)**
Free tier has **no uptime guarantee** and services sleep after inactivity.

**Upgrade Steps:**
1. Go to https://render.com/dashboard
2. Click your **account** → **Billing**
3. Choose **Pro** plan ($7/month minimum)
4. Benefits:
   - ✅ 24/7 uptime guarantee
   - ✅ Unlimited build minutes
   - ✅ Auto-restart on crash
   - ✅ Better performance (more CPU/RAM)

---

## 2. **Health Checks (Auto-Restart)**

Render monitors your app and restarts it if it crashes.

### Already Configured in Code ✅

Your Django app has health check endpoints:
- **Frontend health:** `GET /health/` → Returns HTTP 200
- **API health:** `GET /api/health/` → Returns JSON status

### Render Auto-Detection:
When you deploy on **paid tier**, Render automatically:
- ✅ Detects `/health/` endpoint
- ✅ Pings every 30 seconds
- ✅ Auto-restarts if unhealthy
- ✅ Logs health check failures

No configuration needed! ✅

---

## 3. **Database Reliability (Neon PostgreSQL)**

### Auto-Backups:
1. Go to Neon console: https://console.neon.tech
2. Select your database
3. Go to **Backups** section
4. Enable **Automatic backups** (default: every 24 hours)
5. Retention: **7 days** (free tier)

### Connection Pooling:
Already configured in Django settings:
```python
CONN_MAX_AGE = 600  # 10 minutes
```
This prevents stale connections. ✅

### Database Monitoring:
1. Neon dashboard shows:
   - Connection count
   - Query performance
   - Disk usage
   - CPU load
2. Set alerts for:
   - High connection count (>100)
   - Disk usage >80%
   - Query latency >1s

---

## 4. **Error Monitoring & Alerting**

### Option A: Sentry (Recommended)
Real-time error tracking and alerting.

**Setup:**
1. Go to https://sentry.io
2. Create account (free tier available)
3. Create new Django project
4. Copy your **Sentry DSN**
5. Add to Render environment variables:
   ```
   SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
   ```
6. Sentry immediately starts tracking errors

**Benefits:**
- ✅ Real-time error notifications
- ✅ Error grouping & trends
- ✅ Performance monitoring
- ✅ Email/Slack alerts

### Option B: Render Logs
Monitor via Render dashboard:
1. Service → **Logs** tab
2. Watch for ERROR/CRITICAL messages
3. Set up email alerts (Render Pro feature)

---

## 5. **Auto-Restart on Deployment**

Your `startCommand` in Render config includes restart logic:
```bash
python manage.py migrate && \
python manage.py collectstatic --noinput && \
gunicorn invoiceflow.wsgi -c gunicorn.conf.py
```

This ensures:
- ✅ Database migrations run
- ✅ Static files collected
- ✅ Gunicorn starts fresh
- ✅ No stale connections

---

## 6. **Production Checklist for 24/7 Uptime**

### ✅ Already Done
- [x] Django configured for production (`DEBUG=false`, `PRODUCTION=true`)
- [x] Security headers enabled
- [x] Health checks implemented
- [x] Database connection pooling
- [x] Gunicorn optimized

### ✅ You Must Do
- [ ] **Upgrade Render to paid plan** (CRITICAL for 24/7 uptime)
- [ ] Create Neon PostgreSQL database
- [ ] Set all 6 environment variables
- [ ] Deploy to Render (paid plan)
- [ ] Enable Neon auto-backups
- [ ] Optional: Set up Sentry for error monitoring

---

## 📋 Step-by-Step: Upgrade to 24/7 Uptime

### Step 1: Upgrade Render Plan (5 min)
```
1. Go to render.com/dashboard
2. Click your account → Billing
3. Choose Pro plan ($7/month)
4. Add payment method
5. Confirm upgrade
```

### Step 2: Deploy Your App (5 min)
```
1. Go to Services
2. Select InvoiceFlow service
3. Click "Redeploy latest commit"
4. Wait for green checkmark
5. Your app now has 24/7 uptime ✅
```

### Step 3: Setup Monitoring (5 min)

**Option A - Sentry (recommended):**
```
1. Create account at sentry.io
2. Create Django project
3. Copy DSN
4. Add to Render env vars: SENTRY_DSN=...
5. Redeploy
```

**Option B - Render Email Alerts:**
```
1. Go to service Settings
2. Under "Alerts", enable email notifications
3. Choose: Deployment failures, Health check failures
4. Redeploy
```

### Step 4: Database Backups (2 min)
```
1. Go to Neon console
2. Select database
3. Go to Backups
4. Enable automatic backups
5. Set retention to 7 days
```

---

## 🔄 Auto-Restart Configuration

Render automatically restarts your app if:
1. **Health check fails** (3 consecutive failures = restart)
2. **Out of memory** (OOM kill = restart)
3. **Deployment** (new commit = restart)
4. **Manual restart** (you request it)

### View Restart Events:
```
Render Dashboard → Your Service → Events tab
Shows: Deployment starts, Health checks, Restarts
```

---

## 📊 Monitoring Dashboard

### Essential Metrics to Watch:

**Render Metrics:**
- CPU usage (should be <50% idle)
- Memory usage (should be <70%)
- Request count
- Response time (should be <200ms)

**Neon Metrics:**
- Connection count
- Query latency
- Disk usage
- Active connections

**Sentry Metrics (if enabled):**
- Error rate
- Failed transactions
- Slow endpoints
- User impact

---

## 🆘 Troubleshooting 24/7 Uptime

### Issue: "Service is restarting constantly"
**Cause:** Health check failing, out of memory, or database error  
**Fix:**
1. Check Render logs for error message
2. Verify DATABASE_URL is correct
3. Check Neon database is running
4. Restart manually from Render dashboard

### Issue: "Intermittent 503 errors"
**Cause:** App running out of connections  
**Fix:**
1. Render Pro has 4 GB RAM (upgrade if needed)
2. Check database connections (should be <100)
3. Verify Gunicorn is restarting properly

### Issue: "Database connection timeout"
**Cause:** Neon database sleeping or network issue  
**Fix:**
1. Neon free tier sleeps after 1 week inactivity
2. Upgrade Neon to paid plan for 24/7
3. Or: Upgrade Render (includes database wake-up)

### Issue: "Build takes too long"
**Cause:** Free tier has slower build machines  
**Fix:**
1. Upgrade Render to Pro (faster builds)
2. Currently blocked by pipeline minutes anyway

---

## 💰 Cost Breakdown

**For 24/7 Production:**
- Render Pro: **$7/month** (includes 24/7 uptime)
- Neon PostgreSQL: **FREE** (1 free database on free tier)
- **Total: $7/month**

**Optional:**
- Sentry Error Tracking: **FREE** (5,000 events/month)
- Custom domain (DomainKing): **~$10/year**

**Total Monthly: $7-10**

---

## ✅ Verification Checklist

After upgrading and deploying:

```bash
# 1. Check app is running
curl https://invoiceflow.com.ng
# Should return: InvoiceFlow landing page

# 2. Check health endpoint
curl https://invoiceflow.com.ng/health/
# Should return: {"status": "healthy"}

# 3. Check Render dashboard
# Service status should show: "Live"
# Health checks should show: "Passing"

# 4. Check logs
# No ERROR or CRITICAL messages
# Should see: "Starting Gunicorn server"

# 5. Check database
# Neon console should show: Connected
# Connection count should be: <20
```

---

## 🚀 Next Steps

1. **TODAY:** Upgrade Render to paid plan
2. **TODAY:** Redeploy your app
3. **THIS WEEK:** Set up Sentry or email alerts
4. **THIS WEEK:** Enable database backups

Once complete, your InvoiceFlow app will have:
- ✅ 24/7 uptime guarantee
- ✅ Automatic restarts on failure
- ✅ Real-time error monitoring
- ✅ Daily database backups
- ✅ Production-grade reliability

---

## 📚 Additional Resources

- **Render Docs:** https://render.com/docs
- **Render Uptime SLA:** https://render.com/terms#uptime
- **Neon Documentation:** https://neon.tech/docs
- **Django Production Guide:** https://docs.djangoproject.com/en/5.2/howto/deployment/

---

## 💡 Pro Tips for 24/7 Reliability

1. **Monitor regularly:** Check Render dashboard daily
2. **Test deployments:** Redeploy weekly to catch issues
3. **Database backups:** Restore test weekly to verify
4. **Security updates:** Update dependencies monthly
5. **Load testing:** Test with 100+ concurrent users monthly
6. **Capacity planning:** Monitor growth and upgrade before limits

---

**Your InvoiceFlow platform is ready for 24/7 production. Upgrade Render and you're done!** 🚀

Cost: **$7/month for professional-grade uptime guarantee**

Questions? Check Render docs or Neon docs above.
