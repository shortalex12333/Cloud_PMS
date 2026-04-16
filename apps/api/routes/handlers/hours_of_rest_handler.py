"""
Hours of Rest Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 4).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

DELEGATION PATTERN: The Crew Lens v3 actions (get_hours_of_rest, upsert_hours_of_rest,
monthly signoff, crew templates, warnings) delegate to the existing
handlers.hours_of_rest_handlers.HoursOfRestHandlers class. This handler module is a
thin adapter that translates the Phase 4 handler contract into the existing class API.

INLINE PATTERN: The Tier 6 actions (view_hours_of_rest, update_hours_of_rest,
export_hours_of_rest) were inline in p0_actions_routes.py with direct DB queries.
They are copied verbatim here.

NOTE: The original elif blocks used get_user_scoped_client(authorization, ...) for RLS
enforcement. The Phase 4 dispatcher passes a service-role db_client. The HoursOfRestHandlers
class accepts any Supabase client — RLS enforcement will be addressed when the dispatcher
evolves to support user-scoped clients.
"""
from datetime import datetime, timezone
import uuid as uuid_module
import logging

from fastapi import HTTPException
from supabase import Client

from handlers.hours_of_rest_handlers import HoursOfRestHandlers

logger = logging.getLogger(__name__)


# ============================================================================
# TIER 6: view_hours_of_rest  (was L4123-4163 — inline)
# ============================================================================
async def view_hours_of_rest(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    crew_id = payload.get("crew_id")

    if not crew_id:
        raise HTTPException(status_code=400, detail="crew_id is required")

    try:
        query = db_client.table("hours_of_rest").select(
            "id, crew_id, date, rest_hours, work_hours, created_at"
        ).eq("crew_id", crew_id).eq("yacht_id", yacht_id)

        start_date = payload.get("start_date")
        end_date = payload.get("end_date")

        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)

        records = query.order("date", desc=True).limit(30).execute()

        return {
            "status": "success",
            "success": True,
            "crew_id": crew_id,
            "records": records.data or [],
            "count": len(records.data) if records.data else 0
        }
    except Exception:
        # Table may not exist
        return {
            "status": "success",
            "success": True,
            "crew_id": crew_id,
            "records": [],
            "count": 0,
            "message": "Hours of rest tracking not yet configured"
        }


