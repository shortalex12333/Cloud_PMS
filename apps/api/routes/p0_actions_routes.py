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

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import os
import hashlib
import json
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import centralized Supabase client factory
from integrations.supabase import get_supabase_client, get_tenant_client

from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
from handlers.inventory_handlers import InventoryHandlers
from handlers.handover_handlers import HandoverHandlers
from handlers.handover_workflow_handlers import HandoverWorkflowHandlers
from handlers.manual_handlers import ManualHandlers
from handlers.part_handlers import PartHandlers
from handlers.shopping_list_handlers import ShoppingListHandlers
from handlers.hours_of_rest_handlers import HoursOfRestHandlers
from action_router.validators import validate_payload_entities
from action_router.middleware import validate_action_payload, InputValidationError, validate_state_transition, InvalidStateTransitionError
from action_router.registry import get_action
from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id

logger = logging.getLogger(__name__)

# ============================================================================
# LEDGER HELPER (moved to handlers/ledger_utils.py — imported here for backward compat)
# ============================================================================
from routes.handlers.ledger_utils import build_ledger_event
from routes.handlers import HANDLERS as _ACTION_HANDLERS


# Maps action name → (entity_type, payload_key_for_entity_id)
_ACTION_ENTITY_MAP = {
    "start_work_order":            ("work_order", "work_order_id"),
    "complete_work_order":         ("work_order", "work_order_id"),
    "close_work_order":            ("work_order", "work_order_id"),
    "assign_work_order":           ("work_order", "work_order_id"),
    "add_note_to_work_order":      ("work_order", "work_order_id"),
    "add_part_to_work_order":      ("work_order", "work_order_id"),
    "update_work_order":           ("work_order", "work_order_id"),
    "report_fault":                ("fault", "fault_id"),
    "acknowledge_fault":           ("fault", "fault_id"),
    "close_fault":                 ("fault", "fault_id"),
    "diagnose_fault":              ("fault", "fault_id"),
    "reopen_fault":                ("fault", "fault_id"),
    "update_fault":                ("fault", "fault_id"),
    "add_fault_note":              ("fault", "fault_id"),
    "update_equipment_status":     ("equipment", "equipment_id"),
    "add_equipment_note":          ("equipment", "equipment_id"),
    "update_running_hours":        ("equipment", "equipment_id"),
    "log_part_usage":              ("part", "part_id"),
    "adjust_stock_quantity":       ("part", "part_id"),
    "write_off_part":              ("part", "part_id"),
    "create_shopping_list_item":   ("shopping_list_item", "item_id"),
    "approve_shopping_list_item":  ("shopping_list_item", "item_id"),
    "reject_shopping_list_item":   ("shopping_list_item", "item_id"),
    "mark_shopping_list_ordered":  ("shopping_list_item", "item_id"),
    "promote_candidate_to_part":   ("shopping_list_item", "item_id"),
    "edit_receiving":              ("receiving", "receiving_id"),
    "submit_receiving_for_review": ("receiving", "receiving_id"),
    "accept_receiving":            ("receiving", "receiving_id"),
    "reject_receiving":            ("receiving", "receiving_id"),
    "submit_purchase_order":       ("purchase_order", "purchase_order_id"),
    "approve_purchase_order":      ("purchase_order", "purchase_order_id"),
    "mark_po_received":            ("purchase_order", "purchase_order_id"),
    "cancel_purchase_order":       ("purchase_order", "purchase_order_id"),
}


# ============================================================================
# SUPABASE CLIENT HELPERS
# ============================================================================
# NOTE: get_supabase_client and get_tenant_client are imported from integrations.supabase


def get_tenant_supabase_client(tenant_key_alias: str) -> Client:
    """Get tenant-specific Supabase client instance.

    Uses the centralized get_tenant_client() from integrations/supabase.py.
    This ensures consistent client behavior across all endpoints.

    Routing contract:
    - tenant_key_alias comes from MASTER DB fleet_registry (e.g., 'yTEST_YACHT_001')
    - Env vars on Render: {tenant_key_alias}_SUPABASE_URL, {tenant_key_alias}_SUPABASE_SERVICE_KEY
    """
    logger.info(f"[P0Actions] Using get_tenant_client for {tenant_key_alias}")
    return get_tenant_client(tenant_key_alias)


def get_user_scoped_client(jwt_token: str, tenant_key_alias: str = None) -> Client:
    """Create a user-scoped Supabase client using the user's JWT.

    This enables Row-Level Security (RLS) enforcement - the client
    will use the user's permissions instead of bypassing RLS with service_role.

    Args:
        jwt_token: Bearer token from Authorization header (with or without "Bearer " prefix)
        tenant_key_alias: Tenant identifier (defaults to DEFAULT_YACHT_CODE)

    Returns:
        Supabase client scoped to the user's JWT
    """
    # Strip "Bearer " prefix if present
    if jwt_token and jwt_token.startswith("Bearer "):
        jwt_token = jwt_token[7:]

    # Get tenant URL
    if not tenant_key_alias:
        tenant_key_alias = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{tenant_key_alias}_SUPABASE_URL") or os.getenv("TENANT_1_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    anon_key = os.getenv(f"{tenant_key_alias}_SUPABASE_ANON_KEY") or os.getenv("TENANT_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not anon_key:
        raise ValueError(f"Missing Supabase credentials for user-scoped client (tenant: {tenant_key_alias})")

    # Create client with anon key, then set user JWT
    client = create_client(url, anon_key)

    # Set the user's access token for RLS
    client.auth.set_session(jwt_token, jwt_token)  # Set both access_token and refresh_token to the JWT
    client.postgrest.auth(jwt_token)  # Set auth header for PostgREST queries

    logger.info(f"[RLS] Created user-scoped Supabase client for tenant {tenant_key_alias}")

    return client


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/actions", tags=["p0-actions"])

# Per-tenant handler caches
_handlers_cache = {}

def get_handlers_for_tenant(tenant_key_alias: str):
    """Get or initialize handlers for specific tenant."""
    global _handlers_cache
    if tenant_key_alias not in _handlers_cache:
        supabase = get_tenant_supabase_client(tenant_key_alias)
        if supabase:
            try:
                _handlers_cache[tenant_key_alias] = {
                    "wo_handlers": WorkOrderMutationHandlers(supabase),
                    "inventory_handlers": InventoryHandlers(supabase),
                    "handover_handlers": HandoverHandlers(supabase),
                    "handover_workflow_handlers": HandoverWorkflowHandlers(supabase),
                    "manual_handlers": ManualHandlers(supabase),
                    "part_handlers": PartHandlers(supabase),
                    "shopping_list_handlers": ShoppingListHandlers(supabase),
                    "hor_handlers": HoursOfRestHandlers(supabase),
                }
                logger.info(f"✅ All P0 action handlers initialized for {tenant_key_alias}")
            except Exception as e:
                logger.error(f"Failed to initialize handlers for {tenant_key_alias}: {e}")
                raise HTTPException(status_code=503, detail="Handler initialization failed")
        else:
            logger.warning(f"⚠️ P0 handlers not initialized - no database connection for {tenant_key_alias}")
            raise HTTPException(status_code=503, detail="Database connection not available")
    return _handlers_cache[tenant_key_alias]


# Backward compatibility: module-level handlers for default tenant (fallback)
# Initialize handlers (gracefully handle missing DB connection)
supabase = get_supabase_client()
if supabase:
    try:
        wo_handlers = WorkOrderMutationHandlers(supabase)
        inventory_handlers = InventoryHandlers(supabase)
        handover_handlers = HandoverHandlers(supabase)
        handover_workflow_handlers = HandoverWorkflowHandlers(supabase)
        manual_handlers = ManualHandlers(supabase)
        part_handlers = PartHandlers(supabase)
        shopping_list_handlers = ShoppingListHandlers(supabase)
        hor_handlers = HoursOfRestHandlers(supabase)
        logger.info("✅ All P0 action handlers initialized (default tenant fallback)")
    except Exception as e:
        logger.error(f"Failed to initialize handlers: {e}")
        wo_handlers = None
        inventory_handlers = None
        handover_handlers = None
        manual_handlers = None
        part_handlers = None
        shopping_list_handlers = None
        hor_handlers = None
else:
    logger.warning("⚠️ P0 handlers not initialized - no database connection")
    wo_handlers = None
    inventory_handlers = None
    handover_handlers = None
    manual_handlers = None
    part_handlers = None
    shopping_list_handlers = None
    hor_handlers = None


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
    auth: dict = Depends(get_authenticated_user)
):
    """
    Pre-fill work order form from fault data.

    Returns:
    - Pre-filled form data (title, equipment, location, description, priority)
    - Duplicate check (existing WO for this fault)
    """
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.create_work_order_from_fault_prefill(fault_id, yacht_id, user_id)

    if result["status"] == "error":
        raise HTTPException(
            status_code=400 if result["error_code"] == "FAULT_NOT_FOUND" else 500,
            detail=result["message"]
        )

    return result


