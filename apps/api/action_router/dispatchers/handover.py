"""Handover domain dispatcher — thin param-unpack wrapper over handlers/handover_handlers.py."""

from typing import Dict, Any
from integrations.supabase import get_supabase_client
from handlers.handover_handlers import (
    add_to_handover,
    add_document_to_handover,
    add_predictive_insight_to_handover,
    edit_handover_section,
    export_handover,
    regenerate_handover_summary,
    sign_handover,
    archive_handover,
)


def _ctx(params: Dict[str, Any]) -> tuple:
    """Unpack (payload, context, yacht_id, user_id, user_context, db_client) from params."""
    context = {
        "entity_id": params.get("entity_id"),
        "entity_type": params.get("entity_type"),
        "action_id": params.get("action_id"),
    }
    user_context = {
        "user_id": params.get("user_id"),
        "role": params.get("user_role"),
    }
    return (
        params,
        context,
        params["yacht_id"],
        params.get("user_id", ""),
        user_context,
        get_supabase_client(),
    )


async def _add_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await add_to_handover(*_ctx(params))


async def _add_document_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await add_document_to_handover(*_ctx(params))


async def _add_predictive_insight_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await add_predictive_insight_to_handover(*_ctx(params))


async def _edit_handover_section(params: Dict[str, Any]) -> Dict[str, Any]:
    return await edit_handover_section(*_ctx(params))


async def _export_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await export_handover(*_ctx(params))


async def _regenerate_handover_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    return await regenerate_handover_summary(*_ctx(params))


async def _sign_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await sign_handover(*_ctx(params))


async def _archive_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    return await archive_handover(*_ctx(params))


HANDLERS: Dict[str, Any] = {
    "add_to_handover": _add_to_handover,
    "add_document_to_handover": _add_document_to_handover,
    "add_predictive_insight_to_handover": _add_predictive_insight_to_handover,
    "edit_handover_section": _edit_handover_section,
    "export_handover": _export_handover,
    "regenerate_handover_summary": _regenerate_handover_summary,
    "sign_handover": _sign_handover,
    "archive_handover": _archive_handover,
}
