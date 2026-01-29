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
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


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
        client.postgrest.auth(user_jwt)

        logger.debug(f"Created RLS-enforced Supabase client for tenant: {default_yacht}")
        return client

    except Exception as e:
        logger.error(f"Failed to create user-scoped Supabase client: {e}")
        raise ValueError(f"Failed to create database client: {str(e)}")


def get_service_db(yacht_id: Optional[str] = None) -> Client:
    """
    Create PostgREST client with service key (bypasses RLS).

    ⚠️  WARNING: Only use for admin/setup tasks, NEVER for tenant request paths!

    Service key bypasses RLS policies. Using it for tenant data access is a
    security violation and breaks yacht isolation.

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

    logger.warning("Creating service-key Supabase client - RLS BYPASSED. Only use for admin tasks!")

    try:
        client = create_client(tenant_url, service_key)
        return client
    except Exception as e:
        logger.error(f"Failed to create service Supabase client: {e}")
        raise ValueError(f"Failed to create service database client: {str(e)}")


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
    if "401" in error_str or "403" in error_str or "permission denied" in error_str:
        return {
            "status": "error",
            "error_code": "RLS_DENIED",
            "message": "Access denied by row-level security",
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
