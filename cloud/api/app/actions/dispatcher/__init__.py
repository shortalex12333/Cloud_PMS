"""
Action Dispatcher - Routes validated actions to handlers

Currently in STUB MODE:
- Does NOT call n8n
- Logs action to action_logs table with status="stubbed"
- Returns stub response

Future: Will route to n8n webhooks based on action_def.handler_type
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
import logging
import json

from app.actions.registry import ActionDefinition
from app.core.supabase import supabase_client

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """Result from action dispatch"""
    status: str  # "stubbed", "success", "error"
    action: str
    result: Optional[Dict[str, Any]] = None
    action_log_id: Optional[str] = None
    error: Optional[str] = None


class ActionDispatcher:
    """
    Dispatches validated actions to appropriate handlers.

    Current Mode: STUBBED
    - All actions logged to action_logs table
    - No actual n8n calls made
    - Returns stub responses
    """

    def __init__(self):
        self.db = supabase_client

    async def dispatch(
        self,
        action_def: ActionDefinition,
        merged_fields: Dict[str, Any],
        auth_context: Any  # YachtContext
    ) -> DispatchResult:
        """
        Dispatch an action for execution.

        In stub mode:
        1. Log to action_logs table
        2. Return stubbed response

        Args:
            action_def: The validated action definition
            merged_fields: Combined context + payload fields
            auth_context: Authenticated yacht context

        Returns:
            DispatchResult with status and action log ID
        """
        action_log_id = str(uuid.uuid4())

        try:
            # Log the action (stubbed - no actual execution)
            log_entry = await self._log_action(
                action_log_id=action_log_id,
                action_def=action_def,
                merged_fields=merged_fields,
                auth_context=auth_context,
                status="stubbed"
            )

            logger.info(
                f"Action '{action_def.name}' dispatched (stubbed). "
                f"Log ID: {action_log_id}"
            )

            return DispatchResult(
                status="stubbed",
                action=action_def.name,
                result=None,
                action_log_id=action_log_id
            )

        except Exception as e:
            logger.error(f"Failed to dispatch action '{action_def.name}': {e}")

            # Try to log the error
            try:
                await self._log_action(
                    action_log_id=action_log_id,
                    action_def=action_def,
                    merged_fields=merged_fields,
                    auth_context=auth_context,
                    status="error",
                    error_message=str(e)
                )
            except Exception as log_error:
                logger.error(f"Failed to log action error: {log_error}")

            return DispatchResult(
                status="error",
                action=action_def.name,
                result=None,
                action_log_id=action_log_id,
                error=str(e)
            )

    async def _log_action(
        self,
        action_log_id: str,
        action_def: ActionDefinition,
        merged_fields: Dict[str, Any],
        auth_context: Any,
        status: str,
        error_message: Optional[str] = None,
        n8n_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log action to action_logs table.

        Args:
            action_log_id: Pre-generated UUID for the log entry
            action_def: The action being executed
            merged_fields: All fields passed to action
            auth_context: Authentication context
            status: "stubbed", "pending", "success", "error"
            error_message: Error details if status is "error"
            n8n_response: Response from n8n if any

        Returns:
            Created log entry
        """
        log_entry = {
            "id": action_log_id,
            "yacht_id": str(auth_context.yacht_id),
            "user_id": str(auth_context.user_id),
            "action_name": action_def.name,
            "action_payload": json.dumps(merged_fields),
            "status": status,
            "handler_type": action_def.handler_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if error_message:
            log_entry["error_message"] = error_message

        if n8n_response:
            log_entry["n8n_response"] = json.dumps(n8n_response)

        # Insert using service role (bypasses RLS)
        response = self.db.admin.table("action_logs").insert(log_entry).execute()

        if not response.data:
            raise Exception("Failed to insert action log")

        return response.data[0]

    async def update_action_status(
        self,
        action_log_id: str,
        status: str,
        n8n_response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update action log status (for async completion).

        Args:
            action_log_id: The action log ID to update
            status: New status
            n8n_response: Response from n8n if available
            error_message: Error message if status is error

        Returns:
            Updated log entry
        """
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if n8n_response:
            update_data["n8n_response"] = json.dumps(n8n_response)

        if error_message:
            update_data["error_message"] = error_message

        response = self.db.admin.table("action_logs") \
            .update(update_data) \
            .eq("id", action_log_id) \
            .execute()

        if not response.data:
            raise Exception(f"Action log {action_log_id} not found")

        return response.data[0]


# Global dispatcher instance
action_dispatcher = ActionDispatcher()


async def dispatch_action(
    action_def: ActionDefinition,
    merged_fields: Dict[str, Any],
    auth_context: Any
) -> DispatchResult:
    """
    Convenience function to dispatch an action.

    Args:
        action_def: Validated action definition
        merged_fields: Combined context + payload
        auth_context: Authenticated yacht context

    Returns:
        DispatchResult with execution status
    """
    return await action_dispatcher.dispatch(action_def, merged_fields, auth_context)
