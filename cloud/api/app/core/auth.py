"""
JWT Authentication and Authorization for CelesteOS Cloud API
Handles token generation, validation, and yacht context injection
"""

import jwt
from datetime import datetime, timedelta
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from app.core.config import settings
from app.core.supabase import supabase_client
from app.core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    YachtSignatureError
)

logger = logging.getLogger(__name__)

# HTTP Bearer scheme
security = HTTPBearer()


class YachtContext:
    """Container for yacht-specific request context"""

    def __init__(
        self,
        yacht_id: str,
        yacht_signature: str,
        yacht_name: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None
    ):
        self.yacht_id = yacht_id
        self.yacht_signature = yacht_signature
        self.yacht_name = yacht_name
        self.user_id = user_id
        self.user_role = user_role


def create_access_token(user_id: str, yacht_id: str, role: str = "user") -> str:
    """
    Create JWT access token

    Args:
        user_id: User UUID
        yacht_id: Yacht UUID
        role: User role (user, admin, owner)

    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "user_id": user_id,
        "yacht_id": yacht_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


def create_refresh_token(user_id: str, yacht_id: str) -> str:
    """
    Create JWT refresh token

    Args:
        user_id: User UUID
        yacht_id: Yacht UUID

    Returns:
        JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "user_id": user_id,
        "yacht_id": yacht_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise TokenInvalidError()


async def get_yacht_signature(
    x_yacht_signature: Optional[str] = Header(None, alias="X-Yacht-Signature")
) -> str:
    """
    Extract and validate yacht signature from headers

    Args:
        x_yacht_signature: Yacht signature from X-Yacht-Signature header

    Returns:
        Validated yacht signature

    Raises:
        YachtSignatureError: If signature is missing or invalid
    """
    if not x_yacht_signature:
        raise YachtSignatureError()

    # Verify yacht exists in database
    yacht = supabase_client.get_yacht_by_signature(x_yacht_signature)

    if not yacht:
        raise YachtSignatureError()

    return x_yacht_signature


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    yacht_signature: str = Depends(get_yacht_signature)
) -> YachtContext:
    """
    Validate JWT token and return yacht context

    Args:
        credentials: HTTP Authorization header with Bearer token
        yacht_signature: Validated yacht signature

    Returns:
        YachtContext with user and yacht information

    Raises:
        AuthenticationError: If authentication fails
    """
    token = credentials.credentials

    # Decode token
    try:
        payload = decode_token(token)
    except (TokenExpiredError, TokenInvalidError) as e:
        raise e

    # Extract claims
    user_id = payload.get("user_id")
    yacht_id = payload.get("yacht_id")
    role = payload.get("role", "user")

    if not user_id or not yacht_id:
        raise TokenInvalidError()

    # Verify token in database (for revocation support)
    token_record = supabase_client.verify_token(token)

    if not token_record:
        raise AuthenticationError("Token has been revoked or is invalid")

    # Get yacht information
    yacht = supabase_client.get_yacht_by_signature(yacht_signature)

    if not yacht or yacht['id'] != yacht_id:
        raise YachtSignatureError()

    # Create yacht context
    context = YachtContext(
        yacht_id=yacht_id,
        yacht_signature=yacht_signature,
        yacht_name=yacht.get('name', 'Unknown'),
        user_id=user_id,
        user_role=role
    )

    logger.info(f"Authenticated user {user_id} for yacht {yacht_id}")

    return context


async def get_optional_user(
    request: Request,
    x_yacht_signature: Optional[str] = Header(None, alias="X-Yacht-Signature"),
    authorization: Optional[str] = Header(None)
) -> Optional[YachtContext]:
    """
    Optional authentication - returns yacht context if credentials provided

    Args:
        request: FastAPI request
        x_yacht_signature: Optional yacht signature
        authorization: Optional authorization header

    Returns:
        YachtContext if authenticated, None otherwise
    """
    if not x_yacht_signature or not authorization:
        return None

    try:
        # Extract token from Bearer header
        if not authorization.startswith("Bearer "):
            return None

        token = authorization.replace("Bearer ", "")

        # Decode and validate
        payload = decode_token(token)
        user_id = payload.get("user_id")
        yacht_id = payload.get("yacht_id")
        role = payload.get("role", "user")

        # Verify yacht
        yacht = supabase_client.get_yacht_by_signature(x_yacht_signature)

        if not yacht or yacht['id'] != yacht_id:
            return None

        # Create context
        return YachtContext(
            yacht_id=yacht_id,
            yacht_signature=x_yacht_signature,
            yacht_name=yacht.get('name', 'Unknown'),
            user_id=user_id,
            user_role=role
        )

    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
        return None


def require_role(required_role: str):
    """
    Decorator to require specific user role

    Args:
        required_role: Required role (user, admin, owner)

    Returns:
        Dependency function
    """

    async def role_checker(context: YachtContext = Depends(get_current_user)):
        # Simple role hierarchy: owner > admin > user
        role_hierarchy = {"owner": 3, "admin": 2, "user": 1}

        user_level = role_hierarchy.get(context.user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            from app.core.exceptions import PermissionDeniedError
            raise PermissionDeniedError(
                f"Required role: {required_role}, your role: {context.user_role}"
            )

        return context

    return role_checker
