"""Hours of Rest dispatcher — adapts INTERNAL_HANDLERS (params: dict) to Phase 4 wrappers."""

from typing import Dict, Any
from integrations.supabase import get_supabase_client
from handlers.hours_of_rest_handlers import HANDLERS as _p4


def _adapt(p4_handler):
    """Wrap a Phase 4 handler to accept the old-style (params: dict) calling convention."""
    async def _dispatch(params: Dict[str, Any]) -> Dict[str, Any]:
        context = {
            "entity_id": params.get("entity_id"),
            "entity_type": params.get("entity_type"),
            "action_id": params.get("action_id"),
        }
        user_context = {
            "user_id": params.get("user_id"),
            "role": params.get("user_role"),
        }
        return await p4_handler(
            payload=params,
            context=context,
            yacht_id=params["yacht_id"],
            user_id=params.get("user_id", ""),
            user_context=user_context,
            db_client=get_supabase_client(),
        )
    return _dispatch


HANDLERS: Dict[str, Any] = {action_id: _adapt(fn) for action_id, fn in _p4.items()}
