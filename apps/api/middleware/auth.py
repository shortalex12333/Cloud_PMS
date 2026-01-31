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
import time
from fastapi import Request, HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging

try:
    from cachetools import TTLCache
    HAS_CACHETOOLS = True
except ImportError:
    HAS_CACHETOOLS = False
    logger.warning("[Auth] cachetools not installed - using dict cache without TTL")

logger = logging.getLogger(__name__)

# ============================================================================
# INCIDENT MODE / KILL SWITCH CONFIGURATION
# ============================================================================

# Action groups blocked during incident mode
INCIDENT_BLOCKED_GROUPS = {"MUTATE", "SIGNED", "ADMIN"}

# Cache TTL for system flags (seconds) - short for quick incident response
SYSTEM_FLAGS_CACHE_TTL = int(os.getenv("SYSTEM_FLAGS_CACHE_TTL", "10"))

# ============================================================================
# CONFIGURATION
# ============================================================================

# JWT secret - used to verify all JWTs
# Checks multiple env var names for flexibility:
#   - TENANT_SUPABASE_JWT_SECRET (tenant DB secret - signs user JWTs)
#   - TENNANT_SUPABASE_JWT_SECRET (alternate spelling - typo tolerance)
#   - MASTER_SUPABASE_JWT_SECRET (legacy name)
#   - SUPABASE_JWT_SECRET (fallback)
TENANT_SUPABASE_JWT_SECRET = (
    os.getenv('TENANT_SUPABASE_JWT_SECRET', '') or
    os.getenv('TENNANT_SUPABASE_JWT_SECRET', '')  # Typo tolerance
)
MASTER_SUPABASE_JWT_SECRET = os.getenv('MASTER_SUPABASE_JWT_SECRET', '') or TENANT_SUPABASE_JWT_SECRET
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '') or MASTER_SUPABASE_JWT_SECRET

# TODO: AGENT_TOKEN_SECRET - Configure in Render when Local Agent is deployed
# ============================================================================
# The Local Agent is an on-premise daemon running on each yacht that:
#   - Syncs equipment telemetry, fault logs, sensor readings to cloud
#   - Uses separate auth (not user JWT) via X-Agent-Token header
#   - Requires AGENT_TOKEN_SECRET env var for JWT validation
#
# To enable:
#   1. Generate secret: openssl rand -base64 32
#   2. Add to Render env vars: AGENT_TOKEN_SECRET=<generated_secret>
#   3. Provision agent token via create_agent_token() for each yacht
#
# Not needed until Local Agent feature is built (Phase TBD)
# ============================================================================
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
# SYSTEM FLAGS CACHE (INCIDENT MODE / KILL SWITCH)
# ============================================================================

_system_flags_cache: Optional[Dict] = None
_system_flags_cache_time: float = 0

def get_system_flags() -> Dict:
    """
    Get current system flags from MASTER DB with caching.

    SECURITY: This is the kill switch. When incident_mode is True,
    MUTATE/SIGNED/ADMIN actions should be blocked globally.

    Returns:
        {
            'incident_mode': bool,
            'disable_streaming': bool,
            'disable_signed_urls': bool,
            'disable_writes': bool,
            'incident_reason': str or None,
            'incident_started_at': str or None,
        }
    """
    global _system_flags_cache, _system_flags_cache_time

    now = time.time()

    # Return cached if still valid
    if _system_flags_cache is not None and (now - _system_flags_cache_time) < SYSTEM_FLAGS_CACHE_TTL:
        return _system_flags_cache

    client = get_master_client()
    if not client:
        logger.error("[Auth] Cannot get system flags - no MASTER client")
        # DENY-BY-DEFAULT: If we can't check, assume incident mode OFF but log warning
        return {
            'incident_mode': False,
            'disable_streaming': False,
            'disable_signed_urls': False,
            'disable_writes': False,
            'incident_reason': None,
            'incident_started_at': None,
        }

    try:
        # The system_flags table has a single row with id=1
        result = client.table('system_flags').select('*').eq('id', 1).single().execute()

        if result.data:
            flags = {
                'incident_mode': result.data.get('incident_mode', False),
                'disable_streaming': result.data.get('disable_streaming', False),
                'disable_signed_urls': result.data.get('disable_signed_urls', False),
                'disable_writes': result.data.get('disable_writes', False),
                'incident_reason': result.data.get('incident_reason'),
                'incident_started_at': result.data.get('incident_started_at'),
            }
        else:
            # No row exists yet - default to not in incident mode
            flags = {
                'incident_mode': False,
                'disable_streaming': False,
                'disable_signed_urls': False,
                'disable_writes': False,
                'incident_reason': None,
                'incident_started_at': None,
            }

        # Update cache
        _system_flags_cache = flags
        _system_flags_cache_time = now

        if flags['incident_mode']:
            logger.warning(f"[Auth] INCIDENT MODE ACTIVE: {flags['incident_reason']}")

        return flags

    except Exception as e:
        logger.error(f"[Auth] Failed to get system flags: {e}")
        # DENY-BY-DEFAULT on error: return cached if available, else safe defaults
        if _system_flags_cache is not None:
            return _system_flags_cache
        return {
            'incident_mode': False,
            'disable_streaming': False,
            'disable_signed_urls': False,
            'disable_writes': False,
            'incident_reason': None,
            'incident_started_at': None,
        }