# ============================================================================
# TIER 6: update_hours_of_rest  (was L4165-4226 — inline)
# ============================================================================
async def update_hours_of_rest(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    crew_id = payload.get("crew_id")
    date = payload.get("date")
    hours = payload.get("hours")
    rest_hours = payload.get("rest_hours", hours)
    work_hours = payload.get("work_hours", 24 - float(hours) if hours else None)

    if not crew_id:
        raise HTTPException(status_code=400, detail="crew_id is required")
    if not date:
        raise HTTPException(status_code=400, detail="date is required")
    if hours is None:
        raise HTTPException(status_code=400, detail="hours is required")

    try:
        # Try upsert
        record_data = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "crew_id": crew_id,
            "date": date,
            "rest_hours": float(rest_hours),
            "work_hours": float(work_hours) if work_hours else 24 - float(rest_hours),
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Check if record exists
        existing = db_client.table("hours_of_rest").select("id").eq(
            "crew_id", crew_id
        ).eq("date", date).maybe_single().execute()

        if existing.data:
            db_client.table("hours_of_rest").update({
                "rest_hours": float(rest_hours),
                "work_hours": float(work_hours) if work_hours else 24 - float(rest_hours),
                "updated_by": user_id
            }).eq("id", existing.data["id"]).execute()
        else:
            record_data["created_by"] = user_id
            db_client.table("hours_of_rest").insert(record_data).execute()

        return {
            "status": "success",
            "success": True,
            "message": f"Hours of rest updated for {date}",
            "crew_id": crew_id,
            "date": date,
            "rest_hours": float(rest_hours)
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Hours of rest tracking not yet configured",
            "crew_id": crew_id
        }


# ============================================================================
# TIER 6: export_hours_of_rest  (was L4228-4261 — inline)
# ============================================================================
async def export_hours_of_rest(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    crew_id = payload.get("crew_id")
    export_format = payload.get("format", "csv")

    if not crew_id:
        raise HTTPException(status_code=400, detail="crew_id is required")

    try:
        records = db_client.table("hours_of_rest").select(
            "date, rest_hours, work_hours, created_at"
        ).eq("crew_id", crew_id).eq("yacht_id", yacht_id).order(
            "date", desc=True
        ).limit(90).execute()

        return {
            "status": "success",
            "success": True,
            "crew_id": crew_id,
            "records": records.data or [],
            "export_format": export_format,
            "message": f"Ready for {export_format} export"
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "crew_id": crew_id,
            "records": [],
            "export_format": export_format,
            "message": "No hours of rest data available"
        }




# ============================================================================
# get_hours_of_rest  (was L5176-5222 — delegates to HoursOfRestHandlers)
# ============================================================================
async def get_hours_of_rest(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR] Dispatching 'get_hours_of_rest' - yacht_id={yacht_id}, user_id={user_id}")

    hor = HoursOfRestHandlers(db_client)

    # Extract target user (defaults to current user)
    target_user_id = payload.get("user_id", user_id)

    # Build params dict (only include dates if provided)
    handler_params = {"user_id": target_user_id}
    if "start_date" in payload:
        handler_params["start_date"] = payload["start_date"]
    if "end_date" in payload:
        handler_params["end_date"] = payload["end_date"]

    return await hor.get_hours_of_rest(
        entity_id=target_user_id,
        yacht_id=yacht_id,
        params=handler_params
    )


# ============================================================================
# upsert_hours_of_rest  (was L5176-5222 — delegates to HoursOfRestHandlers)
# ============================================================================
async def upsert_hours_of_rest(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR] Dispatching 'upsert_hours_of_rest' - yacht_id={yacht_id}, user_id={user_id}")

    hor = HoursOfRestHandlers(db_client)

    target_user_id = payload.get("user_id", user_id)

    # Add context fields to payload
    payload["user_id"] = target_user_id
    payload["user_role"] = user_context.get("role")
    payload["user_name"] = user_context.get("name", "Unknown")

    return await hor.upsert_hours_of_rest(
        entity_id=target_user_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# get_monthly_signoff  (was L5225-5262 — delegates to HoursOfRestHandlers)
# ============================================================================
async def get_monthly_signoff(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_SIGNOFF] Dispatching 'get_monthly_signoff' - yacht_id={yacht_id}")

    signoff_id = payload.get("signoff_id")
    if not signoff_id:
        raise HTTPException(status_code=400, detail="signoff_id is required")

    hor = HoursOfRestHandlers(db_client)

    return await hor.get_monthly_signoff(
        entity_id=signoff_id,
        yacht_id=yacht_id,
        params=payload
    )


# ============================================================================
# list_monthly_signoffs  (was L5225-5262 — delegates to HoursOfRestHandlers)
# ============================================================================
async def list_monthly_signoffs(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_SIGNOFF] Dispatching 'list_monthly_signoffs' - yacht_id={yacht_id}")

    hor = HoursOfRestHandlers(db_client)

    params_with_role = {**(payload or {}), "_caller_role": user_context.get("role", "")}
    return await hor.list_monthly_signoffs(
        entity_id=user_id,
        yacht_id=yacht_id,
        params=params_with_role
    )


# ============================================================================
# create_monthly_signoff  (was L5225-5262 — delegates to HoursOfRestHandlers)
# ============================================================================
async def create_monthly_signoff(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_SIGNOFF] Dispatching 'create_monthly_signoff' - yacht_id={yacht_id}")

    # BUG-HOR-5 fix: fleet manager is read-only for HoR — block at dispatcher level
    if user_context.get("role") == "manager":
        return {
            "success": False,
            "action_id": "create_monthly_signoff",
            "error": {
                "code": "FORBIDDEN",
                "message": "Fleet manager has read-only access to hours of rest. Cannot create sign-offs.",
                "status_code": 403,
            }
        }

    hor = HoursOfRestHandlers(db_client)

    return await hor.create_monthly_signoff(
        entity_id=user_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# sign_monthly_signoff  (was L5225-5262 — delegates to HoursOfRestHandlers)
# ============================================================================
async def sign_monthly_signoff(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    logger.info(f"[HOR_SIGNOFF] Dispatching 'sign_monthly_signoff' - yacht_id={yacht_id}")

    signoff_id = payload.get("signoff_id")
    if not signoff_id:
        raise HTTPException(status_code=400, detail="signoff_id is required")

    hor = HoursOfRestHandlers(db_client)

    return await hor.sign_monthly_signoff(
        entity_id=signoff_id,
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload
    )


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Tier 6 — inline HoR (direct DB)
    "view_hours_of_rest":       view_hours_of_rest,
    "update_hours_of_rest":     update_hours_of_rest,
    "export_hours_of_rest":     export_hours_of_rest,
    # Crew Lens v3 — delegation to HoursOfRestHandlers
    "get_hours_of_rest":        get_hours_of_rest,
    "upsert_hours_of_rest":     upsert_hours_of_rest,
    "get_monthly_signoff":      get_monthly_signoff,
    "list_monthly_signoffs":    list_monthly_signoffs,
    "create_monthly_signoff":   create_monthly_signoff,
    "sign_monthly_signoff":     sign_monthly_signoff,
}
