"""
Action Router - Main Entry Point

Single endpoint for all user-initiated mutations in CelesteOS.

POST /v1/actions/execute
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
import time
import uuid

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
        # STEP 8: Dispatch to handler
        # ====================================================================
        try:
            if action_def.handler_type == HandlerType.INTERNAL:
                result = await internal_dispatcher.dispatch(action_id, params)
            elif action_def.handler_type == HandlerType.N8N:
                result = await n8n_dispatcher.dispatch(action_id, params)
            else:
                raise ValueError(f"Unknown handler type: {action_def.handler_type}")

        except HTTPException:
            # Re-raise HTTPException unchanged (from handlers that explicitly set status codes)
            raise

        except ValueError as e:
            # Validation/business logic errors (400)
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=str(e),
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
            await log_action(
                action_id=action_id,
                action_label=action_def.label,
                yacht_id=request_data.context["yacht_id"],
                user_id=user_context["user_id"],
                payload=request_data.payload,
                status="error",
                error_message=str(e),
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

    return SuggestionsResponse(
        candidates=candidates,
        unresolved=unresolved,
        focused_entity=focused_entity,
        warnings=warnings,
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


__all__ = ["router", "execute_action", "get_suggestions"]
