"""
CelesteOS Backend - Microsoft Graph Client Wrappers

Strict read/write separation per doctrine:
- graph_read_client: ONLY for reading emails (Mail.Read)
- graph_write_client: ONLY for sending emails (Mail.Send)

HARD ERRORS if called with wrong token type.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from supabase import Client

logger = logging.getLogger(__name__)

# Graph API base URL
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


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


# ============================================================================
# TOKEN RETRIEVAL
# ============================================================================

def get_user_token(
    supabase: Client,
    user_id: str,
    yacht_id: str,
    purpose: str  # 'read' or 'write'
) -> Dict[str, Any]:
    """
    Get Microsoft token for user with specific purpose.

    Raises:
        TokenNotFoundError: No token found
        TokenExpiredError: Token is expired
        TokenRevokedError: Token has been revoked
    """
    result = supabase.table('auth_microsoft_tokens').select(
        'microsoft_access_token, microsoft_refresh_token, token_expires_at, is_revoked, scopes'
    ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
        'provider', 'microsoft_graph'
    ).eq('token_purpose', purpose).single().execute()

    if not result.data:
        raise TokenNotFoundError(f"No {purpose} token found for user")

    token_data = result.data

    if token_data.get('is_revoked'):
        raise TokenRevokedError(f"Token has been revoked")

    expires_at = datetime.fromisoformat(token_data['token_expires_at'].replace('Z', '+00:00'))
    if expires_at < datetime.now(expires_at.tzinfo):
        raise TokenExpiredError(f"Token expired at {expires_at}")

    return token_data


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
    """

    def __init__(self, supabase: Client, user_id: str, yacht_id: str):
        self.supabase = supabase
        self.user_id = user_id
        self.yacht_id = yacht_id
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        """Get and cache read token."""
        if self._token:
            return self._token

        token_data = get_user_token(
            self.supabase, self.user_id, self.yacht_id, 'read'
        )
        self._token = token_data['microsoft_access_token']
        return self._token

    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
        }

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

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30.0)
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

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30.0)
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

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def get_attachment(self, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Get attachment content."""
        url = f"{GRAPH_API_BASE}/me/messages/{message_id}/attachments/{attachment_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        url = f"{GRAPH_API_BASE}/me"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers(), timeout=30.0)
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


__all__ = [
    'GraphClientError',
    'TokenPurposeMismatchError',
    'TokenNotFoundError',
    'TokenExpiredError',
    'TokenRevokedError',
    'GraphReadClient',
    'GraphWriteClient',
    'create_read_client',
    'create_write_client',
    'get_user_token',
]
