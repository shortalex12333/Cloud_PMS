"""
CelesteOS Backend - Authentication Middleware

Architecture (2026-01-13):
- JWT is verified using MASTER Supabase JWT secret
- user_id is extracted from JWT (sub claim)
- Tenant (yacht_id) is looked up from MASTER DB user_accounts table
- Frontend sends ONLY Authorization: Bearer <token>, no yacht_id

Handles:
- JWT validation against MASTER DB
- Tenant lookup from MASTER DB
- Yacht context injection
- Agent token validation
- Role-based access control
"""

from typing import Optional, Callable, Dict
from functools import wraps
import jwt
from fastapi import Request, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# MASTER DB JWT secret - used to verify all JWTs
MASTER_SUPABASE_JWT_SECRET = os.getenv('MASTER_SUPABASE_JWT_SECRET', '')
# Legacy - keep for backwards compatibility during transition
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '') or MASTER_SUPABASE_JWT_SECRET
AGENT_TOKEN_SECRET = os.getenv('AGENT_TOKEN_SECRET', '')

# MASTER DB connection for tenant lookup
MASTER_SUPABASE_URL = os.getenv('MASTER_SUPABASE_URL', 'https://qvzmkaamzaqxpzbewjxe.supabase.co')
MASTER_SUPABASE_SERVICE_KEY = os.getenv('MASTER_SUPABASE_SERVICE_KEY', '')

if not MASTER_SUPABASE_JWT_SECRET and not SUPABASE_JWT_SECRET:
    logger.error('MASTER_SUPABASE_JWT_SECRET environment variable not set')
    # Don't raise on import - allow health checks to work

security = HTTPBearer()

# ============================================================================
# MASTER DB CLIENT (for tenant lookup)
# ============================================================================

_master_client = None

def get_master_client():
    """Get or create MASTER DB Supabase client."""
    global _master_client
    if _master_client is None:
        if not MASTER_SUPABASE_SERVICE_KEY:
            logger.error("MASTER_SUPABASE_SERVICE_KEY not set")
            return None
        try:
            from supabase import create_client
            _master_client = create_client(MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY)
            logger.info(f"[Auth] MASTER DB client created: {MASTER_SUPABASE_URL[:30]}...")
        except Exception as e:
            logger.error(f"[Auth] Failed to create MASTER client: {e}")
            return None
    return _master_client

# ============================================================================
# TENANT LOOKUP CACHE
# ============================================================================

# Cache tenant info by user_id (cleared on restart)
_tenant_cache: Dict[str, Dict] = {}

def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    """
    Look up tenant info from MASTER DB for a user.

    Returns:
        {
            'yacht_id': 'TEST_YACHT_001',
            'tenant_key_alias': 'yTEST_YACHT_001',
            'role': 'chief_engineer',
            'status': 'active',
            'yacht_name': 'M/Y Test Vessel'
        }
    Or None if user has no tenant assignment.
    """
    # Check cache first
    if user_id in _tenant_cache:
        return _tenant_cache[user_id]

    client = get_master_client()
    if not client:
        logger.error("[Auth] Cannot lookup tenant - no MASTER client")
        return None

    try:
        # Query user_accounts - PK column is 'id' in production schema
        result = client.table('user_accounts').select(
            'yacht_id, role, status'
        ).eq('id', user_id).single().execute()

        if not result.data:
            logger.warning(f"[Auth] No user_accounts row for user {user_id[:8]}...")
            return None

        user_account = result.data

        # Check account status
        if user_account.get('status') != 'active':
            logger.warning(f"[Auth] User {user_id[:8]}... status is {user_account.get('status')}")
            return None

        # Get yacht info from fleet_registry
        # tenant_key_alias may or may not exist in the schema
        fleet_result = client.table('fleet_registry').select(
            'yacht_name, active'
        ).eq('yacht_id', user_account['yacht_id']).single().execute()

        if not fleet_result.data:
            logger.warning(f"[Auth] No fleet_registry for yacht {user_account['yacht_id']}")
            return None

        fleet = fleet_result.data

        if not fleet.get('active'):
            logger.warning(f"[Auth] Yacht {user_account['yacht_id']} is inactive")
            return None

        # Compute tenant_key_alias from yacht_id if not in DB
        # Convention: y + first 8 chars of yacht_id (no hyphens) OR yTEST_YACHT_001 for test
        yacht_id = user_account['yacht_id']
        if yacht_id == '85fe1119-b04c-41ac-80f1-829d23322598':
            # Known test yacht - use the configured alias
            tenant_key_alias = 'yTEST_YACHT_001'
        else:
            # Default pattern: y + yacht_id with hyphens removed
            tenant_key_alias = f"y{yacht_id.replace('-', '')}"

        tenant_info = {
            'yacht_id': yacht_id,
            'tenant_key_alias': tenant_key_alias,
            'role': user_account.get('role', 'member'),
            'status': user_account['status'],
            'yacht_name': fleet.get('yacht_name'),
        }

        # Cache for future requests
        _tenant_cache[user_id] = tenant_info
        logger.info(f"[Auth] Tenant lookup success: user={user_id[:8]}... -> yacht={tenant_info['yacht_id']}")

        return tenant_info

    except Exception as e:
        logger.error(f"[Auth] Tenant lookup failed for {user_id[:8]}...: {e}")
        return None

