"""
Authentication endpoints for CelesteOS Cloud API
/v1/auth/* routes
"""

from fastapi import APIRouter, Depends, status
from datetime import datetime, timedelta
import bcrypt
import logging

from app.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RevokeTokenRequest,
    UserInfo,
    YachtInfo
)
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    YachtContext
)
from app.core.supabase import supabase_client
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    TokenInvalidError,
    YachtSignatureError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    User login endpoint

    Validates credentials and returns access/refresh tokens
    """
    logger.info(f"Login attempt for email: {request.email}")

    # Verify yacht signature
    yacht = supabase_client.get_yacht_by_signature(request.yacht_signature)

    if not yacht:
        raise YachtSignatureError()

    # Get user by email
    response = supabase_client.admin.table('users') \
        .select('*') \
        .eq('email', request.email) \
        .eq('yacht_id', yacht['id']) \
        .single() \
        .execute()

    if not response.data:
        raise AuthenticationError("Invalid email or password")

    user = response.data

    # Verify password
    password_hash = user.get('password_hash')

    if not password_hash:
        raise AuthenticationError("User account not properly configured")

    if not bcrypt.checkpw(request.password.encode('utf-8'), password_hash.encode('utf-8')):
        raise AuthenticationError("Invalid email or password")

    # Generate tokens
    access_token = create_access_token(
        user_id=user['id'],
        yacht_id=yacht['id'],
        role=user.get('role', 'user')
    )

    refresh_token = create_refresh_token(
        user_id=user['id'],
        yacht_id=yacht['id']
    )

    # Store tokens in database
    expires_at = datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

    supabase_client.create_user_token(
        user_id=user['id'],
        yacht_id=yacht['id'],
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat()
    )

    logger.info(f"Login successful for user {user['id']}")

    # Return response
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user=UserInfo(
            id=user['id'],
            email=user['email'],
            name=user.get('name', 'User'),
            role=user.get('role', 'user'),
            yacht_id=yacht['id']
        ),
        yacht=YachtInfo(
            id=yacht['id'],
            name=yacht['name'],
            signature=yacht['signature'],
            status=yacht['status']
        )
    )


@router.post("/refresh", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    Returns new access and refresh tokens
    """
    logger.info("Token refresh attempt")

    # Decode refresh token
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise TokenInvalidError()

    # Verify token type
    if payload.get('type') != 'refresh':
        raise TokenInvalidError()

    # Extract claims
    user_id = payload.get('user_id')
    yacht_id = payload.get('yacht_id')

    if not user_id or not yacht_id:
        raise TokenInvalidError()

    # Verify yacht signature
    yacht = supabase_client.get_yacht_by_signature(request.yacht_signature)

    if not yacht or yacht['id'] != yacht_id:
        raise YachtSignatureError()

    # Verify refresh token in database
    response = supabase_client.admin.table('user_tokens') \
        .select('*') \
        .eq('refresh_token', request.refresh_token) \
        .eq('user_id', user_id) \
        .single() \
        .execute()

    if not response.data:
        raise AuthenticationError("Invalid refresh token")

    # Get user info for role
    user = supabase_client.get_user(user_id)

    if not user:
        raise AuthenticationError("User not found")

    # Generate new tokens
    new_access_token = create_access_token(
        user_id=user_id,
        yacht_id=yacht_id,
        role=user.get('role', 'user')
    )

    new_refresh_token = create_refresh_token(
        user_id=user_id,
        yacht_id=yacht_id
    )

    # Update token in database
    expires_at = datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)

    supabase_client.admin.table('user_tokens') \
        .update({
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'expires_at': expires_at.isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }) \
        .eq('id', response.data['id']) \
        .execute()

    logger.info(f"Token refreshed for user {user_id}")

    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600
    )


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    request: RevokeTokenRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Revoke current or specified access token

    Removes token from database, preventing further use
    """
    # If token not specified, revoke current token (from context)
    token_to_revoke = request.access_token

    if not token_to_revoke:
        # Get current token from request header
        # This would need to be passed through context or extracted from request
        logger.info(f"Revoking current token for user {context.user_id}")

    else:
        logger.info(f"Revoking specified token for user {context.user_id}")

    # Delete token from database
    supabase_client.admin.table('user_tokens') \
        .delete() \
        .eq('user_id', context.user_id) \
        .execute()

    logger.info(f"Token revoked for user {context.user_id}")

    return None


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(context: YachtContext = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    user = supabase_client.get_user(context.user_id)

    if not user:
        raise AuthenticationError("User not found")

    return UserInfo(
        id=user['id'],
        email=user['email'],
        name=user.get('name', 'User'),
        role=user.get('role', 'user'),
        yacht_id=context.yacht_id
    )
