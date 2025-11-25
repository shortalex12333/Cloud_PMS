# Vercel Deployment Configuration

Configuration guide for deploying CelesteOS to Vercel (production only, no localhost).

## ✅ Configuration Status

All code is now configured for **Vercel-only deployment**:
- ✅ No localhost references in code
- ✅ All Microsoft OAuth config uses environment variables
- ✅ CORS configured for production domains only
- ✅ Frontend API URL points to production backend
- ✅ OAuth redirect URI points to production API

## 🚀 Backend Deployment (FastAPI API)

### Required Environment Variables

Set these in your backend hosting platform (Vercel, Railway, Render, etc.):

```bash
# Supabase (REQUIRED)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# JWT Authentication (REQUIRED)
JWT_SECRET=your-jwt-secret-key-very-secure

# Microsoft OAuth (REQUIRED for Outlook integration)
MICROSOFT_CLIENT_ID=41f6dc82-8127-4330-97e0-c6b26e6aa967
MICROSOFT_CLIENT_SECRET=<GET-FROM-AZURE-PORTAL>
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=https://api.celeste7.ai/v1/integrations/outlook/callback

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Getting Microsoft Client Secret

**CRITICAL**: You must set `MICROSOFT_CLIENT_SECRET` from Azure Portal:

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find app with Client ID: `41f6dc82-8127-4330-97e0-c6b26e6aa967`
4. Go to **Certificates & secrets**
5. Under "Client secrets", find the existing secret or create a new one
6. **Copy the secret value** (you can only see it once!)
7. Set as `MICROSOFT_CLIENT_SECRET` environment variable

### Backend Deployment Options

#### Option 1: Vercel (Serverless Functions)

```bash
cd cloud/api
vercel deploy --prod

# Or link to project and auto-deploy
vercel link
vercel --prod
```

Set environment variables in Vercel dashboard:
- Project Settings → Environment Variables
- Add all required variables above

#### Option 2: Railway

```bash
railway login
railway init
railway up

# Set environment variables
railway variables set MICROSOFT_CLIENT_SECRET=<secret>
railway variables set SUPABASE_URL=<url>
# ... etc
```

#### Option 3: Render

1. Create new Web Service
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in dashboard

## 🌐 Frontend Deployment (Next.js)

### Required Environment Variables

Set these in Vercel project settings:

```bash
# API Configuration (REQUIRED)
NEXT_PUBLIC_API_URL=https://api.celeste7.ai/v1

# Supabase (REQUIRED)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Deploy to Vercel

```bash
cd frontend

# Install Vercel CLI
npm i -g vercel

# Deploy
vercel deploy --prod

# Or link to project
vercel link
vercel --prod
```

