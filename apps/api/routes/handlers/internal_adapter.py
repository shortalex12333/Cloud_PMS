"""
Internal Adapter — bridges INTERNAL_HANDLERS (flat params dict) to Phase 4
calling convention (payload, context, yacht_id, user_id, user_context, db_client).

This is a migration shim. As handlers get rewritten to Phase 4 native, entries
here should be removed and replaced with direct handlers in their domain files.
"""

from typing import Any, Dict, Callable

# IMPORTANT: Do NOT import INTERNAL_HANDLERS at module level.
# It causes a circular import: index → handlers → routes/handlers/__init__ → this file.
# Instead, import lazily inside each adapter call.

# Soft-delete actions require entity_type in params (for universal_handlers.soft_delete_entity).
# The adapter must inject it since resolve_entity_context only maps entity_id → domain key.
_SOFT_DELETE_ENTITY_TYPES: Dict[str, str] = {
    "archive_part": "part",
    "delete_part": "part",
    "archive_document": "document",
}


def _make_adapter(action_id: str) -> Callable:
    """
    Create a Phase 4 adapter for an INTERNAL_HANDLERS function.

    Phase 4 signature: (payload, context, yacht_id, user_id, user_context, db_client) -> dict
    INTERNAL_HANDLERS signature: (params: dict) -> dict
    """
    async def _adapted(
        payload: dict,
        context: dict,
        yacht_id: str,
        user_id: str,
        user_context: dict,
        db_client: Any,
    ) -> dict:
        # Lazy import to avoid circular dependency
        from action_router.dispatchers.index import INTERNAL_HANDLERS
        handler_fn = INTERNAL_HANDLERS[action_id]
        # Merge into flat params dict expected by legacy handlers
        # Context contains resolved entity keys (e.g. entity_id → receiving_id)
        params = {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "user_context": user_context,
            "role": user_context.get("role", ""),
            **context,
            **payload,
        }
        # Inject entity_type for soft-delete actions (soft_delete_entity requires it)
        if action_id in _SOFT_DELETE_ENTITY_TYPES:
            params.setdefault("entity_type", _SOFT_DELETE_ENTITY_TYPES[action_id])
        return await handler_fn(params)

    _adapted.__name__ = f"adapted_{action_id}"
    _adapted.__doc__ = f"Phase 4 adapter for INTERNAL_HANDLERS['{action_id}']"
    return _adapted


# Actions served via INTERNAL_HANDLERS (class-based handlers) not yet rewritten
# to Phase 4 flat-function style. Equipment/fault/WO/warranty actions have been migrated;
# only document and parts actions remain here.
_ACTIONS_TO_ADAPT = [
    # Document domain (served by DocumentHandlers via dispatchers/document.py)
    "add_document_comment",
    "add_document_note",
    "archive_document",
    "delete_document_comment",
    "list_document_comments",
    "open_document",
    "update_document_comment",
    "view_document",
    # Parts domain (served by PartHandlers via dispatchers/parts.py)
    "add_note",
    "add_part_note",
    "archive_part",
    "delete_part",
    "suggest_parts",
    "reorder_part",
    "update_part_details",
]

HANDLERS: Dict[str, Callable] = {
    action_id: _make_adapter(action_id)
    for action_id in _ACTIONS_TO_ADAPT
}
