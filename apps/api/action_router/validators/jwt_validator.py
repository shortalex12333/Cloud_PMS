"""
JWT Validator

Validates Supabase JWT tokens and extracts user context.
"""

import jwt
import os
from typing import Dict, Any
from datetime import datetime
from .validation_result import ValidationResult


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
        # Get JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            return ValidationResult.failure(
                error_code="server_config_error",
                message="JWT secret not configured",
            )

        # Decode and verify JWT
        # Note: Supabase tokens have audience="authenticated", skip audience verification
        # as we validate yacht_id separately for tenant isolation
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": False},
        )

        # Extract user context from JWT
        user_id = payload.get("sub")
        if not user_id:
            return ValidationResult.failure(
                error_code="invalid_token",
                message="Token missing user ID (sub claim)",
            )

        # Extract custom claims
        app_metadata = payload.get("app_metadata", {})
        user_metadata = payload.get("user_metadata", {})

        # yacht_id can be in either app_metadata or user_metadata
        yacht_id = app_metadata.get("yacht_id") or user_metadata.get("yacht_id")

        # role can be at top level (Supabase default) or in metadata
        role = payload.get("role") or app_metadata.get("role") or user_metadata.get("role")

        if not yacht_id:
            return ValidationResult.failure(
                error_code="invalid_token",
                message="Token missing yacht_id claim",
            )

        if not role:
            return ValidationResult.failure(
                error_code="invalid_token",
                message="Token missing role claim",
            )

        # Return user context
        return ValidationResult.success(
            context={
                "user_id": user_id,
                "yacht_id": yacht_id,
                "role": role,
                "email": payload.get("email"),
                "exp": payload.get("exp"),
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
