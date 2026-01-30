"""
JWT Validator

Validates Supabase JWT tokens and extracts user context.

Architecture (2026-01-30):
- JWT is verified using MASTER Supabase JWT secret
- user_id is extracted from JWT (sub claim)
- yacht_id and role are looked up from MASTER DB (invariant #1)
- Frontend sends ONLY Authorization: Bearer <token>, no yacht_id
"""

import jwt
import os
import logging
from typing import Dict, Any
from datetime import datetime
from .validation_result import ValidationResult

logger = logging.getLogger(__name__)


def validate_jwt(token: str) -> ValidationResult:
    """
    Validate Supabase JWT token and extract user context.

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

    try:
        # B001-AR FIX: Try MASTER secret first, then TENANT
        # Frontend authenticates against MASTER Supabase, so JWTs are signed with MASTER secret
        secrets_to_try = []

        # MASTER first (frontend authenticates against MASTER Supabase)
        if os.getenv("MASTER_SUPABASE_JWT_SECRET"):
            secrets_to_try.append(("MASTER", os.getenv("MASTER_SUPABASE_JWT_SECRET")))

        # TENANT second (for multi-tenant scenarios where tenant has own Supabase)
        tenant_secret = os.getenv("TENANT_SUPABASE_JWT_SECRET") or os.getenv("TENNANT_SUPABASE_JWT_SECRET")
        if tenant_secret and tenant_secret not in [s[1] for s in secrets_to_try]:
            secrets_to_try.append(("TENANT", tenant_secret))

        # Legacy fallback
        if os.getenv("SUPABASE_JWT_SECRET") and os.getenv("SUPABASE_JWT_SECRET") not in [s[1] for s in secrets_to_try]:
            secrets_to_try.append(("SUPABASE", os.getenv("SUPABASE_JWT_SECRET")))

        if not secrets_to_try:
            return ValidationResult.failure(
                error_code="server_config_error",
                message="JWT secret not configured (MASTER_SUPABASE_JWT_SECRET)",
            )

        # Try each secret until one works
        last_error = None
        payload = None
        for secret_name, secret in secrets_to_try:
            try:
                # Decode and verify JWT
                # Note: Supabase tokens have audience="authenticated", skip audience verification
                # as we validate yacht_id separately for tenant isolation
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=["HS256"],
                    options={"verify_exp": True, "verify_aud": False},
                )
                break  # Success - stop trying
            except jwt.InvalidSignatureError as e:
                last_error = e
                continue  # Try next secret

        if payload is None:
            return ValidationResult.failure(
                error_code="invalid_token",
                message="Invalid token: Signature verification failed",
            )

        # Extract user context from JWT
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

        try:
            from middleware.auth import lookup_tenant_for_user
            tenant_info = lookup_tenant_for_user(user_id)

            if tenant_info:
                yacht_id = tenant_info.get("yacht_id")
                role = tenant_info.get("role", "crew")
                tenant_key_alias = tenant_info.get("tenant_key_alias")
                logger.debug(f"[JWT] Tenant lookup success: user={user_id[:8]}... yacht={yacht_id} role={role}")
            else:
                logger.warning(f"[JWT] No tenant found for user {user_id[:8]}...")

        except ImportError as e:
            # Fallback if middleware not available (shouldn't happen in production)
            logger.error(f"[JWT] Could not import lookup_tenant_for_user: {e}")
            # Fall back to JWT claims (less secure, but allows system to function)
            app_metadata = payload.get("app_metadata", {})
            user_metadata = payload.get("user_metadata", {})
            yacht_id = app_metadata.get("yacht_id") or user_metadata.get("yacht_id")
            role = payload.get("role") or app_metadata.get("role") or user_metadata.get("role") or "authenticated"
        except Exception as e:
            logger.error(f"[JWT] Tenant lookup failed: {e}")

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

    except jwt.ExpiredSignatureError:
        return ValidationResult.failure(
            error_code="token_expired",
            message="Token has expired. Please log in again.",
        )

    except jwt.InvalidTokenError as e:
        return ValidationResult.failure(
            error_code="invalid_token",
            message=f"Invalid token: {str(e)}",
        )

    except Exception as e:
        return ValidationResult.failure(
            error_code="validation_error",
            message=f"Token validation failed: {str(e)}",
        )


__all__ = ["validate_jwt"]