def clear_system_flags_cache():
    """Clear system flags cache (call after updating flags)."""
    global _system_flags_cache, _system_flags_cache_time
    _system_flags_cache = None
    _system_flags_cache_time = 0


def is_incident_mode_active() -> bool:
    """Check if global incident mode is active."""
    return get_system_flags().get('incident_mode', False)


def check_incident_mode_for_action(action_group: str, is_streaming: bool = False) -> Optional[str]:
    """
    Check if an action should be blocked due to incident mode.

    Args:
        action_group: The action group (READ, MUTATE, SIGNED, ADMIN)
        is_streaming: Whether this is a streaming request

    Returns:
        None if allowed, or an error message if blocked
    """
    flags = get_system_flags()

    if not flags['incident_mode']:
        return None  # Not in incident mode, allow all

    # Check if action group is blocked
    if action_group in INCIDENT_BLOCKED_GROUPS:
        reason = flags.get('incident_reason') or 'security incident'
        return f"System in incident mode: {reason}. {action_group} actions are temporarily disabled."

    # Check streaming specifically
    if is_streaming and flags.get('disable_streaming', False):
        reason = flags.get('incident_reason') or 'security incident'
        return f"System in incident mode: {reason}. Streaming is temporarily disabled."

    return None  # Allowed


# ============================================================================
# TENANT LOOKUP CACHE
# ============================================================================

# Cache tenant info by user_id with TTL (15 minutes)
# Reduces MASTER+TENANT DB queries from 200-600ms to <1ms
# TTL of 900s (15 min) balances freshness vs performance:
#   - Role changes propagate within 15 minutes
#   - Most requests hit cache (expect 95%+ hit rate)
#   - Cache survives across requests but not restarts
if HAS_CACHETOOLS:
    _tenant_cache = TTLCache(maxsize=1000, ttl=900)  # 1000 users, 15 min TTL
else:
    _tenant_cache: Dict[str, Dict] = {}  # Fallback to simple dict

_tenant_cache_stats = {"hits": 0, "misses": 0, "errors": 0}

