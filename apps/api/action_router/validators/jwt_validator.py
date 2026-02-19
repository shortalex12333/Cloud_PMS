"""
JWT Validator

Validates Supabase JWT tokens and extracts user context.

Architecture (2026-01-30):
- JWT is verified using MASTER Supabase JWT secret via middleware/auth.py::decode_jwt()
- user_id is extracted from JWT (sub claim)
- yacht_id and role are looked up from MASTER DB (invariant #1)
- Frontend sends ONLY Authorization: Bearer <token>, no yacht_id

Consolidation (2026-02-19):
- Uses middleware/auth.py::decode_jwt() as single source of truth for JWT decoding
- Uses middleware/auth.py::lookup_tenant_for_user() for tenant context
- Returns ValidationResult wrapper for action_router compatibility
"""

import logging
from fastapi import HTTPException
from .validation_result import ValidationResult

logger = logging.getLogger(__name__)


def validate_jwt(token: str) -> ValidationResult:
    """
    Validate Supabase JWT token and extract user context.

    Uses middleware/auth.py::decode_jwt() as the single source of truth
    for JWT decoding and validation.

    Args:
        token: JWT token from Authorization header

    Returns:
        ValidationResult with user context (user_id, yacht_id, role) or error
    """
    if not token:
        return ValidationResult.failure(
            error_code="missing_token",
            message="Authorization token is required",
        )

    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    # HARDENING: Reject empty/whitespace tokens
    if not token or not token.strip():
        return ValidationResult.failure(
            error_code="missing_token",
            message="JWT token required",
        )

    # HARDENING: Reject suspiciously short tokens (JWT typically 100+ chars)
    if len(token) < 20:
        return ValidationResult.failure(
            error_code="invalid_token",
            message="Invalid JWT token format",
        )

    try:
        # Use middleware/auth.py::decode_jwt() as single source of truth
        from middleware.auth import decode_jwt, lookup_tenant_for_user

        # decode_jwt raises HTTPException on failure
        payload = decode_jwt(token)

        # Extract user_id from JWT
        user_id = payload.get("sub")
        if not user_id:
            return ValidationResult.failure(
                error_code="invalid_token",
                message="Token missing user ID (sub claim)",
            )

        # SECURITY: yacht_id and role MUST come from MASTER DB lookup, not JWT claims
        # This is invariant #1: server-resolved context only
        #
        # The auth middleware lookup_tenant_for_user() does:
        # 1. Query MASTER DB user_accounts for yacht_id
        # 2. Query fleet_registry for tenant_key_alias
        # 3. Query TENANT DB auth_users_roles for authoritative role
        #
        # This ensures yacht_id cannot be spoofed via JWT claims
        yacht_id = None
        role = "authenticated"
        tenant_key_alias = None

        tenant_info = lookup_tenant_for_user(user_id)

        if tenant_info:
            yacht_id = tenant_info.get("yacht_id")
            role = tenant_info.get("role", "crew")
            tenant_key_alias = tenant_info.get("tenant_key_alias")
            logger.debug(f"[JWT] Tenant lookup success: user={user_id[:8]}... yacht={yacht_id} role={role}")
        else:
            logger.warning(f"[JWT] No tenant found for user {user_id[:8]}...")

        # Return user context with server-resolved yacht_id and role
        return ValidationResult.success(
            context={
                "user_id": user_id,
                "yacht_id": yacht_id,
                "role": role,
                "email": payload.get("email"),
                "exp": payload.get("exp"),
                "tenant_key_alias": tenant_key_alias,
            }
        )

    except HTTPException as e:
        # Map HTTPException from decode_jwt to ValidationResult
        error_code = "token_expired" if e.status_code == 401 and "expired" in str(e.detail).lower() else "invalid_token"
        return ValidationResult.failure(
            error_code=error_code,
            message=str(e.detail),
        )

    except ImportError as e:
        logger.error(f"[JWT] Could not import from middleware.auth: {e}")
        return ValidationResult.failure(
            error_code="server_config_error",
            message="Authentication middleware not available",
        )

    except Exception as e:
        logger.error(f"[JWT] Validation failed: {e}")
        return ValidationResult.failure(
            error_code="validation_error",
            message=f"Token validation failed: {str(e)}",
        )


__all__ = ["validate_jwt"]
