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

from handlers.inventory_handlers import InventoryHandlers
from handlers.handover_handlers import HandoverHandlers, HandoverWorkflowHandlers
from handlers.manual_handlers import ManualHandlers
from action_router.validators import validate_payload_entities
from middleware.validation_middleware import validate_action_payload, InputValidationError
from middleware.state_machine import validate_state_transition, InvalidStateTransitionError
from action_router.registry import get_action
from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id

logger = logging.getLogger(__name__)

from handlers.ledger_utils import build_ledger_event
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
    "accept_receiving":            ("receiving", "receiving_id"),
    "reject_receiving":            ("receiving", "receiving_id"),
    "submit_purchase_order":       ("purchase_order", "purchase_order_id"),
    "approve_purchase_order":      ("purchase_order", "purchase_order_id"),
    "mark_po_received":            ("purchase_order", "purchase_order_id"),
    "cancel_purchase_order":       ("purchase_order", "purchase_order_id"),
    "delete_purchase_order":       ("purchase_order", "purchase_order_id"),
    "add_po_note":                 ("purchase_order", "purchase_order_id"),
    "update_purchase_status":      ("purchase_order", "purchase_order_id"),
    "add_item_to_purchase":        ("purchase_order", "purchase_order_id"),
    "approve_purchase":            ("purchase_order", "purchase_order_id"),
    "upload_invoice":              ("purchase_order", "purchase_order_id"),
    # Frontend aliases
    "submit_po":                   ("purchase_order", "purchase_order_id"),
    "approve_po":                  ("purchase_order", "purchase_order_id"),
    "receive_po":                  ("purchase_order", "purchase_order_id"),
    "cancel_po":                   ("purchase_order", "purchase_order_id"),
    "delete_po":                   ("purchase_order", "purchase_order_id"),
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
                    "inventory_handlers": InventoryHandlers(supabase),
                    "handover_handlers": HandoverHandlers(supabase),
                    "handover_workflow_handlers": HandoverWorkflowHandlers(supabase),
                    "manual_handlers": ManualHandlers(supabase),
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
        inventory_handlers = InventoryHandlers(supabase)
        handover_handlers = HandoverHandlers(supabase)
        handover_workflow_handlers = HandoverWorkflowHandlers(supabase)
        manual_handlers = ManualHandlers(supabase)
        logger.info("✅ All P0 action handlers initialized (default tenant fallback)")
    except Exception as e:
        logger.error(f"Failed to initialize handlers: {e}")
        inventory_handlers = None
        handover_handlers = None
        manual_handlers = None
else:
    logger.warning("⚠️ P0 handlers not initialized - no database connection")
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
    "close_fault", "acknowledge_fault", "resolve_fault",
    "reopen_fault", "create_work_order_from_fault",
    "add_fault_photo",
    "add_fault_note", "report_fault", "classify_fault",
    "investigate_fault", "archive_fault",
    "link_parts_to_fault", "unlink_part_from_fault",
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
    "add_checklist_item", "mark_checklist_item_complete",
    "submit_checklist", "set_work_order_frequency",
})

_PART_ACTIONS = frozenset({
    "consume_part", "receive_part", "transfer_part", "adjust_stock_quantity",
    "write_off_part", "add_to_shopping_list", "reorder_part", "view_part_stock",
    "view_part_location", "view_part_usage", "view_linked_equipment",
    "view_part_details", "check_stock_level", "log_part_usage",
})

_PO_ACTIONS = frozenset({
    "submit_purchase_order", "approve_purchase_order",
    "mark_po_received", "cancel_purchase_order", "delete_purchase_order",
    "convert_to_po",
    # Frontend-facing aliases + additional PO actions
    "submit_po", "approve_po", "receive_po", "cancel_po", "delete_po",
    "add_po_note", "order_part", "approve_purchase",
    "add_item_to_purchase", "update_purchase_status", "upload_invoice",
    "create_purchase_order",
})

