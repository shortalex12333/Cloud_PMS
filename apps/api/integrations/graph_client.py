"""
CelesteOS Backend - Microsoft Graph Client Wrappers

Strict read/write separation per doctrine:
- graph_read_client: ONLY for reading emails (Mail.Read)
- graph_write_client: ONLY for sending emails (Mail.Send)

HARD ERRORS if called with wrong token type.

Refresh-on-demand:
- Tokens are automatically refreshed when expired
- Refresh failures mark watcher as degraded
"""

import httpx
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from supabase import Client

logger = logging.getLogger(__name__)

# Graph API base URL
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

# Proactive refresh: refresh tokens 5 minutes before expiry
TOKEN_REFRESH_SKEW_SECONDS = 300  # 5 minutes


def needs_refresh(expires_at: datetime, skew_seconds: int = TOKEN_REFRESH_SKEW_SECONDS) -> bool:
    """
    Check if token needs refresh (within skew window of expiry).

    Args:
        expires_at: Token expiry timestamp (must be timezone-aware)
        skew_seconds: Seconds before expiry to trigger refresh (default: 300 = 5 min)

    Returns:
        True if token should be refreshed now
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    refresh_threshold = datetime.now(timezone.utc) + timedelta(seconds=skew_seconds)
    return expires_at <= refresh_threshold

# Azure app config (READ app)
AZURE_READ_APP_ID = os.getenv('AZURE_READ_APP_ID', os.getenv('AZURE_APP_ID', '41f6dc82-8127-4330-97e0-c6b26e6aa967'))
AZURE_READ_CLIENT_SECRET = os.getenv('AZURE_READ_CLIENT_SECRET', os.getenv('AZURE_CLIENT_SECRET', ''))

# Azure app config (WRITE app)
AZURE_WRITE_APP_ID = os.getenv('AZURE_WRITE_APP_ID', 'f0b8944b-8127-4f0f-8ed5-5487462df50c')
AZURE_WRITE_CLIENT_SECRET = os.getenv('AZURE_WRITE_CLIENT_SECRET', '')


class GraphClientError(Exception):
    """Base exception for Graph client errors."""
    pass


class TokenPurposeMismatchError(GraphClientError):
    """Raised when token purpose doesn't match operation."""
    pass


class TokenNotFoundError(GraphClientError):
    """Raised when no valid token found."""
    pass


class TokenExpiredError(GraphClientError):
    """Raised when token is expired."""
    pass


class TokenRevokedError(GraphClientError):
    """Raised when token has been revoked."""
    pass


class TokenRefreshError(GraphClientError):
    """Raised when token refresh fails."""
    pass


