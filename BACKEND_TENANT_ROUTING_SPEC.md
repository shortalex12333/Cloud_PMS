# Backend Tenant Routing Specification

**Date:** 2026-01-13
**Status:** Required for production

## Overview

Frontend now sends ONLY `Authorization: Bearer <master_jwt>`. Backend must:
1. Verify JWT using MASTER Supabase JWT secret
2. Extract `user_id` (sub claim)
3. Query MASTER DB for tenant mapping
4. Load tenant credentials from Render env vars
5. Route request to correct per-yacht Supabase

## Required Environment Variables (Render)

```bash
# Master DB (control plane)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_JWT_SECRET=<actual-jwt-secret-from-supabase-dashboard>
MASTER_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q

# Per-tenant credentials (one set per yacht)
# Format: y<yacht_id_no_dashes>_SUPABASE_*
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=<service-key>
```

## Implementation

### 1. JWT Verification Middleware

```python
import os
import jwt
from functools import wraps
from flask import request, jsonify

MASTER_JWT_SECRET = os.environ.get('MASTER_SUPABASE_JWT_SECRET')

def verify_master_jwt(f):
    """Verify JWT using MASTER Supabase JWT secret."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header.split(' ')[1]

        try:
            # Verify JWT using master secret
            payload = jwt.decode(
                token,
                MASTER_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated'
            )

            # Store user_id for tenant lookup
            request.user_id = payload.get('sub')
            request.email = payload.get('email')

            if not request.user_id:
                return jsonify({'error': 'Invalid token: no sub claim'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401

        return f(*args, **kwargs)
    return decorated
```

### 2. Tenant Lookup

```python
import os
from supabase import create_client

# Master DB client (using service role)
MASTER_URL = os.environ.get('MASTER_SUPABASE_URL')
MASTER_SERVICE_KEY = os.environ.get('MASTER_SUPABASE_SERVICE_KEY')
master_client = create_client(MASTER_URL, MASTER_SERVICE_KEY)

def get_tenant_for_user(user_id: str) -> dict:
    """
    Query MASTER DB for user's tenant mapping.

    Returns:
        {
            'yacht_id': 'TEST_YACHT_001',
            'tenant_key_alias': 'yTEST_YACHT_001',
            'role': 'chief_engineer',
            'status': 'active'
        }
    """
    result = master_client.table('user_accounts').select(
        'yacht_id, role, status'
    ).eq('id', user_id).single().execute()

    if not result.data:
        return None

    user_account = result.data

    # Get tenant_key_alias from fleet_registry
    fleet = master_client.table('fleet_registry').select(
        'tenant_key_alias, active'
    ).eq('yacht_id', user_account['yacht_id']).single().execute()

    if not fleet.data or not fleet.data.get('active'):
        return None

    return {
        'yacht_id': user_account['yacht_id'],
        'tenant_key_alias': fleet.data['tenant_key_alias'],
        'role': user_account['role'],
        'status': user_account['status']
    }
```

### 3. Tenant DB Client Factory

```python
import os
from supabase import create_client

# Cache tenant clients
_tenant_clients = {}

def get_tenant_client(tenant_key_alias: str):
    """
    Get or create Supabase client for tenant.

    Loads credentials from env vars:
        {tenant_key_alias}_SUPABASE_URL
        {tenant_key_alias}_SUPABASE_SERVICE_KEY
    """
    if tenant_key_alias in _tenant_clients:
        return _tenant_clients[tenant_key_alias]

    url_key = f'{tenant_key_alias}_SUPABASE_URL'
    key_key = f'{tenant_key_alias}_SUPABASE_SERVICE_KEY'

    tenant_url = os.environ.get(url_key)
    tenant_key = os.environ.get(key_key)

    if not tenant_url or not tenant_key:
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    client = create_client(tenant_url, tenant_key)
    _tenant_clients[tenant_key_alias] = client

    return client
```

### 4. Complete Request Handler

```python
@app.route('/api/search', methods=['POST'])
@verify_master_jwt
def search():
    """Example endpoint with tenant routing."""

    # Get tenant for authenticated user
    tenant = get_tenant_for_user(request.user_id)

    if not tenant:
        return jsonify({'error': 'User not assigned to any tenant'}), 403

    if tenant['status'] != 'active':
        return jsonify({'error': 'Account not active'}), 403

    try:
        # Get tenant-specific Supabase client
        tenant_client = get_tenant_client(tenant['tenant_key_alias'])
    except ValueError as e:
        return jsonify({'error': 'Tenant configuration error'}), 500

    # Now use tenant_client for all DB operations
    query = request.json.get('query')

    result = tenant_client.table('document_chunks').select('*').text_search(
        'content', query
    ).limit(10).execute()

    return jsonify({'results': result.data})
```

## Error Responses

| Status | When | Response |
|--------|------|----------|
| 401 | JWT missing/invalid/expired | `{"error": "..."}` |
| 403 | User has no tenant mapping | `{"error": "User not assigned to any tenant"}` |
| 403 | Account not active | `{"error": "Account not active"}` |
| 500 | Tenant credentials missing from env | `{"error": "Tenant configuration error"}` |

## Testing

```bash
# 1. Get access token from master auth
TOKEN=$(curl -s -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password' \
  -H 'apikey: <anon_key>' \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@alex-short.com","password":"TestPass123!"}' | jq -r '.access_token')

# 2. Call backend with token
curl -X POST 'https://pipeline-core.int.celeste7.ai/api/search' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query": "generator"}'

# Expected: 200 with search results from tenant DB
```

## Security Notes

1. **MASTER_SUPABASE_JWT_SECRET** must be the actual JWT secret from Supabase Dashboard → Settings → API → JWT Secret
2. Never expose tenant credentials to frontend
3. Always verify JWT before tenant lookup
4. Log security events for failed auth attempts

## Getting the JWT Secret

1. Go to https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/settings/api
2. Find "JWT Secret" under "JWT Settings"
3. Copy the secret (NOT the anon/service key)
4. Set as `MASTER_SUPABASE_JWT_SECRET` in Render

---

*Created as part of auth consolidation 2026-01-13*
