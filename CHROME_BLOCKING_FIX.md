# Chrome PDF Blocking Fix - Complete Analysis and Solution

## Problem Statement

**Error:** "This page has been blocked by Chrome"

**When:** Viewing PDF documents in the frontend after clicking search results

**User Impact:** Users cannot view documents despite search working correctly

---

## Root Cause Analysis

### Why Chrome Blocks the PDF

1. **Cross-Origin Iframe Embedding**
   - Supabase signed URL origin: `https://[project-id].supabase.co/storage/v1/...`
   - Vercel app origin: `https://[your-app].vercel.app`
   - **Different origins = Security restriction**

2. **Chrome Security Headers**
   - Supabase Storage sends `X-Frame-Options` or CSP headers
   - These headers prevent embedding content in iframes from different origins
   - This is a security feature to prevent clickjacking attacks

3. **What Worked vs What Didn't**

   **✅ Manual Sharing (Works):**
   - Opening signed URL directly in new tab
   - Direct navigation, not iframe embedding
   - No cross-origin restrictions apply

   **❌ Iframe Embed (Blocked):**
   - `<iframe src="https://supabase.co/storage/..."/>`
   - Cross-origin content in iframe
   - Chrome's security policy blocks it

---

## Why This Is NOT a CORS Issue

**Common Misconception:** "We need to configure CORS on Supabase Storage"

**Reality:** CORS only applies to `fetch()` and `XMLHttpRequest` requests, not iframe embeds.

**What Actually Blocks Iframes:**
1. `X-Frame-Options` HTTP header (e.g., `SAMEORIGIN` or `DENY`)
2. `Content-Security-Policy: frame-ancestors` directive
3. Browser security for cross-origin embeds

**Why CORS Config Wouldn't Help:**
- CORS headers: `Access-Control-Allow-Origin`, etc.
- These control JavaScript fetch requests
- Iframes don't use fetch - they're document embeds
- Configuring CORS on Supabase wouldn't fix iframe blocking

---

## The Solution: Blob URL Conversion

### Strategy

Instead of embedding the cross-origin URL directly:
1. ✅ Use Supabase signed URL to **fetch** the PDF (this is a fetch request, not an embed)
2. ✅ Convert response to `Blob` object
3. ✅ Create a **blob URL** from the blob (`blob:https://your-app.vercel.app/...`)
4. ✅ Use blob URL in iframe (same-origin, no restrictions)

### Why This Works

**Blob URLs are same-origin:**
```
Before: <iframe src="https://supabase.co/storage/v1/..." />  ❌ Cross-origin
After:  <iframe src="blob:https://your-app.vercel.app/..." /> ✅ Same-origin
```

**Chrome allows same-origin iframe embeds without restrictions.**

---

## Implementation Details

### Changes Made

#### 1. `apps/web/src/lib/documentLoader.ts` (lines 111-180)

**Before:**
```typescript
// Get signed URL
const { data: urlData, error: urlError } = await supabase.storage
  .from(bucketName)
  .createSignedUrl(storagePath, 3600);

return {
  success: true,
  url: urlData.signedUrl, // ❌ Cross-origin URL
  metadata,
};
```

**After:**
```typescript
// Get signed URL
const { data: urlData, error: urlError } = await supabase.storage
  .from(bucketName)
  .createSignedUrl(storagePath, 3600);

// FIX: Fetch PDF as blob to avoid Chrome blocking
const response = await fetch(urlData.signedUrl);
const blob = await response.blob();
const blobUrl = URL.createObjectURL(blob);

return {
  success: true,
  url: blobUrl, // ✅ Same-origin blob URL
  metadata,
};
```

#### 2. `apps/web/src/components/situations/DocumentSituationView.tsx` (lines 49-57)

**Added blob URL cleanup:**
```typescript
// Cleanup blob URL on unmount to prevent memory leaks
useEffect(() => {
  return () => {
    if (documentUrl && documentUrl.startsWith('blob:')) {
      console.log('[DocumentSituationView] Cleaning up blob URL');
      URL.revokeObjectURL(documentUrl);
    }
  };
}, [documentUrl]);
```

**Why cleanup is important:**
- Blob URLs consume memory
- Each document creates a new blob URL
- Must revoke old URLs to prevent memory leaks
- Cleanup happens when component unmounts or URL changes

---

## Security Considerations

### Is This Secure?

**Yes.** The blob URL approach maintains all existing security:

1. **Authentication Still Required**
   - Must be authenticated to get Supabase signed URL
   - Signed URL has 1-hour expiration
   - Blob is created from authenticated fetch

2. **Yacht Isolation Still Enforced**
   - Storage RLS policy checks yacht_id
   - Path must start with user's yacht_id
   - Cannot access other yachts' documents

