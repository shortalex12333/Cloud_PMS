"""
Action Router - Main Entry Point

Single endpoint for all user-initiated mutations in CelesteOS.

POST /v1/actions/execute
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
import time

from .registry import get_action, HandlerType
from .validators import (
    validate_jwt,
    validate_yacht_isolation,
    validate_role_permission,
    validate_required_fields,
    validate_schema,
)
from .dispatchers import internal_dispatcher, n8n_dispatcher
from .logger import log_action

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
                user_context["role"] = tenant_info.get("role", user_context.get("role"))
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
        )

        # ====================================================================
        # STEP 10: Return success response
        # ====================================================================
        return ActionResponse(
            status="success",
            action=action_id,
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


__all__ = ["router", "execute_action"]
