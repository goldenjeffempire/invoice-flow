# Render Deployment - Step-by-Step Instructions

## ✅ YAML Issue Fixed

The render.yaml has been simplified to the minimal required configuration. The previous version had syntax that Render doesn't support (`sync: false`, `buildFilter`).

---

## 🚀 Deploy to Render in 3 Steps

### Step 1: Connect Repository
1. Go to https://render.com/dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repo (goldenjeffempire/invoice-flow)
4. Select `main` branch
5. Render automatically reads the simplified `render.yaml`

### Step 2: Add Environment Variables
In Render dashboard, set these environment variables:

**Database:**
```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require&channel_binding=require
```
(Copy from your Neon PostgreSQL)

**Security Keys (generate these):**
```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate ENCRYPTION_SALT  
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Add to Render:
```
SECRET_KEY=<paste output from above>
ENCRYPTION_SALT=<paste output from above>
```

**Payment Processing:**
```
PAYSTACK_SECRET_KEY=sk_live_your_key
PAYSTACK_PUBLIC_KEY=pk_live_your_key
```

**Email Delivery:**
```
SENDGRID_API_KEY=SG.your_key
```

### Step 3: Deploy
1. Click "Create Web Service"
2. Render auto-starts deployment
3. Watch build logs
4. Once green, your app is live!

---

## 🌐 Setup Custom Domain

### On Render:
1. Go to your InvoiceFlow service
2. Click "Settings"
3. Scroll to "Custom Domain"
4. Add domain: `invoiceflow.com.ng`
5. Click "Add Custom Domain"
6. Copy the DNS records shown

### On DomainKing:
1. Login to DomainKing dashboard
2. Find your domain: `invoiceflow.com.ng`
3. Go to "Manage DNS"
4. Add CNAME record:
   - **Name:** @ (or blank/root)
   - **Type:** CNAME
   - **Value:** [Paste Render's DNS target]
   - **TTL:** 3600
5. Save changes
6. Wait 5-15 minutes for DNS propagation

### Verify:
```bash
# After DNS propagates:
curl https://invoiceflow.com.ng
# Should return your InvoiceFlow landing page ✅
```

---

## ✅ Checklist

- [ ] Create Neon PostgreSQL database (copy DATABASE_URL)
- [ ] Go to Render, connect GitHub repo
- [ ] Set all 6 environment variables (see Step 2 above)
- [ ] Deploy (click "Create Web Service")
- [ ] Wait for green checkmark in Render dashboard
- [ ] Add custom domain to Render settings
- [ ] Configure DomainKing DNS (CNAME record)
- [ ] Wait 5-15 min for DNS
- [ ] Visit https://invoiceflow.com.ng ✅

---

## 🆘 Troubleshooting

**Build Fails with "ModuleNotFoundError"**
- Render didn't run `pip install -r requirements.txt`
- Check that requirements.txt is in root directory
- Restart deployment

**502 Bad Gateway**
- Application crashed during startup
- Check Render logs for error messages
- Usually due to missing environment variables
- Verify all required env vars are set

**Database Connection Failed**
- Wrong DATABASE_URL format
- Neon IP whitelist needs your IP
- Check Neon console for connection issues

**Domain shows Render default page**
- DNS not propagated yet (wait 5-15 min)
- Clear browser cache
- Try incognito mode
- Use `nslookup invoiceflow.com.ng` to verify DNS

**Static files return 404**
- `collectstatic` didn't run
- Check build logs for "Collecting static files"
- Render should run this automatically

---

## 📞 Support

- **Render Docs:** https://render.com/docs
- **Neon Docs:** https://neon.tech/docs
- **Django Deployment:** https://docs.djangoproject.com/en/5.2/howto/deployment/

You're all set! 🚀
