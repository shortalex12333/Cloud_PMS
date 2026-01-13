# Deploy Frontend from universal_v1 Branch to Vercel

## **Repository Information**

- **GitHub Repo:** `shortalex12333/Cloud_PMS`
- **Branch:** `universal_v1` ✅
- **Frontend Directory:** `apps/web`
- **Framework:** Next.js

---

## **Current Status**

✅ Frontend changes committed and pushed to `universal_v1` branch
✅ Commit `11cf69a` contains the frontend fix
❓ Vercel deployment status: Unknown (needs configuration)

---

## **Option 1: Configure Vercel to Deploy from universal_v1 Branch**

### **Step 1: Access Vercel Dashboard**

1. Go to https://vercel.com/dashboard
2. Sign in with your account
3. Find your Cloud PMS project (or create if it doesn't exist)

---

### **Step 2: Connect to GitHub Repository** (if not already connected)

**If project doesn't exist:**

1. Click **"Add New..."** → **"Project"**
2. Click **"Import Git Repository"**
3. Select **`shortalex12333/Cloud_PMS`**
4. Click **"Import"**

**Configure the project:**
- **Framework Preset:** Next.js
- **Root Directory:** `apps/web` ⚠️ **IMPORTANT**
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm install`

---

### **Step 3: Set Production Branch to universal_v1**

**In Project Settings:**

1. Go to **Settings** → **Git**
2. Under **Production Branch**, change from `main` to:
   ```
   universal_v1
   ```
3. Click **"Save"**

**This makes Vercel auto-deploy from `universal_v1` branch.**

---

### **Step 4: Deploy**

**Trigger initial deployment:**

1. Go to **Deployments** tab
2. Click **"Redeploy"** or **"Deploy"**
3. Select branch: **`universal_v1`**
4. Click **"Deploy"**

Vercel will:
- ✅ Pull latest code from `universal_v1` branch
- ✅ Build from `apps/web` directory
- ✅ Deploy to production URL

---

## **Option 2: Manual Deploy via Vercel CLI**

### **Install Vercel CLI:**

```bash
npm install -g vercel
```

### **Login to Vercel:**

```bash
vercel login
```

### **Deploy from Frontend Directory:**

```bash
# Navigate to frontend
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

# Deploy to production
vercel --prod

# Follow prompts:
# - Link to existing project: Yes
# - Select project: (your Cloud PMS project)
# - Override settings: No (use defaults)
```

Vercel will:
- Build the Next.js app
- Deploy to production
- Give you a deployment URL

---

## **Option 3: Deploy via Git Integration (Recommended for Auto-Deploy)**

### **Ensure Vercel is Watching universal_v1:**

**In Vercel Dashboard:**

1. **Settings** → **Git**
2. **Production Branch:** Set to `universal_v1`
3. **Auto-Deploy:** Enabled for production branch
4. **Ignored Build Step:** Leave empty (or ensure it doesn't ignore this branch)

### **Enable Auto-Deploy for Branch:**

1. **Settings** → **Git** → **Deploy Hooks**
2. Ensure GitHub webhook is active
3. If webhook is missing, reconnect GitHub integration:
   - **Settings** → **Git** → **Disconnect** (if connected)
   - **Settings** → **Git** → **Connect Git Repository**
   - Select `shortalex12333/Cloud_PMS`
   - Grant permissions

---

## **Vercel Configuration Files**

Your repo already has:

### **Root `vercel.json`:**
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs"
}
```

### **`apps/web/vercel.json`:**
```json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "outputDirectory": ".next"
}
```

✅ Configuration is correct.

---

## **Important: Root Directory Setting**

⚠️ **CRITICAL:** When setting up Vercel project, you MUST set:

**Root Directory:** `apps/web`

**Why?**
- Your monorepo has the frontend in `apps/web` subdirectory
- Vercel needs to know where to find `package.json`
- Without this setting, build will fail

**How to set:**
1. Vercel Dashboard → Project Settings → General
2. **Root Directory:** `apps/web`
3. Save

---

## **Verify Deployment**

### **After Deployment Completes:**

**1. Check Deployment Status:**
- Vercel Dashboard → Deployments
- Latest deployment should show:
  - ✅ Status: "Ready"
  - ✅ Branch: `universal_v1`
  - ✅ Commit: `11cf69a` or later

**2. Check Deployment URL:**
- Click on deployment to see URL (e.g., `https://your-app.vercel.app`)
- Visit URL in browser

**3. Test the Fix:**

**Test 1 - Equipment Query:**
```
1. Search for "generator"
2. Click on a generator result
3. Expected: "This is not a document. Type: pms_equipment..."
4. NOT: "Document not found"
```

**Test 2 - Document Query:**
```
1. Search for "manual"
2. Click on a document result
3. Expected: Document viewer opens
```

---

## **Troubleshooting**

### **Build Fails:**

**Check Build Logs:**
1. Vercel Dashboard → Deployments
2. Click on failed deployment
3. View "Build Logs"

**Common Issues:**
- ❌ Root directory not set to `apps/web`
- ❌ Node version mismatch
- ❌ Missing environment variables

**Solution:**
- Set Root Directory: `apps/web`
- Check `package.json` for Node version requirements
- Add any required environment variables in Settings → Environment Variables

---

### **Auto-Deploy Not Working:**

**Checklist:**
- [ ] GitHub integration connected
- [ ] Production branch set to `universal_v1`
- [ ] Auto-deploy enabled
- [ ] GitHub webhook active
- [ ] No ignored build step blocking deployment

**Fix:**
1. Settings → Git
2. Disconnect and reconnect GitHub
3. Set production branch to `universal_v1`
4. Enable auto-deploy

---

### **Wrong Branch Deploying:**

If Vercel deploys from `main` instead of `universal_v1`:

**Solution:**
1. Settings → Git → Production Branch
2. Change to: `universal_v1`
3. Save
4. Redeploy

---

## **Quick Deploy Commands**

### **If you have Vercel CLI installed:**

```bash
# One-time setup
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
vercel login

# Deploy to production
vercel --prod

# Or just deploy (preview)
vercel
```

---

## **Expected Result**

After successful deployment:

✅ Frontend deployed from `universal_v1` branch
✅ Latest commit `11cf69a` or newer
✅ Document viewer type validation works correctly
✅ Equipment queries show clear error messages
✅ Future pushes to `universal_v1` auto-deploy

---

## **Deployment Checklist**

- [ ] Vercel project exists or created
- [ ] Connected to `shortalex12333/Cloud_PMS` repo
- [ ] Root directory set to `apps/web`
- [ ] Production branch set to `universal_v1`
- [ ] Auto-deploy enabled
- [ ] Deployment triggered (manual or auto)
- [ ] Deployment status: "Ready"
- [ ] Tested in live app
- [ ] Document viewer works
- [ ] Equipment error messages clear

---

## **Summary**

**Repository:** `shortalex12333/Cloud_PMS`
**Branch:** `universal_v1` ✅
**Frontend Path:** `apps/web` ✅
**Pushed to GitHub:** ✅ Yes (commit `11cf69a`)

**Next Steps:**
1. Configure Vercel project with Root Directory = `apps/web`
2. Set Production Branch = `universal_v1`
3. Deploy manually or enable auto-deploy
4. Verify deployment and test

---

**Need Help?**

Vercel Docs: https://vercel.com/docs/deployments/git
Support: support@vercel.com
