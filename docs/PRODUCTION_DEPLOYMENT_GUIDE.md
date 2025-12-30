# InvoiceFlow - Production Deployment Guide
## Deployment to Render + Custom Domain (DomainKing)

**Status:** ✅ Ready for Production  
**Version:** 2.0.0  
**Last Updated:** December 26, 2025

---

## 📋 Pre-Deployment Checklist

- [x] Application code is production-ready (tested and hardened)
- [x] Render deployment configuration created (render.yaml)
- [x] Gunicorn server configured for production
- [x] Security headers and hardening applied
- [x] Database migrations prepared
- [ ] Environment variables configured (your responsibility)
- [ ] Neon PostgreSQL database created (your responsibility)
- [ ] DomainKing domain setup (your responsibility)
- [ ] SSL certificate provisioning (auto-handled by Render)

---

## 🚀 Step 1: Create Neon PostgreSQL Database

1. **Visit** [https://console.neon.tech](https://console.neon.tech)
2. **Create a new project** with your database name
3. **Copy the connection string** (DATABASE_URL)
4. **Keep it safe** - you'll need it for Render environment variables

Example Neon URL format:
```
postgresql://user:password@host:5432/dbname?sslmode=require&channel_binding=require
```

---

## 📱 Step 2: Deploy to Render

### Option A: Using Git (Recommended)

1. **Push to GitHub:**
   ```bash
   git remote add origin https://github.com/yourusername/invoiceflow.git
   git branch -M main
   git push -u origin main
   ```

2. **Connect Render to GitHub:**
   - Visit [https://render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Select your GitHub repository
   - Choose "invoiceflow"

3. **Render Auto-Detection:**
   - Render will automatically detect `render.yaml`
   - No manual configuration needed!

### Option B: Using Git Integration (Easier)

1. Visit [render.com/dashboard](https://render.com/dashboard)
2. Click "New Web Service"
3. Choose "Deploy an existing repo"
4. Select your GitHub/GitLab/Bitbucket repo
5. Render reads `render.yaml` automatically

---

## 🔐 Step 3: Configure Environment Variables on Render

Once deployed, set these environment variables in Render dashboard:

### Critical Variables (REQUIRED):

```
SECRET_KEY=<generate-strong-random-key-50-chars-minimum>
ENCRYPTION_SALT=<generate-random-base64-string>
DATABASE_URL=postgresql://...  # Your Neon connection string from Step 1
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...
SENDGRID_API_KEY=SG...
```

### Generate Strong Keys:

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate ENCRYPTION_SALT
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### Automatic Configuration:

The `render.yaml` file already configures:
- ✅ Python 3.11 runtime
- ✅ WSGI server (Gunicorn)
- ✅ Database migrations on deploy
- ✅ Static file collection
- ✅ Security headers enabled
- ✅ Production domain settings

---

## 🌐 Step 4: Configure Custom Domain (invoiceflow.com.ng)

### On Render Dashboard:

1. **Go to** your InvoiceFlow web service
2. **Click** "Environment" → "Custom Domains"
3. **Add domain:** `invoiceflow.com.ng`
4. **Add domain:** `www.invoiceflow.com.ng` (optional)
5. **Copy DNS records** provided by Render

### On DomainKing:

1. **Login to** DomainKing dashboard
2. **Go to** Manage DNS for `invoiceflow.com.ng`
3. **Update DNS records:**
   - Type: CNAME
   - Name: @ (or leave blank for root)
   - Value: [Render-provided DNS target]
   - TTL: 3600

4. **For www subdomain** (optional):
   - Type: CNAME
   - Name: www
   - Value: [Render-provided DNS target]
   - TTL: 3600

5. **Save** DNS changes
6. **Wait 5-15 minutes** for DNS propagation

### Verify Setup:

```bash
# Check DNS propagation
nslookup invoiceflow.com.ng
dig invoiceflow.com.ng

# Should resolve to Render's servers
```

---

## 📊 Step 5: Verify Production Deployment

### Health Checks:

```bash
curl https://invoiceflow.com.ng/health/
# Should return: {"status": "healthy", "timestamp": "..."}

curl https://invoiceflow.com.ng/api/health/
# Should return: {"status": "ok", "database": "connected", ...}
```

### View Logs:

On Render dashboard:
- **Logs** tab shows real-time application logs
- **Metrics** tab shows performance and resource usage
- **Events** tab shows deployment history

---

## 🔒 Security Configuration

All security settings are pre-configured in `render.yaml`:

### Automatic Settings:
- ✅ HTTPS/SSL (auto-provisioned)
- ✅ Security headers (HSTS, CSP, COOP/COEP)
- ✅ CORS policy enforcement
- ✅ CSRF protection
- ✅ Input validation
- ✅ Rate limiting

### Manual Settings (if needed):
- Configure WAF on Render
- Enable Render's DDoS protection
- Set up backups for Neon database
- Configure Sentry error tracking

---

## 📈 Post-Deployment Monitoring

### Recommended Setup:

1. **Error Tracking (Sentry):**
   ```bash
   # Install Sentry SDK
   pip install sentry-sdk
   
   # Configure in Django
   import sentry_sdk
   sentry_sdk.init(dsn="your-sentry-dsn")
   ```

2. **Performance Monitoring:**
   - Use Render's built-in metrics
   - Monitor database connections
   - Track API response times

3. **Uptime Monitoring:**
   - Set up Render alerts
   - Configure status page
   - Use external monitoring service

4. **Database Backups:**
   - Enable Neon automatic backups
   - Schedule daily backups
   - Test restore procedures

---

## 🐛 Troubleshooting

### 502 Bad Gateway

**Cause:** Application not starting  
**Fix:** Check Render logs, verify DATABASE_URL is correct

```bash
# On Render logs:
# Look for: "Starting development server"
# or: "Starting Gunicorn server"
```

### 404 on Static Files

**Cause:** Static files not collected  
**Fix:** Render automatically runs `collectstatic`, verify:

```bash
# Check Render build logs for:
# "Collecting static files..."
# "123 static files collected"
```

### Database Connection Failed

**Cause:** Wrong DATABASE_URL or network issue  
**Fix:** 
1. Verify Neon DATABASE_URL in Render environment
2. Check Neon IP whitelist (allow all for now)
3. Test connection: `psql [DATABASE_URL]`

### Domain Not Resolving

**Cause:** DNS not updated yet  
**Fix:**
1. Wait 5-15 minutes for DNS propagation
2. Clear browser cache/DNS cache
3. Check DomainKing DNS records are correct
4. Use `nslookup` to verify DNS

---

## 📝 Environment Variables Reference

### Required for Production:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Django security | `django-insecure-...` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...` |
| `ENCRYPTION_SALT` | Field encryption | `base64-encoded-salt` |
| `PAYSTACK_SECRET_KEY` | Payment processing | `sk_live_...` |
| `SENDGRID_API_KEY` | Email delivery | `SG.xxxxx` |

### Optional for Production:

| Variable | Purpose | Default |
|----------|---------|---------|
| `SENTRY_DSN` | Error tracking | Disabled if not set |
| `REDIS_URL` | Cache backend | Uses in-memory cache |
| `LOG_LEVEL` | Logging verbosity | `info` |

---

## 🎯 Next Steps

After deployment:

1. **Test the application:**
   - Create test invoices
   - Test payment processing
   - Verify email delivery

2. **Monitor performance:**
   - Check Render metrics daily
   - Monitor database performance
   - Review error logs

3. **Backup strategy:**
   - Enable Neon backups
   - Test restore procedures
   - Document backup process

4. **Team access:**
   - Add team members to Render
   - Configure role permissions
   - Set up deployment notifications

---

## 📞 Support Resources

- **Render Docs:** https://render.com/docs
- **Neon Docs:** https://neon.tech/docs
- **Django Deployment:** https://docs.djangoproject.com/en/5.2/howto/deployment/
- **DomainKing Support:** https://domainking.com/support

---

## ✅ Deployment Completed

Your InvoiceFlow application is now:
- ✅ **Running on Render** with automatic scaling
- ✅ **Connected to Neon PostgreSQL** with backups
- ✅ **Accessible via invoiceflow.com.ng** custom domain
- ✅ **Secured with HTTPS** and security headers
- ✅ **Ready for production traffic**

**Ship with confidence! 🚀**
