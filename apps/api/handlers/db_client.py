"""
Database Client Utilities - Per-Request RLS Enforcement
==========================================================

Provides user-scoped database clients for RLS enforcement.

CRITICAL: Never use service key for tenant reads/writes in request paths.
Service key bypasses RLS and should only be used for admin/setup tasks.

Usage:
    from handlers.db_client import get_user_db

    db = get_user_db(user_jwt, yacht_id)
    result = db.table("pms_receiving").select("*").eq("yacht_id", yacht_id).execute()
"""

import os
import logging
import threading
from typing import Optional, Dict
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Connection Pooling
# ==================
# Reuse database connections across requests to avoid 280-980ms connection overhead
_connection_pools: Dict[str, Client] = {}
_pool_lock = threading.Lock()
_pool_stats = {"service_hits": 0, "service_misses": 0}


def get_user_db(user_jwt: str, yacht_id: Optional[str] = None) -> Client:
    """
    Create PostgREST client with user JWT for RLS enforcement.

    This client will execute all queries in the context of the authenticated user,
    with RLS policies active. The yacht_id parameter helps with routing to the
    correct tenant database.

    Args:
        user_jwt: User's JWT token (required for RLS)
        yacht_id: Optional yacht ID for tenant routing (uses DEFAULT_YACHT_CODE if not provided)

    Returns:
        PostgrestClient configured with user's JWT for RLS enforcement

    Raises:
        ValueError: If user_jwt is missing or tenant URL not configured

    Example:
        db = get_user_db(user_jwt="eyJ...", yacht_id="85fe1119-...")
        receivings = db.from_("pms_receiving").select("*").eq("yacht_id", yacht_id).execute()
    """
    if not user_jwt:
        raise ValueError("user_jwt is required for RLS enforcement")

    # Get tenant database URL (default to TEST_YACHT_001)
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    tenant_url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    # Use service key for API key parameter (NOT for auth - just for client creation)
    service_key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not tenant_url or not service_key:
        raise ValueError(f"{default_yacht}_SUPABASE_URL and SERVICE_KEY must be set")

    try:
        # Create supabase client with service key
        client = create_client(tenant_url, service_key)

        # Set user JWT as authorization header for RLS enforcement
        # This overrides the service key for actual requests
        # Use direct header setting instead of auth() method
        if hasattr(client, 'postgrest') and hasattr(client.postgrest, 'session'):
            # Set Authorization header directly
            client.postgrest.session.headers.update({"Authorization": f"Bearer {user_jwt}"})
        else:
            # Fallback: try auth() method if session not available
            try:
                client.postgrest.auth(user_jwt)
            except AttributeError:
                # If neither works, set headers on the client itself
                client.headers.update({"Authorization": f"Bearer {user_jwt}"})

        logger.debug(f"Created RLS-enforced Supabase client for tenant: {default_yacht}")
        return client

    except Exception as e:
        logger.error(f"Failed to create user-scoped Supabase client: {e}", exc_info=True)
        # Don't raise ValueError - return error dict instead to avoid router's 400 handler
        raise RuntimeError(f"Failed to create database client: {str(e)}")