@router.get("/add_note_to_work_order/prefill")
async def add_note_to_work_order_prefill(
    work_order_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Pre-fill data for add note to work order."""
    yacht_id = auth["yacht_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.add_note_to_work_order_prefill(work_order_id, yacht_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/add_part_to_work_order/prefill")
async def add_part_to_work_order_prefill(
    work_order_id: str,
    part_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Pre-fill data for add part to work order."""
    yacht_id = auth["yacht_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.add_part_to_work_order_prefill(work_order_id, part_id, yacht_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/mark_work_order_complete/prefill")
async def mark_work_order_complete_prefill(
    work_order_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Pre-fill data for mark work order complete."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.mark_work_order_complete_prefill(work_order_id, yacht_id, user_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/work_order/create/prepare")
async def prepare_create_work_order(
    request: PreviewRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Phase 1: Generate mutation preview for work order creation.

    This endpoint returns a mutation preview with pre-filled fields based on NLP
    entity extraction and planning document specifications.

    Returns:
    - mutation_preview: Pre-filled payload based on extracted entities
    - missing_required: List of required fields not auto-populated
    - warnings: List of ambiguities (equipment not found, etc.)
    - validation_status: "ready" | "incomplete"
    """
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]

    # Get handlers for tenant
    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    wo_handlers = handlers.get("wo_handlers")
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    # Call the prepare handler
    result = await wo_handlers.prepare_create_work_order(
        query_text=request.payload.get("query_text", ""),
        extracted_entities=request.payload.get("extracted_entities", {}),
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result.get("status") == "error":
        status_code = 400
        if result.get("error_code") == "INTERNAL_ERROR":
            status_code = 500
        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return result


@router.post("/work_order/create/commit")
async def commit_create_work_order(
    request: PreviewRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Phase 2: Execute work order creation after user confirms preview.

    The user has reviewed and possibly edited the mutation_preview.
    This endpoint:
    1. Re-validates all required fields
    2. Validates foreign key constraints (equipment_id, assigned_to)
    3. Executes INSERT with RLS
    4. Writes audit log entry (signature NOT NULL, uses {} for non-signed)
    5. Returns entity ID for frontend to refresh

    Required fields: title, priority, type
    Optional fields: equipment_id, description, assigned_to, due_date
    """
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]

    # Get handlers for tenant
    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    wo_handlers = handlers.get("wo_handlers")
    if not wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    # Extract payload and signature
    payload = request.payload
    signature = payload.get("signature")  # Optional for non-signed actions

    # Call the commit handler
    result = await wo_handlers.commit_create_work_order(
        payload=payload,
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result.get("status") == "error":
        # Map error codes to HTTP status codes
        error_code = result.get("error_code")
        status_code_map = {
            "MISSING_REQUIRED_FIELDS": 400,
            "INVALID_UUID": 400,
            "EQUIPMENT_NOT_FOUND": 404,
            "USER_NOT_FOUND": 404,
            "INSERT_FAILED": 500,
            "INTERNAL_ERROR": 500,
        }
        status_code = status_code_map.get(error_code, 400)
        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return result


# ============================================================================
# PREVIEW ENDPOINTS
# ============================================================================

@router.post("/mark_work_order_complete/preview")
async def mark_work_order_complete_preview(
    request: PreviewRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Preview work order completion."""
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]
    payload = request.payload

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.mark_work_order_complete_preview(
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
    auth: dict = Depends(get_authenticated_user),
):
    """Preview adding part to work order."""
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]
    payload = request.payload

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.add_part_to_work_order_preview(
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
    auth: dict = Depends(get_authenticated_user),
):
    """
    Preview work order creation.

    Shows:
    - What will be created
    - All side effects
    - Warnings (if any)
    """
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]
    payload = request.payload

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _wo_handlers = handlers.get("wo_handlers")
    if not _wo_handlers:
        raise HTTPException(status_code=500, detail="Work order handlers not initialized")

    result = await _wo_handlers.create_work_order_from_fault_preview(
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


# ---------------------------------------------------------------------------
# ENTITY CONTEXT NORMALISATION (Phase 4)
# Maps generic entity_id → domain-specific keys based on action name.
# useEntityLens surfaces always send entity_id; standalone forms send
# domain keys (equipment_id, fault_id, etc.) directly.
# Uses setdefault — if the domain key is already present it is NOT overwritten.
# ---------------------------------------------------------------------------

_EQUIPMENT_ACTIONS = frozenset({
    "create_work_order_for_equipment", "update_equipment_status",
    "flag_equipment_attention", "add_equipment_note",
    "show_manual_section", "view_equipment_details",
    "view_equipment_history", "view_equipment_parts",
    "view_linked_faults", "view_equipment_manual",
    "view_fault_history", "view_work_order_history",
    "suggest_parts",
})

_FAULT_ACTIONS = frozenset({
    "close_fault", "diagnose_fault", "acknowledge_fault", "resolve_fault",
    "reopen_fault", "mark_fault_false_alarm", "create_work_order_from_fault",
    "update_fault", "add_fault_photo", "view_fault_detail",
    "add_fault_note", "report_fault", "classify_fault",
    "investigate_fault", "archive_fault", "delete_fault",
})

_WORK_ORDER_ACTIONS = frozenset({
    "update_work_order", "update_wo", "assign_work_order", "assign_wo",
    "close_work_order", "complete_work_order", "add_wo_hours", "log_work_hours",
    "add_wo_part", "add_part_to_wo", "add_wo_note", "add_note_to_wo",
    "start_work_order", "begin_wo", "cancel_work_order", "cancel_wo",
    "view_work_order_detail", "view_work_order", "get_work_order",
    "add_work_order_photo", "mark_work_order_complete",
    "add_note_to_work_order", "add_part_to_work_order",
    "reassign_work_order", "archive_work_order",
    "add_parts_to_work_order", "view_work_order_checklist", "add_work_order_note",
})

_PART_ACTIONS = frozenset({
    "consume_part", "receive_part", "transfer_part", "adjust_stock_quantity",
    "write_off_part", "add_to_shopping_list", "reorder_part", "view_part_stock",
    "view_part_location", "view_part_usage", "view_linked_equipment",
    "view_part_details", "check_stock_level", "log_part_usage",
})

_PO_ACTIONS = frozenset({
    "submit_purchase_order", "approve_purchase_order",
    "mark_po_received", "cancel_purchase_order",
    "convert_to_po",
})

_RECEIVING_ACTIONS = frozenset({
    "submit_receiving_for_review", "edit_receiving",
    "confirm_receiving", "accept_receiving", "reject_receiving",
    "flag_discrepancy", "create_receiving",
    "attach_receiving_image_with_comment", "extract_receiving_candidates",
    "update_receiving_fields", "add_receiving_item", "adjust_receiving_item",
    "link_invoice_document", "view_receiving_history",
})

_SHOPPING_LIST_ACTIONS = frozenset({
    "submit_list", "approve_list", "add_list_item",
    "create_shopping_list_item", "approve_shopping_list_item",
    "reject_shopping_list_item", "promote_candidate_to_part",
    "view_shopping_list_history", "delete_shopping_item",
    "archive_list", "delete_list",
})

_HANDOVER_ACTIONS = frozenset({
    "sign_handover", "edit_handover_section", "add_to_handover",
    "export_handover", "archive_handover", "delete_handover",
})

_WARRANTY_ACTIONS = frozenset({
    "file_warranty_claim", "draft_warranty_claim",
    "archive_warranty", "void_warranty",
    "add_warranty_note",
})

_CERT_ACTIONS = frozenset({
    "create_vessel_certificate", "create_crew_certificate",
    "update_certificate", "link_document_to_certificate",
    "supersede_certificate", "renew_certificate",
    "suspend_certificate", "revoke_certificate",
    "archive_certificate", "add_certificate_note",
    "assign_certificate",
})


def resolve_entity_context(action: str, context: dict) -> dict:
    """
    Normalise incoming context so handlers receive domain-specific keys.

    Callers from useEntityLens surfaces send `entity_id`.
    Callers from standalone forms send `equipment_id`, `fault_id`, etc. directly.
    After this function, both paths produce the same context shape for handlers.

    Uses setdefault — existing domain keys are never overwritten.
    """
    ctx = dict(context)
    entity_id = ctx.get("entity_id")

    if entity_id:
        if action in _EQUIPMENT_ACTIONS:
            ctx.setdefault("equipment_id", entity_id)
        elif action in _FAULT_ACTIONS:
            ctx.setdefault("fault_id", entity_id)
        elif action in _WORK_ORDER_ACTIONS:
            ctx.setdefault("work_order_id", entity_id)
        elif action in _PART_ACTIONS:
            ctx.setdefault("part_id", entity_id)
        elif action in _PO_ACTIONS:
            ctx.setdefault("purchase_order_id", entity_id)
        elif action in _RECEIVING_ACTIONS:
            ctx.setdefault("receiving_id", entity_id)
        elif action in _SHOPPING_LIST_ACTIONS:
            ctx.setdefault("item_id", entity_id)
        elif action in _HANDOVER_ACTIONS:
            ctx.setdefault("export_id", entity_id)
            ctx.setdefault("handover_id", entity_id)
        elif action in _WARRANTY_ACTIONS:
            ctx.setdefault("warranty_id", entity_id)
        elif action in _CERT_ACTIONS:
            ctx.setdefault("certificate_id", entity_id)

    return ctx


# ============================================================================
# EXECUTE ENDPOINT (All Actions)
# ============================================================================

@router.post("/execute")
async def execute_action(
    request: ActionExecuteRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Execute an action.

    This is the unified endpoint for all P0 actions.
    Routes to appropriate handler based on action name.
    """
    # Fleet-aware auth: provides yacht_id, role, department, tenant_key_alias, vessel_ids
    user_context = auth
    # Validate and resolve yacht_id from request context (fleet-aware)
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))

    action = request.action
    yacht_id = request.context["yacht_id"]
    user_id = user_context["user_id"]
    payload = request.payload

    # ========================================================================
    # AUTHORIZATION-FIRST: Universal Role Check (Security Fix - Parts Lens Gold)
    # ========================================================================
    # CRITICAL SECURITY: Role authorization MUST happen BEFORE payload validation
    # to prevent information disclosure of action structure to unauthorized users.
    #
    # Rationale: Previously, field validation happened first, causing unauthorized
    # users to receive 400 errors with field names instead of immediate 403 denial.
    # This allowed attackers to probe action requirements without authorization.
    #
    # Fix: Query registry for action's allowed_roles and validate BEFORE inspecting payload.
    try:
        action_def = get_action(action)
        if action_def and action_def.allowed_roles:
            user_role = user_context.get("role")

            if not user_role:
                logger.warning(f"[SECURITY] No role found for user {user_id} attempting action '{action}'")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "RLS_DENIED",
                        "message": "User role not found"
                    }
                )

            if user_role not in action_def.allowed_roles:
                logger.warning(
                    f"[SECURITY] Role '{user_role}' denied for action '{action}'. "
                    f"Allowed: {action_def.allowed_roles}"
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "FORBIDDEN",
                        "message": f"Role '{user_role}' is not authorized to perform this action",
                        "required_roles": action_def.allowed_roles
                    }
                )
    except HTTPException:
        # Re-raise HTTP exceptions (403, 401, etc.)
        raise
    except Exception as e:
        # Action not in registry or other error - log but continue
        # (allows legacy actions not yet in registry to still work)
        logger.debug(f"Could not validate role for action '{action}': {e}")

    # ========================================================================
    # REQUIRED FIELD VALIDATION - Return 400 instead of 500 for missing fields
    # ========================================================================
    REQUIRED_FIELDS = {
        "report_fault": ["equipment_id", "description"],
        "diagnose_fault": ["fault_id"],
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
        "view_work_order": ["work_order_id"],
        "view_work_order_detail": ["work_order_id"],
        "add_work_order_photo": ["work_order_id", "photo_url"],
        "add_parts_to_work_order": ["work_order_id", "part_id"],
        "view_work_order_checklist": ["work_order_id"],
        "add_worklist_task": ["task_description"],
        "check_stock_level": ["part_id"],
        "log_part_usage": ["part_id", "quantity", "usage_reason"],
        "add_to_handover": ["summary"],
        "show_manual_section": ["equipment_id"],
        "update_equipment_status": ["equipment_id", "new_status"],
        # Document Lens v2 Actions
        "upload_document": ["file_name", "mime_type"],
        "update_document": ["document_id"],
        "delete_document": ["document_id", "reason", "signature"],
        "add_document_tags": ["document_id", "tags"],
        "get_document_url": ["document_id"],
        # Document Comment Actions (Document Lens v2 - Comments MVP)
        # Document comment actions migrated to action router - see registry.py
        "delete_shopping_item": ["item_id"],
        # Add_wo_* variants
        "add_wo_hours": ["work_order_id", "hours"],
        "add_wo_part": ["work_order_id", "part_id"],
        "add_wo_note": ["work_order_id", "note_text"],
        # Tier 1 - Fault/WO History
        "view_fault_history": ["equipment_id"],
        "add_fault_note": ["note_text"],
        "view_work_order_history": ["equipment_id"],
        "suggest_parts": ["fault_id"],
        # Tier 2 - Equipment Views
        "view_equipment_details": ["equipment_id"],
        "view_equipment_history": ["equipment_id"],
        "view_equipment_parts": ["equipment_id"],
        "view_linked_faults": ["equipment_id"],
        "view_equipment_manual": ["equipment_id"],
        "add_equipment_note": ["equipment_id", "note_text"],
        # Tier 3 - Inventory
        "view_part_stock": ["part_id"],
        "view_part_location": ["part_id"],
        "view_part_usage": ["part_id"],
        "view_linked_equipment": ["part_id"],
        "order_part": ["part_id"],
        "scan_part_barcode": ["barcode"],
        # Part Lens v2 Actions
        "view_part_details": ["part_id"],
        "add_to_shopping_list": ["part_id", "suggested_qty"],
        "consume_part": ["part_id", "quantity"],
        "receive_part": ["part_id", "to_location_id", "quantity", "idempotency_key"],
        "transfer_part": ["part_id", "from_location_id", "to_location_id", "quantity"],
        "adjust_stock_quantity": ["part_id", "quantity_change", "reason", "signature"],
        "write_off_part": ["part_id", "quantity", "reason", "signature"],
        "generate_part_labels": ["part_ids"],
        "request_label_output": ["label_request_id", "output_format"],
        # Tier 4 - Checklists
        "view_checklist": ["checklist_id"],
        "mark_checklist_item_complete": ["checklist_item_id"],
        "add_checklist_note": ["checklist_item_id", "note_text"],
        "add_checklist_item": ["work_order_id", "title"],
        "add_checklist_photo": ["checklist_item_id", "photo_url"],
        # Tier 5 - Handover/Communication
        "add_document_to_handover": ["handover_id", "document_id"],
        "add_predictive_insight_to_handover": ["handover_id", "insight_text"],
        "edit_handover_section": ["handover_id", "section_name"],
        "export_handover": ["handover_id"],
        "regenerate_handover_summary": ["handover_id"],
        "view_smart_summary": ["entity_type", "entity_id"],
        "upload_photo": ["entity_type", "entity_id", "photo_url"],
        "record_voice_note": ["entity_type", "entity_id"],
        # Tier 6 - Compliance/HoR
        "view_compliance_status": [],
        "tag_for_survey": ["equipment_id"],
        # Hours of Rest Actions (Crew Lens v3 - Action Registry)
        "get_hours_of_rest": ["yacht_id"],
        "upsert_hours_of_rest": ["yacht_id", "user_id", "record_date"],
        "get_monthly_signoff": ["yacht_id", "signoff_id"],
        "list_monthly_signoffs": ["yacht_id"],
        "create_monthly_signoff": ["yacht_id", "user_id", "month", "department"],
        "sign_monthly_signoff": ["signoff_id", "signature_level", "signature_data"],
        "create_crew_template": ["yacht_id", "user_id", "schedule_name", "schedule_template"],
        "apply_crew_template": ["yacht_id", "user_id", "week_start_date"],
        "list_crew_templates": ["yacht_id"],
        "list_crew_warnings": ["yacht_id"],
        "acknowledge_warning": ["warning_id"],
        "dismiss_warning": ["warning_id", "hod_justification", "dismissed_by_role"],
        # Tier 7 - Purchasing
        "create_purchase_request": ["title"],
        "add_item_to_purchase": ["purchase_request_id", "item_description"],
        "approve_purchase": ["purchase_request_id"],
        "upload_invoice": ["purchase_request_id", "invoice_url"],
        "track_delivery": ["purchase_request_id"],
        "log_delivery_received": ["purchase_request_id"],
        "update_purchase_status": ["purchase_request_id", "status"],
        # Tier 8 - Fleet View
        "view_fleet_summary": [],
        "open_vessel": ["vessel_id"],
        "export_fleet_summary": [],
        # Tier 9 - Remaining Actions
        "update_worklist_progress": ["worklist_item_id", "progress"],
        "view_related_documents": ["entity_type", "entity_id"],
        "view_document_section": ["document_id", "section_id"],
        "request_predictive_insight": ["entity_type", "entity_id"],
        "add_work_order_note": ["work_order_id", "note_text"],
        # Certificate Actions (Certificate Lens v2)
        "create_vessel_certificate": ["certificate_type", "certificate_name", "issuing_authority"],
        "create_crew_certificate": ["person_name", "certificate_type", "issuing_authority"],
        "update_certificate": ["certificate_id"],
        "link_document_to_certificate": ["certificate_id", "document_id"],
        "supersede_certificate": ["certificate_id", "reason", "signature"],
        # Shopping List Actions (Shopping List Lens v1)
        "create_shopping_list_item": ["source_type"],  # part_name auto-filled from part_id; quantity defaults to 1
        "approve_shopping_list_item": ["item_id", "quantity_approved"],
        "reject_shopping_list_item": ["item_id", "rejection_reason"],
        "promote_candidate_to_part": ["item_id"],
        "view_shopping_list_history": ["item_id"],
    }

    if action in REQUIRED_FIELDS:
        # Merge context + payload: context holds entity_id/certificate_id, payload holds user fields
        merged_for_check = {**request.context, **payload}
        missing = [f for f in REQUIRED_FIELDS[action] if not merged_for_check.get(f)]
        # Allow task_description OR description for add_worklist_task
        if action == "add_worklist_task" and not merged_for_check.get("task_description") and merged_for_check.get("description"):
            missing = [f for f in missing if f != "task_description"]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "MISSING_REQUIRED_FIELD",
                    "message": f"Missing required field(s): {', '.join(missing)}"
                }
            )

    # ========================================================================
    # INPUT VALIDATION - Security Fix 2026-02-10 (Day 3)
    # ========================================================================
    # Validate payload fields (UUID format, positive numbers, enums, etc.)
    try:
        payload = validate_action_payload(action, payload)
    except InputValidationError as e:
        logger.warning(f"[VALIDATION] Action '{action}' failed: {e.field} - {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": e.code,
                "message": e.message,
                "field": e.field
            }
        )

    # ========================================================================
    # RLS ENTITY VALIDATION - Security Fix 2026-02-10
    # ========================================================================
    # Verify all entity IDs in payload belong to user's yacht
    # This prevents cross-yacht data access even when entity IDs are known
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        if tenant_alias:
            rls_db = get_tenant_supabase_client(tenant_alias)
            rls_result = await validate_payload_entities(rls_db, payload, yacht_id)
            if not rls_result.valid:
                logger.warning(
                    f"[RLS] Entity validation failed for action '{action}': "
                    f"{rls_result.error.message if rls_result.error else 'Unknown error'}"
                )
                raise HTTPException(
                    status_code=404,
                    detail={
                        "status": "error",
                        "error_code": "NOT_FOUND",
                        "message": rls_result.error.message if rls_result.error else "Entity not found"
                    }
                )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Log but don't fail on RLS check errors (graceful degradation)
        logger.debug(f"[RLS] Could not validate entities for action '{action}': {e}")

    # ========================================================================
    # ROLE VALIDATION - Security fix for Fault Lens v1
    # ========================================================================
    # Define allowed roles for each action (Fault Lens v1 - Phase 7)
    FAULT_LENS_ROLES = {
        "report_fault": ["crew", "chief_engineer", "chief_officer", "captain"],
        "add_fault_photo": ["crew", "chief_engineer", "chief_officer", "captain"],
        "add_fault_note": ["crew", "chief_engineer", "chief_officer", "captain"],
        "view_fault_detail": ["crew", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
        "view_fault_history": ["crew", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
        "acknowledge_fault": ["chief_engineer", "chief_officer", "captain"],
        "close_fault": ["chief_engineer", "chief_officer", "captain"],
        "update_fault": ["chief_engineer", "chief_officer", "captain"],
        "diagnose_fault": ["chief_engineer", "chief_officer", "captain"],
        "reopen_fault": ["chief_engineer", "chief_officer", "captain"],
        "mark_fault_false_alarm": ["chief_engineer", "chief_officer", "captain"],
        "create_work_order_from_fault": ["chief_engineer", "chief_officer", "captain", "manager"],
    }

    # PART LENS SIGNED ACTIONS - STRICT role enforcement (captain/manager only)
    PART_LENS_SIGNED_ROLES = {
        "adjust_stock_quantity": ["chief_engineer", "captain", "manager"],
        # NOTE: write_off_part role check is at handler level (checks role_at_signing + is_manager RPC)
    }


    # WORK ORDER LENS ACTIONS - Role enforcement (Security Fix 2026-02-08)
    # Centralized RBAC for all work order actions
    # READ actions: all authenticated roles
    # MUTATE actions: chief_engineer and above
    # SIGNED actions: subset requiring signatures (captain/manager for create/archive)
    WORK_ORDER_LENS_ROLES = {
        # READ actions - all roles can view
        "view_work_order": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "view_work_order_detail": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "view_work_order_checklist": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "view_work_order_history": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "view_my_work_orders": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "list_work_orders": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],

        # MUTATE actions - management only (HOD and above)
        "update_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "assign_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "start_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "cancel_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "add_note_to_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "add_part_to_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "add_work_order_photo": ["chief_engineer", "chief_officer", "captain", "manager"],
        "close_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],

        # SIGNED actions - require signatures
        # create_work_order: crew allowed with department-level RBAC (enforced in handler)
        "create_work_order": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        "create_work_order_from_fault": ["chief_engineer", "chief_officer", "captain", "manager"],
        "mark_work_order_complete": ["chief_engineer", "chief_officer", "captain", "manager"],
        "reassign_work_order": ["chief_engineer", "chief_officer", "captain", "manager"],
        "archive_work_order": ["captain", "manager"],
    }

    if action in FAULT_LENS_ROLES:
        user_role = user_context.get("role")
        allowed_roles = FAULT_LENS_ROLES[action]

        if not user_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": "RLS_DENIED",
                    "message": "User role not found"
                }
            )

        if user_role not in allowed_roles:
            logger.warning(f"[SECURITY] Role '{user_role}' denied for action '{action}'. Allowed: {allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{user_role}' is not authorized to perform action '{action}'"
                }
            )

    # PART LENS SIGNED ACTIONS - Role validation (canon-critical for Part Lens v2)
    if action in PART_LENS_SIGNED_ROLES:
        user_role = user_context.get("role")
        allowed_roles = PART_LENS_SIGNED_ROLES[action]

        if not user_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": "RLS_DENIED",
                    "message": "User role not found for signed action"
                }
            )

        if user_role not in allowed_roles:
            logger.warning(f"[SECURITY] Role '{user_role}' denied for SIGNED action '{action}'. Allowed: {allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{user_role}' forbidden: not authorized to perform signed action '{action}'"
                }
            )

    # WORK ORDER LENS ACTIONS - Role validation (Security Fix 2026-02-08)
    # Enforce RBAC BEFORE signature checks and handler execution
    if action in WORK_ORDER_LENS_ROLES:
        user_role = user_context.get("role")
        allowed_roles = WORK_ORDER_LENS_ROLES[action]

        if not user_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "User role not found",
                    "status_code": 403,
                    "path": request.url.path if hasattr(request, "url") else "/v1/actions/execute"
                }
            )

        if user_role not in allowed_roles:
            logger.warning(f"[SECURITY] Role '{user_role}' denied for work order action '{action}'. Allowed: {allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": f"Role '{user_role}' is not authorized to perform action '{action}'",
                    "status_code": 403,
                    "path": request.url.path if hasattr(request, "url") else "/v1/actions/execute"
                }
            )

    # ========================================================================
    # ENTITY CONTEXT NORMALISATION + HANDLER DISPATCH (Phase 4)
    # resolve_entity_context maps entity_id → domain key once for all handlers.
    # Registered handlers return here. Unregistered actions fall through to the
    # legacy try/elif chain below. Delete the chain only after all actions migrated.
    # ========================================================================
    resolved_context = resolve_entity_context(action, request.context)

    if action in _ACTION_HANDLERS:
        tenant_alias = user_context.get("tenant_key_alias", "")
        db_client = get_tenant_supabase_client(tenant_alias)
        try:
            result = await _ACTION_HANDLERS[action](
                payload=payload,
                context=resolved_context,
                yacht_id=yacht_id,
                user_id=user_id,
                user_context=user_context,
                db_client=db_client,
            )
            # Handlers that return {"status": "error", ...} should be HTTP 400
            if isinstance(result, dict) and result.get("status") == "error":
                raise HTTPException(
                    status_code=400,
                    detail=result,
                )
            # ── Phase B ledger safety net ─────────────────────────────────
            # If the handler did not already write a ledger entry, write a
            # generic one now using ACTION_METADATA.  Fire-and-forget: a
            # failure here NEVER fails the mutation response.
            if isinstance(result, dict) and not result.get("_ledger_written"):
                from action_router.ledger_metadata import ACTION_METADATA
                meta = ACTION_METADATA.get(action)
                if meta:
                    try:
                        from routes.handlers.ledger_utils import build_ledger_event
                        _ACTION_SUMMARY = {
                            "add_note": "Note added",
                            "upload_document": "Document uploaded",
                            "reorder_part": "Part reorder requested",
                            "adjust_stock_quantity": "Stock quantity adjusted",
                            "add_checklist_item": "Checklist item added",
                            "complete_checklist_item": "Checklist item completed",
                        }
                        # For create actions the entity_id comes from the handler
                        # result, not the payload. Fallback chain:
                        #   payload[field] → result[field] → result.id → yacht_id
                        _id_field = meta["entity_id_field"]
                        entity_id = (
                            payload.get(_id_field)
                            or (isinstance(result, dict) and (result.get(_id_field) or result.get("id")))
                            or yacht_id
                        )
                        _summary = _ACTION_SUMMARY.get(action) or action.replace("_", " ").capitalize()
                        _entity_name = result.get("entity_name") if isinstance(result, dict) else None
                        # HMAC01 Option 1: if the caller supplied a signature
                        # payload (SIGNED variant actions), propagate it into
                        # ledger_events.metadata. Non-signed mutations still
                        # land here with metadata={} as before.
                        _sig = payload.get("signature") if isinstance(payload, dict) else None
                        _ledger_metadata = {"signature": _sig} if _sig else None
                        ledger_event = build_ledger_event(
                            yacht_id=yacht_id,
                            user_id=user_id,
                            event_type=meta["event_type"],
                            entity_type=meta["entity_type"],
                            entity_id=entity_id,
                            action=action,
                            user_role=user_context.get("role"),
                            change_summary=_summary,
                            entity_name=_entity_name,
                            metadata=_ledger_metadata,
                        )
                        db_client.table("ledger_events").insert(ledger_event).execute()
                    except Exception as _ledger_err:
                        if "204" not in str(_ledger_err):
                            logger.warning(
                                f"[Ledger safety net] {action}: {_ledger_err}"
                            )
            # ─────────────────────────────────────────────────────────────
            # Normalize: frontend expects {success: true} (boolean) but many
            # handlers return {status: "success"} (string). Inject success=true
            # on any non-error response so EntityLensPage.tsx:407 works.
            if isinstance(result, dict) and result.get("status") != "error":
                result.setdefault("success", True)
            return result
        except HTTPException:
            raise
        except (ValueError, KeyError) as e:
            logger.warning(f"Validation error for action '{action}': {e}")
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "VALIDATION_ERROR",
                    "message": str(e),
                }
            )
        except Exception as e:
            logger.error(f"Handler error for action '{action}': {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "error_code": "HANDLER_ERROR",
                    "message": str(e),
                }
            )

    # Legacy elif chain — handles all actions not yet migrated to HANDLERS
    try:
        # ===== WORK ORDER ACTIONS (P0 Actions 2-5) =====
        if action == "create_work_order_from_fault":
            # STRICT SIGNATURE VALIDATION (canon-critical for Fault Lens v1)
            signature = payload.get("signature")

            # 1. Check signature is present → 400 signature_required
            if not signature:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "error_code": "signature_required",
                        "message": "Signature payload required for SIGNED action"
                    }
                )

            # 2. Validate signature structure → 400 invalid_signature
            required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type"}
            if not isinstance(signature, dict):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "error_code": "invalid_signature",
                        "message": "Signature must be an object"
                    }
                )

            missing_keys = required_sig_keys - set(signature.keys())
            if missing_keys:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "error_code": "invalid_signature",
                        "message": f"Invalid signature: missing keys {sorted(missing_keys)}"
                    }
                )

            # 3. Validate signer role → 403 invalid_signer_role
            # Only captain and manager can sign create_work_order_from_fault
            role_at_signing = signature.get("role_at_signing")
            allowed_signer_roles = ["captain", "manager"]
            if role_at_signing not in allowed_signer_roles:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "invalid_signer_role",
                        "message": f"Role '{role_at_signing}' cannot sign this action",
                        "required_roles": allowed_signer_roles
                    }
                )

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

                    # Create audit log entry (Fault Lens v1 - signature NOT NULL)
                    audit_data = {
                        "yacht_id": yacht_id,
                        "action": "create_work_order_from_fault",
                        "entity_type": "work_order",
                        "entity_id": wo_id,
                        "user_id": user_id,
                        "signature": signature,  # Canonical signature with all required keys
                        "new_values": wo_result.data[0],
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    db_client.table("pms_audit_log").insert(audit_data).execute()

                    result = {
                        "status": "success",
                        "work_order_id": wo_id,
                        "message": "Work order created from fault"
                    }
                    try:
                        ledger_event = build_ledger_event(
                            yacht_id=yacht_id,
                            user_id=user_id,
                            event_type="create",
                            entity_type="work_order",
                            entity_id=wo_id,
                            action="create_work_order_from_fault",
                            user_role=user_context.get("role"),
                            change_summary="Work order created from fault",
                        )
                        db_client.table("ledger_events").insert(ledger_event).execute()
                    except Exception as ledger_err:
                        if "204" in str(ledger_err):
                            pass
                        else:
                            logger.warning(f"[Ledger] Failed to record {action}: {ledger_err}")
                else:
                    result = {
                        "status": "error",
                        "error_code": "INSERT_FAILED",
                        "message": "Failed to create work order"
                    }

        else:
            # Unknown action — all known actions are in _ACTION_HANDLERS (Phase 4)
            logger.warning(f"[ROUTING] Unknown action requested: {action}")
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "INVALID_ACTION",
                    "message": f"Action '{action}' is not recognized or not implemented"
                }
            )

    except HTTPException:
        # Let HTTPExceptions propagate with their original status code
        raise
    except PermissionError as e:
        # Permission errors from handlers should return 403
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # Validation errors from handlers should return 400
        logger.warning(f"Action validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Check if it's a SignatureRequiredError (custom exception from part_handlers)
        if e.__class__.__name__ == "SignatureRequiredError":
            logger.warning(f"Signature validation failed: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        # Check if it's a ConflictError (custom exception from part_handlers)
        elif e.__class__.__name__ == "ConflictError":
            logger.warning(f"Conflict detected: {e}")
            raise HTTPException(status_code=409, detail=str(e))
        error_str = str(e).lower()

        # Handle 204 No Content - postgrest-py throws but operation succeeded
        if "204" in error_str and "missing response" in error_str:
            logger.info(f"Action completed with 204 No Content (success): {action}")
            return JSONResponse(content={
                "status": "success",
                "success": True,
                "message": f"Action {action} completed successfully"
            })

        logger.error(f"Action execution failed: {e}", exc_info=True)

        # Parse database errors to return appropriate status codes (Phase 8)
        # 404 - Resource not found
        if "pgrst116" in error_str or "0 rows" in error_str or "result contains 0 rows" in error_str or "not found" in error_str:
            raise HTTPException(status_code=404, detail=str(e))
        # 400 - Foreign key violations (invalid reference)
        elif "foreign key" in error_str or "violates foreign key constraint" in error_str or "fk_" in error_str:
            raise HTTPException(status_code=400, detail=f"Invalid reference: {str(e)}")
        # 409 - Duplicate entries
        elif "unique constraint" in error_str or "duplicate key" in error_str or "already exists" in error_str:
            raise HTTPException(status_code=409, detail="Resource already exists")
        # 400 - Check constraint violations (data validation)
        elif "check constraint" in error_str or "violates check constraint" in error_str:
            raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")
        # 400 - Invalid signature
        elif "signature" in error_str and ("invalid" in error_str or "missing" in error_str or "required" in error_str):
            raise HTTPException(status_code=400, detail=str(e))
        # 403 - RLS/permission denied
        elif "policy" in error_str or "permission denied" in error_str:
            raise HTTPException(status_code=403, detail=f"Access denied: {str(e)}")
        # 500 - Real server errors (connection issues, server misconfiguration)
        else:
            raise HTTPException(status_code=500, detail=str(e))

    # Handle errors from handler (support both old and new formats)
    # New format (ActionResponseEnvelope): has "success" field
    # Old format: has "status" field
    if "success" in result:
        # New ActionResponseEnvelope format
        if not result["success"] and result.get("error"):
            error = result["error"]
            error_code = error.get("error_code", "UNKNOWN_ERROR")
            status_code = error.get("status_code", 500)
            # Preserve full error structure - use JSONResponse to avoid wrapping in {detail: {}}
            return JSONResponse(status_code=status_code, content=error)
    elif "status" in result and result["status"] == "error":
        # Old format - preserve full error structure including error_code
        error_code = result.get("error_code", "UNKNOWN_ERROR")

        # Map error codes to HTTP status codes
        if error_code in ("FAULT_NOT_FOUND", "WO_NOT_FOUND", "EQUIPMENT_NOT_FOUND", "PART_NOT_FOUND",
                          "NOT_FOUND", "RECEIVING_NOT_FOUND", "DOCUMENT_NOT_FOUND"):
            status_code = 404
        elif error_code == "SIGNATURE_REQUIRED":
            status_code = 400  # Client error - user forgot to sign (not a permission issue)
        elif error_code in ("RLS_DENIED", "INSUFFICIENT_PERMISSIONS"):
            status_code = 403
        elif error_code in ("CONFLICT", "DUPLICATE_RECORD", "DUPLICATE_WO_EXISTS"):
            status_code = 409
        elif error_code in ("INVALID_SIGNATURE", "INVALID_STORAGE_PATH", "INVALID_MODE",
                            "MISSING_REQUIRED_FIELD", "EXTRACT_PREPARE_ONLY",
                            "INVALID_STATUS_TRANSITION", "ALREADY_ACCEPTED",
                            "INVALID_CONFIRMATION_TOKEN", "AT_LEAST_ONE_ITEM_REQUIRED",
                            "WO_CLOSED", "INSUFFICIENT_STOCK", "NO_ITEMS", "MISSING_REASON",
                            "INVALID_QUANTITY", "NO_FIELDS_TO_UPDATE", "INSERT_FAILED"):
            status_code = 400
        else:
            status_code = 400  # Default to 400 for unknown error codes

        # Return error structure directly at top level (not wrapped in detail)
        error_response = {
            "status": "error",
            "error_code": error_code,
            "message": result.get("message", "Unknown error")
        }
        if "hint" in result:
            error_response["hint"] = result["hint"]

        return JSONResponse(status_code=status_code, content=error_response)

    # ── Centralised ledger write (non-fatal) ─────────────────────────────────
    # Captures every successful mutation automatically. Failures are logged only.
    try:
        _resp_dict = result if isinstance(result, dict) else {}
        if _resp_dict.get("status") == "success" or _resp_dict.get("success") is True:
            _entity_type, _entity_key = _ACTION_ENTITY_MAP.get(action, ("unknown", None))
            _entity_id = str(payload.get(_entity_key, "")) if _entity_key else ""

            if any(w in action for w in ("create", "report", "add", "log")):
                _ev_type = "create"
            elif any(w in action for w in ("approve", "accept")):
                _ev_type = "approval"
            elif any(w in action for w in ("reject", "cancel", "close", "write_off")):
                _ev_type = "rejection"
            elif any(w in action for w in ("complete", "start", "submit")):
                _ev_type = "status_change"
            else:
                _ev_type = "update"

            _ledger_ev = build_ledger_event(
                yacht_id=str(yacht_id),
                user_id=str(user_id),
                event_type=_ev_type,
                entity_type=_entity_type,
                entity_id=_entity_id or "00000000-0000-0000-0000-000000000000",
                action=action,
                user_role=user_role or "",
                change_summary=_resp_dict.get("message", action.replace("_", " ").title()),
                actor_name=user_context.get("email", ""),
                department=user_context.get("department", ""),
                event_category="write",
            )
            _ledger_tenant_alias = user_context.get("tenant_key_alias", "")
            if _ledger_tenant_alias:
                _ledger_db = get_tenant_supabase_client(_ledger_tenant_alias)
                _ledger_db.table("ledger_events").insert(_ledger_ev).execute()
    except Exception as _le:
        logger.warning(f"[Ledger] Non-fatal post-action write failed for '{action}': {_le}")
    # ─────────────────────────────────────────────────────────────────────────

    # Add execution_id to response for E2E test tracing
    import uuid
    result["execution_id"] = str(uuid.uuid4())
    result["action"] = request.action
    return result


# ============================================================================
# MY WORK ORDERS (READ) - v_my_work_orders_summary
# ============================================================================

@router.get("/work-orders/list-my")
async def list_my_work_orders_endpoint(
    group_key: Optional[str] = None,
    assigned_to: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List My Work Orders with deterministic grouping and sorting.

    Query params:
        group_key: Filter by group (overdue/critical/time_consuming/other)
        assigned_to: Filter by assignee (defaults to current user)

    Returns work orders grouped by:
        - overdue: days_overdue desc, criticality_rank asc nulls last, due_at asc
        - critical: criticality_rank asc, due_at asc nulls last
        - time_consuming: estimated_duration_minutes desc, due_at asc nulls last
        - other: status priority then last_activity_at desc

    Excludes deleted_at IS NOT NULL.
    """
    from handlers.list_handlers import ListHandlers

    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    # Role gating: crew, chief_engineer, chief_officer, captain, manager
    user_role = auth.get("role", "")
    allowed_roles = ["crew", "chief_engineer", "chief_officer", "captain", "manager"]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized for view_my_work_orders"
        )

    # Get tenant DB client
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    # Create handler and execute
    handlers = ListHandlers(db_client)
    result = await handlers.list_my_work_orders(
        yacht_id=yacht_id,
        user_id=user_id,
        assigned_to=assigned_to,
        group_key=group_key,
    )

    return result


# ============================================================================
# PAGINATED LIST ENDPOINTS (for Fragmented Routes / Quick Filters)
# ============================================================================

@router.get("/v1/work-orders")
async def list_work_orders_endpoint(
    offset: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List work orders with pagination and optional filters.

    Query params:
        offset: Pagination offset (default 0)
        limit: Page size (default 50, max 100)
        status: Filter by status (pending, open, in_progress, completed, etc.)
        priority: Filter by priority (low, medium, high, urgent)

    Returns:
        Paginated list of work orders for the user's yacht.
    """
    from handlers.list_handlers import ListHandlers

    yacht_id = auth["yacht_id"]

    # Role gating: crew and above can view work orders
    user_role = auth.get("role", "")
    allowed_roles = ["crew", "chief_engineer", "chief_officer", "captain", "manager", "admin"]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized for list_work_orders"
        )

    # Clamp limit
    limit = min(limit, 100)

    # Build filters
    filters = {}
    if status:
        filters["status"] = {"value": status}
    if priority:
        filters["priority"] = {"value": priority}

    # Get tenant DB client
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    # Create handler and execute
    handlers = ListHandlers(db_client)
    result = await handlers.list_work_orders(
        yacht_id=yacht_id,
        filters=filters,
        params={"offset": offset, "limit": limit},
    )

    # Transform to match frontend FetchResponse<WorkOrder> format
    data = result.get("data", {})
    items = data.get("items", [])
    total_count = data.get("total_count", len(items))

    return {
        "data": items,
        "total": total_count,
    }


@router.get("/v1/faults")
async def list_faults_endpoint(
    offset: int = 0,
    limit: int = 50,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List faults with pagination and optional filters.

    Query params:
        offset: Pagination offset (default 0)
        limit: Page size (default 50, max 100)
        severity: Filter by severity (critical, high, medium, low)
        resolved: Filter by resolved status (true/false)

    Returns:
        Paginated list of faults for the user's yacht.
    """
    from handlers.list_handlers import ListHandlers

    yacht_id = auth["yacht_id"]

    # Role gating
    user_role = auth.get("role", "")
    allowed_roles = ["crew", "chief_engineer", "chief_officer", "captain", "manager", "admin"]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized for list_faults"
        )

    # Clamp limit
    limit = min(limit, 100)

    # Build filters
    filters = {}
    if severity:
        filters["severity"] = {"value": severity}
    if resolved is not None:
        if resolved:
            filters["resolved_at"] = {"op": "not_null"}
        else:
            filters["resolved_at"] = {"op": "is_null"}

    # Get tenant DB client
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    # Create handler and execute
    handlers = ListHandlers(db_client)
    result = await handlers.list_faults(
        yacht_id=yacht_id,
        filters=filters,
        params={"offset": offset, "limit": limit},
    )

    # Transform to match frontend FetchResponse<Fault> format
    data = result.get("data", {})
    items = data.get("items", [])
    total_count = data.get("total_count", len(items))

    return {
        "data": items,
        "total": total_count,
    }


@router.get("/v1/inventory")
async def list_inventory_endpoint(
    offset: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    location: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List inventory/parts with pagination and optional filters.

    Query params:
        offset: Pagination offset (default 0)
        limit: Page size (default 50, max 100)
        category: Filter by category
        location: Filter by location

    Returns:
        Paginated list of parts/inventory for the user's yacht.
    """
    from handlers.list_handlers import ListHandlers

    yacht_id = auth["yacht_id"]

    # Role gating
    user_role = auth.get("role", "")
    allowed_roles = ["crew", "chief_engineer", "chief_officer", "captain", "manager", "admin"]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized for list_inventory"
        )

    # Clamp limit
    limit = min(limit, 100)

    # Build filters
    filters = {}
    if category:
        filters["category"] = {"value": category}
    if location:
        filters["location"] = {"value": location}

    # Get tenant DB client
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    # Create handler and execute
    handlers = ListHandlers(db_client)
    result = await handlers.list_parts(
        yacht_id=yacht_id,
        filters=filters,
        params={"offset": offset, "limit": limit},
    )

    # Transform to match frontend FetchResponse<Part> format
    data = result.get("data", {})
    items = data.get("items", [])
    total_count = data.get("total_count", len(items))

    return {
        "data": items,
        "total": total_count,
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/handover")
async def get_handover_items(
    limit: int = 200,
    category: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get handover draft items for the requesting user (not yet exported).

    Returns full row data scoped to:
    - yacht_id from JWT
    - added_by = requesting user
    - deleted_at IS NULL
    - export_status != 'exported'
    """
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    try:
        query = db_client.table("handover_items").select("*") \
            .eq("yacht_id", yacht_id) \
            .eq("added_by", user_id) \
            .is_("deleted_at", None) \
            .neq("export_status", "exported") \
            .order("created_at", desc=True) \
            .limit(limit)

        if category:
            query = query.eq("category", category)

        result = query.execute()
        items = result.data or []
        return {"status": "success", "items": items, "count": len(items)}

    except Exception as e:
        logger.error(f"Failed to fetch handover items: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch handover items: {str(e)}")




# ============================================================================
# ACTION LIST ENDPOINT
# ============================================================================

@router.get("/list")
async def list_actions_endpoint(
    q: str = None,
    domain: str = None,
    entity_id: str = None,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List available actions with role-gating and search.

    Query params:
        q: Search query (optional)
        domain: Filter by domain (e.g., "certificates")
        entity_id: Entity ID for storage path preview (optional)

    Returns:
        List of actions the user can perform, with storage options where applicable.
    """
    from action_router.registry import search_actions, get_storage_options, ACTION_REGISTRY
    from action_router.entity_actions import _build_field_schema

    user_role = auth.get("role")
    yacht_id = auth["yacht_id"]

    # Search actions with role-gating
    actions = search_actions(query=q, role=user_role, domain=domain)

    # Enrich with storage options AND field_schema so the frontend can
    # render forms directly without needing to re-query per action.
    for action in actions:
        action_def = ACTION_REGISTRY.get(action["action_id"])
        if action_def:
            action["field_schema"] = _build_field_schema(action_def)
        storage_opts = get_storage_options(
            action["action_id"],
            yacht_id=yacht_id,
            entity_id=entity_id,
        )
        if storage_opts:
            action["storage_options"] = storage_opts

    return {
        "query": q,
        "actions": actions,
        "total_count": len(actions),
        "role": user_role,
    }


@router.post("/suggestions")
async def suggest_actions_endpoint(
    request: Dict[str, Any],
    auth: dict = Depends(get_authenticated_user),
):
    """
    Suggest actions based on context with ambiguity detection (Phase 8).

    Request body:
        {
            "q": "search query (optional)",
            "domain": "domain filter (optional)",
            "context": {
                "entity_type": "fault|work_order|equipment|part",
                "entity_id": "UUID (optional)"
            }
        }

    Returns:
        {
            "actions": [...],      # Contextually-gated actions
            "candidates": [...],   # Disambiguation candidates (if ambiguous)
            "unresolved": [...],   # Queries that matched nothing
            "role": "crew|chief_engineer|...",
            "context": {...}       # Echo back context
        }

    Context gating:
    - create_work_order_from_fault: requires entity_type=fault AND entity_id
    - add_fault_photo, add_fault_note: requires entity_type=fault
    - add_work_order_photo: requires entity_type=work_order
    """
    from action_router.registry import search_actions, get_storage_options, ACTION_REGISTRY

    user_role = auth.get("role")
    yacht_id = auth["yacht_id"]

    # Extract request parameters
    query = request.get("q")
    domain = request.get("domain")
    context = request.get("context", {})
    entity_type = context.get("entity_type")
    entity_id = context.get("entity_id")

    # Search actions with role-gating
    all_actions = search_actions(query=query, role=user_role, domain=domain)

    # Apply context gating
    actions = []
    for action in all_actions:
        action_def = ACTION_REGISTRY.get(action["action_id"])
        if not action_def:
            continue

        # Check context requirements
        if action_def.context_required:
            # Verify all required context fields are present
            context_match = all(
                context.get(key) == value
                for key, value in action_def.context_required.items()
            )
            if not context_match:
                continue  # Skip this action if context doesn't match

        # Enrich with storage options
        storage_opts = get_storage_options(
            action["action_id"],
            yacht_id=yacht_id,
            entity_id=entity_id,
        )
        if storage_opts:
            action["storage_options"] = storage_opts

        actions.append(action)

    # Ambiguity detection
    candidates = []
    unresolved = []

    # If query provided but no matches, mark as unresolved
    if query and len(actions) == 0:
        unresolved.append({
            "query": query,
            "reason": "No actions matched query with current role and context"
        })

    # If multiple high-score matches (>0.8), mark as candidates for disambiguation
    if len(actions) > 1:
        high_score_actions = [a for a in actions if a.get("match_score", 0) > 0.8]
        if len(high_score_actions) > 1:
            candidates = high_score_actions

    return {
        "actions": actions,
        "candidates": candidates,
        "unresolved": unresolved,
        "total_count": len(actions),
        "role": user_role,
        "context": context,
    }


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
    auth: dict = Depends(get_authenticated_user)
):
    """Pre-fill data for log part usage."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _inventory_handlers = handlers.get("inventory_handlers")
    if not _inventory_handlers:
        raise HTTPException(status_code=500, detail="Inventory handlers not initialized")

    result = await _inventory_handlers.log_part_usage_prefill(
        part_id, yacht_id, user_id, work_order_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/add_to_handover/prefill")
async def add_to_handover_prefill(
    entity_type: str,
    entity_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Pre-fill data for add to handover."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_handlers = handlers.get("handover_handlers")
    if not _handover_handlers:
        raise HTTPException(status_code=500, detail="Handover handlers not initialized")

    result = await _handover_handlers.add_to_handover_prefill(
        entity_type, entity_id, yacht_id, user_id
    )

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


# ============================================================================
# HANDOVER WORKFLOW ENDPOINTS (Dual-hash, Dual-signature)
# ============================================================================

@router.post("/handover/{draft_id}/validate")
async def validate_handover_draft_route(
    draft_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Validate handover draft for finalization."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.validate_draft(
        yacht_id=yacht_id,
        user_id=user_id
    )

    return result


@router.post("/handover/{draft_id}/finalize")
async def finalize_handover_draft_route(
    draft_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Finalize draft: lock content and generate content_hash."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    user_role = auth.get("role")

    # Require officer+ role
    officer_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    if user_role not in officer_roles:
        raise HTTPException(status_code=403, detail=f"Requires officer+ role. Your role: {user_role}")

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.finalize_draft(
        yacht_id=yacht_id,
        user_id=user_id
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.post("/handover/{draft_id}/export")
async def export_handover_route(
    draft_id: str,
    export_type: str = "html",
    department: Optional[str] = None,
    shift_date: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """Generate handover export with document_hash."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    user_role = auth.get("role")

    # Require officer+ role
    officer_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    if user_role not in officer_roles:
        raise HTTPException(status_code=403, detail=f"Requires officer+ role. Your role: {user_role}")

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.export_handover(
        yacht_id=yacht_id,
        user_id=user_id,
        export_type=export_type,
        department=department,
        shift_date=shift_date
    )

    if result.get("status") == "error":
        # Map error codes to appropriate HTTP status codes
        error_code = result.get("error_code")
        status_code = 400

        if error_code == "NO_ITEMS":
            status_code = 404
        elif error_code == "NOT_FINALIZED":
            status_code = 409
        elif error_code == "SERVICE_UNAVAILABLE":
            status_code = 503
        elif error_code in ["DATABASE_ERROR", "EXPORT_FAILED"]:
            status_code = 500

        raise HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "error_code": error_code,
                "message": result.get("message")
            }
        )

    return result


@router.post("/handover/{export_id}/sign/outgoing")
async def sign_outgoing_route(
    export_id: str,
    note: Optional[str] = None,
    method: str = "typed",
    auth: dict = Depends(get_authenticated_user)
):
    """[DEPRECATED — T4 consolidation] Outgoing user signs the export.

    Canonical path is ``POST /v1/handover/export/{id}/submit`` (richer: signed
    HTML regen, review_status transition, full signature JSONB, ledger
    cascade). This route is kept for one release to drain any lingering
    callers; no frontend code path targets it. Fires a WARN log on every call
    to flag migration.
    """
    logger.warning(
        "DEPRECATED route hit: POST /v1/actions/handover/%s/sign/outgoing "
        "(caller user=%s role=%s). Migrate to "
        "POST /v1/handover/export/{id}/submit. Scheduled for removal once "
        "traffic drains (T4 consolidation, PR #642 follow-up).",
        export_id, auth.get("user_id"), auth.get("role"),
    )

    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    user_role = auth.get("role")

    # Require officer+ role
    officer_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    if user_role not in officer_roles:
        raise HTTPException(status_code=403, detail=f"Requires officer+ role. Your role: {user_role}")

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.sign_outgoing(
        export_id=export_id,
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=user_role,
        note=note,
        method=method
    )

    if result.get("status") == "error":
        status_code = 400
        if result.get("error_code") == "EXPORT_NOT_FOUND":
            status_code = 404
        elif result.get("error_code") == "INVALID_STATUS":
            status_code = 409
        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return result


@router.post("/handover/{export_id}/sign/incoming")
async def sign_incoming_route(
    export_id: str,
    acknowledge_critical: bool,
    note: Optional[str] = None,
    method: str = "typed",
    auth: dict = Depends(get_authenticated_user)
):
    """Incoming crew acknowledges the handover.

    Per handover.md role matrix (row 'Sign incoming (acknowledge)'): any authenticated
    user on the yacht may acknowledge a handover addressed to them. Acknowledgement is
    receipt, not review — yacht_id scoping is already enforced by `auth` dependency.
    """
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    user_role = auth.get("role")

    # No role gate: any authenticated user on the yacht can acknowledge receipt of a
    # handover. Review/approval gating happens at countersign (separate endpoint).

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.sign_incoming(
        export_id=export_id,
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=user_role,
        acknowledge_critical=acknowledge_critical,
        note=note,
        method=method
    )

    if result.get("status") == "error":
        status_code = 400
        if result.get("error_code") == "EXPORT_NOT_FOUND":
            status_code = 404
        elif result.get("error_code") == "INVALID_STATUS":
            status_code = 409
        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return result


@router.get("/handover/pending")
async def get_pending_handovers_route(
    role_filter: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """Get handovers pending signature."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.get_pending_handovers(
        yacht_id=yacht_id,
        user_id=user_id,
        role_filter=role_filter
    )

    return result


# ============================================================================
# GET /v1/handover/queue — aggregated candidates for next handover draft
# NOTE: MUST be declared before /{export_id}/verify — static routes must
# precede dynamic routes in FastAPI or the dynamic pattern matches "queue".
# ============================================================================

@router.get("/handover/queue")
async def get_handover_queue(
    auth: dict = Depends(get_authenticated_user),
    yacht_id_param: Optional[str] = Query(None, alias="yacht_id"),
    include: Optional[List[str]] = Query(None),
):
    """
    Return open items that are candidates for inclusion in the next handover.
    Sections: open_faults, overdue_work_orders, low_stock_parts, pending_orders, already_queued.
    Pass ?include[]=faults&include[]=work_orders to filter sections (default: all).
    Read-only — no ledger writes.
    """
    yacht_id = resolve_yacht_id(auth, yacht_id_param)
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])

    # Determine which sections to return
    all_sections = {"faults", "work_orders", "parts", "orders", "queued"}
    requested = set(include) if include else all_sections

    open_faults = []
    overdue_work_orders = []
    low_stock_parts = []
    pending_orders = []
    already_queued = []

    # ── open faults ──────────────────────────────────────────────────────────
    if "faults" in requested:
        try:
            result = db_client.table("pms_faults").select(
                "id, title, severity, equipment_name, created_at"
            ).eq("yacht_id", yacht_id).neq(
                "status", "resolved"
            ).order("created_at", desc=True).limit(20).execute()
            open_faults = result.data or []
        except Exception as e:
            logger.warning(f"[handover/queue] faults query failed: {e}")

    # ── overdue work orders ───────────────────────────────────────────────────
    if "work_orders" in requested:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            result = db_client.table("pms_work_orders").select(
                "id, title, priority, due_at, assigned_to"
            ).eq("yacht_id", yacht_id).not_.in_(
                "status", ["completed", "cancelled", "closed"]
            ).lt("due_at", now_iso).order("due_at").limit(20).execute()
            overdue_work_orders = result.data or []
        except Exception as e:
            logger.warning(f"[handover/queue] work_orders query failed: {e}")

    # ── low stock parts ───────────────────────────────────────────────────────
    if "parts" in requested:
        try:
            result = db_client.table("pms_parts").select(
                "id, name, quantity_on_hand, minimum_quantity"
            ).eq("yacht_id", yacht_id).execute()
            raw = result.data or []
            low_stock_parts = [
                {
                    "id": p["id"],
                    "name": p.get("name", ""),
                    "current_qty": p.get("quantity_on_hand", 0),
                    "reorder_threshold": p.get("minimum_quantity", 0),
                }
                for p in raw
                if (p.get("quantity_on_hand") or 0) <= (p.get("minimum_quantity") or 0)
            ][:20]
        except Exception as e:
            logger.warning(f"[handover/queue] parts query failed: {e}")

    # ── pending purchase orders ───────────────────────────────────────────────
    if "orders" in requested:
        try:
            result = db_client.table("pms_purchase_orders").select(
                "id, po_number, status, created_at"
            ).eq("yacht_id", yacht_id).in_(
                "status", ["draft", "pending", "submitted", "pending_approval"]
            ).order("created_at", desc=True).limit(20).execute()
            pending_orders = [
                {
                    "id": p["id"],
                    "title": p.get("po_number") or f"PO {p['id'][:8]}",
                    "status": p.get("status", ""),
                    "created_at": p.get("created_at", ""),
                }
                for p in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[handover/queue] orders query failed: {e}")

    # ── already queued handover items ─────────────────────────────────────────
    if "queued" in requested:
        try:
            result = db_client.table("handover_items").select(
                "id, entity_type, entity_id, summary, priority"
            ).eq("yacht_id", yacht_id).eq(
                "status", "pending"
            ).order("priority", desc=True).limit(50).execute()
            already_queued = result.data or []
        except Exception as e:
            logger.warning(f"[handover/queue] handover_items query failed: {e}")

    return {
        "open_faults": open_faults,
        "overdue_work_orders": overdue_work_orders,
        "low_stock_parts": low_stock_parts,
        "pending_orders": pending_orders,
        "already_queued": already_queued,
        "counts": {
            "faults": len(open_faults),
            "work_orders": len(overdue_work_orders),
            "parts": len(low_stock_parts),
            "orders": len(pending_orders),
            "already_queued": len(already_queued),
        },
    }


@router.get("/handover/{export_id}/verify")
async def verify_export_route(
    export_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """Get verification data for an export."""
    yacht_id = auth["yacht_id"]

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.verify_export(
        export_id=export_id,
        yacht_id=yacht_id
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))

    return result


# ============================================================================
# ADDITIONAL PREVIEW ENDPOINTS (P0 Action 7)
# ============================================================================

@router.post("/log_part_usage/preview")
async def log_part_usage_preview(
    request: PreviewRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """Preview part usage logging."""
    request.context["yacht_id"] = resolve_yacht_id(auth, request.context.get("yacht_id"))
    yacht_id = request.context["yacht_id"]
    user_id = auth["user_id"]
    payload = request.payload

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _inventory_handlers = handlers.get("inventory_handlers")
    if not _inventory_handlers:
        raise HTTPException(status_code=500, detail="Inventory handlers not initialized")

    result = await _inventory_handlers.log_part_usage_preview(
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
