# Dev Auth Guide - Extracting Supabase JWT

## How to Get Your JWT for Local API Testing

### Method 1: Browser DevTools (Recommended)

1. Log into the app at https://app.celeste7.ai (or localhost:3000)
2. Open DevTools (F12 or Cmd+Option+I)
3. Go to **Application** tab → **Local Storage** → select the app domain
4. Find the key: `sb-vzsohavtuotocgrfkfyd-auth-token`
5. Expand the value and copy the `access_token` field

### Method 2: Console Command

In browser console while logged in:
```javascript
const { data } = await supabase.auth.getSession();
console.log(data.session.access_token);
```

### Using the JWT for API Calls

```bash
# Set in terminal session (not .env to avoid accidental commit)
export DEV_JWT="eyJ..."

# Call API endpoints
curl -H "Authorization: Bearer $DEV_JWT" \
     http://localhost:8000/email/message/<id>/render
```

### Important Security Notes

- NEVER commit JWTs to git
- NEVER store in .env files that might be committed
- JWTs expire after ~1 hour; get a fresh one if calls fail with 401
- For CI/CD, use service role key with proper test isolation
