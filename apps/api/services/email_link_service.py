"""
Email Link Service
==================
Single source of truth for all email-to-object link mutations.

Used by:
- routes/email_link_routes.py (all CRUD endpoints)
- routes/email_sync_routes.py (action/execute micro-actions)

No direct route concerns here — only DB writes and audit logic.
"""

from typing import Optional, Dict
import logging
from services.email_graph_helpers import utcnow

logger = logging.getLogger(__name__)

# Valid target object types (must match DB constraint)
VALID_LINK_OBJECT_TYPES = [
    'work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier'
]

# Table mapping for object existence checks (yacht_id-scoped)
OBJECT_TYPE_TABLE_MAP = {
    'work_order': 'pms_work_orders',
    'equipment': 'pms_equipment',
    'part': 'pms_parts',
    'fault': 'pms_faults',
    'purchase_order': 'pms_purchase_orders',
    'supplier': 'pms_suppliers',
}

# Roles allowed to manage email links
LINK_MANAGE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']

# Roles allowed to save evidence attachments
EVIDENCE_SAVE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']


async def audit_link_action(
    supabase,
    yacht_id: str,
    user_id: str,
    action: str,
    link_id: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    idempotency_key: Optional[str] = None,
    user_role: Optional[str] = None,
) -> None:
    """Write a link action to pms_audit_log."""
    try:
        signature = {
            'timestamp': utcnow(),
            'action_version': 'M4',
        }
        if idempotency_key:
            signature['idempotency_key'] = idempotency_key
        if user_role:
            signature['user_role'] = user_role

        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': action,
            'entity_type': 'email_link',
            'entity_id': link_id,
            'user_id': user_id,
            'old_values': old_values or {},
            'new_values': new_values or {},
            'signature': signature,
        }).execute()
        logger.info(f"[audit] {action} link={link_id[:8]} user={user_id[:8]} yacht={yacht_id[:8]}")
    except Exception as e:
        logger.error(f"Failed to audit link action: {e}")


async def check_idempotency(
    supabase,
    yacht_id: str,
    idempotency_key: str,
    action: str,
) -> Optional[Dict]:
    """
    Return cached result if idempotent operation was already performed, else None.
    Window: 24 hours (implicit via pms_audit_log retention).
    """
    if not idempotency_key:
        return None
    try:
        result = supabase.table('pms_audit_log').select('new_values').eq(
            'yacht_id', yacht_id
        ).eq('action', action).eq(
            'signature->>idempotency_key', idempotency_key
        ).limit(1).execute()
        if result.data:
            logger.info(f"[idempotency] Cached result for key={idempotency_key[:16]}")
            return result.data[0].get('new_values', {})
        return None
    except Exception as e:
        logger.warning(f"[idempotency] Check failed: {e}")
        return None


async def upsert_email_link(
    supabase,
    yacht_id: str,
    thread_id: str,
    object_type: str,
    object_id: str,
    user_id: str,
    confidence: str = 'user_confirmed',
    suggested_reason: str = 'manual',
) -> Dict:
    """
    Insert a new active link or return the existing one (idempotent).

    Returns: {link_id: str, created: bool}
    Raises: nothing — caller decides how to handle None link_id.
    """
    # Check for existing active link
    existing = supabase.table('email_links').select('id').eq(
        'yacht_id', yacht_id
    ).eq('thread_id', thread_id).eq(
        'object_type', object_type
    ).eq('object_id', object_id).eq('is_active', True).limit(1).execute()

    if existing.data:
        return {'link_id': existing.data[0]['id'], 'created': False}

    result = supabase.table('email_links').insert({
        'yacht_id': yacht_id,
        'thread_id': thread_id,
        'object_type': object_type,
        'object_id': object_id,
        'confidence': confidence,
        'suggested_reason': suggested_reason,
        'accepted_at': utcnow(),
        'accepted_by': user_id,
        'is_active': True,
    }).execute()

    link_id = result.data[0]['id'] if result.data else None
    return {'link_id': link_id, 'created': True}