**Or use Vercel Dashboard**:
1. Go to [vercel.com](https://vercel.com)
2. Import GitHub repository
3. Select `frontend` directory as root
4. Set environment variables
5. Deploy

### Custom Domain Setup

In Vercel dashboard:
1. Go to Project Settings → Domains
2. Add custom domain: `app.celesteos.com` or `celeste7.ai`
3. Update DNS records as instructed
4. Vercel will automatically provision SSL certificate

## 🗄️ Database Setup (Supabase)

### Apply Migrations

```bash
# Using Supabase CLI
cd cloud/supabase
supabase db push

# Or manually in Supabase SQL Editor
# Copy contents of migrations and execute:
# - 001_initial_schema.sql
# - 002_documents_uploads.sql
# - 003_integration_tokens.sql
```

### Verify Tables Created

In Supabase Dashboard → Table Editor, verify:
- ✅ `integration_tokens` table exists
- ✅ `users` table exists
- ✅ RLS policies are enabled on `integration_tokens`

### Check RLS Policies

Run in SQL Editor:

```sql
-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'integration_tokens';

-- Should return: rowsecurity = true

-- Check policies
SELECT * FROM pg_policies
WHERE tablename = 'integration_tokens';

-- Should have 2 policies:
-- 1. "Users can access own integration tokens" (FOR ALL, user_id = auth.uid())
-- 2. "Service role has full access to integration tokens" (FOR ALL TO service_role)
```

## 🔐 Microsoft App Registration Verification

Verify redirect URI in Azure Portal:

1. Go to Azure Portal → App registrations
2. Find app: `41f6dc82-8127-4330-97e0-c6b26e6aa967`
3. Go to **Authentication** → **Platform configurations** → **Web**
4. Verify redirect URI is set:
   ```
   https://api.celeste7.ai/v1/integrations/outlook/callback
   ```
5. If not present, click **Add URI** and add it
6. Make sure **ID tokens** and **Access tokens** are checked
7. Click **Save**

### API Permissions

Verify these permissions are granted (should already be configured):
- ✅ `Mail.Read` - Read user mail
- ✅ `User.Read` - Sign in and read user profile
- ✅ `MailboxSettings.Read` - Read user mailbox settings
- ✅ `offline_access` - Maintain access to data you have given it access to

## 🧪 Testing Deployment

### 1. Test Backend API

```bash
# Health check
curl https://api.celeste7.ai/health

# Should return 200 OK with API info
```

### 2. Test Frontend

Visit: `https://app.celesteos.com` (or your Vercel URL)

Should see home page with:
- ✅ "Welcome to CelesteOS" heading
- ✅ Login prompt or user info (if authenticated)
- ✅ "Go to Settings" link (if authenticated)

### 3. Test Outlook Integration

1. **Login to CelesteOS** (set up Supabase auth first)
2. **Navigate to** `/settings`
3. **Click "Connect Outlook"**
4. **Should open Microsoft OAuth popup** (not blocked)
5. **Login with Microsoft account**
6. **Grant permissions**
7. **Popup should close automatically**
8. **Verify "Connected ✓" appears** with your email

### Debugging OAuth Flow

If OAuth fails, check:

**Backend logs**:
```bash
# Check Vercel/Railway/Render logs
# Look for:
# ✅ "Generated Microsoft auth URL for user: <user_id>"
# ✅ "Received auth code for user_id: <user_id>"
# ✅ "Token stored successfully for user: <user_id>"

# Or errors:
# ❌ "Token exchange failed: ..."
# ❌ "Failed to store token: ..."
```

**Common issues**:
- `MICROSOFT_CLIENT_SECRET` not set → Token exchange fails
- Redirect URI mismatch → OAuth error from Microsoft
- RLS policies not applied → Database insert fails
- CORS error → Frontend origin not in allowed list

## 📊 Environment Variable Checklist

### Backend (cloud/api)

- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_ANON_KEY`
- [ ] `SUPABASE_SERVICE_KEY`
- [ ] `JWT_SECRET`
- [ ] `MICROSOFT_CLIENT_ID` (should be: 41f6dc82-8127-4330-97e0-c6b26e6aa967)
- [ ] `MICROSOFT_CLIENT_SECRET` **← CRITICAL: Get from Azure Portal**
- [ ] `MICROSOFT_TENANT_ID` (should be: common)
- [ ] `MICROSOFT_REDIRECT_URI` (should be: https://api.celeste7.ai/v1/integrations/outlook/callback)
- [ ] `ENVIRONMENT` (set to: production)
- [ ] `LOG_LEVEL` (set to: INFO or DEBUG for troubleshooting)

### Frontend (frontend/)

- [ ] `NEXT_PUBLIC_API_URL` (should be: https://api.celeste7.ai/v1)
- [ ] `NEXT_PUBLIC_SUPABASE_URL`
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Database (Supabase)

- [ ] Migrations applied (001, 002, 003)
- [ ] `integration_tokens` table exists
- [ ] RLS enabled on `integration_tokens`
- [ ] Storage buckets created (`yacht-uploads`, `yacht-documents`)

### Azure (Microsoft App Registration)

- [ ] Redirect URI configured: `https://api.celeste7.ai/v1/integrations/outlook/callback`
- [ ] Client secret exists and copied to backend env
- [ ] API permissions granted (Mail.Read, User.Read, MailboxSettings.Read, offline_access)

## 🔄 Deployment Workflow

### Initial Setup (One-time)

1. **Apply database migrations** in Supabase
2. **Configure Azure redirect URI** (if not done)
3. **Get Microsoft client secret** from Azure Portal
4. **Deploy backend** with all environment variables
5. **Deploy frontend** with environment variables
6. **Test OAuth flow** end-to-end

### Subsequent Deploys

```bash
# Backend
cd cloud/api
git pull
vercel --prod  # or railway up, etc.

# Frontend
cd frontend
git pull
vercel --prod
```

Vercel auto-deploys on push to main if GitHub integration is set up.

## 🐛 Troubleshooting

### "Popup blocked" error

**Cause**: Browser blocking popup windows
**Solution**:
- Allow popups for your domain
- Fallback: App will redirect in same window

### "Failed to get auth URL" error

**Cause**: Backend not reachable
**Solution**:
- Check `NEXT_PUBLIC_API_URL` is correct
- Verify backend is deployed and healthy: `curl https://api.celeste7.ai/health`
- Check CORS settings include your frontend domain

### "Token exchange failed" error

**Cause**: Microsoft client secret not set or incorrect
**Solution**:
- Verify `MICROSOFT_CLIENT_SECRET` is set in backend environment
- Check it matches the secret in Azure Portal
- Look at backend logs for detailed error message

### "Failed to store token" error

**Cause**: Database migration not applied or RLS policy blocking insert
**Solution**:
- Apply migration `003_integration_tokens.sql`
- Verify service role policy exists and allows inserts
- Check backend has `SUPABASE_SERVICE_KEY` set (not anon key)

### CORS errors in browser console

**Cause**: Frontend origin not in allowed CORS origins
**Solution**:
- Add your Vercel URL to `CORS_ORIGINS` in `cloud/api/app/core/config.py`
- Current allowed origins:
  - `https://app.celesteos.com`
  - `https://celeste7.ai`
  - `https://*.celeste7.ai` (for Vercel preview deployments)
- Redeploy backend after updating

### OAuth redirect URI mismatch

**Cause**: Redirect URI in code doesn't match Azure Portal
**Solution**:
- Verify `MICROSOFT_REDIRECT_URI` in backend env matches Azure Portal exactly
- Should be: `https://api.celeste7.ai/v1/integrations/outlook/callback`
- Case-sensitive, must include `/v1/integrations/outlook/callback` path

## 📚 Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/)
- [Azure App Registrations](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

## ✅ Ready for Production

Once all checklist items are complete:
1. ✅ Backend deployed with all environment variables
2. ✅ Frontend deployed with environment variables
3. ✅ Database migrations applied
4. ✅ Microsoft client secret configured
5. ✅ OAuth redirect URI verified in Azure
6. ✅ End-to-end OAuth flow tested successfully

Your Outlook integration is ready for production use! 🚀

---

**Deployment Date**: 2025-11-20
**Branch**: `claude/add-file-reading-013P1WA2TehYr3YeKk1z9MEq`
**Configuration**: Vercel production deployment (no localhost)