def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    """
    Look up tenant info from MASTER DB for a user, then get yacht-specific role from TENANT DB.

    Uses TTLCache to reduce database queries:
    - Cache HIT: <1ms (95%+ of requests after warmup)
    - Cache MISS: 200-600ms (MASTER + TENANT DB queries)

    Returns:
        {
            'yacht_id': 'TEST_YACHT_001',
            'tenant_key_alias': 'yTEST_YACHT_001',
            'role': 'chief_engineer',  # From tenant DB auth_users_roles
            'status': 'active',
            'yacht_name': 'M/Y Test Vessel'
        }
    Or None if user has no tenant assignment.
    """
    # Check cache first (fast path - <1ms)
    if user_id in _tenant_cache:
        _tenant_cache_stats["hits"] += 1
        logger.debug(f"[Auth] Tenant cache HIT for user {user_id[:8]}... (hits: {_tenant_cache_stats['hits']})")
        return _tenant_cache[user_id]

    # Cache MISS - query databases (slow path - 200-600ms)
    _tenant_cache_stats["misses"] += 1
    logger.debug(f"[Auth] Tenant cache MISS for user {user_id[:8]}... (misses: {_tenant_cache_stats['misses']})")

    client = get_master_client()
    if not client:
        logger.error("[Auth] Cannot lookup tenant - no MASTER client")
        _tenant_cache_stats["errors"] += 1
        return None

    try:
        # Query user_accounts - PK column is 'id' in production schema
        result = client.table('user_accounts').select(
            'yacht_id, status'
        ).eq('id', user_id).single().execute()

        if not result.data:
            logger.warning(f"[Auth] No user_accounts row for user {user_id[:8]}...")
            return None

        user_account = result.data

        # Check account status
        if user_account.get('status') != 'active':
            logger.warning(f"[Auth] User {user_id[:8]}... status is {user_account.get('status')}")
            return None

        # Get yacht info from fleet_registry (including tenant_key_alias)
        fleet_result = client.table('fleet_registry').select(
            'yacht_name, active, tenant_key_alias'
        ).eq('yacht_id', user_account['yacht_id']).single().execute()

        if not fleet_result.data:
            logger.warning(f"[Auth] No fleet_registry for yacht {user_account['yacht_id']}")
            return None

        fleet = fleet_result.data

        if not fleet.get('active'):
            logger.warning(f"[Auth] Yacht {user_account['yacht_id']} is inactive")
            return None

        # Get tenant_key_alias from fleet_registry (already fetched above)
        yacht_id = user_account['yacht_id']
        tenant_key_alias = fleet.get('tenant_key_alias') or f"y{yacht_id}"

        # SECURITY: Query tenant DB for yacht-specific role from auth_users_roles
        # DENY-BY-DEFAULT: If tenant role lookup fails, return None (block all access)
        # The master DB user_accounts.role is not yacht-specific and MUST NOT be trusted
        tenant_role = None
        try:
            from pipeline_service import get_tenant_client
            tenant_client = get_tenant_client(tenant_key_alias)
            if not tenant_client:
                logger.error(f"[Auth] SECURITY: Failed to get tenant client for {tenant_key_alias}")
                return None

            role_result = tenant_client.table('auth_users_roles').select(
                'role, valid_from, valid_until'
            ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('is_active', True).execute()

            if role_result.data and len(role_result.data) > 0:
                # If multiple active roles exist, take the most recent one
                # Sort by valid_from descending to get latest assignment
                sorted_roles = sorted(
                    role_result.data,
                    key=lambda r: r.get('valid_from', ''),
                    reverse=True
                )
                tenant_role = sorted_roles[0]['role']
                logger.info(f"[Auth] Found yacht-specific role: {tenant_role} for user {user_id[:8]}... on yacht {yacht_id}")
            else:
                logger.error(f"[Auth] SECURITY: No active role in auth_users_roles for user {user_id[:8]}... on yacht {yacht_id}")
                return None

        except Exception as role_err:
            logger.error(f"[Auth] SECURITY: Failed to query tenant DB for role: {role_err}")
            return None

        tenant_info = {
            'yacht_id': yacht_id,
            'tenant_key_alias': tenant_key_alias,
            'role': tenant_role,
            'status': user_account['status'],
            'yacht_name': fleet.get('yacht_name'),
        }

        # Cache for future requests
        _tenant_cache[user_id] = tenant_info
        logger.info(f"[Auth] Tenant lookup success: user={user_id[:8]}... -> yacht={tenant_info['yacht_id']}, role={tenant_role}")

        return tenant_info

    except Exception as e:
        logger.error(f"[Auth] Tenant lookup failed for {user_id[:8]}...: {e}")
        return None

def clear_tenant_cache(user_id: str = None):
    """Clear tenant cache (on logout or role change)."""
    global _tenant_cache
    if user_id:
        _tenant_cache.pop(user_id, None)
        logger.info(f"[Auth] Cleared tenant cache for user {user_id[:8]}...")
    else:
        _tenant_cache.clear()
        logger.info("[Auth] Cleared entire tenant cache")


def get_tenant_cache_stats() -> dict:
    """
    Get tenant cache statistics for monitoring.

    Returns:
        dict: Cache statistics including hits, misses, hit rate, cache size
    """
    total = _tenant_cache_stats["hits"] + _tenant_cache_stats["misses"]
    hit_rate = (_tenant_cache_stats["hits"] / total * 100) if total > 0 else 0

    stats = {
        "size": len(_tenant_cache),
        "hits": _tenant_cache_stats["hits"],
        "misses": _tenant_cache_stats["misses"],
        "errors": _tenant_cache_stats["errors"],
        "total_requests": total,
        "hit_rate": f"{hit_rate:.1f}%"
    }

    if HAS_CACHETOOLS and hasattr(_tenant_cache, 'maxsize') and hasattr(_tenant_cache, 'ttl'):
        stats["max_size"] = _tenant_cache.maxsize
        stats["ttl_seconds"] = _tenant_cache.ttl

    return stats

# ============================================================================
# JWT VALIDATION
# ============================================================================

def decode_jwt(token: str) -> dict:
    """
    Decode and validate JWT token using Supabase JWT secret.

    IMPORTANT: User JWTs are signed by MASTER Supabase (qvzmkaamzaqxpzbewjxe).
    The frontend authenticates against MASTER, so use MASTER secret first.
    Falls back to TENANT secret if MASTER verification fails (handles both cases).

    Returns decoded payload with:
    - sub (user_id)
    - email
    - role (from JWT, not authoritative - use tenant lookup)
    - exp (expiration)
    """
    # Build list of secrets to try, in priority order
    # MASTER first (frontend authenticates against MASTER Supabase)
    secrets_to_try = []
    if MASTER_SUPABASE_JWT_SECRET:
        secrets_to_try.append(('MASTER', MASTER_SUPABASE_JWT_SECRET))
    if TENANT_SUPABASE_JWT_SECRET and TENANT_SUPABASE_JWT_SECRET != MASTER_SUPABASE_JWT_SECRET:
        secrets_to_try.append(('TENANT', TENANT_SUPABASE_JWT_SECRET))
    if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET not in [MASTER_SUPABASE_JWT_SECRET, TENANT_SUPABASE_JWT_SECRET]:
        secrets_to_try.append(('SUPABASE', SUPABASE_JWT_SECRET))

    if not secrets_to_try:
        logger.error('[Auth] No JWT secrets configured')
        raise HTTPException(status_code=500, detail='JWT secret not configured')

    last_error = None
    for secret_name, secret in secrets_to_try:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=['HS256'],
                audience='authenticated',
                options={'verify_exp': True}
            )
            logger.debug(f'[Auth] JWT verified with {secret_name} secret')
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token expired')
        except jwt.InvalidSignatureError as e:
            logger.debug(f'[Auth] JWT failed verification with {secret_name}: {e}')
            last_error = e
            continue  # Try next secret
        except jwt.InvalidTokenError as e:
            last_error = e
            continue  # Try next secret

    # All secrets failed
    logger.warning(f'[Auth] JWT verification failed with all secrets. Last error: {last_error}')
    raise HTTPException(status_code=401, detail=f'Invalid token: Signature verification failed')


