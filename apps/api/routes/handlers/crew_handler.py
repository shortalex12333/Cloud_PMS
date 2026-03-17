"""
Crew Action Handlers (Templates + Warnings)

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 4).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

DELEGATION PATTERN: These actions delegate to the existing
handlers.hours_of_rest_handlers.HoursOfRestHandlers class, which owns
crew templates and compliance warnings as part of the Hours of Rest domain.
This handler module is a thin adapter that translates the Phase 4 handler
contract into the existing class API.

NOTE: The original elif blocks used get_user_scoped_client(authorization, ...) for RLS
enforcement. The Phase 4 dispatcher passes a service-role db_client. The HoursOfRestHandlers
class accepts any Supabase client — RLS enforcement will be addressed when the dispatcher
evolves to support user-scoped clients.
"""
import logging

from supabase import Client

from handlers.hours_of_rest_handlers import HoursOfRestHandlers

logger = logging.getLogger(__name__)


# ============================================================================
# DELEGATION HELPER
# ============================================================================

def _hor_instance(db_client: Client) -> HoursOfRestHandlers:
    """Create HoursOfRestHandlers bound to the dispatcher's db_client."""
    return HoursOfRestHandlers(db_client)


# ============================================================================
# create_crew_template  (was L5265-5295 — delegates to HoursOfRestHandlers)
# ============================================================================
async def create_crew_template(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_TEMPLATE] Dispatching 'create_crew_template' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)

    return await hor.create_crew_template(
        entity_id=user_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# apply_crew_template  (was L5265-5295 — delegates to HoursOfRestHandlers)
# ============================================================================
async def apply_crew_template(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_TEMPLATE] Dispatching 'apply_crew_template' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)

    return await hor.apply_crew_template(
        entity_id=user_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# list_crew_templates  (was L5265-5295 — delegates to HoursOfRestHandlers)
# ============================================================================
async def list_crew_templates(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_TEMPLATE] Dispatching 'list_crew_templates' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)

    return await hor.list_crew_templates(
        entity_id=user_id,
        yacht_id=yacht_id,
        params=payload
    )


# ============================================================================
# list_crew_warnings  (was L5298-5334 — delegates to HoursOfRestHandlers)
# ============================================================================
async def list_crew_warnings(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_WARNING] Dispatching 'list_crew_warnings' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)

    return await hor.list_crew_warnings(
        entity_id=user_id,
        yacht_id=yacht_id,
        params=payload
    )


# ============================================================================
# acknowledge_warning  (was L5298-5334 — delegates to HoursOfRestHandlers)
# ============================================================================
async def acknowledge_warning(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_WARNING] Dispatching 'acknowledge_warning' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)
    warning_id = payload.get("warning_id")

    return await hor.acknowledge_warning(
        entity_id=warning_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# dismiss_warning  (was L5298-5334 — delegates to HoursOfRestHandlers)
# ============================================================================
async def dismiss_warning(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_WARNING] Dispatching 'dismiss_warning' - yacht_id={yacht_id}")

    hor = _hor_instance(db_client)
    warning_id = payload.get("warning_id")

    return await hor.dismiss_warning(
        entity_id=warning_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Crew templates (HoR domain)
    "create_crew_template":     create_crew_template,
    "apply_crew_template":      apply_crew_template,
    "list_crew_templates":      list_crew_templates,
    # Crew warnings (HoR domain)
    "list_crew_warnings":       list_crew_warnings,
    "acknowledge_warning":      acknowledge_warning,
    "dismiss_warning":          dismiss_warning,
}
