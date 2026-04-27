"""
Email Graph Helpers
===================
Shared helpers used across email route files.

Centralising here prevents the same function being defined 3 times with
slightly different names (outlook_auth_error / _outlook_auth_error).
"""

import re
import logging
from datetime import datetime, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def utcnow() -> str:
    """Timezone-aware UTC timestamp as ISO string. Replaces datetime.utcnow()."""
    return datetime.now(timezone.utc).isoformat()


def outlook_auth_error(error_code: str, message: str, status_code: int = 401) -> HTTPException:
    """
    Structured HTTPException for Outlook OAuth errors.

    Frontend checks response.detail.error_code:
    - starts with 'outlook_' → show "Reconnect Outlook" UI
    - otherwise → treat as session expiry (standard 401)
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "requires_outlook_reconnect": True,
        }
    )


async def mark_watcher_degraded(
    supabase,
    user_id: str,
    yacht_id: str,
    error_message: str,
) -> None:
    """Mark email watcher as degraded with error message."""
    try:
        supabase.table('email_watchers').update({
            'sync_status': 'degraded',
            'last_sync_error': error_message[:500],
            'last_sync_at': utcnow(),
            'updated_at': utcnow(),
        }).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'provider', 'microsoft_graph'
        ).execute()
        logger.info(f"[email] Marked watcher degraded: {error_message[:100]}")
    except Exception as e:
        logger.error(f"[email] Failed to mark watcher degraded: {e}")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for Content-Disposition header and storage (prevents path injection)."""
    filename = re.sub(r'[/\\:\x00]', '_', filename)
    if len(filename) > 255:
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        filename = filename[:250] + ('.' + ext if ext else '')
    return filename
