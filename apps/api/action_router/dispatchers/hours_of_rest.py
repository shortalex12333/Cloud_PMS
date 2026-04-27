"""Hours of Rest domain action handlers (MLC 2006 / STCW compliance)."""

from typing import Dict, Any
import logging
from integrations.supabase import get_supabase_client
from handlers.hours_of_rest_handlers import HoursOfRestHandlers

logger = logging.getLogger(__name__)

_hours_of_rest_handlers = None


def _get_hor_handlers():
    global _hours_of_rest_handlers
    if _hours_of_rest_handlers is None:
        _hours_of_rest_handlers = HoursOfRestHandlers(get_supabase_client())
    return _hours_of_rest_handlers


async def _hor_get_records(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().get_hours_of_rest(
        entity_id=params.get("user_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _hor_upsert_record(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().upsert_hours_of_rest(
        entity_id=params["user_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_list_signoffs(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().list_monthly_signoffs(
        entity_id=params.get("user_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _hor_get_signoff(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().get_monthly_signoff(
        entity_id=params["signoff_id"],
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _hor_create_signoff(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().create_monthly_signoff(
        entity_id=params["user_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_sign_signoff(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().sign_monthly_signoff(
        entity_id=params["signoff_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_list_templates(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().list_crew_templates(
        entity_id=params.get("user_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _hor_create_template(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().create_crew_template(
        entity_id=params["user_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_apply_template(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().apply_crew_template(
        entity_id=params["user_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_list_warnings(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().list_crew_warnings(
        entity_id=params.get("user_id") or params.get("entity_id"),
        yacht_id=params["yacht_id"],
        params=params,
    )


async def _hor_acknowledge_warning(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().acknowledge_warning(
        entity_id=params["warning_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


async def _hor_dismiss_warning(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_hor_handlers().dismiss_warning(
        entity_id=params["warning_id"],
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        payload=params,
    )


HANDLERS: Dict[str, Any] = {
    "get_hours_of_rest": _hor_get_records,
    "upsert_hours_of_rest": _hor_upsert_record,
    "list_monthly_signoffs": _hor_list_signoffs,
    "get_monthly_signoff": _hor_get_signoff,
    "create_monthly_signoff": _hor_create_signoff,
    "sign_monthly_signoff": _hor_sign_signoff,
    "list_crew_templates": _hor_list_templates,
    "create_crew_template": _hor_create_template,
    "apply_crew_template": _hor_apply_template,
    "apply_template": _hor_apply_template,  # alias
    "list_crew_warnings": _hor_list_warnings,
    "acknowledge_warning": _hor_acknowledge_warning,
    "dismiss_warning": _hor_dismiss_warning,
}
