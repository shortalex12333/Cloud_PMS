# JWT Token Refresh Guide

**Last Token Generated**: 2026-02-01
**Token Expiry**: 1 hour from generation
**User**: x@alex-short.com

---

## Quick Token Refresh

### Method 1: Using Python Script (Recommended)

```bash
# Navigate to project
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Run token refresh script
python3 /private/tmp/claude/-Volumes-Backup-CELESTE/2c7d59b4-1f2a-49d5-a582-d77d8ac60cb0/scratchpad/get_token.py

# Token saved to: /tmp/jwt_token.txt
# Export to environment:
export JWT_TOKEN=$(cat /tmp/jwt_token.txt)
```

### Method 2: Using cURL (Manual)

```bash
# Request token from Supabase
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Content-Type: application/json" \
  -d '{"email": "x@alex-short.com", "password": "Password2!"}'

# Extract access_token from response
```

### Method 3: Using Node.js

```javascript
const axios = require('axios');

async function getToken() {
  const response = await axios.post(
    'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password',
    {
      email: 'x@alex-short.com',
      password: 'Password2!'
    },
    {
      headers: {
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw',
        'Content-Type': 'application/json'
      }
    }
  );

  const token = response.data.access_token;
  const expiresIn = response.data.expires_in;

  console.log(`Token: ${token}`);
  console.log(`Expires in: ${expiresIn} seconds`);

  return token;
}

getToken();
```

---

## Testing Endpoints with Fresh Token

### Test 1: Health Check (No Auth Required)

```bash
curl https://pipeline-core.int.celeste7.ai/v2/search/health
```

Expected:
```json
{
  "status": "healthy",
  "orchestrator_ready": true,
  "has_intent_parser": true,
  "has_entity_extractor": true
}
```

### Test 2: Basic Search

```bash
export JWT_TOKEN=$(cat /tmp/jwt_token.txt)

curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "oil filter caterpillar", "limit": 10}'
```

Expected: JSON response with results, entities, timing

### Test 3: Orchestrated Search V2

```bash
curl -X POST https://pipeline-core.int.celeste7.ai/v2/search \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "pending shopping list items",
    "surface_state": "search"
  }'
```

Expected: JSON response with trust payload explaining routing

---

## Current Token Status (As of 2026-02-01)

```
✅ Fresh JWT Token Available
Location: /tmp/jwt_token.txt
Expires: 1 hour from generation
User: x@alex-short.com
```

### Validation Results

All endpoints tested and operational:

```
1. Part Search: 'oil filter caterpillar'
   ✅ Results: 10, Timing: 3121ms

2. Shopping List: 'pending shopping list items'
   ✅ Results: 0, Timing: 285ms

3. Equipment: 'main engine'
   ✅ Results: 10, Timing: 263ms

4. Fault Code: 'error code P0420'
   ✅ Results: 1, Timing: 2547ms

5. Work Order: 'completed work orders'
   ✅ Results: 0, Timing: 3296ms
```

---

## Automated Token Refresh Script

The Python script at:
```
/private/tmp/claude/-Volumes-Backup-CELESTE/2c7d59b4-1f2a-49d5-a582-d77d8ac60cb0/scratchpad/get_token.py
```

Features:
- Authenticates with Supabase
- Extracts JWT token
- Saves to `/tmp/jwt_token.txt`
- Shows expiry time
- Provides export command

---

## Token Expiry Handling

JWT tokens expire after **1 hour**. When testing:

1. **Check expiry before long test sessions**
2. **Refresh token when you see 401 Unauthorized**
3. **Implement token refresh in production code**

### Production Token Refresh Pattern

```javascript
class TokenManager {
  constructor() {
    this.token = null;
    this.expiresAt = null;
  }

  async getToken() {
    // Check if token is still valid
    if (this.token && Date.now() < this.expiresAt - 60000) {
      return this.token;
    }

    // Refresh token
    const response = await this.authenticate();
    this.token = response.access_token;
    this.expiresAt = Date.now() + (response.expires_in * 1000);

    return this.token;
  }

  async authenticate() {
    // Call Supabase auth endpoint
    // ...
  }
}
```

---

## Troubleshooting

### Error: "401 Unauthorized"
**Cause**: Token expired or invalid
**Solution**: Refresh token using script above

### Error: "Invalid grant"
**Cause**: Incorrect credentials
**Solution**: Verify email/password are correct

### Error: "Could not parse request body"
**Cause**: Password special characters not escaped
**Solution**: Use Python script instead of cURL

---

## Credentials (For Reference)

**Supabase Master**:
- URL: `https://qvzmkaamzaqxpzbewjxe.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (in scripts above)

**Test User**:
- Email: `x@alex-short.com`
- Password: `Password2!`

**Production API**:
- Base URL: `https://pipeline-core.int.celeste7.ai`

---

## Quick Commands

```bash
# Get fresh token
python3 /private/tmp/claude/-Volumes-Backup-CELESTE/2c7d59b4-1f2a-49d5-a582-d77d8ac60cb0/scratchpad/get_token.py

# Export to environment
export JWT_TOKEN=$(cat /tmp/jwt_token.txt)

# Test health
curl https://pipeline-core.int.celeste7.ai/v2/search/health

# Test search
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "oil filter", "limit": 10}'

# Run comprehensive tests
cd /private/tmp/claude/-Volumes-Backup-CELESTE/2c7d59b4-1f2a-49d5-a582-d77d8ac60cb0/scratchpad
python3 test_all_lenses_comprehensive.py
```

---

**Last Updated**: 2026-02-01
**Next Token Refresh**: When you see 401 errors or after 1 hour
