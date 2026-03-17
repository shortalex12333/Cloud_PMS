"""
Ledger helper — shared by dispatcher and all handler files.
Extracted from p0_actions_routes.py to avoid circular imports.
"""

import hashlib
import json
from datetime import datetime


def build_ledger_event(
    yacht_id: str,
    user_id: str,
    event_type: str,  # Must be: create, update, delete, status_change, assignment, etc.
    entity_type: str,  # e.g., 'work_order', 'fault', 'equipment'
    entity_id: str,
    action: str,  # e.g., 'add_note', 'add_checklist_item'
    user_role: str = None,
    change_summary: str = None,
    metadata: dict = None,
    department: str = None,
    actor_name: str = None,
    event_category: str = "write"
) -> dict:
    """Build a ledger event with correct schema for ledger_events table.

    Required columns (NOT NULL):
    - yacht_id, event_type, entity_type, entity_id, action, user_id, proof_hash

    event_type must be one of:
    - create, update, delete, status_change, assignment, approval, rejection,
      escalation, handover, import, export
    """
    event_data = {
        "yacht_id": str(yacht_id),
        "user_id": str(user_id),
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "action": action,
        "source_context": "microaction",
        "metadata": metadata or {},
    }

    if user_role:
        event_data["user_role"] = user_role
    if change_summary:
        event_data["change_summary"] = change_summary
    if department:
        event_data["department"] = department
    if actor_name:
        event_data["actor_name"] = actor_name
    event_data["event_category"] = event_category or "write"

    # Generate proof_hash (SHA-256 of event data)
    hash_input = json.dumps({
        "yacht_id": event_data["yacht_id"],
        "user_id": event_data["user_id"],
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }, sort_keys=True)
    event_data["proof_hash"] = hashlib.sha256(hash_input.encode()).hexdigest()

    return event_data
