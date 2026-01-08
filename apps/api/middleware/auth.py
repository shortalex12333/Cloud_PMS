"""
CelesteOS Backend - Authentication Middleware

Handles:
- JWT validation
- Yacht context injection
- Agent token validation
- Role-based access control
"""

from typing import Optional, Callable
from functools import wraps
import jwt
from fastapi import Request, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')
AGENT_TOKEN_SECRET = os.getenv('AGENT_TOKEN_SECRET', '')

if not SUPABASE_JWT_SECRET:
    raise ValueError('SUPABASE_JWT_SECRET environment variable not set')

security = HTTPBearer()

# ============================================================================
# JWT VALIDATION
# ============================================================================

def decode_jwt(token: str) -> dict:
    """
    Decode and validate JWT token from Supabase.

    Returns decoded payload with:
    - user_id
    - yacht_id
    - role
    - exp (expiration)
    """
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=['HS256'],
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
    'inject_yacht_context',
    'validate_agent_token',
    'require_role',
    'enforce_yacht_isolation',
    'create_agent_token',
]
