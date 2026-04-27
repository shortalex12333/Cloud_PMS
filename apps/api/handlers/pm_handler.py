"""
Preventive Maintenance (PM) Action Handlers

Migrated from p0_actions_routes.py elif block (Phase 4, Task 5).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

Block (L2540-2545): create_pm_schedule, record_pm_completion, defer_pm_task,
    update_pm_schedule, view_pm_due_list
    — BLOCKED: pms_maintenance_schedules table does not exist in tenant DB.
"""
import logging

from fastapi import HTTPException
from supabase import Client

logger = logging.getLogger(__name__)


# ============================================================================
# BLOCKED ACTIONS (L2540-2545) — table does not exist yet
# ============================================================================

async def create_pm_schedule(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'create_pm_schedule' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
    )


async def record_pm_completion(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'record_pm_completion' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
    )


async def defer_pm_task(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'defer_pm_task' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
    )


async def update_pm_schedule(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'update_pm_schedule' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
    )


async def view_pm_due_list(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'view_pm_due_list' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
    )


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    "create_pm_schedule": create_pm_schedule,
    "record_pm_completion": record_pm_completion,
    "defer_pm_task": defer_pm_task,
    "update_pm_schedule": update_pm_schedule,
    "view_pm_due_list": view_pm_due_list,
}