_RECEIVING_ACTIONS = frozenset({
    "confirm_receiving", "accept_receiving", "reject_receiving",
    "flag_discrepancy", "create_receiving",
    "attach_receiving_image_with_comment", "extract_receiving_candidates",
    "update_receiving_fields", "add_receiving_item", "adjust_receiving_item",
    "link_invoice_document", "view_receiving_history", "draft_supplier_email",
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
    "submit_warranty_claim", "approve_warranty_claim",
    "reject_warranty_claim", "close_warranty_claim",
    "compose_warranty_email", "view_warranty_claim",
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
    "link_equipment_to_certificate",
    "unlink_equipment_from_certificate",
    # reads — entity_id → certificate_id resolution
    "list_vessel_certificates", "list_crew_certificates",
    "get_certificate_details", "view_certificate_history",
    "find_expiring_certificates",
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
    # REQUIRED FIELD VALIDATION - Delegated to registry.py (authoritative source)
    # ========================================================================
    # NOTE: The hardcoded REQUIRED_FIELDS dict was removed 2026-04-25 (FAULT05 Issue 7).
    # Registry.py carries required_fields per action and is the single source of truth.
    # Validation via registry happens in the handler dispatch below via _ACTION_HANDLERS.

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
    # ENTITY CONTEXT NORMALISATION + HANDLER DISPATCH (Phase 4)
    # resolve_entity_context maps entity_id → domain key once for all handlers.
    # Role validation is handled by the registry check above (lines 419-455).
    # All actions not in _ACTION_HANDLERS receive a 400 after this block.
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
                        from handlers.ledger_utils import build_ledger_event, write_ledger_event
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
                        write_ledger_event(db_client, ledger_event)
                    except Exception as _ledger_err:
                        if "204" not in str(_ledger_err):
                            logger.warning(
                                f"[Ledger safety net] {action}: {_ledger_err}"
                            )
            # ── Indexing trigger (PR-IDX-1) ───────────────────────────────
            # Self-contained: never borrows meta/_id_field from the ledger
            # block above — that block is skipped when _ledger_written=True.
            try:
                from services.indexing_trigger import enqueue_for_projection
                from action_router.ledger_metadata import ACTION_METADATA as _IDX_META_MAP
                _idx_meta = _IDX_META_MAP.get(action)
                if _idx_meta:
                    _idx_id_field = _idx_meta["entity_id_field"]
                    _index_entity_id = (
                        payload.get(_idx_id_field)
                        or (isinstance(result, dict) and (result.get(_idx_id_field) or result.get("id")))
                        or yacht_id
                    )
                    enqueue_for_projection(
                        entity_id=str(_index_entity_id),
                        entity_type=_idx_meta["entity_type"],
                        yacht_id=yacht_id,
                        db_client=db_client,
                    )
            except Exception as _idx_err:
                logger.warning(f"[Indexing trigger] {action}: {_idx_err}")
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
        except HTTPException:
            raise  # Pass handler-raised 404/403/400 through unchanged
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


    # All known actions are registered in _ACTION_HANDLERS (Phase 4).
    # Anything that reaches here was not registered — return 400.
    logger.warning(f"[ROUTING] Unknown action requested: {action}")
    raise HTTPException(
        status_code=400,
        detail={
            "status": "error",
            "error_code": "INVALID_ACTION",
            "message": f"Action '{action}' is not recognized or not implemented"
        }
    )


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
    """Get handover draft items for the requesting user (not yet exported)."""
    yacht_id = auth["yacht_id"]
    user_id = auth["user_id"]
    db_client = get_tenant_supabase_client(auth["tenant_key_alias"])
    handler = HandoverHandlers(db_client)
    try:
        return await handler.get_handover_items(
            yacht_id=yacht_id,
            user_id=user_id,
            limit=limit,
            category=category,
        )
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
    actions_count = len(_ACTION_HANDLERS)
    return {
        "status": "healthy" if actions_count > 0 else "degraded",
        "service": "p0_actions",
        "dispatch": "phase4",
        "registered_actions": actions_count,
        "version": "2.0.0"
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

    handlers = get_handlers_for_tenant(auth["tenant_key_alias"])
    _handover_wf = handlers.get("handover_workflow_handlers")
    if not _handover_wf:
        raise HTTPException(status_code=500, detail="Handover workflow handlers not initialized")

    result = await _handover_wf.export_handover(
        yacht_id=yacht_id,
        user_id=user_id,
        export_type=export_type,
        department=department,
        shift_date=shift_date,
        user_role=user_role,
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
        elif error_code == "FORBIDDEN":
            status_code = 403

        raise HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "error_code": error_code,
                "message": result.get("message")
            }
        )

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
    handler = HandoverHandlers(db_client)
    requested = set(include) if include else None
    return await handler.get_handover_queue(yacht_id=yacht_id, sections=requested)


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