def get_service_db(yacht_id: Optional[str] = None) -> Client:
    """
    Create PostgREST client with service key (bypasses RLS).

    ⚠️  WARNING: Only use for admin/setup tasks, NEVER for tenant request paths!

    Service key bypasses RLS policies. Using it for tenant data access is a
    security violation and breaks yacht isolation.

    CONNECTION POOLING: This function reuses connections across requests to avoid
    280-980ms connection overhead per request.

    Args:
        yacht_id: Optional yacht ID for tenant routing

    Returns:
        PostgrestClient configured with service key (RLS bypassed)

    Example:
        # ONLY for admin scripts, migrations, or system operations
        db = get_service_db()
        result = db.from_("pms_audit_log").select("*").execute()
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    tenant_url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    service_key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not tenant_url or not service_key:
        raise ValueError(f"{default_yacht}_SUPABASE_URL and SERVICE_KEY must be set")

    # Connection pooling: Check if we already have a connection for this tenant
    pool_key = f"{default_yacht}_service"

    # Fast path: Check if pool exists (no lock needed for read)
    if pool_key in _connection_pools:
        _pool_stats["service_hits"] += 1
        logger.debug(f"[Connection Pool] HIT for {pool_key} (hits: {_pool_stats['service_hits']})")
        return _connection_pools[pool_key]

    # Slow path: Create new connection (with lock to prevent race conditions)
    with _pool_lock:
        # Double-check after acquiring lock (another thread might have created it)
        if pool_key in _connection_pools:
            _pool_stats["service_hits"] += 1
            return _connection_pools[pool_key]

        logger.warning("Creating service-key Supabase client - RLS BYPASSED. Only use for admin tasks!")
        _pool_stats["service_misses"] += 1

        try:
            client = create_client(tenant_url, service_key)
            _connection_pools[pool_key] = client
            logger.info(f"[Connection Pool] MISS - Created new pool for {pool_key} (total pools: {len(_connection_pools)})")
            return client
        except Exception as e:
            logger.error(f"Failed to create service Supabase client: {e}")
            raise ValueError(f"Failed to create service database client: {str(e)}")


def get_pool_stats() -> dict:
    """
    Get connection pool statistics for monitoring.

    Returns:
        dict: Pool statistics including hits, misses, hit rate, active pools
    """
    total = _pool_stats["service_hits"] + _pool_stats["service_misses"]
    hit_rate = (_pool_stats["service_hits"] / total * 100) if total > 0 else 0

    return {
        "connection_pools": {
            "active_pools": len(_connection_pools),
            "pool_keys": list(_connection_pools.keys())
        },
        "service_connections": {
            "hits": _pool_stats["service_hits"],
            "misses": _pool_stats["service_misses"],
            "total_requests": total,
            "hit_rate": f"{hit_rate:.1f}%"
        }
    }


def map_postgrest_error(error: Exception, default_code: str = "DATABASE_ERROR") -> dict:
    """
    Map PostgREST exceptions to standardized error responses.

    Args:
        error: Exception from PostgREST query
        default_code: Fallback error code if specific mapping not found

    Returns:
        dict: Standardized error response {status, error_code, message, hint}
    """
    error_str = str(error).lower()

    # PostgREST 401/403 -> RLS denial
    # Also catch PostgreSQL error code 42501 (insufficient_privilege) and RLS policy violations
    if ("401" in error_str or "403" in error_str or "permission denied" in error_str or
        "42501" in error_str or "row-level security" in error_str or "policy" in error_str):
        return {
            "status": "error",
            "error_code": "RLS_DENIED",
            "message": "Access denied by row-level security policy",
            "hint": "Verify your role has permission for this yacht"
        }

    # PostgREST 404 -> Not found
    if "404" in error_str or "not found" in error_str:
        return {
            "status": "error",
            "error_code": "NOT_FOUND",
            "message": "Resource not found",
            "hint": "Check that the ID exists and belongs to your yacht"
        }

    # PostgREST 409 -> Conflict
    if "409" in error_str or "duplicate" in error_str or "unique constraint" in error_str:
        return {
            "status": "error",
            "error_code": "CONFLICT",
            "message": "Resource conflict or duplicate",
            "hint": "A resource with these identifiers already exists"
        }

    # PostgREST 400 -> Bad request
    if "400" in error_str or "invalid" in error_str:
        return {
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": "Invalid request to database",
            "hint": "Check your request parameters and format"
        }

    # Default: Internal error (log full trace server-side, minimal client message)
    logger.error(f"Unmapped PostgREST error: {error}", exc_info=True)
    return {
        "status": "error",
        "error_code": default_code,
        "message": "An unexpected database error occurred",
        "hint": "Contact support if this persists"
    }