def clear_tenant_cache(user_id: str = None):
    """Clear tenant cache (on logout or role change)."""
    global _tenant_cache
    if user_id:
        _tenant_cache.pop(user_id, None)
    else:
        _tenant_cache.clear()

# ============================================================================
# JWT VALIDATION
# ============================================================================

def decode_jwt(token: str) -> dict:
    """
    Decode and validate JWT token using MASTER Supabase JWT secret.

    Returns decoded payload with:
    - sub (user_id)
    - email
    - role (from JWT, not authoritative - use tenant lookup)
    - exp (expiration)
    """
    secret = MASTER_SUPABASE_JWT_SECRET or SUPABASE_JWT_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail='JWT secret not configured')

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            audience='authenticated',
            options={'verify_exp': True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {str(e)}')


def extract_yacht_id(token: str) -> str:
    """
    Extract yacht_id from JWT token.
    """
    payload = decode_jwt(token)
    yacht_id = payload.get('yacht_id')

    if not yacht_id:
        raise HTTPException(status_code=403, detail='No yacht_id in token')

    return yacht_id


def extract_user_id(token: str) -> str:
    """
    Extract user_id from JWT token.
    """
    payload = decode_jwt(token)
    user_id = payload.get('sub') or payload.get('user_id')

    if not user_id:
        raise HTTPException(status_code=403, detail='No user_id in token')

    return user_id


def extract_role(token: str) -> str:
    """
    Extract user role from JWT token.
    """
    payload = decode_jwt(token)
    role = payload.get('role', 'crew')
    return role


# ============================================================================
# MIDDLEWARE DEPENDENCIES
# ============================================================================

async def validate_user_jwt(
    authorization: HTTPAuthorizationCredentials = Header(..., alias='Authorization')
) -> dict:
    """
    FastAPI dependency to validate user JWT and return payload.
    DEPRECATED: Use get_authenticated_user() for tenant lookup.

    Usage:
        @app.get('/endpoint')
        async def endpoint(auth: dict = Depends(validate_user_jwt)):
            user_id = auth['user_id']
            yacht_id = auth['yacht_id']
    """
    token = authorization.credentials
    payload = decode_jwt(token)

    return {
        'user_id': payload.get('sub') or payload.get('user_id'),
        'yacht_id': payload.get('yacht_id'),
        'role': payload.get('role', 'crew'),
        'email': payload.get('email'),
    }


async def get_authenticated_user(
    authorization: str = Header(..., alias='Authorization')
) -> dict:
    """
    FastAPI dependency for JWT validation + tenant lookup.

    This is the PRIMARY auth dependency for all endpoints.
    - Validates JWT using MASTER DB secret
    - Looks up tenant from MASTER DB user_accounts
    - Returns full auth context including tenant_key_alias

    Usage:
        @app.post('/search')
        async def search(auth: dict = Depends(get_authenticated_user)):
            yacht_id = auth['yacht_id']
            tenant_key_alias = auth['tenant_key_alias']

    Returns:
        {
            'user_id': 'uuid',
            'email': 'user@example.com',
            'yacht_id': 'TEST_YACHT_001',
            'tenant_key_alias': 'yTEST_YACHT_001',
            'role': 'chief_engineer',
            'yacht_name': 'M/Y Test Vessel'
        }

    Raises:
        401: Invalid/expired JWT
        403: User has no tenant assignment or account not active
    """
    # Extract token from "Bearer <token>"
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Invalid Authorization header format')

    token = authorization.split(' ', 1)[1]

    # Verify JWT
    payload = decode_jwt(token)
    user_id = payload.get('sub')

    if not user_id:
        raise HTTPException(status_code=401, detail='Invalid token: no user_id')

    # Look up tenant from MASTER DB
    tenant = lookup_tenant_for_user(user_id)

    if not tenant:
        raise HTTPException(
            status_code=403,
            detail='User not assigned to any tenant or account not active'
        )

    return {
        'user_id': user_id,
        'email': payload.get('email'),
        'yacht_id': tenant['yacht_id'],
        'tenant_key_alias': tenant['tenant_key_alias'],
        'role': tenant['role'],
        'yacht_name': tenant.get('yacht_name'),
    }


async def inject_yacht_context(
    authorization: HTTPAuthorizationCredentials = Header(..., alias='Authorization')
) -> str:
    """
    FastAPI dependency to extract and return yacht_id.

    Usage:
        @app.get('/endpoint')
        async def endpoint(yacht_id: str = Depends(inject_yacht_context)):
            # yacht_id is guaranteed to exist
    """
    token = authorization.credentials
    return extract_yacht_id(token)


async def validate_agent_token(
    x_yacht_signature: str = Header(...),
    x_agent_token: str = Header(...)
) -> dict:
    """
    FastAPI dependency to validate Local Agent tokens.

    Used for ingestion endpoints only.

    Returns:
        {
            'yacht_signature': str,
            'agent_id': str,
        }
    """
    # Validate agent token (HMAC or JWT-based)
    try:
        payload = jwt.decode(
            x_agent_token,
            AGENT_TOKEN_SECRET,
            algorithms=['HS256'],
            options={'verify_exp': True}
        )

        agent_yacht_sig = payload.get('yacht_signature')

        if agent_yacht_sig != x_yacht_signature:
            raise HTTPException(
                status_code=403,
                detail='Yacht signature mismatch'
            )

        return {
            'yacht_signature': x_yacht_signature,
            'agent_id': payload.get('agent_id'),
        }
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f'Invalid agent token: {str(e)}')


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

