"""
CelesteOS Backend - OAuth Authentication Routes

Handles OAuth token exchange and storage for Microsoft Graph.
This keeps all secrets (Azure, Supabase service keys) in Render only.

Endpoints:
- POST /auth/outlook/exchange  - Exchange code for tokens and store
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import os
import httpx
import hashlib
import base64
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# CONFIGURATION
# ============================================================================

# Azure App Configuration (from env vars)
AZURE_READ_APP_ID = os.getenv('AZURE_READ_APP_ID', '')
AZURE_READ_CLIENT_SECRET = os.getenv('AZURE_READ_CLIENT_SECRET', '')
AZURE_WRITE_APP_ID = os.getenv('AZURE_WRITE_APP_ID', '')
AZURE_WRITE_CLIENT_SECRET = os.getenv('AZURE_WRITE_CLIENT_SECRET', '')

AZURE_TENANT = 'common'
TOKEN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT}/oauth2/v2.0/token"
GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

# Redirect URI base (production)
REDIRECT_BASE = os.getenv('OAUTH_REDIRECT_BASE', 'https://app.celeste7.ai')


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TokenExchangeRequest(BaseModel):
    """Request to exchange OAuth code for tokens."""
    code: str = Field(..., description="Authorization code from Microsoft")
    state: str = Field(..., description="State parameter containing user_id and purpose")
    redirect_uri: str = Field(..., description="Redirect URI used in auth request")


class TokenExchangeResponse(BaseModel):
    """Response from token exchange."""
    success: bool
    error: Optional[str] = None
    error_code: Optional[str] = None
    warning: Optional[str] = None
    email: Optional[str] = None


class OutlookStatusResponse(BaseModel):
    """Response for Outlook connection status."""
    connected: bool
    email: Optional[str] = None
    token_purpose: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_state(state: str) -> Optional[dict]:
    """Parse OAuth state parameter.

    Supports two formats:
    1. Colon-separated: userId:purpose:random (from Vercel oauth-utils.ts)
    2. Base64 JSON: {"user_id": "...", "purpose": "..."} (legacy)
    """
    try:
        # Try colon-separated format first (Vercel frontend)
        parts = state.split(':')
        if len(parts) >= 2:
            user_id = parts[0]
            purpose = parts[1]
            if user_id and purpose in ('read', 'write'):
                logger.info(f"[Auth] Parsed state (colon format): user_id={user_id[:8]}..., purpose={purpose}")
                return {'user_id': user_id, 'purpose': purpose}

        # Fallback to base64 JSON format (legacy)
        decoded = base64.urlsafe_b64decode(state + '==').decode('utf-8')
        data = json.loads(decoded)
        logger.info(f"[Auth] Parsed state (base64 format): user_id={data.get('user_id', '')[:8]}...")
        return data
    except Exception as e:
        logger.error(f"[Auth] Failed to parse state: {e}, state={state[:20]}...")
        return None


def hash_email(email: str) -> str:
    """Hash email for storage (privacy)."""
    return hashlib.sha256(email.lower().encode()).hexdigest()


def get_master_supabase():
    """Get Supabase client for MASTER database (authentication only)."""
    from supabase import create_client

    url = os.getenv('MASTER_SUPABASE_URL', '')
    key = os.getenv('MASTER_SUPABASE_SERVICE_KEY', '')

    if not url or not key:
        logger.error(f"[Auth] No MASTER Supabase credentials")
        return None

    return create_client(url, key)


def get_yacht_supabase(yacht_id: str):
    """Get Supabase client for a specific yacht."""
    from supabase import create_client

    # For now, use the test yacht credentials
    # In production, this would lookup the yacht's Supabase credentials
    yacht_code = os.getenv('DEFAULT_YACHT_CODE', 'yTEST_YACHT_001')

    url = os.getenv(f'{yacht_code}_SUPABASE_URL', '')
    key = os.getenv(f'{yacht_code}_SUPABASE_SERVICE_KEY', '')

    if not url or not key:
        logger.error(f"[Auth] No Supabase credentials for yacht: {yacht_code}")
        return None

    return create_client(url, key)


async def exchange_code_for_tokens(
    code: str,
    redirect_uri: str,
    purpose: str  # 'read' or 'write'
) -> dict:
    """Exchange authorization code for access/refresh tokens."""

    # Read env vars at request time (not module load time) to pick up
    # env vars added after process start
    if purpose == 'read':
        client_id = os.getenv('AZURE_READ_APP_ID', '')
        client_secret = os.getenv('AZURE_READ_CLIENT_SECRET', '')
    else:
        client_id = os.getenv('AZURE_WRITE_APP_ID', '')
        client_secret = os.getenv('AZURE_WRITE_CLIENT_SECRET', '')

    if not client_id or not client_secret:
        logger.error(f"[Auth] Missing Azure credentials for {purpose} app. "
                     f"AZURE_{purpose.upper()}_APP_ID set: {bool(client_id)}, "
                     f"AZURE_{purpose.upper()}_CLIENT_SECRET set: {bool(client_secret)}")
        return {'success': False, 'error': f'Missing Azure credentials for {purpose} app'}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )

        if response.status_code != 200:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            logger.error(f"[Auth] Token exchange failed: {response.status_code} - {error_data}")
            return {
                'success': False,
                'error': error_data.get('error_description', 'Token exchange failed'),
                'error_code': error_data.get('error', 'token_exchange_failed'),
            }

        return {'success': True, 'data': response.json()}


async def fetch_graph_profile(access_token: str) -> Optional[dict]:
    """Fetch user profile from Microsoft Graph."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GRAPH_ME_URL,
            headers={'Authorization': f'Bearer {access_token}'},
        )

        if response.status_code != 200:
            logger.warning(f"[Auth] Failed to fetch profile: {response.status_code}")
            return None

        data = response.json()
        return {
            'email': data.get('mail') or data.get('userPrincipalName', ''),
            'displayName': data.get('displayName', ''),
        }


