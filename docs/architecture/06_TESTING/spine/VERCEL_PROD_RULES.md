# VERCEL_PROD_RULES - Production Deployment Contract

**Generated:** 2026-01-13
**Purpose:** Vercel production configuration rules

---

## Production Branch

```
Branch: main
Auto-deploy: Yes
Production URL: https://app.celeste7.ai
```

**RULE:** Only `main` branch deploys to production domain.

---

## Domain Configuration

| Domain | Type | Target |
|--------|------|--------|
| `app.celeste7.ai` | Production | main branch |
| `auth.celeste7.ai` | Redirect | → app.celeste7.ai |
| `*.vercel.app` | Preview | Feature branches |

### Redirect Configuration

```json
// vercel.json
{
  "redirects": [
    {
      "source": "/(.*)",
      "destination": "https://app.celeste7.ai/$1",
      "permanent": true,
      "has": [{ "type": "host", "value": "auth.celeste7.ai" }]
    }
  ]
}
```

---

## Required Settings (Vercel Dashboard)

### Framework Preset

```
Framework: Next.js
Root Directory: apps/web
Build Command: npm run build
Output Directory: .next
Install Command: npm install
```

### Environment Variables

| Variable | Environment | Value |
|----------|-------------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Production | `https://qvzmkaamzaqxpzbewjxe.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production | `eyJ...` (anon key) |
| `NEXT_PUBLIC_API_URL` | Production | `https://pipeline-core.int.celeste7.ai` |

### Build Settings

```
Node.js Version: 18.x
```

---

## CSP Headers (next.config.js)

```javascript
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: `
      default-src 'self';
      script-src 'self' 'unsafe-eval' 'unsafe-inline';
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: blob: https:;
      font-src 'self';
      connect-src 'self'
        https://qvzmkaamzaqxpzbewjxe.supabase.co
        https://vzsohavtuotocgrfkfyd.supabase.co
        https://pipeline-core.int.celeste7.ai
        wss://*.supabase.co;
      frame-ancestors 'none';
    `.replace(/\s{2,}/g, ' ').trim()
  }
];
```

**CRITICAL:** Both Supabase URLs must be in `connect-src` or API calls fail.

---

## Deployment Protection

### Production Protection

```
Settings → Deployment Protection → Production
- Vercel Authentication: DISABLED (public app)
- Password Protection: DISABLED
```

**RULE:** Production must be publicly accessible without Vercel login prompt.

### Preview Protection

```
Settings → Deployment Protection → Preview
- Vercel Authentication: ENABLED (protect preview URLs)
```

---

## Troubleshooting

### Problem: main branch not deploying

**Check:**
1. Vercel Dashboard → Project → Settings → Git
2. Confirm "Production Branch" = `main`
3. Check if deployment was paused
4. Check for build errors in Deployments tab

### Problem: app.celeste7.ai shows Vercel login prompt

**Cause:** Deployment Protection enabled for production

**Fix:**
1. Settings → Deployment Protection
2. Select "Production"
3. Set Vercel Authentication to DISABLED

### Problem: CSP blocking Supabase

**Symptom:** Browser console shows CSP violation for `connect-src`

**Fix:**
1. Check `next.config.js` headers
2. Ensure both Supabase URLs are in connect-src
3. Redeploy after changes

### Problem: Preview URL works but production doesn't

**Cause:** Environment variables not set for Production

**Fix:**
1. Settings → Environment Variables
2. Select "Production" environment
3. Add missing variables
4. Redeploy

---

## Deployment Checklist

Before deploying to production:

- [ ] All environment variables set for Production environment
- [ ] CSP headers include all required domains
- [ ] Deployment Protection disabled for production
- [ ] Build succeeds locally: `npm run build`
- [ ] TypeScript check passes: `npm run typecheck`
- [ ] ESLint passes: `npm run lint`

---

## Monitoring

### Build Status

```
Vercel Dashboard → Project → Deployments
- Green checkmark = successful
- Red X = build failed (check logs)
```

### Runtime Errors

```
Vercel Dashboard → Project → Analytics → Runtime Errors
```

### Function Logs

```
Vercel Dashboard → Project → Logs
Filter by: Production
```

---

## Git Integration

### Branch Protection

```
GitHub → Settings → Branches → main
- Require pull request reviews: Recommended
- Require status checks: Recommended
```

### Auto-deploy Triggers

```
Push to main → Vercel detects → Build → Deploy
```

---

**Last Updated:** 2026-01-13
