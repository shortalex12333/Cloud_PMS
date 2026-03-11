"""
Action Telemetry - Structured Event Logging

Provides telemetry and ledger events for the action execution flow.

Events:
- action_suggestion_viewed: User sees action suggestions
- action_prefill_requested: /v1/actions/prefill called
- action_prefill_completed: Prefill returns
- action_execute_requested: /v1/actions/execute called
- action_execute_completed: Action execution finishes

Usage:
    from action_router.telemetry import log_action_event

    log_action_event("action_execute_completed", {
        "action_id": "create_work_order",
        "user_id": "uuid-...",
        "yacht_id": "uuid-...",
        "status": "success",
        "entity_id": "wo-uuid-...",
        "duration_ms": 234,
    })
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger("action_telemetry")


def log_action_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Log a structured action telemetry event.

    All events include:
    - event: Event type name
    - timestamp: ISO 8601 timestamp (UTC)
    - Plus all fields from data dict

    Args:
        event_type: One of the defined event types
        data: Event-specific data fields

    Event Types and Required Fields:

    action_suggestion_viewed:
        - user_id: str
        - yacht_id: str
        - query_text: str
        - suggested_actions: List[str] (action_ids)

    action_prefill_requested:
        - user_id: str
        - yacht_id: str
        - action_id: str
        - query_text: str
        - extracted_entities: Dict[str, Any]

    action_prefill_completed:
        - action_id: str
        - user_id: str
        - yacht_id: str
        - ready_to_commit: bool
        - disambiguation_required: bool
        - missing_fields: List[str]
        - duration_ms: int (optional)

    action_execute_requested:
        - user_id: str
        - yacht_id: str
        - action_id: str
        - payload_keys: List[str]

    action_execute_completed:
        - action_id: str
        - user_id: str
        - yacht_id: str
        - status: str ("success" or "error")
        - entity_id: str (optional, if created)
        - duration_ms: int
        - error_code: str (optional, on error)
    """
    try:
        logger.info(
            event_type,
            extra={
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data
            }
        )
    except Exception as e:
        # Telemetry should never break the main flow
        logger.warning(f"Failed to log telemetry event {event_type}: {e}")


def log_suggestion_viewed(
    user_id: str,
    yacht_id: str,
    query_text: Optional[str],
    suggested_actions: List[str],
) -> None:
    """Log when user sees action suggestions."""
    log_action_event("action_suggestion_viewed", {
        "user_id": user_id,
        "yacht_id": yacht_id,
        "query_text": query_text or "",
        "suggested_actions": suggested_actions,
        "suggestion_count": len(suggested_actions),
    })


def log_prefill_requested(
    user_id: str,
    yacht_id: str,
    action_id: str,
    query_text: str,
    extracted_entities: Dict[str, Any],
) -> None:
    """Log when /v1/actions/prefill is called."""
    log_action_event("action_prefill_requested", {
        "user_id": user_id,
        "yacht_id": yacht_id,
        "action_id": action_id,
        "query_text": query_text,
        "extracted_entities": extracted_entities,
        "entity_count": len(extracted_entities),
    })


def log_prefill_completed(
    action_id: str,
    user_id: str,
    yacht_id: str,
    ready_to_commit: bool,
    disambiguation_required: bool,
    missing_fields: List[str],
    duration_ms: Optional[int] = None,
) -> None:
    """Log when prefill returns."""
    log_action_event("action_prefill_completed", {
        "action_id": action_id,
        "user_id": user_id,
        "yacht_id": yacht_id,
        "ready_to_commit": ready_to_commit,
        "disambiguation_required": disambiguation_required,
        "missing_fields": missing_fields,
        "missing_field_count": len(missing_fields),
        "duration_ms": duration_ms,
    })


def log_execute_requested(
    user_id: str,
    yacht_id: str,
    action_id: str,
    payload_keys: List[str],
) -> None:
    """Log when /v1/actions/execute is called."""
    log_action_event("action_execute_requested", {
        "user_id": user_id,
        "yacht_id": yacht_id,
        "action_id": action_id,
        "payload_keys": payload_keys,
        "payload_field_count": len(payload_keys),
    })


def log_execute_completed(
    action_id: str,
    user_id: str,
    yacht_id: str,
    status: str,
    duration_ms: int,
    entity_id: Optional[str] = None,
    error_code: Optional[str] = None,
) -> None:
    """Log when action execution finishes."""
    data = {
        "action_id": action_id,
        "user_id": user_id,
        "yacht_id": yacht_id,
        "status": status,
        "duration_ms": duration_ms,
    }
    if entity_id:
        data["entity_id"] = entity_id
    if error_code:
        data["error_code"] = error_code

    log_action_event("action_execute_completed", data)


__all__ = [
    "log_action_event",
    "log_suggestion_viewed",
    "log_prefill_requested",
    "log_prefill_completed",
    "log_execute_requested",
    "log_execute_completed",
]