class GraphApiError(GraphClientError):
    """Raised when Graph API returns an error."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


# ============================================================================
# TOKEN REFRESH
# ============================================================================

async def refresh_access_token(
    supabase: Client,
    user_id: str,
    yacht_id: str,
    purpose: str  # 'read' or 'write'
) -> str:
    """
    Refresh access token using stored refresh token.

    Returns: new access token
    Raises: TokenRefreshError on failure

    NEVER logs token values.
    """
    # Get current token record with refresh_token
    result = supabase.table('auth_microsoft_tokens').select(
        'id, microsoft_refresh_token, scopes'
    ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
        'provider', 'microsoft_graph'
    ).eq('token_purpose', purpose).eq('is_revoked', False).single().execute()

    if not result.data:
        raise TokenRefreshError(f"No {purpose} token record found for refresh")

    refresh_token = result.data.get('microsoft_refresh_token')
    if not refresh_token:
        raise TokenRefreshError("No refresh token available")

    token_id = result.data['id']

    # Get app credentials based on purpose
    if purpose == 'read':
        client_id = AZURE_READ_APP_ID
        client_secret = AZURE_READ_CLIENT_SECRET
    else:
        client_id = AZURE_WRITE_APP_ID
        client_secret = AZURE_WRITE_CLIENT_SECRET

    if not client_secret:
        raise TokenRefreshError(f"Missing client secret for {purpose} app")

    # Call Microsoft token endpoint
    logger.info(f"[TokenRefresh] Refreshing {purpose} token for user (id redacted)")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30.0
        )

    if not response.is_success:
        error_data = response.json() if response.content else {}
        error_msg = error_data.get('error_description', error_data.get('error', 'Unknown error'))
        logger.error(f"[TokenRefresh] Failed with status {response.status_code}: {error_msg}")
        raise TokenRefreshError(f"Refresh failed: {error_msg}")

    data = response.json()
    new_access_token = data.get('access_token')
    new_refresh_token = data.get('refresh_token')  # Microsoft may issue a new one
    expires_in = data.get('expires_in', 3600)

    if not new_access_token:
        raise TokenRefreshError("No access token in refresh response")

    # Calculate new expiry
    new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Update token in database
    update_data = {
        'microsoft_access_token': new_access_token,
        'token_expires_at': new_expires_at.isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }

    # Update refresh token if a new one was issued
    if new_refresh_token:
        update_data['microsoft_refresh_token'] = new_refresh_token

    supabase.table('auth_microsoft_tokens').update(update_data).eq('id', token_id).execute()

    logger.info(f"[TokenRefresh] Successfully refreshed {purpose} token, expires in {expires_in}s")

    return new_access_token


# ============================================================================
# TOKEN RETRIEVAL (with auto-refresh)
# ============================================================================

def get_user_token(
    supabase: Client,
    user_id: str,
    yacht_id: str,
    purpose: str,  # 'read' or 'write'
    check_expiry: bool = True
) -> Dict[str, Any]:
    """
    Get Microsoft token for user with specific purpose.

    Args:
        check_expiry: If True, raises TokenExpiredError when expired.
                      If False, returns token data even if expired (for refresh flow).

    Raises:
        TokenNotFoundError: No token found
        TokenExpiredError: Token is expired (only if check_expiry=True)
        TokenRevokedError: Token has been revoked
    """
    # Use maybe_single() to avoid exception when no token exists
    # This allows graceful 401 "Email not connected" instead of 500
    result = supabase.table('auth_microsoft_tokens').select(
        'id, microsoft_access_token, microsoft_refresh_token, token_expires_at, is_revoked, scopes'
    ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
        'provider', 'microsoft_graph'
    ).eq('token_purpose', purpose).maybe_single().execute()

    if not result.data:
        raise TokenNotFoundError(f"No {purpose} token found for user")

    token_data = result.data

    if token_data.get('is_revoked'):
        raise TokenRevokedError(f"Token has been revoked")

    # Parse expiry
    expires_at_str = token_data['token_expires_at']
    if expires_at_str.endswith('Z'):
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
    elif '+' in expires_at_str or expires_at_str.endswith('00:00'):
        expires_at = datetime.fromisoformat(expires_at_str)
    else:
        expires_at = datetime.fromisoformat(expires_at_str).replace(tzinfo=timezone.utc)

    token_data['is_expired'] = expires_at < datetime.now(timezone.utc)

    if check_expiry and token_data['is_expired']:
        raise TokenExpiredError(f"Token expired at {expires_at}")

    return token_data


async def get_valid_token(
    supabase: Client,
    user_id: str,
    yacht_id: str,
    purpose: str  # 'read' or 'write'
) -> str:
    """
    Get a valid (non-expired) access token, refreshing if necessary.

    This is the main entry point for getting tokens with auto-refresh.

    PROACTIVE REFRESH: Refreshes tokens 5 minutes before expiry to prevent
    mid-request failures. This is critical for long-running sync operations.

    Returns: valid access token
    Raises: TokenNotFoundError, TokenRevokedError, TokenRefreshError
    """
    # Get token without expiry check
    token_data = get_user_token(supabase, user_id, yacht_id, purpose, check_expiry=False)

    # Parse expiry for proactive refresh check
    expires_at_str = token_data.get('token_expires_at', '')
    try:
        if expires_at_str:
            if expires_at_str.endswith('Z'):
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            elif '+' in expires_at_str or expires_at_str.endswith('00:00'):
                expires_at = datetime.fromisoformat(expires_at_str)
            else:
                expires_at = datetime.fromisoformat(expires_at_str).replace(tzinfo=timezone.utc)
        else:
            # No expiry means treat as expired
            expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    except (ValueError, TypeError):
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

    # PROACTIVE REFRESH: Refresh if expired OR within 5-min skew window
    if token_data.get('is_expired') or needs_refresh(expires_at):
        reason = "expired" if token_data.get('is_expired') else "proactive (within 5-min window)"
        logger.info(f"[GetToken] Token {reason}, refreshing {purpose} token")
        # Refresh and return new token
        return await refresh_access_token(supabase, user_id, yacht_id, purpose)

    return token_data['microsoft_access_token']


# ============================================================================
# READ CLIENT
# ============================================================================

class GraphReadClient:
    """
    Graph client for READ operations only.

    Allowed operations:
    - list_messages (inbox/sent)
    - get_message
    - get_message_content (render)
    - list_attachments
    - get_attachment

    FORBIDDEN operations (will raise TokenPurposeMismatchError):
    - send_message
    - create_draft
    - delete_message
    - move_message

    Auto-refresh:
    - Automatically refreshes expired tokens before API calls
    - On 401 from Graph, attempts one refresh and retry
    """

    def __init__(self, supabase: Client, user_id: str, yacht_id: str):
        self.supabase = supabase
        self.user_id = user_id
        self.yacht_id = yacht_id
        self._token: Optional[str] = None
        self._refresh_attempted: bool = False

    async def _get_token(self) -> str:
        """Get valid read token with auto-refresh."""
        if self._token and not self._refresh_attempted:
            return self._token

        # Use get_valid_token which handles refresh
        self._token = await get_valid_token(
            self.supabase, self.user_id, self.yacht_id, 'read'
        )
        self._refresh_attempted = False
        return self._token

    async def _headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            'Authorization': f'Bearer {await self._get_token()}',
            'Content-Type': 'application/json',
        }

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with automatic retry on 401.

        On 401:
        1. Clear cached token
        2. Refresh token
        3. Retry request once
        4. If still 401, raise GraphApiError
        """
        async with httpx.AsyncClient() as client:
            headers = await self._headers()
            response = await client.request(method, url, headers=headers, timeout=30.0, **kwargs)

            # If 401 and haven't retried yet, attempt refresh and retry
            if response.status_code == 401 and not self._refresh_attempted:
                logger.info("[GraphRead] Got 401, attempting token refresh and retry")
                self._refresh_attempted = True
                self._token = None

                try:
                    # Get fresh token (will trigger refresh)
                    headers = await self._headers()
                    response = await client.request(method, url, headers=headers, timeout=30.0, **kwargs)
                except TokenRefreshError as e:
                    raise GraphApiError(f"Token refresh failed: {e}", 401)

            # Reset refresh flag on success
            if response.is_success:
                self._refresh_attempted = False

            return response

    async def list_messages(
        self,
        folder: str = 'inbox',
        top: int = 50,
        skip: int = 0,
        select: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        delta_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List messages from a folder.

        Returns:
            {
                'messages': [...],
                'delta_link': 'url for next sync',
                'next_link': 'url for pagination'
            }
        """
        if delta_link:
            url = delta_link
        else:
            # Build URL with query params
            folder_map = {
                'inbox': 'inbox',
                'sent': 'sentItems',
                'drafts': 'drafts',
            }
            folder_name = folder_map.get(folder, folder)
            url = f"{GRAPH_API_BASE}/me/mailFolders/{folder_name}/messages/delta"

            params = []
            if top:
                params.append(f"$top={top}")
            if skip:
                params.append(f"$skip={skip}")
            if select:
                params.append(f"$select={','.join(select)}")
            if filter_query:
                params.append(f"$filter={filter_query}")

            if params:
                url = f"{url}?{'&'.join(params)}"

        response = await self._request_with_retry('GET', url)
        response.raise_for_status()
        data = response.json()

        return {
            'messages': data.get('value', []),
            'delta_link': data.get('@odata.deltaLink'),
            'next_link': data.get('@odata.nextLink'),
        }

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get message metadata by ID."""
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}"
        response = await self._request_with_retry('GET', url)
        response.raise_for_status()
        return response.json()

    async def get_message_content(self, message_id: str) -> Dict[str, Any]:
        """
        Get full message content for rendering.
        This is fetch-on-click - content is NOT stored.
        """
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}"
        params = "$select=id,subject,body,bodyPreview,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,hasAttachments,attachments"
        url = f"{url}?{params}&$expand=attachments($select=id,name,contentType,size)"

        response = await self._request_with_retry('GET', url)
        response.raise_for_status()
        return response.json()

    async def get_attachment(self, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Get attachment content."""
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments/{attachment_id}"
        response = await self._request_with_retry('GET', url)
        response.raise_for_status()
        return response.json()

    async def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        url = f"{GRAPH_API_BASE}/me"
        response = await self._request_with_retry('GET', url)
        response.raise_for_status()
        return response.json()

    # FORBIDDEN OPERATIONS - raise hard errors

    async def send_message(self, *args, **kwargs):
        """FORBIDDEN: Use GraphWriteClient for sending."""
        raise TokenPurposeMismatchError(
            "Cannot send email with READ token. Use GraphWriteClient."
        )

    async def create_draft(self, *args, **kwargs):
        """FORBIDDEN: Use GraphWriteClient for drafts."""
        raise TokenPurposeMismatchError(
            "Cannot create draft with READ token. Use GraphWriteClient."
        )


# ============================================================================
# WRITE CLIENT
# ============================================================================

class GraphWriteClient:
    """
    Graph client for WRITE operations only.

    Allowed operations:
    - send_message
    - create_draft

    FORBIDDEN operations (will raise TokenPurposeMismatchError):
    - list_messages
    - get_message
    - get_message_content
    """

    def __init__(self, supabase: Client, user_id: str, yacht_id: str):
        self.supabase = supabase
        self.user_id = user_id
        self.yacht_id = yacht_id
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        """Get and cache write token."""
        if self._token:
            return self._token

        token_data = get_user_token(
            self.supabase, self.user_id, self.yacht_id, 'write'
        )
        self._token = token_data['microsoft_access_token']
        return self._token

    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
        }

    async def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        body_type: str = 'HTML',
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email.

        Returns:
            Message ID and status
        """
        message = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': body_type,
                    'content': body,
                },
                'toRecipients': [
                    {'emailAddress': {'address': addr}} for addr in to
                ],
            },
            'saveToSentItems': True,
        }

        if cc:
            message['message']['ccRecipients'] = [
                {'emailAddress': {'address': addr}} for addr in cc
            ]

        if attachments:
            message['message']['attachments'] = attachments

        url = f"{GRAPH_API_BASE}/me/sendMail"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=self._headers(), json=message, timeout=30.0
            )
            response.raise_for_status()

        return {'sent': True}

    async def create_draft(
        self,
        to: List[str],
        subject: str,
        body: str,
        body_type: str = 'HTML',
    ) -> Dict[str, Any]:
        """Create a draft email."""
        draft = {
            'subject': subject,
            'body': {
                'contentType': body_type,
                'content': body,
            },
            'toRecipients': [
                {'emailAddress': {'address': addr}} for addr in to
            ],
        }

        url = f"{GRAPH_API_BASE}/me/messages"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=self._headers(), json=draft, timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # FORBIDDEN OPERATIONS - raise hard errors

    async def list_messages(self, *args, **kwargs):
        """FORBIDDEN: Use GraphReadClient for reading."""
        raise TokenPurposeMismatchError(
            "Cannot list messages with WRITE token. Use GraphReadClient."
        )

    async def get_message(self, *args, **kwargs):
        """FORBIDDEN: Use GraphReadClient for reading."""
        raise TokenPurposeMismatchError(
            "Cannot get message with WRITE token. Use GraphReadClient."
        )

    async def get_message_content(self, *args, **kwargs):
        """FORBIDDEN: Use GraphReadClient for rendering."""
        raise TokenPurposeMismatchError(
            "Cannot render message with WRITE token. Use GraphReadClient."
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_read_client(supabase: Client, user_id: str, yacht_id: str) -> GraphReadClient:
    """Create a Graph read client for user."""
    return GraphReadClient(supabase, user_id, yacht_id)


def create_write_client(supabase: Client, user_id: str, yacht_id: str) -> GraphWriteClient:
    """Create a Graph write client for user."""
    return GraphWriteClient(supabase, user_id, yacht_id)


# ============================================================================
# WATCHER STATUS HELPERS
# ============================================================================

async def mark_watcher_degraded(
    supabase: Client,
    user_id: str,
    yacht_id: str,
    error_reason: str
) -> None:
    """
    Mark email watcher as degraded after token refresh failure.

    This triggers the UI to show "Reconnect Outlook" banner.
    """
    try:
        supabase.table('email_watchers').update({
            'sync_status': 'degraded',
            'last_sync_error': error_reason,
            'degraded_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).eq('yacht_id', yacht_id).execute()
        logger.warning(f"[Watcher] Marked degraded: {error_reason}")
    except Exception as e:
        logger.error(f"[Watcher] Failed to mark degraded: {e}")


async def clear_watcher_degraded(
    supabase: Client,
    user_id: str,
    yacht_id: str
) -> None:
    """
    Clear degraded status after successful token refresh.
    """
    try:
        supabase.table('email_watchers').update({
            'sync_status': 'active',
            'last_sync_error': None,
            'degraded_at': None,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).eq('yacht_id', yacht_id).execute()
        logger.info(f"[Watcher] Cleared degraded status")
    except Exception as e:
        logger.error(f"[Watcher] Failed to clear degraded: {e}")


# ============================================================================
# PROACTIVE TOKEN REFRESH (Worker Heartbeat)
# ============================================================================

async def refresh_expiring_tokens(
    supabase: Client,
    skew_seconds: int = TOKEN_REFRESH_SKEW_SECONDS
) -> Dict[str, Any]:
    """
    Proactively refresh all tokens expiring within the skew window.

    Call this periodically from a worker/heartbeat (e.g., every 2-3 minutes).

    Returns:
        {
            'refreshed': [{'user_id': ..., 'yacht_id': ..., 'purpose': ...}, ...],
            'failed': [{'user_id': ..., 'error': ...}, ...],
            'checked': int
        }
    """
    refresh_threshold = datetime.now(timezone.utc) + timedelta(seconds=skew_seconds)

    # Find tokens expiring soon
    result = supabase.table('auth_microsoft_tokens').select(
        'id, user_id, yacht_id, token_purpose, token_expires_at'
    ).eq('is_revoked', False).lt(
        'token_expires_at', refresh_threshold.isoformat()
    ).execute()

    stats = {'refreshed': [], 'failed': [], 'checked': len(result.data) if result.data else 0}

    for token in (result.data or []):
        user_id = token['user_id']
        yacht_id = token['yacht_id']
        purpose = token['token_purpose']

        try:
            await refresh_access_token(supabase, user_id, yacht_id, purpose)
            stats['refreshed'].append({
                'user_id': user_id,
                'yacht_id': yacht_id,
                'purpose': purpose
            })
            # Clear degraded if previously set
            await clear_watcher_degraded(supabase, user_id, yacht_id)
            logger.info(f"[ProactiveRefresh] Refreshed {purpose} token for user {user_id[:8]}...")
        except Exception as e:
            stats['failed'].append({
                'user_id': user_id,
                'yacht_id': yacht_id,
                'purpose': purpose,
                'error': str(e)
            })
            # Mark watcher degraded
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"refresh_failed: {str(e)[:100]}")
            logger.error(f"[ProactiveRefresh] Failed for user {user_id[:8]}...: {e}")

    return stats


__all__ = [
    'GraphClientError',
    'TokenPurposeMismatchError',
    'TokenNotFoundError',
    'TokenExpiredError',
    'TokenRevokedError',
    'TokenRefreshError',
    'GraphApiError',
    'GraphReadClient',
    'GraphWriteClient',
    'create_read_client',
    'create_write_client',
    'get_user_token',
    'get_valid_token',
    'refresh_access_token',
    'needs_refresh',
    'mark_watcher_degraded',
    'clear_watcher_degraded',
    'refresh_expiring_tokens',
    'TOKEN_REFRESH_SKEW_SECONDS',
]