def check_scopes(scopes: List[str], purpose: str) -> dict:
    """Check for forbidden scopes based on purpose."""
    forbidden_for_read = ['Mail.Send', 'Mail.ReadWrite']
    forbidden_for_write = ['Mail.Read', 'Mail.ReadWrite']

    forbidden = forbidden_for_read if purpose == 'read' else forbidden_for_write
    found_forbidden = [s for s in scopes if s in forbidden]

    return {
        'valid': len(found_forbidden) == 0,
        'forbidden': found_forbidden,
        'warning': len(found_forbidden) > 0,
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/outlook/exchange", response_model=TokenExchangeResponse)
async def exchange_outlook_tokens(request: TokenExchangeRequest):
    """
    Exchange Microsoft OAuth authorization code for tokens and store them.

    This endpoint is called by the Vercel frontend after Microsoft redirects
    back with an authorization code. All secrets stay in Render.
    """
    try:
        # Parse state to get user_id, purpose, yacht context
        state_data = parse_state(request.state)
        if not state_data:
            return TokenExchangeResponse(
                success=False,
                error="Invalid state parameter",
                error_code="invalid_state",
            )

        user_id = state_data.get('user_id')
        purpose = state_data.get('purpose', 'read')

        if not user_id:
            return TokenExchangeResponse(
                success=False,
                error="Missing user_id in state",
                error_code="invalid_state",
            )

        logger.info(f"[Auth] Processing OAuth exchange for user {user_id}, purpose={purpose}")

        # Exchange code for tokens
        token_result = await exchange_code_for_tokens(
            request.code,
            request.redirect_uri,
            purpose,
        )

        if not token_result['success']:
            return TokenExchangeResponse(
                success=False,
                error=token_result.get('error', 'Token exchange failed'),
                error_code=token_result.get('error_code', 'token_exchange_failed'),
            )

        token_data = token_result['data']
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token', '')
        expires_in = token_data.get('expires_in', 3600)
        scopes = token_data.get('scope', '').split(' ')

        # Check for forbidden scopes
        scope_check = check_scopes(scopes, purpose)
        if not scope_check['valid']:
            logger.warning(f"[Auth] Forbidden scopes detected: {scope_check['forbidden']}")

        # Fetch user profile
        profile = await fetch_graph_profile(access_token)
        email = profile['email'] if profile else ''
        display_name = profile['displayName'] if profile else ''
        email_hash = hash_email(email) if email else ''

        logger.info(f"[Auth] Got profile: {email}")

        # Step 1: Query MASTER DB to find which yacht this user belongs to
        master_supabase = get_master_supabase()
        if not master_supabase:
            return TokenExchangeResponse(
                success=False,
                error="Failed to connect to authentication database",
                error_code="master_db_connection_failed",
            )

        try:
            logger.info(f"[Auth] Querying MASTER DB user_accounts for user_id={user_id}")
            user_account = master_supabase.table('user_accounts').select('yacht_id, role, email').eq('id', user_id).maybe_single().execute()

            if not user_account.data:
                logger.error(f"[Auth] User {user_id} not found in MASTER user_accounts table")
                return TokenExchangeResponse(
                    success=False,
                    error="User account not found",
                    error_code="no_user_account",
                )

            yacht_id = user_account.data.get('yacht_id')
            user_role = user_account.data.get('role')
            logger.info(f"[Auth] Found user in MASTER DB: yacht_id={yacht_id}, role={user_role}")

        except Exception as e:
            logger.error(f"[Auth] Failed to lookup user in MASTER DB: {e}")
            return TokenExchangeResponse(
                success=False,
                error="Failed to lookup user account",
                error_code="user_lookup_failed",
            )

        if not yacht_id:
            logger.error(f"[Auth] User {user_id} has no yacht_id assigned in MASTER DB")
            return TokenExchangeResponse(
                success=False,
                error="User has no yacht assigned",
                error_code="no_yacht",
            )

        # Step 2: Get TENANT DB client for this yacht
        tenant_supabase = get_yacht_supabase(yacht_id)
        if not tenant_supabase:
            return TokenExchangeResponse(
                success=False,
                error="Failed to connect to yacht database",
                error_code="tenant_db_connection_failed",
            )

        # Store token
        token_record = {
            'user_id': user_id,
            'yacht_id': yacht_id,
            'provider': 'microsoft_graph',
            'token_purpose': purpose,
            'microsoft_access_token': access_token,
            'microsoft_refresh_token': refresh_token,
            'token_expires_at': (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
            'scopes': scopes,
            'provider_email_hash': email_hash,
            'provider_display_name': display_name,
            'is_revoked': False,
            'updated_at': datetime.utcnow().isoformat(),
        }

        # Step 3: Store token in TENANT DB
        upsert_result = tenant_supabase.table('auth_microsoft_tokens').upsert(
            token_record,
            on_conflict='user_id,yacht_id,provider,token_purpose',
        ).execute()

        if not upsert_result.data:
            logger.error(f"[Auth] Failed to store token in TENANT DB")
            return TokenExchangeResponse(
                success=False,
                error="Failed to store token",
                error_code="storage_failed",
            )

        logger.info(f"[Auth] Token stored successfully in TENANT DB for user {user_id}, yacht {yacht_id}")

        # Create/update watcher record in TENANT DB
        watcher_status = 'active' if purpose == 'read' and scope_check['valid'] else 'degraded'

        watcher_record = {
            'user_id': user_id,
            'yacht_id': yacht_id,
            'provider': 'microsoft_graph',
            'mailbox_address_hash': email_hash,  # NOTE: Column is mailbox_address_hash, not provider_email_hash
            'sync_status': watcher_status,
            'updated_at': datetime.utcnow().isoformat(),
        }

        try:
            tenant_supabase.table('email_watchers').upsert(
                watcher_record,
                on_conflict='user_id,yacht_id',
            ).execute()
            logger.info(f"[Auth] Watcher updated in TENANT DB: {watcher_status}")
        except Exception as e:
            logger.warning(f"[Auth] Failed to update watcher (non-fatal): {e}")

        return TokenExchangeResponse(
            success=True,
            email=email,
            warning='forbidden_scopes' if scope_check['warning'] else None,
        )

    except Exception as e:
        logger.exception(f"[Auth] Unexpected error in token exchange: {e}")
        return TokenExchangeResponse(
            success=False,
            error=str(e),
            error_code="unexpected",
        )


@router.get("/outlook/status", response_model=OutlookStatusResponse)
async def get_outlook_status(authorization: str = Header(None)):
    """
    Get Outlook OAuth connection status for the authenticated user.

    This endpoint queries both MASTER and TENANT databases to determine
    if the user has valid OAuth tokens stored.

    Headers:
        Authorization: Bearer <supabase_jwt_token>
    """
    try:
        # Extract user_id from Supabase JWT
        if not authorization or not authorization.startswith('Bearer '):
            return OutlookStatusResponse(connected=False)

        token = authorization.split(' ')[1]

        # Decode and VERIFY JWT signature (SECURITY FIX: P0-001)
        import jwt

        # Get JWT secret for signature verification
        jwt_secret = (
            os.getenv("MASTER_SUPABASE_JWT_SECRET") or
            os.getenv("TENANT_SUPABASE_JWT_SECRET") or
            os.getenv("SUPABASE_JWT_SECRET")
        )

        if not jwt_secret:
            logger.error("[Auth] No JWT secret configured for signature verification")
            return OutlookStatusResponse(connected=False)

        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_exp": True}
            )
            user_id = payload.get('sub')
        except jwt.ExpiredSignatureError:
            logger.warning("[Auth] JWT expired")
            return OutlookStatusResponse(connected=False)
        except jwt.InvalidTokenError as e:
            logger.warning(f"[Auth] JWT validation failed: {e}")
            return OutlookStatusResponse(connected=False)

        if not user_id:
            return OutlookStatusResponse(connected=False)

        # Step 1: Get yacht_id from MASTER DB
        master_supabase = get_master_supabase()
        if not master_supabase:
            logger.error(f"[Auth] No MASTER Supabase connection for status check")
            return OutlookStatusResponse(connected=False)

        try:
            user_account = master_supabase.table('user_accounts').select('yacht_id').eq('id', user_id).maybe_single().execute()

            if not user_account.data:
                logger.warning(f"[Auth] User {user_id} not found in MASTER user_accounts")
                return OutlookStatusResponse(connected=False)

            yacht_id = user_account.data.get('yacht_id')

            if not yacht_id:
                logger.warning(f"[Auth] User {user_id} has no yacht_id")
                return OutlookStatusResponse(connected=False)

        except Exception as e:
            logger.error(f"[Auth] Error querying MASTER DB for status: {e}")
            return OutlookStatusResponse(connected=False)

        # Step 2: Query TENANT DB for OAuth tokens
        tenant_supabase = get_yacht_supabase(yacht_id)
        if not tenant_supabase:
            logger.error(f"[Auth] No TENANT Supabase connection for status check")
            return OutlookStatusResponse(connected=False)

        try:
            # Check for 'read' token (most common)
            token_result = tenant_supabase.table('auth_microsoft_tokens')\
                .select('provider_email_hash, token_purpose, scopes, token_expires_at, is_revoked')\
                .eq('user_id', user_id)\
                .eq('yacht_id', yacht_id)\
                .eq('provider', 'microsoft_graph')\
                .eq('token_purpose', 'read')\
                .eq('is_revoked', False)\
                .maybe_single()\
                .execute()

            if token_result.data:
                # Convert email hash back to email (we can't, so we'll just indicate connected)
                return OutlookStatusResponse(
                    connected=True,
                    email=None,  # We only store hash, not actual email
                    token_purpose=token_result.data.get('token_purpose'),
                    scopes=token_result.data.get('scopes', []),
                    expires_at=token_result.data.get('token_expires_at'),
                )

            # If no 'read' token, check for 'write' token
            token_result = tenant_supabase.table('auth_microsoft_tokens')\
                .select('provider_email_hash, token_purpose, scopes, token_expires_at, is_revoked')\
                .eq('user_id', user_id)\
                .eq('yacht_id', yacht_id)\
                .eq('provider', 'microsoft_graph')\
                .eq('token_purpose', 'write')\
                .eq('is_revoked', False)\
                .maybe_single()\
                .execute()

            if token_result.data:
                return OutlookStatusResponse(
                    connected=True,
                    email=None,
                    token_purpose=token_result.data.get('token_purpose'),
                    scopes=token_result.data.get('scopes', []),
                    expires_at=token_result.data.get('token_expires_at'),
                )

            # No valid tokens found
            return OutlookStatusResponse(connected=False)

        except Exception as e:
            logger.error(f"[Auth] Error querying TENANT DB for tokens: {e}")
            return OutlookStatusResponse(connected=False)

    except Exception as e:
        logger.exception(f"[Auth] Unexpected error in status check: {e}")
        return OutlookStatusResponse(connected=False)


class DisconnectResponse(BaseModel):
    """Response from disconnect endpoint."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


@router.post("/outlook/disconnect", response_model=DisconnectResponse)
async def disconnect_outlook(authorization: str = Header(None)):
    """
    Disconnect Outlook OAuth - revoke all tokens for the user.

    Soft-deletes tokens (is_revoked=true) and marks watcher as disconnected.
    Email history is preserved.

    Headers:
        Authorization: Bearer <supabase_jwt_token>
    """
    try:
        # Extract user_id from Supabase JWT
        if not authorization or not authorization.startswith('Bearer '):
            return DisconnectResponse(
                success=False,
                error="Unauthorized",
                error_code="unauthorized",
            )

        token = authorization.split(' ')[1]

        # Decode and VERIFY JWT signature
        import jwt

        jwt_secret = (
            os.getenv("MASTER_SUPABASE_JWT_SECRET") or
            os.getenv("TENANT_SUPABASE_JWT_SECRET") or
            os.getenv("SUPABASE_JWT_SECRET")
        )

        if not jwt_secret:
            logger.error("[Auth] No JWT secret configured for disconnect")
            return DisconnectResponse(
                success=False,
                error="Server configuration error",
                error_code="no_jwt_secret",
            )

        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_exp": True}
            )
            user_id = payload.get('sub')
        except jwt.ExpiredSignatureError:
            return DisconnectResponse(
                success=False,
                error="Token expired",
                error_code="token_expired",
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"[Auth] JWT validation failed: {e}")
            return DisconnectResponse(
                success=False,
                error="Invalid token",
                error_code="invalid_token",
            )

        if not user_id:
            return DisconnectResponse(
                success=False,
                error="No user ID in token",
                error_code="no_user_id",
            )

        logger.info(f"[Auth] Processing disconnect for user {user_id}")

        # Step 1: Get yacht_id from MASTER DB
        master_supabase = get_master_supabase()
        if not master_supabase:
            return DisconnectResponse(
                success=False,
                error="Failed to connect to authentication database",
                error_code="master_db_connection_failed",
            )

        try:
            user_account = master_supabase.table('user_accounts').select('yacht_id').eq('id', user_id).maybe_single().execute()

            if not user_account.data:
                return DisconnectResponse(
                    success=False,
                    error="User not found",
                    error_code="user_not_found",
                )

            yacht_id = user_account.data.get('yacht_id')

            if not yacht_id:
                return DisconnectResponse(
                    success=False,
                    error="No yacht assigned to user",
                    error_code="no_yacht",
                )

        except Exception as e:
            logger.error(f"[Auth] Error querying MASTER DB: {e}")
            return DisconnectResponse(
                success=False,
                error="Failed to lookup user",
                error_code="user_lookup_failed",
            )

        # Step 2: Get TENANT DB client
        tenant_supabase = get_yacht_supabase(yacht_id)
        if not tenant_supabase:
            return DisconnectResponse(
                success=False,
                error="Failed to connect to yacht database",
                error_code="tenant_db_connection_failed",
            )

        # Step 3: Revoke all Microsoft tokens (soft delete)
        try:
            revoke_result = tenant_supabase.table('auth_microsoft_tokens').update({
                'is_revoked': True,
                'revoked_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').eq('is_revoked', False).execute()

            logger.info(f"[Auth] Revoked tokens for user {user_id}")

        except Exception as e:
            logger.error(f"[Auth] Failed to revoke tokens: {e}")
            return DisconnectResponse(
                success=False,
                error="Failed to revoke tokens",
                error_code="revoke_failed",
            )

        # Step 4: Mark watcher as disconnected
        try:
            tenant_supabase.table('email_watchers').update({
                'sync_status': 'disconnected',
                'updated_at': datetime.utcnow().isoformat(),
            }).eq('user_id', user_id).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').execute()

            logger.info(f"[Auth] Watcher marked as disconnected for user {user_id}")

        except Exception as e:
            logger.warning(f"[Auth] Failed to update watcher (non-fatal): {e}")

        logger.info(f"[Auth] Successfully disconnected Outlook for user {user_id}")

        return DisconnectResponse(
            success=True,
            message="Disconnected successfully. Email history preserved.",
        )

    except Exception as e:
        logger.exception(f"[Auth] Unexpected error in disconnect: {e}")
        return DisconnectResponse(
            success=False,
            error=str(e),
            error_code="unexpected",
        )
