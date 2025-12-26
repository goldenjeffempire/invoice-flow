# InvoiceFlow - Quick Start to Production

**Goal:** Deploy InvoiceFlow to production in 25 minutes  
**Platform:** Render + Neon + DomainKing  
**Domain:** invoiceflow.com.ng

---

## ⚡ TL;DR - 3 Step Deployment

### Step 1: Create Database (5 min)
```
1. Go to https://neon.tech
2. Sign up and create new database
3. Copy connection string (your DATABASE_URL)
```

### Step 2: Deploy to Render (10 min)
```
1. Go to https://render.com
2. Connect your GitHub repo
3. Render reads render.yaml automatically
4. Set these environment variables:
   - SECRET_KEY (generate random 50+ chars)
   - DATABASE_URL (from Neon above)
   - ENCRYPTION_SALT (generate random base64)
   - PAYSTACK_SECRET_KEY (your Paystack key)
   - PAYSTACK_PUBLIC_KEY (your Paystack key)
   - SENDGRID_API_KEY (your SendGrid key)
5. Deploy (click "Create Web Service")
```

### Step 3: Setup Domain (10 min)
```
1. Copy DNS record from Render dashboard
2. Go to DomainKing → manage invoiceflow.com.ng DNS
3. Add CNAME record:
   - Name: @ (or blank)
   - Value: [Render DNS target]
   - TTL: 3600
4. Wait 5-15 minutes for DNS
5. Visit https://invoiceflow.com.ng ✅
```

---

## 🔑 Generate Required Keys

### SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output → paste in Render env vars

### ENCRYPTION_SALT
```bash
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```
Copy the output → paste in Render env vars

---

## ✅ Verify Deployment

```bash
# After domain DNS propagates (5-15 min):
curl https://invoiceflow.com.ng/health/
# Should return: {"status": "healthy", ...}

# Or visit in browser:
# https://invoiceflow.com.ng
```

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| 502 Bad Gateway | Check Render logs, verify DATABASE_URL |
| Domain not working | Wait 5-15 min for DNS, check DomainKing records |
| Static files 404 | Render auto-runs collectstatic, check build logs |
| Database connection fails | Verify Neon DATABASE_URL is correct |

---

## 📞 Full Guides

- **Detailed Deployment:** See `PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Complete Audit:** See `FINAL_PRODUCTION_AUDIT_AND_DEPLOYMENT_REPORT.md`
- **API Documentation:** See `API_DOCUMENTATION.md`

---

**You're ready to go!** 🚀