3. **No New Vulnerabilities**
   - Blob URL is random and unguessable
   - Only accessible from same origin
   - Temporary and revoked after use

### What Changes

**Before:**
```
User clicks document
  → Creates signed URL (authenticated)
  → Embeds signed URL in iframe
  → Chrome blocks (cross-origin)
```

**After:**
```
User clicks document
  → Creates signed URL (authenticated)
  → Fetches PDF data using signed URL
  → Creates blob from data
  → Embeds blob URL in iframe
  → Chrome allows (same-origin)
```

**Security is the same** - we just moved the signed URL from iframe src to fetch request.

---

## Testing Instructions

### 1. Wait for Vercel Deployment

After pushing commit `f96aebd`, Vercel will auto-deploy (2-5 minutes).

### 2. Test Document Viewing

1. Open your Vercel app in browser
2. Search for "manual"
3. Click on a document result
4. **Expected:** PDF loads successfully in viewer ✅
5. **NOT:** "This page has been blocked by Chrome" ❌

### 3. Test Download Functionality

1. While viewing a document, click Download button
2. **Expected:** PDF downloads successfully ✅

### 4. Check Console Logs

Open browser DevTools → Console:

**Expected logs:**
```
[documentLoader] Fetching PDF as blob to avoid CORS/CSP blocking...
[documentLoader] Created blob URL: { blob_size: 123456, blob_type: "application/pdf" }
[documentLoader] Document loaded successfully
```

### 5. Test Equipment (Should Still Reject)

1. Search for "generator" (equipment)
2. Click result
3. **Expected:** Error message: "This is not a document. Type: pms_equipment..." ✅
4. This confirms Phase 1 validation is still working

---

## Deployment Status

### Commit Information

- **Commit:** `f96aebd`
- **Branch:** `universal_v1`
- **Repository:** `shortalex12333/Cloud_PMS`
- **Pushed:** Yes (pushed to GitHub)

### Auto-Deployment

Vercel should auto-deploy if:
- ✅ Connected to `shortalex12333/Cloud_PMS`
- ✅ Production branch set to `universal_v1`
- ✅ Auto-deploy enabled
- ✅ GitHub webhook active

**Deployment time:** ~2-5 minutes after push

---

## Verification Checklist

After deployment completes:

- [ ] Document search works ("manual")
- [ ] Clicking document opens viewer
- [ ] PDF displays without Chrome blocking
- [ ] Download button works
- [ ] Equipment search shows appropriate error
- [ ] Console shows blob URL creation logs
- [ ] No memory leaks (blob URLs cleaned up)

---

## If Test Still Fails

### Possible Issues

1. **Vercel Not Deployed Yet**
   - Check Vercel dashboard for deployment status
   - Wait additional 2-3 minutes
   - Check for build errors

2. **Different Error Message**
   - Check browser console for errors
   - Look for fetch failures
   - Verify Supabase authentication

3. **Files Still Missing in Storage**
   - This fix assumes PDF files exist in Supabase Storage
   - If files missing, signed URL fetch will fail with 404
   - Check `STORAGE_ISSUE_ANALYSIS.md` for file upload instructions

### Next Iteration

If blob URL approach fails:
1. Check browser console for specific error
2. Verify fetch request succeeds (network tab)
3. Check blob type and size
4. Try alternative: embed with `<object>` tag instead of `<iframe>`

---

## Summary

**Problem:** Chrome blocked cross-origin iframe embeds from Supabase Storage

**Root Cause:** Security headers preventing different-origin content in iframes

**Solution:** Fetch PDF as blob, create same-origin blob URL, embed that instead

**Security:** Unchanged - same authentication and yacht isolation

**Deployment:** Commit `f96aebd` pushed to `universal_v1` branch

**Next Step:** Wait for Vercel deployment, then test document viewing

---

## Technical Details

### Why Manual Sharing Works

When you share a Supabase Storage link manually:
```
Direct navigation: window.location = "https://supabase.co/storage/..."
```

This is NOT an iframe embed:
- No `X-Frame-Options` check
- No CSP frame-ancestors check
- Just a normal page load

### Why Our Previous Approach Didn't Work

```tsx
<iframe src={signedUrl} /> // ❌ Cross-origin embed blocked
```

Chrome sees:
- Parent: `https://your-app.vercel.app`
- Iframe: `https://supabase.co/storage/...`
- Different origins → Check headers → Block

### Why Blob URL Works

```tsx
<iframe src={blobUrl} /> // ✅ Same-origin embed allowed
```

Chrome sees:
- Parent: `https://your-app.vercel.app`
- Iframe: `blob:https://your-app.vercel.app/...`
- Same origin → Allow

---

**Fix deployed and ready for testing.** ✅
