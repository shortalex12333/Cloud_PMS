# CelesteOS Vercel Deployment Guide

## 🚀 Quick Deploy

### Option 1: Deploy via Vercel CLI

```bash
# Install Vercel CLI globally (if not installed)
npm i -g vercel

# Navigate to frontend directory
cd frontend

# Login to Vercel
vercel login

# Deploy
vercel
```

### Option 2: Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your GitHub repository
4. Select the `frontend` directory as the root
5. Vercel will auto-detect Next.js
6. Add environment variables (see below)
7. Click "Deploy"

## 🔐 Required Environment Variables

Add these in Vercel Dashboard → Settings → Environment Variables:

```env
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
NEXT_PUBLIC_API_BASE_URL=https://api.celeste7.ai/webhook/
```

## 📋 Deployment Settings

Vercel should auto-detect these, but verify:

- **Framework Preset:** Next.js
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm install`
- **Node Version:** 18.x or higher

## 🌐 Post-Deployment

After deployment, your app will be available at:
- Production: `https://celesteos.vercel.app` (or your custom domain)
- Preview: Unique URL for each branch/PR

### Custom Domain (Optional)

1. Go to Project Settings → Domains
2. Add your domain (e.g., `app.celesteos.cloud`)
3. Update DNS records as instructed by Vercel

## 🔄 Continuous Deployment

Vercel automatically deploys:
- **Production:** Every push to `main` branch
- **Preview:** Every push to other branches/PRs

## 🐛 Troubleshooting

### Build Fails

Check:
1. All environment variables are set
2. `package.json` scripts are correct
3. No TypeScript errors
4. Build logs in Vercel dashboard

### Environment Variables Not Working

- Make sure they're prefixed with `NEXT_PUBLIC_` for client-side access
- Redeploy after adding new env vars
- Check they're set for correct environment (Production/Preview/Development)

### 404 on Routes

- Verify Next.js App Router structure
- Check vercel.json configuration
- Ensure dynamic routes are properly named

## 📊 Performance

Expected performance:
- **First Load:** < 1s
- **Search Response:** < 500ms
- **Lighthouse Score:** 90+

## 🔒 Security Notes

- Never commit `.env.local` to git (already in .gitignore)
- Service role key should only be used in server-side API routes
- Use environment variables in Vercel dashboard for production secrets

## 📞 Support

Issues? Check:
- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
- Project build logs in Vercel dashboard