def require_role(*allowed_roles: str):
    """
    Decorator to enforce role-based access.

    Usage:
        @app.get('/dashboard')
        @require_role('chief_engineer', 'manager')
        async def dashboard(auth: dict = Depends(validate_user_jwt)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, auth: dict, **kwargs):
            user_role = auth.get('role', 'crew')

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f'Access denied. Required roles: {", ".join(allowed_roles)}'
                )

            return await func(*args, auth=auth, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# YACHT ISOLATION ENFORCEMENT
# ============================================================================

async def enforce_yacht_isolation(
    request: Request,
    resource_yacht_id: str,
    yacht_id: str = Header(..., alias='inject_yacht_context')
) -> None:
    """
    Ensure requested resource belongs to user's yacht.

    Usage:
        yacht_id = Depends(inject_yacht_context)
        resource = db.get_resource(resource_id)
        enforce_yacht_isolation(request, resource.yacht_id, yacht_id)
    """
    if resource_yacht_id != yacht_id:
        raise HTTPException(
            status_code=403,
            detail='Access denied: Resource belongs to different yacht'
        )


# ============================================================================
# TOKEN UTILITIES
# ============================================================================

def create_agent_token(yacht_signature: str, agent_id: str, expires_days: int = 365) -> str:
    """
    Create JWT token for Local Agent.

    Used during agent provisioning.
    """
    from datetime import datetime, timedelta

    payload = {
        'yacht_signature': yacht_signature,
        'agent_id': agent_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=expires_days),
    }

    token = jwt.encode(payload, AGENT_TOKEN_SECRET, algorithm='HS256')
    return token


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'decode_jwt',
    'extract_yacht_id',
    'extract_user_id',
    'extract_role',
    'validate_user_jwt',
    'get_authenticated_user',  # NEW: Primary auth dependency
    'lookup_tenant_for_user',  # NEW: Tenant lookup
    'clear_tenant_cache',      # NEW: Cache management
    'inject_yacht_context',
    'validate_agent_token',
    'require_role',
    'enforce_yacht_isolation',
    'create_agent_token',
]
