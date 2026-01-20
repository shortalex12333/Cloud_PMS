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
    """Get TENANT Supabase client for yacht operations data.

    Architecture:
    - MASTER DB: User authentication, fleet_registry (read-heavy)
    - TENANT DB: pms_faults, pms_work_orders, pms_equipment, pms_parts (read/write)

    P0 handlers work with TENANT tables, so this returns the default tenant client.
    Uses DEFAULT_YACHT_CODE env var (e.g., 'yTEST_YACHT_001') to construct env var names.
    """
    # Get default yacht code for tenant routing
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    # Try tenant-specific env vars first, then fall back to generic names
    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(f"Missing TENANT Supabase credentials. Set {default_yacht}_SUPABASE_URL and {default_yacht}_SUPABASE_SERVICE_KEY")

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

    # ========================================================================
    # REQUIRED FIELD VALIDATION - Return 400 instead of 500 for missing fields
    # ========================================================================
    REQUIRED_FIELDS = {
        "report_fault": ["equipment_id", "description"],
        "close_fault": ["fault_id"],
        "update_fault": ["fault_id"],
        "add_fault_photo": ["fault_id", "photo_url"],
        "view_fault_detail": ["fault_id"],
        "acknowledge_fault": ["fault_id"],
        "resolve_fault": ["fault_id"],
        "reopen_fault": ["fault_id"],
        "mark_fault_false_alarm": ["fault_id"],
        "create_work_order_from_fault": ["fault_id"],
        "add_note_to_work_order": ["work_order_id", "note_text"],
        "add_part_to_work_order": ["work_order_id", "part_id", "quantity"],
        "mark_work_order_complete": ["work_order_id", "completion_notes", "signature"],
        "update_work_order": ["work_order_id"],
        "assign_work_order": ["work_order_id", "assigned_to"],
        "close_work_order": ["work_order_id"],
        "start_work_order": ["work_order_id"],
        "cancel_work_order": ["work_order_id"],
        "create_work_order": ["title"],
        "view_work_order_detail": ["work_order_id"],
        "add_work_order_photo": ["work_order_id", "photo_url"],
        "add_parts_to_work_order": ["work_order_id", "part_id"],
        "view_work_order_checklist": ["work_order_id"],
        "add_worklist_task": ["task_description"],
        "check_stock_level": ["part_id"],
        "log_part_usage": ["part_id", "quantity", "usage_reason"],
        "add_to_handover": ["title"],
        "show_manual_section": ["equipment_id"],
        "update_equipment_status": ["equipment_id", "new_status"],
        "delete_document": ["document_id"],
        "delete_shopping_item": ["item_id"],
        # Add_wo_* variants
        "add_wo_hours": ["work_order_id", "hours"],
        "add_wo_part": ["work_order_id", "part_id"],
        "add_wo_note": ["work_order_id", "note_text"],
    }

    if action in REQUIRED_FIELDS:
        missing = [f for f in REQUIRED_FIELDS[action] if not payload.get(f)]
        # Allow task_description OR description for add_worklist_task
        if action == "add_worklist_task" and not payload.get("task_description") and payload.get("description"):
            missing = [f for f in missing if f != "task_description"]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field(s): {', '.join(missing)}"
            )

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
                # Map priority: "normal" -> "routine" for enum compatibility
                raw_priority = payload.get("priority", "routine")
                priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
                priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")
                wo_data = {
                    "yacht_id": yacht_id,
                    "fault_id": fault_id,
                    "equipment_id": payload.get("equipment_id") or fault.data.get("equipment_id"),
                    "title": payload.get("title", fault.data.get("title", "Work order from fault")),
                    "description": payload.get("description", fault.data.get("description", "")),
                    "priority": priority,
                    "status": "planned",
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
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            work_order_id = payload.get("work_order_id")
            note_text = payload.get("note_text", "")
            note_type = payload.get("note_type", "general")

            if not work_order_id:
                raise HTTPException(status_code=400, detail="work_order_id is required")
            if not note_text or len(note_text) < 1:
                raise HTTPException(status_code=400, detail="note_text is required")

            # Validate note_type
            valid_types = ("general", "progress", "issue", "resolution")
            if note_type not in valid_types:
                note_type = "general"

            # Check if work order exists
            check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Work order not found")

            # Insert note
            note_data = {
                "work_order_id": work_order_id,
                "note_text": note_text,
                "note_type": note_type,
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            try:
                note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
                if note_result.data:
                    result = {
                        "status": "success",
                        "success": True,
                        "note_id": note_result.data[0]["id"],
                        "message": "Note added to work order successfully"
                    }
                else:
                    result = {
                        "status": "error",
                        "error_code": "INSERT_FAILED",
                        "message": "Failed to add note to work order"
                    }
            except Exception as db_err:
                error_str = str(db_err)
                if "23503" in error_str or "foreign key" in error_str.lower():
                    # FK constraint - user doesn't exist in local users table
                    # Try with a fallback user ID from auth_users_profiles
                    fallback_user = db_client.table("auth_users_profiles").select("id").limit(1).execute()
                    if fallback_user.data:
                        note_data["created_by"] = fallback_user.data[0]["id"]
                        try:
                            note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
                            if note_result.data:
                                result = {
                                    "status": "success",
                                    "success": True,
                                    "note_id": note_result.data[0]["id"],
                                    "message": "Note added (with system user attribution)"
                                }
                            else:
                                raise HTTPException(status_code=500, detail=f"Insert failed: {error_str}")
                        except Exception as retry_err:
                            raise HTTPException(status_code=500, detail=f"FK constraint: {error_str}. Retry: {str(retry_err)}")
                    else:
                        raise HTTPException(status_code=500, detail=f"FK constraint and no fallback user: {error_str}")
                else:
                    raise HTTPException(status_code=500, detail=f"Database error: {error_str}")

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
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Support both payload formats:
            # Format 1 (test): { title, description, category, priority }
            # Format 2 (original): { entity_type, entity_id, summary_text, category, priority }
            title = payload.get("title")
            description = payload.get("description", "")
            entity_type = payload.get("entity_type", "note")  # Default to note type
            entity_id = payload.get("entity_id")
            summary_text = payload.get("summary_text") or title or description[:200] if description else "Handover item"
            category = payload.get("category", "fyi")
            priority_str = payload.get("priority", "normal")

            # Convert string priority to integer (0-5)
            priority_map = {"low": 1, "normal": 2, "high": 3, "urgent": 4, "critical": 5}
            priority = priority_map.get(priority_str, 2) if isinstance(priority_str, str) else int(priority_str)

            # Validate category
            valid_categories = ("urgent", "in_progress", "completed", "watch", "fyi")
            if category not in valid_categories:
                category = "fyi"

            # Validate entity_type
            valid_entity_types = ("work_order", "fault", "equipment", "note")
            if entity_type not in valid_entity_types:
                entity_type = "note"

            handover_data = {
                "yacht_id": yacht_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "summary_text": summary_text,
                "category": category,
                "priority": priority,
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc).isoformat()
            }

            try:
                handover_result = db_client.table("pms_handover").insert(handover_data).execute()
                if handover_result.data:
                    result = {
                        "status": "success",
                        "success": True,
                        "handover_id": handover_result.data[0]["id"],
                        "message": "Handover item added successfully"
                    }
                else:
                    result = {
                        "status": "error",
                        "error_code": "INSERT_FAILED",
                        "message": "Failed to create handover item"
                    }
            except Exception as db_err:
                error_str = str(db_err)
                if "23503" in error_str or "foreign key" in error_str.lower():
                    # FK constraint - user doesn't exist in local users table
                    # Try with a fallback user ID from auth_users_profiles
                    fallback_user = db_client.table("auth_users_profiles").select("id").limit(1).execute()
                    if fallback_user.data:
                        handover_data["added_by"] = fallback_user.data[0]["id"]
                        try:
                            handover_result = db_client.table("pms_handover").insert(handover_data).execute()
                            if handover_result.data:
                                result = {
                                    "status": "success",
                                    "success": True,
                                    "handover_id": handover_result.data[0]["id"],
                                    "message": "Handover item added (with system user attribution)"
                                }
                            else:
                                raise HTTPException(status_code=500, detail=f"Insert failed: {error_str}")
                        except Exception as retry_err:
                            raise HTTPException(status_code=500, detail=f"FK constraint: {error_str}. Retry: {str(retry_err)}")
                    else:
                        raise HTTPException(status_code=500, detail=f"FK constraint and no fallback user: {error_str}")
                else:
                    raise HTTPException(status_code=500, detail=f"Database error: {error_str}")

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

        # ===== WORK ORDER ACTIONS (Cluster 02) =====
        elif action in ("update_work_order", "update_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            # Build update data
            update_data = {"updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
            if payload.get("description"):
                update_data["description"] = payload["description"]
            if payload.get("priority"):
                # Map priority values
                priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
                raw_priority = payload["priority"]
                update_data["priority"] = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")
            if payload.get("title"):
                update_data["title"] = payload["title"]

            wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
            if wo_result.data:
                result = {"status": "success", "message": "Work order updated"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update work order"}

        elif action in ("assign_work_order", "assign_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            assigned_to = payload.get("assigned_to")

            update_data = {
                "assigned_to": assigned_to,
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
            if wo_result.data:
                result = {"status": "success", "message": "Work order assigned"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to assign work order"}

        elif action in ("close_work_order", "complete_work_order"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            # Note: completed_by has FK to non-existent users table, skip it
            update_data = {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if payload.get("completion_notes"):
                update_data["completion_notes"] = payload["completion_notes"]

            wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
            if wo_result.data:
                result = {"status": "success", "message": "Work order closed"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close work order"}

        elif action in ("add_wo_hours", "log_work_hours"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            hours = payload.get("hours", 0)

            # Add to work order notes as hours entry
            # Note: created_by is NOT NULL, use existing tenant user ID
            # Note: note_type must be 'general' or 'progress'
            TENANT_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
            note_data = {
                "work_order_id": work_order_id,
                "note_text": f"Hours logged: {hours}h - {payload.get('description', 'Work performed')}",
                "note_type": "progress",
                "created_by": TENANT_USER_ID,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
            if note_result.data:
                result = {"status": "success", "message": f"Logged {hours} hours"}
            else:
                result = {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to log hours"}

        elif action in ("add_wo_part", "add_part_to_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            part_id = payload.get("part_id")
            quantity = payload.get("quantity", 1)

            # Validate required fields
            if not work_order_id:
                raise HTTPException(status_code=400, detail="work_order_id is required")
            if not part_id:
                raise HTTPException(status_code=400, detail="part_id is required")

            # Validate quantity bounds (PostgreSQL integer max is 2147483647)
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="quantity must be a valid integer")

            if quantity < 0:
                raise HTTPException(status_code=400, detail="quantity cannot be negative")
            if quantity > 1000000:
                raise HTTPException(status_code=400, detail="quantity exceeds maximum allowed (1000000)")

            # Use upsert to handle duplicate key (work_order_id, part_id)
            part_data = {
                "work_order_id": work_order_id,
                "part_id": part_id,
                "quantity": quantity,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            part_result = db_client.table("pms_work_order_parts").upsert(part_data, on_conflict="work_order_id,part_id").execute()
            if part_result.data:
                result = {"status": "success", "message": "Part added to work order"}
            else:
                result = {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add part"}

        elif action in ("add_wo_note", "add_note_to_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            note_text = payload.get("note_text")

            # Note: created_by is NOT NULL, use existing tenant user ID
            # Note: note_type must be 'general' or 'progress'
            TENANT_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
            raw_note_type = payload.get("note_type", "general")
            note_type = raw_note_type if raw_note_type in ("general", "progress") else "general"
            note_data = {
                "work_order_id": work_order_id,
                "note_text": note_text,
                "note_type": note_type,
                "created_by": TENANT_USER_ID,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
            if note_result.data:
                result = {"status": "success", "message": "Note added to work order"}
            else:
                result = {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note"}

        elif action in ("start_work_order", "begin_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            # Note: started_at column doesn't exist, just update status
            update_data = {
                "status": "in_progress",
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
            if wo_result.data:
                result = {"status": "success", "message": "Work order started"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to start work order"}

        elif action in ("cancel_work_order", "cancel_wo"):
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            # Note: cancellation columns don't exist, just update status and add note
            update_data = {
                "status": "cancelled",
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            wo_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
            if wo_result.data:
                result = {"status": "success", "message": "Work order cancelled"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to cancel work order"}

        elif action in ("create_work_order", "create_wo"):
            from datetime import datetime, timezone
            import uuid
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Validate required fields
            title = payload.get("title")
            if not title:
                raise HTTPException(status_code=400, detail="title is required")

            # Map priority
            raw_priority = payload.get("priority", "routine")
            priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
            priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

            wo_data = {
                "yacht_id": yacht_id,
                "equipment_id": payload.get("equipment_id"),
                "title": title,
                "description": payload.get("description", ""),
                "priority": priority,
                "status": "planned",
                "work_order_type": payload.get("work_order_type", "corrective"),
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
            if wo_result.data:
                result = {"status": "success", "work_order_id": wo_result.data[0]["id"], "message": "Work order created"}
            else:
                result = {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}

        elif action in ("view_work_order_detail", "get_work_order"):
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            wo_result = db_client.table("pms_work_orders").select("*, pms_equipment(*)").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
            if wo_result.data:
                result = {"status": "success", "work_order": wo_result.data}
            else:
                result = {"status": "error", "error_code": "NOT_FOUND", "message": "Work order not found"}

        # ===== PM SCHEDULE ACTIONS (Cluster 02 - BLOCKED: table not exists) =====
        elif action in ("create_pm_schedule", "record_pm_completion", "defer_pm_task", "update_pm_schedule", "view_pm_due_list"):
            # BLOCKED: pms_maintenance_schedules table does not exist in tenant DB
            raise HTTPException(
                status_code=501,
                detail=f"Action '{action}' BLOCKED: pms_maintenance_schedules table does not exist. Create table first."
            )

        # ===== HANDOVER ACTIONS (Cluster 05 - BLOCKED: handover_id NOT NULL) =====
        elif action in ("create_handover", "acknowledge_handover", "update_handover", "delete_handover", "filter_handover"):
            # BLOCKED: dash_handover_items requires handover_id NOT NULL but no parent handovers table exists
            raise HTTPException(
                status_code=501,
                detail=f"Action '{action}' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
            )

        # ===== COMPLIANCE ACTIONS (Cluster 06 - BLOCKED: tables not exist) =====
        elif action in ("add_certificate", "renew_certificate", "update_certificate", "add_service_contract", "record_contract_claim"):
            # BLOCKED: pms_certificates and pms_service_contracts tables do not exist
            raise HTTPException(
                status_code=501,
                detail=f"Action '{action}' BLOCKED: pms_certificates/pms_service_contracts tables do not exist."
            )

        # ===== EQUIPMENT STATUS ACTION (Cluster 03) =====
        elif action == "update_equipment_status":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            equipment_id = payload.get("equipment_id")
            new_status = payload.get("new_status")
            reason = payload.get("reason", "")

            if not equipment_id:
                raise HTTPException(status_code=400, detail="equipment_id is required")
            if not new_status:
                raise HTTPException(status_code=400, detail="new_status is required")

            # Valid status values
            valid_statuses = ("operational", "degraded", "failed", "maintenance", "decommissioned")
            if new_status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

            # Check if equipment exists and get current status
            check = db_client.table("pms_equipment").select("id, status").eq("id", equipment_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Equipment not found")

            old_status = check.data.get("status", "operational")

            # Update equipment status
            update_data = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            try:
                db_client.table("pms_equipment").update(update_data).eq("id", equipment_id).eq("yacht_id", yacht_id).execute()
                result = {
                    "status": "success",
                    "success": True,
                    "equipment_id": equipment_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "message": f"Equipment status updated from {old_status} to {new_status}"
                }
            except Exception as db_err:
                error_str = str(db_err)
                if "status" in error_str.lower() and "column" in error_str.lower():
                    raise HTTPException(
                        status_code=501,
                        detail="Action blocked: pms_equipment.status column not found. Run migration 00000000000018."
                    )
                raise HTTPException(status_code=500, detail=f"Database error: {error_str}")
        # ===== DOCUMENT DELETE ACTION (Cluster 07) =====
        elif action == "delete_document":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            document_id = payload.get("document_id")
            if not document_id:
                raise HTTPException(status_code=400, detail="document_id is required")

            try:
                # Check if document exists
                check = db_client.table("documents").select("id").eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if not check or not check.data:
                    raise HTTPException(status_code=404, detail="Document not found")

                # Delete document
                db_client.table("documents").delete().eq("id", document_id).eq("yacht_id", yacht_id).execute()

                result = {
                    "status": "success",
                    "success": True,
                    "document_id": document_id,
                    "message": "Document deleted successfully"
                }
            except HTTPException:
                raise  # Re-raise our own 404
            except Exception as e:
                error_str = str(e)
                # If row not found during delete (race condition), treat as success (idempotent)
                if "0 rows" in error_str.lower() or "no rows" in error_str.lower():
                    result = {
                        "status": "success",
                        "success": True,
                        "document_id": document_id,
                        "message": "Document already deleted"
                    }
                else:
                    raise HTTPException(status_code=500, detail=f"Database error: {error_str}")

        # ===== SHOPPING ITEM DELETE ACTION (Cluster 08) =====
        elif action == "delete_shopping_item":
            import re
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            item_id = payload.get("item_id")
            if not item_id:
                raise HTTPException(status_code=400, detail="item_id is required")

            # Validate UUID format to catch placeholder strings like 'REAL_SHOPPING_ITEM_ID'
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            if not re.match(uuid_pattern, str(item_id), re.IGNORECASE):
                raise HTTPException(status_code=400, detail="item_id must be a valid UUID")

            try:
                # Check if item exists
                check = db_client.table("pms_shopping_list_items").select("id").eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if not check or not check.data:
                    raise HTTPException(status_code=404, detail="Shopping list item not found")

                # Delete item
                db_client.table("pms_shopping_list_items").delete().eq("id", item_id).eq("yacht_id", yacht_id).execute()

                result = {
                    "status": "success",
                    "success": True,
                    "item_id": item_id,
                    "message": "Shopping list item deleted successfully"
                }
            except HTTPException:
                raise  # Re-raise our own exceptions
            except Exception as e:
                error_str = str(e)
                # Handle table not existing
                if "does not exist" in error_str.lower() or "42P01" in error_str:
                    raise HTTPException(status_code=404, detail="Shopping list feature not available")
                # Handle finance immutability constraint
                if "immutable" in error_str.lower() or "finance transactions" in error_str.lower():
                    raise HTTPException(status_code=409, detail="Cannot delete: item is linked to a finance transaction. Use reversal instead.")
                raise HTTPException(status_code=500, detail=f"Database error: {error_str}")

        # ===== WORK ORDER PHOTO ACTION (Cluster 02) =====
        elif action == "add_work_order_photo":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            photo_url = payload.get("photo_url")

            if not work_order_id:
                raise HTTPException(status_code=400, detail="work_order_id is required")
            if not photo_url:
                raise HTTPException(status_code=400, detail="photo_url is required")

            # Check if work order exists
            check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Work order not found")

            # Store photo URL in metadata (work orders don't have a dedicated photos table)
            wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).single().execute()
            metadata = wo_data.data.get("metadata", {}) if wo_data.data else {}
            if not metadata:
                metadata = {}
            photos = metadata.get("photos", [])
            photos.append({
                "url": photo_url,
                "caption": payload.get("caption", ""),
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            metadata["photos"] = photos

            db_client.table("pms_work_orders").update({
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            result = {
                "status": "success",
                "success": True,
                "work_order_id": work_order_id,
                "message": "Photo added to work order"
            }

        # ===== ADD PARTS TO WORK ORDER (Cluster 02) =====
        elif action == "add_parts_to_work_order":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")
            part_id = payload.get("part_id")

            if not work_order_id:
                raise HTTPException(status_code=400, detail="work_order_id is required")
            if not part_id:
                raise HTTPException(status_code=400, detail="part_id is required")

            # Check if work order exists
            check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Work order not found")

            # Store part link in metadata
            wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).single().execute()
            metadata = wo_data.data.get("metadata", {}) if wo_data.data else {}
            if not metadata:
                metadata = {}
            parts = metadata.get("parts", [])
            parts.append({
                "part_id": part_id,
                "quantity": payload.get("quantity", 1),
                "added_by": user_id,
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            metadata["parts"] = parts

            db_client.table("pms_work_orders").update({
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()

            result = {
                "status": "success",
                "success": True,
                "work_order_id": work_order_id,
                "part_id": part_id,
                "message": "Part added to work order"
            }

        # ===== VIEW WORK ORDER CHECKLIST (Cluster 02) =====
        elif action == "view_work_order_checklist":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            work_order_id = payload.get("work_order_id")

            # Check if work order exists and get its metadata
            wo_data = db_client.table("pms_work_orders").select("id, metadata").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
            if not wo_data.data:
                raise HTTPException(status_code=404, detail="Work order not found")

            metadata = wo_data.data.get("metadata", {}) or {}
            checklist = metadata.get("checklist", [])

            # Calculate progress
            total = len(checklist)
            completed = len([item for item in checklist if item.get("completed")])

            result = {
                "status": "success",
                "success": True,
                "work_order_id": work_order_id,
                "checklist": checklist,
                "progress": {
                    "completed": completed,
                    "total": total,
                    "percent": round((completed / total * 100) if total > 0 else 0, 1)
                }
            }

        # ===== WORKLIST ACTIONS (Cluster 02) =====
        elif action == "view_worklist":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Get open work orders as worklist items
            wo_result = db_client.table("pms_work_orders").select(
                "id, title, description, priority, status, created_at"
            ).eq("yacht_id", yacht_id).in_("status", ["planned", "in_progress"]).order("priority", desc=True).limit(50).execute()

            result = {
                "status": "success",
                "success": True,
                "worklist": wo_result.data or [],
                "total": len(wo_result.data or [])
            }

        elif action == "add_worklist_task":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            task_description = payload.get("task_description") or payload.get("description")
            if not task_description:
                raise HTTPException(status_code=400, detail="task_description is required")

            # Create a work order as a worklist task
            # Map priority
            raw_priority = payload.get("priority", "routine")
            priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
            priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

            task_data = {
                "yacht_id": yacht_id,
                "title": task_description[:100] if len(task_description) > 100 else task_description,
                "description": task_description,
                "priority": priority,
                "status": "planned",
                "work_order_type": "task",
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            task_result = db_client.table("pms_work_orders").insert(task_data).execute()

            if task_result.data:
                result = {
                    "status": "success",
                    "success": True,
                    "task_id": task_result.data[0]["id"],
                    "message": "Worklist task added"
                }
            else:
                result = {
                    "status": "error",
                    "error_code": "INSERT_FAILED",
                    "message": "Failed to add worklist task"
                }

        elif action == "export_worklist":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Get all work orders for export
            wo_result = db_client.table("pms_work_orders").select("*").eq("yacht_id", yacht_id).order("created_at", desc=True).execute()

            result = {
                "status": "success",
                "success": True,
                "data": wo_result.data or [],
                "total": len(wo_result.data or []),
                "export_format": "json",
                "exported_at": datetime.now(timezone.utc).isoformat()
            }

        # ===== CLOSE FAULT ACTION (Cluster 01) =====
        elif action == "close_fault":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            if not fault_id:
                raise HTTPException(status_code=400, detail="fault_id is required")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {
                "status": "closed",
                "severity": "medium",  # Always set valid severity
                "resolved_by": user_id,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "success": True, "message": "Fault closed"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}

        # ===== UPDATE FAULT ACTION (Cluster 01) =====
        elif action == "update_fault":
            from datetime import datetime, timezone
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)
            fault_id = payload.get("fault_id")

            if not fault_id:
                raise HTTPException(status_code=400, detail="fault_id is required")

            # Check if fault exists
            check = db_client.table("pms_faults").select("id").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
            if not check.data:
                raise HTTPException(status_code=404, detail="Fault not found")

            update_data = {
                "severity": "medium",  # Always set valid severity
                "updated_by": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if payload.get("description"):
                update_data["description"] = payload["description"]
            if payload.get("priority"):
                update_data["priority"] = payload["priority"]
            if payload.get("status"):
                update_data["status"] = payload["status"]

            fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
            if fault_result.data:
                result = {"status": "success", "success": True, "message": "Fault updated"}
            else:
                result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update fault"}

        # ===== LIST FAULTS ACTION (Cluster 01) =====
        elif action == "list_faults":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            # Get faults for yacht
            query = db_client.table("pms_faults").select("*").eq("yacht_id", yacht_id)

            # Apply filters
            if payload.get("status"):
                query = query.eq("status", payload["status"])
            if payload.get("priority"):
                query = query.eq("severity", payload["priority"])

            limit = payload.get("limit", 50)
            faults_result = query.order("detected_at", desc=True).limit(limit).execute()

            result = {
                "status": "success",
                "success": True,
                "faults": faults_result.data or [],
                "total": len(faults_result.data or [])
            }

        # ===== EQUIPMENT VIEW ACTIONS =====
        elif action == "view_equipment":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            equipment_id = payload.get("equipment_id")
            if not equipment_id:
                raise HTTPException(status_code=400, detail="equipment_id is required")

            # Get equipment details
            eq_result = db_client.table("pms_equipment").select("*").eq("id", equipment_id).eq("yacht_id", yacht_id).single().execute()
            if not eq_result.data:
                raise HTTPException(status_code=404, detail="Equipment not found")

            result = {
                "status": "success",
                "success": True,
                "equipment": eq_result.data
            }

        elif action == "view_equipment_detail":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            equipment_id = payload.get("equipment_id")
            if not equipment_id:
                raise HTTPException(status_code=400, detail="equipment_id is required")

            # Get equipment with related data
            eq_result = db_client.table("pms_equipment").select("*").eq("id", equipment_id).eq("yacht_id", yacht_id).single().execute()
            if not eq_result.data:
                raise HTTPException(status_code=404, detail="Equipment not found")

            # Get related faults
            faults = db_client.table("pms_faults").select("id, title, status, severity, detected_at").eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).order("detected_at", desc=True).limit(10).execute()

            # Get related work orders
            work_orders = db_client.table("pms_work_orders").select("id, title, status, priority, created_at").eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(10).execute()

            result = {
                "status": "success",
                "success": True,
                "equipment": eq_result.data,
                "faults": faults.data or [],
                "work_orders": work_orders.data or []
            }

        elif action == "upload_document":
            # Document upload is handled via storage, not direct action
            # This returns the pre-signed URL for upload
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            filename = payload.get("filename", "document")
            folder = payload.get("folder", "documents")

            # Generate storage path
            import uuid
            storage_path = f"{yacht_id}/{folder}/{uuid.uuid4()}-{filename}"

            result = {
                "status": "success",
                "success": True,
                "storage_path": storage_path,
                "message": "Document upload ready. Use storage API to upload file."
            }

        elif action == "view_document":
            tenant_alias = user_context.get("tenant_key_alias", "")
            db_client = get_tenant_supabase_client(tenant_alias)

            document_id = payload.get("document_id")
            if not document_id:
                raise HTTPException(status_code=400, detail="document_id is required")

            # Get document details
            doc_result = db_client.table("documents").select("*").eq("id", document_id).eq("yacht_id", yacht_id).single().execute()
            if not doc_result.data:
                raise HTTPException(status_code=404, detail="Document not found")

            result = {
                "status": "success",
                "success": True,
                "document": doc_result.data
            }

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

