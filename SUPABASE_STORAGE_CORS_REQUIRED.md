# Supabase Storage CORS Configuration Required

## Why This Is Needed

Even though we're using blob URLs for PDF viewing, the browser still needs to **fetch** the PDF from Supabase Storage first. This fetch request is subject to CORS policies.

**Without proper CORS configuration:**
- Browser blocks fetch request to Supabase Storage
- Blob conversion fails
- PDF never loads

---

## Required Configuration

### Access Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Select your project: `vzsohavtuotocgrfkfyd`
3. Navigate to **Storage** → **documents** bucket
4. Click **Configuration** or **CORS settings**

---

### CORS Configuration (Battle-Tested)

**IMPORTANT:** Only include stable domains. Never add changing Vercel preview URLs.

```json
{
  "allowedOrigins": [
    "https://app.celeste7.ai",
    "https://staging.celeste7.ai",
    "http://localhost:3000"
  ],
  "allowedMethods": [
    "GET",
    "HEAD",
    "OPTIONS"
  ],
  "allowedHeaders": [
    "Authorization",
    "Content-Type",
    "Range"
  ],
  "exposedHeaders": [
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "Content-Type"
  ],
  "maxAge": 3600
}
```

**Why OPTIONS:** Browsers send preflight OPTIONS requests when using Authorization header or Range requests. Without OPTIONS support, preflight fails and PDF won't load.

**Why Accept-Ranges:** PDF viewers use Range requests for progressive loading. Exposing this header helps clients optimize requests.

---

## Why These Settings

### `allowedOrigins`
- **Explicit list only** (never `["*"]`)
- Production domain
- Vercel deployment domain
- Localhost for development
- No wildcards for security

### `allowedMethods`
- **GET** - Fetch PDF data
- **HEAD** - Check if file exists (used by some PDF viewers)
- **NOT POST/PUT/DELETE** - Read-only access

### `allowedHeaders`
- **Authorization** - Signed URL authentication
- **Content-Type** - Required for proper MIME type handling
- **Range** - Critical for PDF viewers (allows partial content requests)