def extract_yacht_id(token: str) -> str:
    """
    Extract yacht_id from JWT token.

    DEPRECATED: DO NOT USE FOR APP ROUTES.

    SECURITY WARNING: This function trusts JWT claims for yacht_id.
    For app routes, use get_authenticated_user() which performs server-side
    tenant lookup from MASTER DB (invariant #1: yacht_id from server, not client).

    Only use for:
    - Agent token validation (machine-to-machine)
    - Legacy endpoints being migrated

    Migration: Replace with get_authenticated_user() dependency.
    """
    import warnings
    warnings.warn(
        "extract_yacht_id() trusts JWT claims - use get_authenticated_user() for app routes",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning("[SECURITY] extract_yacht_id() called - this trusts JWT claims, not server context")

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

    DEPRECATED: DO NOT USE FOR APP ROUTES.

    SECURITY WARNING: This function trusts JWT claims for role.
    For app routes, use get_authenticated_user() which looks up the
    authoritative role from TENANT DB auth_users_roles table.

    JWT role can be stale or manipulated. TENANT DB role is authoritative.
    """
    import warnings
    warnings.warn(
        "extract_role() trusts JWT claims - use get_authenticated_user() for app routes",
        DeprecationWarning,
        stacklevel=2
    )
    logger.warning("[SECURITY] extract_role() called - role from JWT is NOT authoritative")

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

    DEPRECATED: DO NOT USE FOR APP ROUTES.

    SECURITY WARNING: This function trusts JWT claims for yacht_id.
    For app routes, use get_authenticated_user() which performs server-side
    tenant lookup from MASTER DB (invariant #1: yacht_id from server, not client).

    Migration:
        # Old (INSECURE):
        async def endpoint(yacht_id: str = Depends(inject_yacht_context)):

        # New (SECURE):
        async def endpoint(auth: dict = Depends(get_authenticated_user)):
            yacht_id = auth['yacht_id']  # Server-resolved
    """
    import warnings
    warnings.warn(
        "inject_yacht_context() trusts JWT claims - use get_authenticated_user() for app routes",
        DeprecationWarning,
        stacklevel=2
    )
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
# INCIDENT MODE ENFORCEMENT
# ============================================================================

def enforce_incident_mode(action_group: str, is_streaming: bool = False):
    """
    FastAPI dependency factory to enforce incident mode checks.

    Usage:
        @app.post('/update')
        async def update(
            auth: dict = Depends(get_authenticated_user),
            _: None = Depends(enforce_incident_mode("MUTATE"))
        ):
            ...
    """
    async def _check():
        error = check_incident_mode_for_action(action_group, is_streaming)
        if error:
            logger.warning(f"[Auth] INCIDENT MODE BLOCK: {action_group} action denied")
            raise HTTPException(status_code=503, detail=error)
    return _check


async def check_streaming_allowed():
    """
    FastAPI dependency to check if streaming is allowed.

    Use this for streaming endpoints.

    Raises:
        503 if streaming is disabled due to incident mode
    """
    flags = get_system_flags()
    if flags.get('incident_mode') and flags.get('disable_streaming'):
        reason = flags.get('incident_reason') or 'security incident'
        raise HTTPException(
            status_code=503,
            detail=f"Streaming temporarily disabled: {reason}"
        )


async def check_signed_urls_allowed():
    """
    FastAPI dependency to check if signed URL generation is allowed.

    Use this for storage/document endpoints.

    Raises:
        503 if signed URLs are disabled due to incident mode
    """
    flags = get_system_flags()
    if flags.get('incident_mode') and flags.get('disable_signed_urls'):
        reason = flags.get('incident_reason') or 'security incident'
        raise HTTPException(
            status_code=503,
            detail=f"Document access temporarily disabled: {reason}"
        )


async def check_writes_allowed():
    """
    FastAPI dependency to check if write operations are allowed.

    Use this for any mutation endpoints.

    Raises:
        503 if writes are disabled due to incident mode
    """
    flags = get_system_flags()
    if flags.get('incident_mode') and flags.get('disable_writes'):
        reason = flags.get('incident_reason') or 'security incident'
        raise HTTPException(
            status_code=503,
            detail=f"Write operations temporarily disabled: {reason}"
        )


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
    # JWT functions
    'decode_jwt',
    'extract_yacht_id',
    'extract_user_id',
    'extract_role',
    # Auth dependencies
    'validate_user_jwt',
    'get_authenticated_user',
    'inject_yacht_context',
    'validate_agent_token',
    # Tenant lookup
    'lookup_tenant_for_user',
    'clear_tenant_cache',
    'get_tenant_cache_stats',
    # Incident mode / kill switch
    'get_system_flags',
    'clear_system_flags_cache',
    'is_incident_mode_active',
    'check_incident_mode_for_action',
    'enforce_incident_mode',
    'check_streaming_allowed',
    'check_signed_urls_allowed',
    'check_writes_allowed',
    # Role-based access
    'require_role',
    'enforce_yacht_isolation',
    # Token utilities
    'create_agent_token',
]
