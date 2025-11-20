"""
Security validators for authentication and authorization
"""
from jose import JWTError, jwt
from fastapi import HTTPException, status, Header
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


async def validate_jwt(authorization: str = Header(...)) -> dict:
    """
    Validate JWT token from Authorization header

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        Decoded JWT payload

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload

    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def validate_yacht_signature(
    x_yacht_signature: Optional[str] = Header(None)
) -> str:
    """
    Validate yacht signature from header

    Args:
        x_yacht_signature: Yacht signature header value

    Returns:
        Validated yacht signature

    Raises:
        HTTPException: If signature is missing or invalid
    """
    if not x_yacht_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing yacht signature header"
        )

    # TODO: Add actual signature validation against database
    # For now, we just check it exists and is non-empty
    if len(x_yacht_signature) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid yacht signature format"
        )

    return x_yacht_signature


async def get_yacht_id_from_signature(signature: str) -> str:
    """
    Retrieve yacht_id from yacht signature

    Args:
        signature: Yacht signature

    Returns:
        Yacht ID (UUID)

    Raises:
        HTTPException: If signature is invalid
    """
    from utils.supabase_client import get_supabase_client

    try:
        client = get_supabase_client(use_service_role=True)
        result = client.table("yachts") \
            .select("id") \
            .eq("signature", signature) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yacht not found for signature"
            )

        return result.data["id"]

    except Exception as e:
        logger.error(f"Failed to get yacht ID from signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate yacht signature"
        )