**Why Range is important:**
- PDF viewers often request specific page ranges
- Enables progressive loading (don't need to download entire 100MB PDF)
- Better performance and user experience

### `exposedHeaders`
- **Content-Length** - Browser needs this to show download progress
- **Content-Range** - Required for range requests
- **Content-Type** - Ensures browser knows it's a PDF

### `maxAge`
- **3600 seconds = 1 hour**
- Caches preflight OPTIONS requests
- Reduces load on Supabase
- Better performance (fewer round trips)

---

## Security Notes

### Why This Is Secure

1. **Read-Only Access**
   - Only GET and HEAD methods
   - No write operations allowed
   - No data modification possible

2. **Signed URLs Required**
   - Files aren't public
   - Access requires valid signed URL (short-lived)
   - Signed URLs validated by Supabase

3. **Explicit Origins**
   - Only your domains can fetch
   - No wildcard origins
   - Prevents unauthorized cross-origin access

4. **Yacht Isolation at Storage Level**
   - RLS policy enforces yacht_id in path
   - Users can only access their yacht's folder
   - Path format: `documents/{yacht_id}/...`

---

## Alternative: SQL-Based Configuration

If your Supabase version supports it:

```sql
-- Update CORS for documents bucket
UPDATE storage.buckets
SET allowed_origins = ARRAY[
  'https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app',
  'https://app.celeste7.ai',
  'http://localhost:3000'
],
allowed_methods = ARRAY['GET', 'HEAD'],
allowed_headers = ARRAY['Authorization', 'Content-Type', 'Range']
WHERE name = 'documents';

-- Verify
SELECT name, allowed_origins, allowed_methods, allowed_headers
FROM storage.buckets
WHERE name = 'documents';
```

---

## Verification Steps

### 1. Check Configuration

After applying CORS settings:

```bash
# Test CORS preflight
curl -X OPTIONS \
  'https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/documents/...' \
  -H 'Origin: https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: Authorization,Range' \
  -v
```

**Expected response headers:**
```
Access-Control-Allow-Origin: https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app
Access-Control-Allow-Methods: GET, HEAD
Access-Control-Allow-Headers: Authorization, Content-Type, Range
Access-Control-Max-Age: 3600
```

### 2. Test in Browser

1. Open your Vercel app
2. Open DevTools → Network tab
3. Search for "manual" and click a document
4. Look for request to `supabase.co/storage/v1/...`

**Expected:**
- Status: 200 OK
- Response headers include `Access-Control-Allow-Origin`
- No CORS errors in console

**If blocked:**
- Status: CORS error
- Console shows: "has been blocked by CORS policy"
- Check Supabase CORS configuration

### 3. Test Range Requests

PDF viewers often use range requests for better performance:

```bash
curl -X GET \
  'https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/sign/documents/...' \
  -H 'Origin: https://cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app' \
  -H 'Range: bytes=0-1024' \
  -v
```

**Expected:**
- Status: 206 Partial Content
- `Content-Range` header present
- CORS headers present

---

## Common Issues

### Issue 1: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Cause:** CORS not configured or wrong origin

**Fix:**
1. Verify configuration in Supabase Dashboard
2. Check origin exactly matches (case-sensitive, no trailing slash)
3. Clear browser cache

### Issue 2: "CORS policy: Request header field authorization is not allowed"

**Cause:** `Authorization` not in `allowedHeaders`

**Fix:**
Add `"Authorization"` to `allowedHeaders` in CORS config

### Issue 3: Range requests fail

**Cause:** Missing `Range` in allowed headers or `Content-Range` in exposed headers

**Fix:**
Add both:
```json
"allowedHeaders": ["Authorization", "Content-Type", "Range"],
"exposedHeaders": ["Content-Length", "Content-Range"]
```

### Issue 4: Works in localhost, fails in production

**Cause:** Production domain not in `allowedOrigins`

**Fix:**
Add your Vercel domain to `allowedOrigins`

---

## Performance Impact

### With Proper CORS Configuration

**First request (preflight + actual):**
```
OPTIONS request (preflight) → ~50ms
GET request (fetch PDF)     → ~100-500ms
Total:                        ~150-550ms
```

**Subsequent requests (cached preflight):**
```
GET request (fetch PDF)     → ~100-500ms
Total:                        ~100-500ms
```

**Improvement:** ~50ms saved per request (after first)

### Without maxAge

Every request requires preflight:
```
Total: ~150-550ms per request (no caching)
```

**With maxAge=3600:**
```
First:      ~150-550ms
Next hour:  ~100-500ms per request
```

**Result:** ~30% performance improvement on cached requests

---

## Monitoring

### What to Log

1. **CORS Failures**
   - Origin that was blocked
   - Requested method
   - Requested headers

2. **Storage Access Patterns**
   - Most accessed documents
   - Range request usage
   - Cache hit rate

3. **Performance Metrics**
   - Time to first byte
   - Full download time
   - Range request latency

### Dashboard Checks

**Supabase Dashboard → Storage → Logs:**
- Look for 403 errors (CORS blocking)
- Check for unusual access patterns
- Monitor bandwidth usage

---

## Checklist

After configuring:

- [ ] CORS configured in Supabase Dashboard
- [ ] Origins exactly match (no typos)
- [ ] Methods include GET and HEAD
- [ ] Headers include Authorization, Content-Type, Range
- [ ] Exposed headers include Content-Length, Content-Range
- [ ] maxAge set to 3600
- [ ] Tested with curl (preflight and actual request)
- [ ] Tested in browser (no CORS errors)
- [ ] Tested range requests (PDF pagination works)
- [ ] Verified no access to other yachts' files

---

## Summary

**What:** Configure Supabase Storage bucket CORS

**Why:** Browser needs permission to fetch PDFs from Supabase

**Where:** Supabase Dashboard → Storage → documents bucket → Configuration

**Security:** Read-only, explicit origins, signed URLs required, yacht isolation enforced

**Performance:** 1-hour preflight cache, range request support for progressive loading

**Status:** ⚠️ **MUST BE CONFIGURED FOR PDF VIEWING TO WORK**

---

**This is the final piece needed for PDF viewing to work correctly.**
