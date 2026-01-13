"""
P0 Actions Routes
=================

FastAPI routes for 8 P0 actions.

Endpoints:
- GET  /v1/actions/{action_name}/prefill - Pre-fill form data (MUTATE actions only)
- POST /v1/actions/{action_name}/preview - Preview changes before commit (MUTATE actions only)
- POST /v1/actions/execute - Execute action (all actions)

All routes require JWT authentication and yacht isolation validation.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
from handlers.inventory_handlers import InventoryHandlers
from handlers.handover_handlers import HandoverHandlers
from handlers.manual_handlers import ManualHandlers
from action_router.validators import validate_jwt, validate_yacht_isolation
from middleware.auth import lookup_tenant_for_user

logger = logging.getLogger(__name__)

# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    # Support both naming conventions (Render uses SUPABASE_URL, frontend uses NEXT_PUBLIC_*)
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("Missing Supabase credentials")

    return create_client(url, key)


def get_tenant_supabase_client(tenant_key_alias: str) -> Client:
    """Get tenant-specific Supabase client instance.

    Routing contract:
    - tenant_key_alias comes from MASTER DB fleet_registry (e.g., 'yTEST_YACHT_001')
    - Env vars on Render: {tenant_key_alias}_SUPABASE_URL, {tenant_key_alias}_SUPABASE_SERVICE_KEY
    - Example: yTEST_YACHT_001_SUPABASE_URL, yTEST_YACHT_001_SUPABASE_SERVICE_KEY
    """
    if not tenant_key_alias:
        raise ValueError("tenant_key_alias is required for tenant DB access")

    url = os.getenv(f"{tenant_key_alias}_SUPABASE_URL")
    key = os.getenv(f"{tenant_key_alias}_SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(f"Missing tenant credentials for {tenant_key_alias}. "
                        f"Expected: {tenant_key_alias}_SUPABASE_URL and {tenant_key_alias}_SUPABASE_SERVICE_KEY")

    return create_client(url, key)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/actions", tags=["p0-actions"])

# Initialize handlers
try:
    supabase = get_supabase_client()
    wo_handlers = WorkOrderMutationHandlers(supabase)
    inventory_handlers = InventoryHandlers(supabase)
    handover_handlers = HandoverHandlers(supabase)
    manual_handlers = ManualHandlers(supabase)
    logger.info("✅ All P0 action handlers initialized")
except Exception as e:
    logger.error(f"Failed to initialize handlers: {e}")
    wo_handlers = None
    inventory_handlers = None
    handover_handlers = None
    manual_handlers = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class PrefillRequest(BaseModel):
    """Query parameters for prefill endpoint."""
    fault_id: Optional[str] = Field(None, description="Fault ID (for create_work_order_from_fault)")
    work_order_id: Optional[str] = Field(None, description="Work order ID")
    part_id: Optional[str] = Field(None, description="Part ID")
    equipment_id: Optional[str] = Field(None, description="Equipment ID")


class PreviewRequest(BaseModel):
    """Request body for preview endpoint."""
    context: Dict[str, Any] = Field(..., description="Yacht ID, user ID, role")
    payload: Dict[str, Any] = Field(..., description="Action-specific parameters")


class ActionExecuteRequest(BaseModel):
    """Request body for execute endpoint."""
    action: str = Field(..., description="Action name")
    context: Dict[str, Any] = Field(..., description="Yacht ID, user ID, role")
    payload: Dict[str, Any] = Field(..., description="Action-specific parameters")


# ============================================================================
# PREFILL ENDPOINTS
# ============================================================================

@router.get("/create_work_order_from_fault/prefill")
async def create_work_order_from_fault_prefill(
    fault_id: str,
    authorization: str = Header(None)
):
    """
    Pre-fill work order form from fault data.

    Returns:
    - Pre-filled form data (title, equipment, location, description, priority)
    - Duplicate check (existing WO for this fault)
    """
    # Validate JWT
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]
    user_id = user_context["user_id"]

    # Call handler
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.create_work_order_from_fault_prefill(fault_id, yacht_id, user_id)

    if result["status"] == "error":
        raise HTTPException(
            status_code=400 if result["error_code"] == "FAULT_NOT_FOUND" else 500,
            detail=result["message"]
        )

    return result


@router.get("/add_note_to_work_order/prefill")
async def add_note_to_work_order_prefill(
    work_order_id: str,
    authorization: str = Header(None)
):
    """Pre-fill data for add note to work order."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]

    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.add_note_to_work_order_prefill(work_order_id, yacht_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/add_part_to_work_order/prefill")
async def add_part_to_work_order_prefill(
    work_order_id: str,
    part_id: str,
    authorization: str = Header(None)
):
    """Pre-fill data for add part to work order."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]

    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.add_part_to_work_order_prefill(work_order_id, part_id, yacht_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/mark_work_order_complete/prefill")
async def mark_work_order_complete_prefill(
    work_order_id: str,
    authorization: str = Header(None)
):
    """Pre-fill data for mark work order complete."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]
    user_id = user_context["user_id"]

    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.mark_work_order_complete_prefill(work_order_id, yacht_id, user_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


# ============================================================================
# PREVIEW ENDPOINTS
# ============================================================================

@router.post("/mark_work_order_complete/preview")
async def mark_work_order_complete_preview(
    request: PreviewRequest,
    authorization: str = Header(None)
):
    """Preview work order completion."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Validate yacht isolation
    yacht_result = validate_yacht_isolation(request.context, user_context)
    if not yacht_result.valid:
        raise HTTPException(status_code=403, detail=yacht_result.error.message)

    # Extract parameters
    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    # Call handler
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.mark_work_order_complete_preview(
        work_order_id=payload["work_order_id"],
        completion_notes=payload["completion_notes"],
        parts_used=payload.get("parts_used", []),
        signature=payload["signature"],
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/add_part_to_work_order/preview")
async def add_part_to_work_order_preview(
    request: PreviewRequest,
    authorization: str = Header(None)
):
    """Preview adding part to work order."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Validate yacht isolation
    yacht_result = validate_yacht_isolation(request.context, user_context)
    if not yacht_result.valid:
        raise HTTPException(status_code=403, detail=yacht_result.error.message)

    # Extract parameters
    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    # Call handler
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.add_part_to_work_order_preview(
        work_order_id=payload["work_order_id"],
        part_id=payload["part_id"],
        quantity=payload["quantity"],
        notes=payload.get("notes"),
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/create_work_order_from_fault/preview")
async def create_work_order_from_fault_preview(
    request: PreviewRequest,
    authorization: str = Header(None)
):
    """
    Preview work order creation.

    Shows:
    - What will be created
    - All side effects
    - Warnings (if any)
    """
    # Validate JWT
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Validate yacht isolation
    yacht_result = validate_yacht_isolation(request.context, user_context)
    if not yacht_result.valid:
        raise HTTPException(status_code=403, detail=yacht_result.error.message)

    # Extract parameters
    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    # Call handler
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await wo_handlers.create_work_order_from_fault_preview(
        fault_id=payload["fault_id"],
        title=payload["title"],
        equipment_id=payload.get("equipment_id"),
        location=payload.get("location"),
        description=payload.get("description"),
        priority=payload["priority"],
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


# ============================================================================
# EXECUTE ENDPOINT (All Actions)
# ============================================================================

@router.post("/execute")
async def execute_action(
    request: ActionExecuteRequest,
    authorization: str = Header(None)
):
    """
    Execute an action.

    This is the unified endpoint for all P0 actions.
    Routes to appropriate handler based on action name.
    """
    # Validate JWT
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Resolve tenant from MASTER DB if yacht_id not in JWT
    if not user_context.get("yacht_id") and lookup_tenant_for_user:
        tenant_info = lookup_tenant_for_user(user_context["user_id"])
        if tenant_info:
            user_context["yacht_id"] = tenant_info["yacht_id"]
            user_context["tenant_key_alias"] = tenant_info.get("tenant_key_alias")
            user_context["role"] = tenant_info.get("role", user_context.get("role"))
        else:
            raise HTTPException(status_code=403, detail="User is not assigned to any yacht/tenant")

    # Validate yacht isolation
    yacht_result = validate_yacht_isolation(request.context, user_context)
    if not yacht_result.valid:
        raise HTTPException(status_code=403, detail=yacht_result.error.message)

    action = request.action
    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    # Route to handler based on action name
    try:
        # ===== WORK ORDER ACTIONS (P0 Actions 2-5) =====
        if action == "create_work_order_from_fault":
            # Use tenant client directly (wo_handlers may not be available)
            from datetime import datetime, timezone
            import uuid
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Get fault info
            fault = db_client.table("pms_faults").select("*").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not fault.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            # Check for duplicate WO
            existing = db_client.table("pms_work_orders").select("id").eq("fault_id", fault_id).execute()
            if existing.data and not payload.get("override_duplicate", False):
                result = {
                    "status": "error",
                    "error_code": "DUPLICATE_WO_EXISTS",
                    "message": f"Work order already exists for this fault"
                }
            else:
                # Create work order
                wo_data = {
                    "yacht_id": yacht_id,
                    "fault_id": fault_id,
                    "equipment_id": payload.get("equipment_id") or fault.data.get("equipment_id"),
                    "title": payload.get("title", fault.data.get("title", "Work order from fault")),
                    "description": payload.get("description", fault.data.get("description", "")),
                    "priority": payload.get("priority", "normal"),
                    "status": "pending",
                    "created_by": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
                if wo_result.data:
                    wo_id = wo_result.data[0]["id"]
                    # Link WO to fault
                    db_client.table("pms_faults").update({
                        "work_order_id": wo_id,
                        "updated_by": user_id,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

                    result = {
                        "status": "success",
                        "work_order_id": wo_id,
                        "message": "Work order created from fault"
                    }
                else:
                    result = {
                        "status": "error",
                        "error_code": "INSERT_FAILED",
                        "message": "Failed to create work order"
                    }

        elif action == "add_note_to_work_order":
            if not wo_handlers:
                raise HTTPException(status_code=500, detail="Work order handlers not initialized")
            result = await wo_handlers.add_note_to_work_order_execute(
                work_order_id=payload["work_order_id"],
                note_text=payload["note_text"],
                note_type=payload.get("note_type", "general"),
                yacht_id=yacht_id,
                user_id=user_id
            )

        elif action == "add_part_to_work_order":
            if not wo_handlers:
                raise HTTPException(status_code=500, detail="Work order handlers not initialized")
            result = await wo_handlers.add_part_to_work_order_execute(
                work_order_id=payload["work_order_id"],
                part_id=payload["part_id"],
                quantity=payload["quantity"],
                notes=payload.get("notes"),
                yacht_id=yacht_id,
                user_id=user_id
            )

        elif action == "mark_work_order_complete":
            if not wo_handlers:
                raise HTTPException(status_code=500, detail="Work order handlers not initialized")
            result = await wo_handlers.mark_work_order_complete_execute(
                work_order_id=payload["work_order_id"],
                completion_notes=payload["completion_notes"],
                parts_used=payload.get("parts_used", []),
                signature=payload["signature"],
                yacht_id=yacht_id,
                user_id=user_id
            )

        # ===== INVENTORY ACTIONS (P0 Actions 6-7) =====
        elif action == "check_stock_level":
            if not inventory_handlers:
                raise HTTPException(status_code=500, detail="Inventory handlers not initialized")
            result = await inventory_handlers.check_stock_level_execute(
                part_id=payload["part_id"],
                yacht_id=yacht_id,
                user_id=user_id
            )

        elif action == "log_part_usage":
            if not inventory_handlers:
                raise HTTPException(status_code=500, detail="Inventory handlers not initialized")
            result = await inventory_handlers.log_part_usage_execute(
                part_id=payload["part_id"],
                quantity=payload["quantity"],
                usage_reason=payload["usage_reason"],
                yacht_id=yacht_id,
                user_id=user_id,
                work_order_id=payload.get("work_order_id"),
                equipment_id=payload.get("equipment_id"),
                notes=payload.get("notes")
            )

        # ===== HANDOVER ACTIONS (P0 Action 8) =====
        elif action == "add_to_handover":
            if not handover_handlers:
                raise HTTPException(status_code=500, detail="Handover handlers not initialized")
            result = await handover_handlers.add_to_handover_execute(
                entity_type=payload["entity_type"],
                entity_id=payload["entity_id"],
                summary_text=payload["summary_text"],
                category=payload["category"],
                yacht_id=yacht_id,
                user_id=user_id,
                priority=payload.get("priority", "normal")
            )

        # ===== MANUAL ACTIONS (P0 Action 1) =====
        elif action == "show_manual_section":
            if not manual_handlers:
                raise HTTPException(status_code=500, detail="Manual handlers not initialized")
            result = await manual_handlers.show_manual_section_execute(
                equipment_id=payload["equipment_id"],
                yacht_id=yacht_id,
                user_id=user_id,
                fault_code=payload.get("fault_code"),
                section_id=payload.get("section_id")
            )

        # ===== FAULT ACTIONS =====
        # pms_faults schema: id, yacht_id, equipment_id, fault_code, title, description,
        #                    severity, detected_at, resolved_at, resolved_by, work_order_id,
        #                    metadata, status, created_at, updated_by, updated_at
        # Valid severity values: low, medium, high, critical
        # Valid status values: open, investigating, resolved, closed
        elif action == "report_fault":
            # Validate required fields
            if not payload.get("equipment_id"):
                raise HTTPException(status_code=400, detail="equipment_id is required")
            description = payload.get("description", "")
            if len(description) < 10:
                raise HTTPException(status_code=400, detail="description must be at least 10 characters")

            # Insert fault record
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Ensure severity is valid (default to medium)
            severity = payload.get("severity", "medium")
            if severity not in ("low", "medium", "high", "critical"):
                severity = "medium"

            fault_data = {
                "yacht_id": yacht_id,
                "equipment_id": payload.get("equipment_id"),
                "fault_code": payload.get("fault_code", "MANUAL"),
                "title": payload.get("title", description[:100] if description else "Reported fault"),
                "description": description,
                "severity": severity,
                "status": "open",
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"reported_by": user_id}
            }
            fault_result = db_client.table("pms_faults").insert(fault_data).execute()
            if fault_result.data:
                result = {
                    "status": "success",
                    "fault_id": fault_result.data[0]["id"],
                    "message": "Fault reported successfully"
                }
            else:
                result = {
                    "status": "error",
                    "error_code": "INSERT_FAILED",
                    "message": "Failed to create fault record"
                }

        elif action == "acknowledge_fault":
            # Update fault status to investigating (valid: open, investigating, resolved, closed)
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Check if fault exists (don't select severity to avoid enum errors)
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            # Always include severity in update to fix any bad data
            update_data = {
                "status": "investigating",
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault acknowledged"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to acknowledge fault"}

        elif action == "resolve_fault":
            # Update fault status to resolved
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {
                "status": "resolved",
                "severity": "medium",  # Always set valid severity
                "resolved_by": user_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault resolved"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to resolve fault"}

        elif action == "diagnose_fault":
            # Add diagnosis to fault metadata
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Get current fault metadata (avoid selecting severity to prevent enum errors)
            current = db_client.table("pms_faults").select("id, metadata").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not current.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            metadata = current.data.get("metadata", {}) or {}
            metadata["diagnosis"] = payload.get("diagnosis", "")
            metadata["diagnosed_by"] = user_id
            metadata["diagnosed_at"] = datetime.now(timezone.utc).isoformat()

            update_data = {
                "metadata": metadata,
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Diagnosis added"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add diagnosis"}

        elif action == "close_fault":
            # Close fault (status = closed)
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {
                "status": "closed",
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault closed"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}

        elif action == "update_fault":
            # Update fault details
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {"updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
            if payload.get("title"):
                update_data["title"] = payload["title"]
            if payload.get("description"):
                update_data["description"] = payload["description"]

            # Handle severity - use provided value if valid, otherwise default to medium
            if payload.get("severity") and payload["severity"] in ("low", "medium", "high", "critical"):
                update_data["severity"] = payload["severity"]
            else:
                update_data["severity"] = "medium"  # Always set valid severity

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault updated"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update fault"}

        elif action == "reopen_fault":
            # Reopen a closed fault
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {
                "status": "open",
                "severity": "medium",  # Always set valid severity
                "resolved_at": None,
                "resolved_by": None,
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault reopened"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to reopen fault"}

        elif action == "mark_fault_false_alarm":
            # Mark fault as false alarm (use closed status + metadata)
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Get current fault (avoid selecting severity)
            current = db_client.table("pms_faults").select("id, metadata").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not current.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            metadata = current.data.get("metadata", {}) or {}
            metadata["false_alarm"] = True
            metadata["false_alarm_by"] = user_id
            metadata["false_alarm_at"] = datetime.now(timezone.utc).isoformat()

            update_data = {
                "status": "closed",
                "metadata": metadata,
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Fault marked as false alarm"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to mark as false alarm"}

        elif action == "add_fault_photo":
            # Add photo URL to fault metadata
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            # Get current fault (avoid selecting severity)
            current = db_client.table("pms_faults").select("id, metadata").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not current.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            metadata = current.data.get("metadata", {}) or {}
            photos = metadata.get("photos", [])
            photos.append({"url": payload.get("photo_url"), "added_by": user_id, "added_at": datetime.now(timezone.utc).isoformat()})
            metadata["photos"] = photos

            update_data = {
                "metadata": metadata,
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "message": "Photo added to fault"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add photo"}

        elif action == "view_fault_detail":
            # Get fault details with equipment info
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_result = db_client.table("pms_faults").select("*, pms_equipment(*)").eq("id", payload.get("fault_id")).eq("yacht_id", yacht_id).single().execute()
            if fault_result.data:
                result = {"status": "success", "fault": fault_result.data}
            else:
                result = {"status": "error", "error_code": "NOT_FOUND", "message": "Fault not found"}

        else:
            raise HTTPException(
                status_code=404,
                detail=f"Action '{action}' not found or not implemented"
            )

    except HTTPException:
        # Let HTTPExceptions propagate with their original status code
        raise
    except Exception as e:
        logger.error(f"Action execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # Handle errors from handler
    if result["status"] == "error":
        status_code = 400
        error_code = result.get("error_code", "UNKNOWN_ERROR")

        if error_code in ("FAULT_NOT_FOUND", "WO_NOT_FOUND", "EQUIPMENT_NOT_FOUND", "PART_NOT_FOUND"):
            status_code = 404
        elif error_code in ("INVALID_SIGNATURE", "WO_CLOSED", "DUPLICATE_WO_EXISTS"):
            status_code = 400
        elif error_code in ("INSUFFICIENT_STOCK",):
            status_code = 400

        raise HTTPException(status_code=status_code, detail=result["message"])

    return result


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/handover")
async def get_handover_items(
    yacht_id: Optional[str] = None,
    limit: int = 20,
    category: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    Get handover items for a yacht, sorted by priority and recency.

    Query Parameters:
    - yacht_id: Optional (uses JWT yacht_id if not provided)
    - limit: Maximum number of items to return (default: 20)
    - category: Optional filter by category

    Returns:
    - List of handover items with user names
    - Sorted by priority (desc) and added_at (desc)
    """
    # Validate JWT
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Use yacht_id from JWT if not provided in query
    if not yacht_id:
        yacht_id = user_context.get("yacht_id")

    if not yacht_id:
        raise HTTPException(status_code=400, detail="yacht_id is required")

    # Validate yacht isolation
    if yacht_id != user_context.get("yacht_id"):
        raise HTTPException(status_code=403, detail="Access denied: yacht isolation violation")

    try:
        # Build query
        # Note: Removed users:added_by join as it requires explicit FK relationship
        # User names can be resolved separately if needed
        query = supabase.table("handover").select(
            "id, yacht_id, entity_type, entity_id, summary_text, category, priority, "
            "added_at, added_by"
        ).eq("yacht_id", yacht_id)

        # Apply category filter if provided
        if category:
            query = query.eq("category", category)

        # Order by priority (desc) and added_at (desc)
        query = query.order("priority", desc=True).order("added_at", desc=True)

        # Apply limit
        query = query.limit(limit)

        # Execute query
        result = query.execute()

        if not result.data:
            return {
                "status": "success",
                "items": [],
                "count": 0
            }

        # Transform results to include user names
        items = []
        for item in result.data:
            user_info = item.get("users", {})
            items.append({
                "id": item["id"],
                "entity_type": item["entity_type"],
                "entity_id": item["entity_id"],
                "title": None,  # TODO: Could be fetched from entity if needed
                "summary_text": item["summary_text"],
                "category": item["category"],
                "priority": item["priority"],
                "added_by": item["added_by"],
                "added_by_name": user_info.get("full_name", "Unknown") if user_info else "Unknown",
                "added_at": item["added_at"]
            })

        return {
            "status": "success",
            "items": items,
            "count": len(items)
        }

    except Exception as e:
        logger.error(f"Failed to fetch handover items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch handover items: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for P0 actions routes."""
    handlers_count = sum([
        1 if wo_handlers else 0,
        1 if inventory_handlers else 0,
        1 if handover_handlers else 0,
        1 if manual_handlers else 0
    ])

    return {
        "status": "healthy" if handlers_count == 4 else "degraded",
        "service": "p0_actions",
        "handlers_loaded": handlers_count,
        "total_handlers": 4,
        "handlers": {
            "work_order": wo_handlers is not None,
            "inventory": inventory_handlers is not None,
            "handover": handover_handlers is not None,
            "manual": manual_handlers is not None
        },
        "p0_actions_implemented": 8,
        "version": "1.0.0"
    }


__all__ = ["router"]

# ============================================================================
# ADDITIONAL PREFILL ENDPOINTS (P0 Actions 7 & 8)
# ============================================================================

@router.get("/log_part_usage/prefill")
async def log_part_usage_prefill(
    part_id: str,
    work_order_id: Optional[str] = None,
    authorization: str = Header(None)
):
    """Pre-fill data for log part usage."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]
    user_id = user_context["user_id"]

    if not inventory_handlers:
        raise HTTPException(status_code=500, detail="Inventory handlers not initialized")

    result = await inventory_handlers.log_part_usage_prefill(
        part_id, yacht_id, user_id, work_order_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/add_to_handover/prefill")
async def add_to_handover_prefill(
    entity_type: str,
    entity_id: str,
    authorization: str = Header(None)
):
    """Pre-fill data for add to handover."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context
    yacht_id = user_context["yacht_id"]
    user_id = user_context["user_id"]

    if not handover_handlers:
        raise HTTPException(status_code=500, detail="Handover handlers not initialized")

    result = await handover_handlers.add_to_handover_prefill(
        entity_type, entity_id, yacht_id, user_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


# ============================================================================
# ADDITIONAL PREVIEW ENDPOINTS (P0 Action 7)
# ============================================================================

@router.post("/log_part_usage/preview")
async def log_part_usage_preview(
    request: PreviewRequest,
    authorization: str = Header(None)
):
    """Preview part usage logging."""
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail=jwt_result.error.message)

    user_context = jwt_result.context

    # Validate yacht isolation
    yacht_result = validate_yacht_isolation(request.context, user_context)
    if not yacht_result.valid:
        raise HTTPException(status_code=403, detail=yacht_result.error.message)

    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    if not inventory_handlers:
        raise HTTPException(status_code=500, detail="Inventory handlers not initialized")

    result = await inventory_handlers.log_part_usage_preview(
        part_id=payload["part_id"],
        quantity=payload["quantity"],
        yacht_id=yacht_id,
        user_id=user_id,
        work_order_id=payload.get("work_order_id"),
        equipment_id=payload.get("equipment_id"),
        usage_reason=payload.get("usage_reason", "other"),
        notes=payload.get("notes")
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result

