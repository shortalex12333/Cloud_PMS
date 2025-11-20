"""
Third-party integrations endpoints (Outlook/Microsoft OAuth)
Copied and adapted from c.os.4.1 repo (server/routes/emailRoutes.ts)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import secrets
import httpx
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging

from app.core.auth import get_current_user, YachtContext
from app.core.supabase import supabase_client
from app.core.config import settings
from app.models.integrations import (
    OutlookAuthUrlResponse,
    OutlookStatusResponse,
    IntegrationTokenData
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Microsoft OAuth scopes (copied from c.os.4.1)
MICROSOFT_SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/MailboxSettings.Read",
    "offline_access"
]


def generate_auth_url(state: str) -> str:
    """
    Generate Microsoft OAuth2 authorization URL
    Copied from c.os.4.1/server/routes/emailRoutes.ts:generateAuthUrl()
    Uses configuration from settings (environment variables)
    """
    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "scope": " ".join(MICROSOFT_SCOPES),
        "state": state,
        "prompt": "select_account",  # Allow user to pick account
        "response_mode": "query"
    }

    authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
    return f"{authority}/oauth2/v2.0/authorize?{urlencode(params)}"


@router.get("/outlook/auth-url", response_model=OutlookAuthUrlResponse)
async def get_outlook_auth_url(
    context: YachtContext = Depends(get_current_user)
):
    """
    Generate Microsoft OAuth URL for the current user
    Copied from c.os.4.1/server/routes/emailRoutes.ts:/microsoft-auth endpoint

    Frontend calls this endpoint, gets the auth_url, then redirects user to Microsoft login.
    """
    try:
        # Generate state with user_id and random CSRF token
        # Format: user_id:random_token
        csrf_token = secrets.token_urlsafe(16)
        state = f"{context.user_id}:{csrf_token}"

        auth_url = generate_auth_url(state)

        logger.info(f"🚀 Generated Microsoft auth URL for user: {context.user_id}")

        return OutlookAuthUrlResponse(
            auth_url=auth_url,
            state=state
        )
    except Exception as e:
        logger.error(f"❌ Failed to generate auth URL: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate authentication URL"
        )


@router.get("/outlook/callback")
async def outlook_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Handle OAuth callback from Microsoft
    Copied from c.os.4.1/server/routes/emailRoutes.ts:/auth/microsoft/callback

    This endpoint:
    1. Receives authorization code from Microsoft
    2. Exchanges code for access/refresh tokens
    3. Fetches user profile from Microsoft Graph
    4. Stores tokens in integration_tokens table
    5. Returns success HTML page that closes popup window
    """
    try:
        # Handle OAuth errors
        if error:
            logger.error(f"❌ OAuth error: {error} - {error_description}")
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Error</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: red; }}
                    </style>
                </head>
                <body>
                    <h2 class="error">❌ Authentication Error</h2>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                    <p>Please close this window and try again.</p>
                    <script>
                        setTimeout(function() {{ window.close(); }}, 5000);
                    </script>
                </body>
                </html>
            """, status_code=400)

        if not code:
            raise HTTPException(
                status_code=400,
                detail="No authorization code received"
            )

        # Extract user_id from state parameter (format: "user_id:random")
        if not state:
            raise HTTPException(
                status_code=400,
                detail="Missing state parameter"
            )

        user_id = state.split(':')[0]
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid state parameter - user_id required"
            )

        logger.info(f"✅ Received auth code for user_id: {user_id}")

        # Exchange authorization code for access token
        token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
        token_data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "scope": " ".join(MICROSOFT_SCOPES),
            "code": code,
            "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if not token_response.is_success:
                error_text = token_response.text
                logger.error(f"❌ Token exchange failed: {token_response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Token exchange failed: {error_text}"
                )

            token_json = token_response.json()
            logger.info(f"📄 Token data received for user: {user_id}")

            # Get user profile info from Microsoft Graph
            graph_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={
                    "Authorization": f"Bearer {token_json['access_token']}",
                    "Content-Type": "application/json"
                }
            )

            user_info = None
            if graph_response.is_success:
                user_info = graph_response.json()
                logger.info(f"👤 Microsoft user info: {user_info.get('id')} - {user_info.get('mail') or user_info.get('userPrincipalName')}")

        # Calculate token expiry
        expires_in = token_json.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Prepare token data for database
        token_data_obj = IntegrationTokenData(
            user_id=user_id,
            provider="microsoft",
            access_token=token_json["access_token"],
            refresh_token=token_json.get("refresh_token"),
            token_type=token_json.get("token_type", "Bearer"),
            expires_at=expires_at,
            provider_user_id=user_info.get("id") if user_info else None,
            provider_email=user_info.get("mail") or user_info.get("userPrincipalName") if user_info else None,
            display_name=user_info.get("displayName") if user_info else None,
            scopes=MICROSOFT_SCOPES
        )

        # Store tokens in Supabase (upsert to handle re-auth)
        try:
            # Delete existing token for this user/provider
            supabase_client._service_client.table('integration_tokens').delete().eq(
                'user_id', user_id
            ).eq('provider', 'microsoft').execute()

            # Insert new token
            result = supabase_client._service_client.table('integration_tokens').insert({
                'user_id': user_id,
                'provider': 'microsoft',
                'access_token': token_data_obj.access_token,
                'refresh_token': token_data_obj.refresh_token,
                'token_type': token_data_obj.token_type,
                'expires_at': token_data_obj.expires_at.isoformat(),
                'provider_user_id': token_data_obj.provider_user_id,
                'provider_email': token_data_obj.provider_email,
                'display_name': token_data_obj.display_name,
                'scopes': token_data_obj.scopes
            }).execute()

            logger.info(f"✅ Token stored successfully for user: {user_id}")

        except Exception as e:
            logger.error(f"❌ Failed to store token: {e}")
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Connection Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: red; }}
                    </style>
                </head>
                <body>
                    <h2 class="error">❌ Failed to Save Email Connection</h2>
                    <p>Authentication succeeded but failed to save credentials.</p>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <p>Please try again or contact support.</p>
                    <script>
                        setTimeout(function() {{ window.close(); }}, 5000);
                    </script>
                </body>
                </html>
            """, status_code=500)

        # Success - return HTML that closes the popup and notifies parent window
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Email Connected!</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: green; }}
                </style>
            </head>
            <body>
                <h2 class="success">✅ Email Successfully Connected!</h2>
                <p>Your Microsoft account has been linked to CelesteOS.</p>
                <p>You can now close this window and return to the app.</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'MICROSOFT_AUTH_SUCCESS',
                            email: '{token_data_obj.provider_email}',
                            display_name: '{token_data_obj.display_name}'
                        }}, '*');
                        setTimeout(function() {{ window.close(); }}, 2000);
                    }} else {{
                        setTimeout(function() {{
                            window.location.href = '/';
                        }}, 3000);
                    }}
                </script>
            </body>
            </html>
        """)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Callback handling error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process authentication callback: {str(e)}"
        )


@router.get("/outlook/status", response_model=OutlookStatusResponse)
async def get_outlook_status(
    context: YachtContext = Depends(get_current_user)
):
    """
    Check if current user has Outlook connected
    Copied from c.os.4.1/server/routes/emailRoutes.ts:/user/:userId/status

    Frontend uses this to show "Connect Outlook" button or "Connected ✅" status.
    Returns only connection status - NEVER returns tokens to frontend.
    """
    try:
        # Query integration_tokens table
        result = supabase_client._service_client.table('integration_tokens').select(
            'provider_email, display_name, created_at, expires_at'
        ).eq('user_id', str(context.user_id)).eq('provider', 'microsoft').execute()

        if result.data and len(result.data) > 0:
            token_record = result.data[0]

            # Check if token is expired
            expires_at = datetime.fromisoformat(token_record['expires_at'].replace('Z', '+00:00'))
            is_expired = expires_at < datetime.utcnow()

            if is_expired:
                logger.warning(f"⚠️ Token expired for user {context.user_id}")
                # Token expired - user needs to reconnect
                return OutlookStatusResponse(connected=False)

            logger.info(f"✅ User {context.user_id} has Outlook connected")
            return OutlookStatusResponse(
                connected=True,
                provider_email=token_record.get('provider_email'),
                display_name=token_record.get('display_name'),
                connected_at=datetime.fromisoformat(token_record['created_at'].replace('Z', '+00:00'))
            )
        else:
            logger.info(f"ℹ️ User {context.user_id} does not have Outlook connected")
            return OutlookStatusResponse(connected=False)

    except Exception as e:
        logger.error(f"❌ Error checking Outlook status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check Outlook status: {str(e)}"
        )


@router.delete("/outlook/disconnect")
async def disconnect_outlook(
    context: YachtContext = Depends(get_current_user)
):
    """
    Disconnect user's Outlook integration (delete tokens)
    """
    try:
        supabase_client._service_client.table('integration_tokens').delete().eq(
            'user_id', str(context.user_id)
        ).eq('provider', 'microsoft').execute()

        logger.info(f"✅ Disconnected Outlook for user: {context.user_id}")
        return {"success": True, "message": "Outlook disconnected successfully"}

    except Exception as e:
        logger.error(f"❌ Error disconnecting Outlook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect Outlook: {str(e)}"
        )
