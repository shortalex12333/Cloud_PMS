"""
Actions API endpoints
POST /v1/actions/execute - Unified action execution endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from app.core.auth import get_current_user, YachtContext
from app.actions.registry import list_actions, get_actions_for_role, ActionDefinition
from app.actions.validators import (
    validate_action_request,
    ActionValidationError,
    UnknownActionError,
    MissingFieldsError,
    YachtMismatchError,
    UserMismatchError,
    RolePermissionError
)
from app.actions.dispatcher import dispatch_action, DispatchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["Actions"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class ActionContext(BaseModel):
    """Context for action execution (from client)"""
    yacht_id: Optional[str] = Field(None, description="Yacht UUID (validated against JWT)")
    user_id: Optional[str] = Field(None, description="User UUID (validated against JWT)")
    role: Optional[str] = Field(None, description="User role (validated against JWT)")


class ExecuteActionRequest(BaseModel):
    """Request body for POST /v1/actions/execute"""
    action: str = Field(..., description="Action name from registry (e.g., 'create_work_order')")
    context: ActionContext = Field(default_factory=ActionContext, description="Execution context")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific payload")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "create_work_order",
                "context": {
                    "yacht_id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "123e4567-e89b-12d3-a456-426614174001",
                    "role": "Engineer"
                },
                "payload": {
                    "equipment_id": "123e4567-e89b-12d3-a456-426614174002",
                    "title": "Replace port engine oil filter",
                    "priority": "medium",
                    "description": "Scheduled maintenance - 500 hour service"
                }
            }
        }


class ExecuteActionResponse(BaseModel):
    """Response for POST /v1/actions/execute"""
    status: str = Field(..., description="Execution status: stubbed, success, error")
    action: str = Field(..., description="Action name that was executed")
    result: Optional[Dict[str, Any]] = Field(None, description="Action result (null in stub mode)")
    action_log_id: Optional[str] = Field(None, description="UUID of the action log entry")
    error: Optional[str] = Field(None, description="Error message if status is error")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "stubbed",
                "action": "create_work_order",
                "result": None,
                "action_log_id": "123e4567-e89b-12d3-a456-426614174003"
            }
        }


class ActionInfo(BaseModel):
    """Information about an available action"""
    name: str
    description: str
    requires: List[str]
    allowed_roles: List[str]
    handler_type: str


class ActionCatalogueResponse(BaseModel):
    """Response for GET /v1/actions/catalogue"""
    actions: List[ActionInfo]
    total: int


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/execute", response_model=ExecuteActionResponse)
async def execute_action(
    request: ExecuteActionRequest,
    auth_context: YachtContext = Depends(get_current_user)
):
    """
    Execute a micro-action through the unified action router.

    **Validation Pipeline:**
    1. Action exists in registry
    2. Context yacht_id/user_id matches JWT claims
    3. User role has permission for this action
    4. All required fields are present

    **Current Mode: STUBBED**
    - Actions are logged to action_logs table
    - No actual n8n workflows are triggered
    - Returns status="stubbed" with action_log_id

    **Error Codes:**
    - 400: Unknown action or missing required fields
    - 403: Context mismatch or role not permitted
    - 500: Internal dispatch error
    """
    logger.info(
        f"Execute action request: action={request.action}, "
        f"user={auth_context.user_id}, yacht={auth_context.yacht_id}"
    )

    try:
        # Run validation pipeline
        action_def, merged_fields = validate_action_request(
            action_name=request.action,
            context=request.context.model_dump(),
            payload=request.payload,
            auth_context=auth_context
        )

        # Dispatch action (currently stubbed)
        result: DispatchResult = await dispatch_action(
            action_def=action_def,
            merged_fields=merged_fields,
            auth_context=auth_context
        )

        return ExecuteActionResponse(
            status=result.status,
            action=result.action,
            result=result.result,
            action_log_id=result.action_log_id,
            error=result.error
        )

    except UnknownActionError as e:
        logger.warning(f"Unknown action: {request.action}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )

    except MissingFieldsError as e:
        logger.warning(f"Missing fields for {request.action}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )

    except YachtMismatchError as e:
        logger.warning(f"Yacht mismatch for {request.action}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    except UserMismatchError as e:
        logger.warning(f"User mismatch for {request.action}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    except RolePermissionError as e:
        logger.warning(f"Role permission denied for {request.action}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )

    except ActionValidationError as e:
        # Catch-all for other validation errors
        logger.warning(f"Validation error for {request.action}: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )

    except Exception as e:
        logger.error(f"Internal error executing {request.action}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error executing action: {str(e)}"
        )


@router.get("/catalogue", response_model=ActionCatalogueResponse)
async def get_action_catalogue(
    auth_context: YachtContext = Depends(get_current_user)
):
    """
    Get catalogue of available actions for the authenticated user's role.

    Returns only actions the user's role is permitted to execute.
    """
    # Get actions available for user's role
    user_role = auth_context.user_role or "Crew"

    # Normalize role for lookup
    role_normalized = user_role.strip().title()

    # Get available actions for this role
    available_actions = get_actions_for_role(role_normalized)

    actions = [
        ActionInfo(
            name=action.name,
            description=action.description,
            requires=action.requires,
            allowed_roles=action.allowed_roles,
            handler_type=action.handler_type
        )
        for action in available_actions
    ]

    return ActionCatalogueResponse(
        actions=actions,
        total=len(actions)
    )


@router.get("/catalogue/all")
async def get_all_actions():
    """
    Get list of all action names (public endpoint for reference).

    Does not require authentication.
    """
    return {
        "actions": list_actions(),
        "total": len(list_actions())
    }
