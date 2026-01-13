# Fix Chrome CORS Blocking for Document Viewing

## Problem

Chrome blocks PDFs with error: **"This page has been blocked by Chrome"**

This is a **CORS (Cross-Origin Resource Sharing)** issue - Supabase Storage needs to allow your Vercel domain to access files.

---

## Solution: Configure CORS in Supabase Dashboard

### Step 1: Access Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Storage** in the left sidebar

---

### Step 2: Configure CORS for "documents" Bucket

1. Find the **"documents"** bucket (or create it if it doesn't exist)
2. Click on the bucket settings (gear icon or "..." menu)
3. Go to **Configuration** or **CORS settings**

---

### Step 3: Add CORS Rules

Add the following CORS configuration:

```json
{
  "allowedOrigins": [
    "https://your-vercel-app.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001"
  ],
  "allowedMethods": [
    "GET",
    "HEAD"
  ],
  "allowedHeaders": [
    "*"
  ],
  "maxAge": 3600
}
```

**Replace `https://your-vercel-app.vercel.app` with your actual Vercel deployment URL.**

---

### Step 4: Alternative - Allow All Origins (Less Secure)

If you want to allow access from any domain (not recommended for production):

```json
{
  "allowedOrigins": ["*"],
  "allowedMethods": ["GET", "HEAD"],
  "allowedHeaders": ["*"],
  "maxAge": 3600
}
```

---

## How to Find Your Vercel Domain

1. Go to https://vercel.com/dashboard
2. Find your Cloud PMS project
3. Click on it
4. Look for the **Production Domain** (e.g., `cloud-pms.vercel.app`)
5. Use this in the CORS configuration above

---

## Alternative: SQL-Based CORS Configuration

If your Supabase version supports it, you can configure CORS via SQL:

```sql
-- Enable CORS for the documents bucket
UPDATE storage.buckets
SET allowed_origins = ARRAY[
  'https://your-vercel-app.vercel.app',
  'http://localhost:3000'
]
WHERE name = 'documents';
```

---

## Verify the Fix

After configuring CORS:

1. **Clear browser cache** (important!)
2. Go to your Vercel app
3. Search for "manual"
4. Click on a document result
5. PDF should now load successfully ✅

---

## Additional Storage Configuration

### Make Bucket Public (if needed)

If you want documents to be publicly accessible (not recommended if they contain sensitive data):

1. In Supabase Dashboard → Storage → documents bucket
2. Toggle **"Public bucket"** to ON
3. This allows access without authentication (use with caution)

---

### Storage RLS Policies

Your storage bucket should have RLS (Row Level Security) policies that match your yacht isolation:

```sql
-- Policy: Users can only access documents for their yacht
CREATE POLICY "Yacht isolation for documents"
ON storage.objects
FOR SELECT
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_yacht
    WHERE user_id = auth.uid()
  )
);
```

This ensures users can only access documents that belong to their yacht.

---

## Common CORS Errors and Solutions

### Error: "No 'Access-Control-Allow-Origin' header"

**Solution:** Add your Vercel domain to `allowedOrigins` in CORS config

### Error: "CORS policy: Request header field authorization is not allowed"

**Solution:** Add `"authorization"` to `allowedHeaders`:

```json
{
  "allowedHeaders": ["authorization", "content-type", "*"]
}
```

### Error: "The request client is not a secure context"

**Solution:** Make sure you're using HTTPS (not HTTP) in production

---

## Testing Checklist

After applying CORS fix:

- [ ] Configured CORS in Supabase Storage dashboard
- [ ] Added your Vercel domain to `allowedOrigins`
- [ ] Allowed GET and HEAD methods
- [ ] Cleared browser cache
- [ ] Tested document search in live app
- [ ] Clicked on a document result
- [ ] PDF loads successfully without Chrome blocking

---

## Summary

**Root Cause:** Supabase Storage CORS not configured for Vercel domain
**Fix:** Add Vercel domain to CORS `allowedOrigins` in Supabase Dashboard
**Verification:** Clear cache and test document viewing in browser

This is **not related** to Phase 1 or Phase 2 deployment fixes - those are working correctly! ✅
