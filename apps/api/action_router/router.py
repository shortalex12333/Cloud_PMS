"""
Action Router - Main Entry Point

Single endpoint for all user-initiated mutations in CelesteOS.

POST /v1/actions/execute
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field
import time
import uuid
import logging

from .registry import (
    get_action,
    HandlerType,
    ActionVariant,
    search_actions,
    get_storage_options,
    check_context_gating,
    get_actions_for_domain,
    ACTION_REGISTRY,
    validate_signature_role,
    FieldMetadata as RegistryFieldMetadata,
)
from .validators import (
    validate_jwt,
    validate_yacht_isolation,
    validate_role_permission,
    validate_required_fields,
    validate_schema,
)
from .dispatchers import internal_dispatcher, n8n_dispatcher
from .logger import log_action
from .telemetry import (
    log_suggestion_viewed,
    log_prefill_requested,
    log_prefill_completed,
    log_execute_requested,
    log_execute_completed,
)

# Import prefill engine and field metadata
from common.prefill_engine import build_mutation_preview, build_prepare_response
from common.field_metadata import FieldMetadata as PrefillFieldMetadata

# Import tenant lookup and Supabase client
try:
    from integrations.supabase import get_tenant_client
except ImportError:
    get_tenant_client = None

logger = logging.getLogger(__name__)

# Feature flags for Fault Lens v1 (fail-closed)
try:
    from integrations.feature_flags import (
        FAULT_LENS_V1_ENABLED,
        check_fault_lens_feature,
    )
except ImportError:
    # Fallback if feature flags not available
    FAULT_LENS_V1_ENABLED = False
    def check_fault_lens_feature(feature: str):
        return False, "Feature flags not available"

# Import tenant lookup from auth middleware (Architecture Option 1)
try:
    from middleware.auth import lookup_tenant_for_user
except ImportError:
    # Fallback if middleware not available
    lookup_tenant_for_user = None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class ActionRequest(BaseModel):
    """Request model for action execution."""

    action: str
    context: Dict[str, Any]
    payload: Dict[str, Any]


class ActionResponse(BaseModel):
    """Response model for action execution."""

    status: str
    action: str
    execution_id: str = None
    result: Dict[str, Any] = None
    error_code: str = None
    message: str = None


# ============================================================================
# PREPARE ENDPOINT MODELS (for /v1/actions/prepare)
# ============================================================================


class PrepareRequest(BaseModel):
    """Request model for prepare endpoint."""

    q: str
    domain: str
    candidate_action_ids: List[str]
    context: Dict[str, Any]  # yacht_id, user_role
    hint_entities: Optional[Dict[str, Any]] = None
    client: Dict[str, str]  # timezone, now_iso


class PrefillField(BaseModel):
    """Prefilled field with confidence and source."""

    value: Any
    confidence: float
    source: str  # entity_resolver, keyword_map, temporal, template, context, backend_auto


class AmbiguityCandidate(BaseModel):
    """Candidate option for ambiguous field."""

    id: str
    label: str
    confidence: float


class Ambiguity(BaseModel):
    """Ambiguous field with multiple candidates."""

    field: str
    candidates: List[AmbiguityCandidate]


class PrepareError(BaseModel):
    """Structured error for prepare endpoint."""

    error_code: str
    message: str
    field: Optional[str] = None


class PrepareResponse(BaseModel):
    """Response model for prepare endpoint."""

    action_id: str
    match_score: float
    ready_to_commit: bool
    prefill: Dict[str, PrefillField]
    missing_required_fields: List[str]
    ambiguities: List[Ambiguity]
    errors: List[PrepareError]


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/actions", tags=["actions"])


@router.post("/execute", response_model=ActionResponse)
async def execute_action(
    request_data: ActionRequest,
    authorization: str = Header(None),
) -> ActionResponse:
    """
    Execute an action with full validation and dispatch.

    Flow:
    1. Validate JWT → extract user context
    2. Validate action exists
    3. Validate yacht isolation
    4. Validate role permissions
    5. Validate required fields
    6. Validate schema (if defined)
    7. Dispatch to handler
    8. Log execution
    9. Return result

    Args:
        request_data: Action request with action, context, payload
        authorization: JWT token from Authorization header

    Returns:
        ActionResponse with status and result/error

    Raises:
        HTTPException: On validation or execution errors
    """
    start_time = time.time()
    action_id = request_data.action
    execution_id = str(uuid.uuid4())

    try:
        # ====================================================================
        # STEP 1: Validate JWT and extract user context
        # ====================================================================
        jwt_result = validate_jwt(authorization)
        if not jwt_result.valid:
            await log_action(
                action_id=action_id,
                action_label=action_id,
                yacht_id=request_data.context.get("yacht_id", "unknown"),
                user_id="unknown",
                payload=request_data.payload,
                status="error",
                error_message=jwt_result.error.message,
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": jwt_result.error.error_code,
                    "message": jwt_result.error.message,
                    "action": action_id,
                },
            )

        user_context = jwt_result.context

        # ====================================================================
        # STEP 1.5: Resolve tenant from MASTER DB if yacht_id not in JWT
        # Architecture Option 1: JWT verification + DB tenant lookup
        # ====================================================================
        if not user_context.get("yacht_id") and lookup_tenant_for_user:
            tenant_info = lookup_tenant_for_user(user_context["user_id"])
            if tenant_info:
                user_context["yacht_id"] = tenant_info["yacht_id"]
                user_context["tenant_key_alias"] = tenant_info.get("tenant_key_alias")
                # SECURITY: ONLY use tenant-scoped role from auth_users_roles
                # NEVER fall back to JWT/MASTER role - deny-by-default
                if not tenant_info.get("role"):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "status": "error",
                            "error_code": "no_tenant_role",
                            "message": "User has no active role on yacht",
                            "action": action_id,
                        },
                    )
                user_context["role"] = tenant_info["role"]
            else:
                # User not assigned to any tenant
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "user_no_tenant",
                        "message": "User is not assigned to any yacht/tenant",
                        "action": action_id,
                    },
                )

        # ====================================================================
        # STEP 2: Validate action exists
        # ====================================================================
        try:
            action_def = get_action(action_id)
        except KeyError:
            await log_action(
                action_id=action_id,
                action_label=action_id,
                yacht_id=request_data.context.get("yacht_id", "unknown"),
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=f"Action '{action_id}' not found",
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "action_not_found",
                    "message": f"Action '{action_id}' not found in registry",
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 3: Validate yacht isolation
        # ====================================================================
        yacht_result = validate_yacht_isolation(
            request_data.context, user_context
        )
        if not yacht_result.valid:
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context.get("yacht_id", "unknown"),
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=yacht_result.error.message,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": yacht_result.error.error_code,
                    "message": yacht_result.error.message,
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 4: Validate role permissions
        # ====================================================================
        role_result = validate_role_permission(
            user_context, action_def.allowed_roles, action_id
        )
        if not role_result.valid:
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=role_result.error.message,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": role_result.error.error_code,
                    "message": role_result.error.message,
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 4.5: Validate SIGNED actions (Fault Lens v1)
        # ====================================================================
        if action_def.variant == ActionVariant.SIGNED:
            # Check feature flag for faults domain signed actions
            if action_def.domain == "faults":
                enabled, message = check_fault_lens_feature("signed_actions")
                if not enabled:
                    raise HTTPException(
                        status_code=503,
                        detail={
                            "status": "error",
                            "error_code": "FEATURE_DISABLED",
                            "message": message,
                            "action": action_id,
                        },
                    )

            # Validate signature is present
            signature = request_data.payload.get("signature")
            if not signature:
                await log_action(
                    action_id=action_id,
                    action_label=action_def.label,
                    yacht_id=request_data.context["yacht_id"],
                    user_id=user_context["user_id"],
                    payload=request_data.payload,
                    status="error",
                    error_message="Signature required for SIGNED action",
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "error_code": "signature_required",
                        "message": "Signature payload required for SIGNED action",
                        "action": action_id,
                    },
                )

            # Validate signature structure
            required_keys = ["signed_at", "user_id", "role_at_signing", "signature_type"]
            missing_keys = [k for k in required_keys if k not in signature]
            if missing_keys:
                await log_action(
                    action_id=action_id,
                    action_label=action_def.label,
                    yacht_id=request_data.context["yacht_id"],
                    user_id=user_context["user_id"],
                    payload=request_data.payload,
                    status="error",
                    error_message=f"Invalid signature: missing {missing_keys}",
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "status": "error",
                        "error_code": "invalid_signature",
                        "message": f"Invalid signature: missing keys {missing_keys}",
                        "action": action_id,
                    },
                )

            # Validate signer role
            role_at_signing = signature.get("role_at_signing")
            sig_result = validate_signature_role(action_id, role_at_signing)
            if not sig_result["valid"]:
                await log_action(
                    action_id=action_id,
                    action_label=action_def.label,
                    yacht_id=request_data.context["yacht_id"],
                    user_id=user_context["user_id"],
                    payload=request_data.payload,
                    status="error",
                    error_message=sig_result["reason"],
                )
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "invalid_signer_role",
                        "message": sig_result["reason"],
                        "action": action_id,
                        "required_roles": sig_result["required_roles"],
                    },
                )

        # ====================================================================
        # STEP 5: Merge parameters (context + payload + user_context)
        # ====================================================================
        params = {
            **request_data.context,
            **request_data.payload,
            "user_id": user_context["user_id"],
            "role": user_context["role"],
        }

        # ====================================================================
        # STEP 6: Validate required fields
        # ====================================================================
        field_result = validate_required_fields(
            params, action_def.required_fields, action_id
        )
        if not field_result.valid:
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=field_result.error.message,
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": field_result.error.error_code,
                    "message": field_result.error.message,
                    "action": action_id,
                    "details": field_result.error.details,
                },
            )

        # ====================================================================
        # STEP 7: Validate schema (if defined)
        # ====================================================================
        schema_result = validate_schema(
            request_data.payload, action_def.schema_file, action_id
        )
        if not schema_result.valid:
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=schema_result.error.message,
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": schema_result.error.error_code,
                    "message": schema_result.error.message,
                    "action": action_id,
                    "details": schema_result.error.details,
                },
            )

        # ====================================================================
        # STEP 7.5: Log action_execute_requested telemetry event
        # ====================================================================
        log_execute_requested(
            user_id=str(user_context["user_id"]),
            yacht_id=str(request_data.context["yacht_id"]),
            action_id=action_id,
            payload_keys=list(request_data.payload.keys()),
        )

        # ====================================================================
        # STEP 8: Dispatch to handler
        # ====================================================================
        try:
            if action_def.handler_type == HandlerType.INTERNAL:
                result = await internal_dispatcher.dispatch(action_id, params)
            elif action_def.handler_type == HandlerType.N8N:
                result = await n8n_dispatcher.dispatch(action_id, params)
            else:
                raise ValueError(f"Unknown handler type: {action_def.handler_type}")

        except ValueError as e:
            # Validation/business logic errors (400)
            duration_ms = int((time.time() - start_time) * 1000)
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=str(e),
            )
            # Log action_execute_completed telemetry event for error
            log_execute_completed(
                action_id=action_id,
                user_id=str(user_context["user_id"]),
                yacht_id=str(request_data.context["yacht_id"]),
                status="error",
                duration_ms=duration_ms,
                error_code="handler_validation_error",
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "handler_validation_error",
                    "message": str(e),
                    "action": action_id,
                },
            )

        except Exception as e:
            # Handler/n8n failures (502)
            duration_ms = int((time.time() - start_time) * 1000)
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=str(e),
            )
            # Log action_execute_completed telemetry event for error
            log_execute_completed(
                action_id=action_id,
                user_id=str(user_context["user_id"]),
                yacht_id=str(request_data.context["yacht_id"]),
                status="error",
                duration_ms=duration_ms,
                error_code="handler_execution_error",
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "status": "error",
                    "error_code": "handler_execution_error",
                    "message": str(e),
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 9: Log success
        # ====================================================================
        duration_ms = int((time.time() - start_time) * 1000)
        await log_action(
            action_id=action_id,
            action_label=action_def.label,
            yacht_id=request_data.context["yacht_id"],
            user_id=user_context["user_id"],
            payload=request_data.payload,
            status="success",
            result=result,
            duration_ms=duration_ms,
            execution_id=execution_id,
        )

        # Log action_execute_completed telemetry event
        entity_id = None
        if isinstance(result, dict):
            # Extract entity_id from result (common patterns)
            entity_id = result.get("id") or result.get("entity_id") or result.get(
                "work_order_id"
            ) or result.get("note_id") or result.get("fault_id")
            if entity_id:
                entity_id = str(entity_id)

        log_execute_completed(
            action_id=action_id,
            user_id=str(user_context["user_id"]),
            yacht_id=str(request_data.context["yacht_id"]),
            status="success",
            duration_ms=duration_ms,
            entity_id=entity_id,
        )

        # ====================================================================
        # STEP 10: Return success response
        # ====================================================================
        return ActionResponse(
            status="success",
            action=action_id,
            execution_id=execution_id,
            result=result,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        await log_action(
            action_id=action_id,
            action_label=action_id,
            yacht_id=request_data.context.get("yacht_id", "unknown"),
            user_id=user_context.get("user_id", "unknown") if "user_context" in locals() else "unknown",
            payload=request_data.payload,
            status="error",
            error_message=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "internal_server_error",
                "message": f"Unexpected error: {str(e)}",
                "action": action_id,
            },
        )


# ============================================================================
# ACTION LIST ENDPOINT
# ============================================================================


@router.get("/list")
async def list_actions_endpoint(
    q: str = None,
    domain: str = None,
    entity_id: str = None,
    authorization: str = Header(None),
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
    # Validate JWT and extract user context
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": jwt_result.error.error_code,
                "message": jwt_result.error.message,
            },
        )

    user_context = jwt_result.context
    user_role = user_context.get("role")
    yacht_id = user_context.get("yacht_id")

    # Search actions with role-gating
    actions = search_actions(query=q, role=user_role, domain=domain)

    # Enrich with storage options
    for action in actions:
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


# ============================================================================
# SUGGESTIONS API ENDPOINT
# ============================================================================


class SuggestionsRequest(BaseModel):
    """Request model for suggestions endpoint."""

    query_text: str = None
    domain: str = None
    entity_type: str = None
    entity_id: str = None
    limit: int = 5


class SuggestionsResponse(BaseModel):
    """Response model for suggestions endpoint."""

    candidates: list
    unresolved: list = []
    focused_entity: dict = None
    warnings: list = []


@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    request_data: SuggestionsRequest,
    authorization: str = Header(None),
) -> SuggestionsResponse:
    """
    Get action suggestions based on query text and context.

    Fault Lens v1 requirements:
    - Do NOT surface create_work_order_from_fault from free-text search
    - Only list context-gated actions when focused on appropriate entity
    - Return multiple candidates (never just one when there are matches)
    - Include unresolved[] for ambiguous entity references
    - Domain filter is honored; match_scores are deterministic

    Args:
        request_data: SuggestionsRequest with query, domain, entity context
        authorization: JWT token from Authorization header

    Returns:
        SuggestionsResponse with candidates[], unresolved[], focused_entity
    """
    # Feature flag check for faults domain
    if request_data.domain == "faults":
        enabled, message = check_fault_lens_feature("suggestions")
        if not enabled:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "error_code": "FEATURE_DISABLED",
                    "message": message,
                },
            )

    # Validate JWT and extract user context
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "error_code": jwt_result.error.error_code,
                "message": jwt_result.error.message,
            },
        )

    user_context = jwt_result.context
    user_role = user_context.get("role")
    yacht_id = user_context.get("yacht_id")

    # Build candidates list
    candidates = []
    unresolved = []
    warnings = []

    # Search actions with role-gating and optional domain filter
    actions = search_actions(
        query=request_data.query_text,
        role=user_role,
        domain=request_data.domain,
    )

    # Filter by context gating
    for action in actions:
        action_id = action["action_id"]

        # Check context gating requirements
        gating_result = check_context_gating(
            action_id,
            entity_type=request_data.entity_type,
            entity_id=request_data.entity_id,
        )

        if not gating_result["allowed"]:
            # Context-gated action not allowed in current context
            # Do NOT include in candidates (per brief: "Do not surface from free-text")
            continue

        # Enrich with storage options if applicable
        storage_opts = get_storage_options(
            action_id,
            yacht_id=yacht_id,
            entity_id=request_data.entity_id,
        )
        if storage_opts:
            action["storage_options"] = storage_opts

        candidates.append(action)

    # Limit results
    candidates = candidates[:request_data.limit]

    # Build focused_entity if entity context provided
    focused_entity = None
    if request_data.entity_type and request_data.entity_id:
        focused_entity = {
            "entity_type": request_data.entity_type,
            "entity_id": request_data.entity_id,
        }

        # Add context-specific actions when focused
        # These are actions that require entity context
        context_actions = []
        for action_id, action_def in ACTION_REGISTRY.items():
            if action_def.context_required:
                # Check if this action is allowed for current context
                gating = check_context_gating(
                    action_id,
                    entity_type=request_data.entity_type,
                    entity_id=request_data.entity_id,
                )
                if gating["allowed"] and user_role in action_def.allowed_roles:
                    # Check if already in candidates
                    existing_ids = [c["action_id"] for c in candidates]
                    if action_id not in existing_ids:
                        context_actions.append({
                            "action_id": action_id,
                            "label": action_def.label,
                            "variant": action_def.variant.value if action_def.variant else "MUTATE",
                            "allowed_roles": action_def.allowed_roles,
                            "required_fields": action_def.required_fields,
                            "domain": action_def.domain,
                            "match_score": 0.95,  # High score for context-specific actions
                            "context_match": True,
                        })

        # Add context actions to candidates (but keep total under limit)
        for ctx_action in context_actions:
            if len(candidates) < request_data.limit:
                candidates.append(ctx_action)

    # Ensure we never return just one candidate if there are more available
    # (Per brief: "Return multiple candidates (never just one)")
    if len(candidates) == 1 and len(actions) > 1:
        # Try to add more candidates up to limit
        for action in actions[1:request_data.limit]:
            action_id = action["action_id"]
            gating_result = check_context_gating(
                action_id,
                entity_type=request_data.entity_type,
                entity_id=request_data.entity_id,
            )
            if gating_result["allowed"]:
                existing_ids = [c["action_id"] for c in candidates]
                if action_id not in existing_ids:
                    candidates.append(action)
                    if len(candidates) >= request_data.limit:
                        break

    # Sort by match_score descending
    candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # Log action_suggestion_viewed telemetry event
    log_suggestion_viewed(
        user_id=str(user_context.get("user_id", "unknown")),
        yacht_id=str(yacht_id or "unknown"),
        query_text=request_data.query_text,
        suggested_actions=[c.get("action_id", "") for c in candidates],
    )

    return SuggestionsResponse(
        candidates=candidates,
        unresolved=unresolved,
        focused_entity=focused_entity,
        warnings=warnings,
    )


# ============================================================================
# PREFILL ENDPOINT
# ============================================================================


class PrefillPayload(BaseModel):
    """Payload for prefill endpoint."""

    query_text: str = Field(..., description="Natural language query text")
    extracted_entities: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional pre-extracted entities from NLP pipeline"
    )


class PrefillRequest(BaseModel):
    """Request model for prefill endpoint."""

    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context including yacht_id (validated from JWT)"
    )
    payload: PrefillPayload


class PrefillResponse(BaseModel):
    """Response model for prefill endpoint."""

    status: str
    mutation_preview: Dict[str, Any] = Field(default_factory=dict)
    missing_required: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    dropdown_options: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    ready_to_commit: bool = False


def convert_registry_field_metadata_to_prefill(
    registry_metadata: List[RegistryFieldMetadata]
) -> Dict[str, PrefillFieldMetadata]:
    """
    Convert registry FieldMetadata list to prefill engine dict format.

    The registry stores field_metadata as a list of FieldMetadata objects.
    The prefill engine expects a dict with field names as keys.

    Args:
        registry_metadata: List of FieldMetadata from ACTION_REGISTRY

    Returns:
        Dict mapping field names to PrefillFieldMetadata objects
    """
    result = {}

    for rm in registry_metadata:
        # Convert registry FieldMetadata to prefill FieldMetadata
        # Note: registry uses FieldClassification enum, prefill uses string literals
        classification = rm.classification.value if hasattr(rm.classification, 'value') else str(rm.classification)

        result[rm.name] = PrefillFieldMetadata(
            name=rm.name,
            classification=classification,
            auto_populate_from=rm.auto_populate_from,
            lookup_required=rm.lookup_required,
            description=rm.description,
            options=rm.options,
        )

    return result


@router.post("/prefill/{action_id}", response_model=PrefillResponse)
async def prefill_action(
    action_id: str,
    request_data: PrefillRequest,
    authorization: str = Header(None),
) -> PrefillResponse:
    """
    Generate mutation preview for an action using NLP-extracted entities.

    This is a generic prefill endpoint that works with any action that has
    field_metadata defined in the ACTION_REGISTRY.

    Flow:
    1. Validate JWT -> extract user context
    2. Validate action exists and has field_metadata
    3. Validate yacht isolation
    4. Validate role permissions
    5. Convert registry field_metadata to prefill format
    6. Call build_mutation_preview() from prefill_engine
    7. Return standardized prefill response

    Args:
        action_id: Action identifier from ACTION_REGISTRY
        request_data: PrefillRequest with context and payload
        authorization: JWT token from Authorization header

    Returns:
        PrefillResponse with mutation_preview, missing_required, warnings,
        dropdown_options, and ready_to_commit status

    Raises:
        HTTPException: On validation or prefill errors
    """
    try:
        # ====================================================================
        # STEP 1: Validate JWT and extract user context
        # ====================================================================
        jwt_result = validate_jwt(authorization)
        if not jwt_result.valid:
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": jwt_result.error.error_code,
                    "message": jwt_result.error.message,
                    "action": action_id,
                },
            )

        user_context = jwt_result.context

        # ====================================================================
        # STEP 1.5: Resolve tenant from MASTER DB if yacht_id not in JWT
        # ====================================================================
        if not user_context.get("yacht_id") and lookup_tenant_for_user:
            tenant_info = lookup_tenant_for_user(user_context["user_id"])
            if tenant_info:
                user_context["yacht_id"] = tenant_info["yacht_id"]
                user_context["tenant_key_alias"] = tenant_info.get("tenant_key_alias")
                if not tenant_info.get("role"):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "status": "error",
                            "error_code": "no_tenant_role",
                            "message": "User has no active role on yacht",
                            "action": action_id,
                        },
                    )
                user_context["role"] = tenant_info["role"]
            else:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "user_no_tenant",
                        "message": "User is not assigned to any yacht/tenant",
                        "action": action_id,
                    },
                )

        # ====================================================================
        # STEP 2: Validate action exists and has field_metadata
        # ====================================================================
        try:
            action_def = get_action(action_id)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "error_code": "action_not_found",
                    "message": f"Action '{action_id}' not found in registry",
                    "action": action_id,
                },
            )

        # Check if action has field_metadata for prefill
        if not action_def.field_metadata:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "no_field_metadata",
                    "message": f"Action '{action_id}' does not support prefill (no field_metadata defined)",
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 3: Validate yacht isolation
        # ====================================================================
        # Use yacht_id from JWT context, not from request
        yacht_id = user_context.get("yacht_id")
        if not yacht_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "missing_yacht_id",
                    "message": "yacht_id not found in JWT context",
                    "action": action_id,
                },
            )

        # Validate request context matches JWT context if provided
        if request_data.context.get("yacht_id"):
            yacht_result = validate_yacht_isolation(
                request_data.context, user_context
            )
            if not yacht_result.valid:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": yacht_result.error.error_code,
                        "message": yacht_result.error.message,
                        "action": action_id,
                    },
                )

        # ====================================================================
        # STEP 4: Validate role permissions
        # ====================================================================
        role_result = validate_role_permission(
            user_context, action_def.allowed_roles, action_id
        )
        if not role_result.valid:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": "error",
                    "error_code": role_result.error.error_code,
                    "message": role_result.error.message,
                    "action": action_id,
                },
            )

        # ====================================================================
        # STEP 5: Convert registry field_metadata to prefill format
        # ====================================================================
        field_metadata_dict = convert_registry_field_metadata_to_prefill(
            action_def.field_metadata
        )

        # ====================================================================
        # STEP 6: Get Supabase client for lookups
        # ====================================================================
        supabase_client = None
        tenant_key_alias = user_context.get("tenant_key_alias")

        if get_tenant_client:
            try:
                supabase_client = get_tenant_client(tenant_key_alias)
            except Exception as e:
                logger.warning(f"[Prefill] Failed to get tenant client: {e}")

        if not supabase_client:
            # Fallback warning - lookups will fail but prefill can still work
            logger.warning(
                f"[Prefill] No Supabase client available for action {action_id}. "
                "Entity lookups will fail."
            )

        # ====================================================================
        # STEP 7: Call build_mutation_preview
        # ====================================================================
        prefill_start_time = time.time()
        query_text = request_data.payload.query_text
        extracted_entities = request_data.payload.extracted_entities or {}
        user_id = user_context.get("user_id")

        # Log action_prefill_requested telemetry event
        log_prefill_requested(
            user_id=str(user_id or "unknown"),
            yacht_id=str(yacht_id),
            action_id=action_id,
            query_text=query_text,
            extracted_entities=extracted_entities,
        )

        # Build additional context for lookups
        lookup_context = {
            **request_data.context,
            "action_id": action_id,
        }

        preview_result = await build_mutation_preview(
            query_text=query_text,
            extracted_entities=extracted_entities,
            field_metadata=field_metadata_dict,
            yacht_id=yacht_id,
            supabase_client=supabase_client,
            user_id=user_id,
            context=lookup_context,
        )

        # ====================================================================
        # STEP 8: Log action_prefill_completed telemetry event
        # ====================================================================
        prefill_duration_ms = int((time.time() - prefill_start_time) * 1000)
        missing_fields = preview_result.get("missing_required", [])
        dropdown_opts = preview_result.get("dropdown_options", {})
        ready_to_commit = preview_result.get("ready_to_commit", False)

        log_prefill_completed(
            action_id=action_id,
            user_id=str(user_id or "unknown"),
            yacht_id=str(yacht_id),
            ready_to_commit=ready_to_commit,
            disambiguation_required=len(dropdown_opts) > 0,
            missing_fields=missing_fields,
            duration_ms=prefill_duration_ms,
        )

        # ====================================================================
        # STEP 9: Return standardized response
        # ====================================================================
        return PrefillResponse(
            status="success",
            mutation_preview=preview_result.get("mutation_preview", {}),
            missing_required=missing_fields,
            warnings=preview_result.get("warnings", []),
            dropdown_options=dropdown_opts,
            ready_to_commit=ready_to_commit,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[Prefill] Unexpected error for action {action_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "prefill_error",
                "message": f"Prefill failed: {str(e)}",
                "action": action_id,
            },
        )


# ============================================================================
# PREPARE ENDPOINT (for /v1/actions/prepare)
# ============================================================================


@router.post("/prepare", response_model=PrepareResponse)
async def prepare_action(
    request_data: PrepareRequest,
    authorization: str = Header(None),
) -> PrepareResponse:
    """
    Generate action prefill preview from NLP query with per-field confidence.

    This endpoint accepts natural language queries and returns prefilled form
    data with confidence scores, missing fields, and disambiguation options.

    Flow:
    1. Validate JWT -> extract user context
    2. Validate yacht isolation (RLS enforcement)
    3. Call build_prepare_response() from prefill_engine
    4. Return structured PrepareResponse

    Args:
        request_data: PrepareRequest with q, domain, candidate_action_ids, context, hint_entities, client
        authorization: JWT token from Authorization header

    Returns:
        PrepareResponse with action_id, prefill (with confidence per field),
        missing_required_fields, ambiguities, and structured errors

    Raises:
        HTTPException: On validation or preparation errors

    Example request:
        POST /v1/actions/prepare
        {
            "q": "create urgent work order for main engine next week",
            "domain": "work_orders",
            "candidate_action_ids": ["create_work_order"],
            "context": {"yacht_id": "uuid", "user_role": "chief_engineer"},
            "hint_entities": {"equipment": "main engine", "priority": "urgent", "scheduled_date": "next week"},
            "client": {"timezone": "America/New_York", "now_iso": "2026-03-01T16:00:00-05:00"}
        }

    Example response:
        {
            "action_id": "create_work_order",
            "match_score": 0.95,
            "ready_to_commit": false,
            "prefill": {
                "equipment_id": {"value": "uuid", "confidence": 0.92, "source": "entity_resolver"},
                "priority": {"value": "HIGH", "confidence": 0.95, "source": "keyword_map"},
                "scheduled_date": {"value": "2026-03-09", "confidence": 0.85, "source": "temporal"}
            },
            "missing_required_fields": ["description"],
            "ambiguities": [],
            "errors": []
        }
    """
    try:
        # ====================================================================
        # STEP 1: Validate JWT and extract user context
        # ====================================================================
        jwt_result = validate_jwt(authorization)
        if not jwt_result.valid:
            raise HTTPException(
                status_code=401,
                detail={
                    "status": "error",
                    "error_code": jwt_result.error.error_code,
                    "message": jwt_result.error.message,
                },
            )

        user_context = jwt_result.context

        # ====================================================================
        # STEP 1.5: Resolve tenant from MASTER DB if yacht_id not in JWT
        # ====================================================================
        if not user_context.get("yacht_id") and lookup_tenant_for_user:
            tenant_info = lookup_tenant_for_user(user_context["user_id"])
            if tenant_info:
                user_context["yacht_id"] = tenant_info["yacht_id"]
                user_context["tenant_key_alias"] = tenant_info.get("tenant_key_alias")
                if not tenant_info.get("role"):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "status": "error",
                            "error_code": "no_tenant_role",
                            "message": "User has no active role on yacht",
                        },
                    )
                user_context["role"] = tenant_info["role"]
            else:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": "user_no_tenant",
                        "message": "User is not assigned to any yacht/tenant",
                    },
                )

        # ====================================================================
        # STEP 2: Validate yacht isolation (RLS enforcement)
        # ====================================================================
        yacht_id = user_context.get("yacht_id")
        if not yacht_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "missing_yacht_id",
                    "message": "yacht_id not found in JWT context",
                },
            )

        # Validate request context matches JWT context if provided
        if request_data.context.get("yacht_id"):
            yacht_result = validate_yacht_isolation(
                request_data.context, user_context
            )
            if not yacht_result.valid:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": "error",
                        "error_code": yacht_result.error.error_code,
                        "message": yacht_result.error.message,
                    },
                )

        # ====================================================================
        # STEP 3: Validate domain (if needed)
        # ====================================================================
        valid_domains = [
            "work_orders", "faults", "equipment", "parts", "inventory",
            "certificates", "crew", "documents", "shopping_list", "receiving"
        ]

        if request_data.domain not in valid_domains:
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": "INVALID_DOMAIN",
                    "message": f"Domain '{request_data.domain}' not recognized. Valid: {', '.join(valid_domains)}",
                },
            )

        # ====================================================================
        # STEP 4: Get Supabase client for lookups
        # ====================================================================
        supabase_client = None
        tenant_key_alias = user_context.get("tenant_key_alias")

        if get_tenant_client:
            try:
                supabase_client = get_tenant_client(tenant_key_alias)
            except Exception as e:
                logger.warning(f"[Prepare] Failed to get tenant client: {e}")

        if not supabase_client:
            logger.warning(
                f"[Prepare] No Supabase client available. Entity lookups will fail."
            )

        # ====================================================================
        # STEP 5: Merge context with user info
        # ====================================================================
        context = {
            **request_data.context,
            "yacht_id": yacht_id,
            "user_id": user_context.get("user_id"),
            "user_role": user_context.get("role"),
        }

        # ====================================================================
        # STEP 6: Call build_prepare_response from prefill_engine
        # ====================================================================
        prepare_result = await build_prepare_response(
            q=request_data.q,
            domain=request_data.domain,
            candidate_action_ids=request_data.candidate_action_ids,
            context=context,
            hint_entities=request_data.hint_entities or {},
            client=request_data.client,
            supabase_client=supabase_client,
        )

        # ====================================================================
        # STEP 7: Convert to PrepareResponse format
        # ====================================================================
        # Convert prefill dict to PrefillField objects
        prefill_fields = {}
        for field_name, field_data in prepare_result.get("prefill", {}).items():
            prefill_fields[field_name] = PrefillField(
                value=field_data.get("value"),
                confidence=field_data.get("confidence", 0.0),
                source=field_data.get("source", "unknown")
            )

        # Convert ambiguities
        ambiguities = []
        for amb in prepare_result.get("ambiguities", []):
            candidates = [
                AmbiguityCandidate(
                    id=cand.get("id", ""),
                    label=cand.get("label", ""),
                    confidence=cand.get("confidence", 0.5)
                )
                for cand in amb.get("candidates", [])
            ]
            ambiguities.append(Ambiguity(
                field=amb.get("field", ""),
                candidates=candidates
            ))

        # Convert errors
        errors = [
            PrepareError(
                error_code=err.get("error_code", ""),
                message=err.get("message", ""),
                field=err.get("field")
            )
            for err in prepare_result.get("errors", [])
        ]

        # ====================================================================
        # STEP 8: Return structured response
        # ====================================================================
        return PrepareResponse(
            action_id=prepare_result.get("action_id", ""),
            match_score=prepare_result.get("match_score", 0.0),
            ready_to_commit=prepare_result.get("ready_to_commit", False),
            prefill=prefill_fields,
            missing_required_fields=prepare_result.get("missing_required_fields", []),
            ambiguities=ambiguities,
            errors=errors
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[Prepare] Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "prepare_error",
                "message": f"Prepare failed: {str(e)}",
            },
        )


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for Action Router."""
    return {
        "status": "healthy",
        "service": "action_router",
        "version": "1.0.0",
    }


__all__ = ["router", "execute_action", "get_suggestions", "prefill_action", "prepare_action"]
