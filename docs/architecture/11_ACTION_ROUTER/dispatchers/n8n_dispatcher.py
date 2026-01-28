"""
n8n Action Dispatcher

Forwards complex actions to n8n workflows for orchestration.

These are actions that require multi-step processes, external integrations,
or complex business logic that's better handled in n8n.
"""

from typing import Dict, Any
import os
import httpx


# ============================================================================
# N8N WORKFLOW MAPPING
# ============================================================================

N8N_WORKFLOWS: Dict[str, str] = {
    # Work Orders
    "create_work_order": "/webhook/create_work_order",
    "create_work_order_fault": "/webhook/create_work_order",

    # Handovers
    "add_to_handover": "/webhook/add_to_handover",
    "add_document_to_handover": "/webhook/add_document_to_handover",
    "add_part_to_handover": "/webhook/add_part_to_handover",
    "add_predictive_to_handover": "/webhook/add_predictive_to_handover",
    "export_handover": "/webhook/export_handover",

    # Inventory
    "order_part": "/webhook/order_part",
}


# ============================================================================
# DISPATCHER
# ============================================================================


async def dispatch(action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch action to n8n workflow.

    Args:
        action_id: ID of action to execute
        params: Merged context + payload + user_context

    Returns:
        Result from n8n workflow

    Raises:
        KeyError: If action_id not found
        httpx.HTTPError: If n8n request fails
    """
    # Get n8n base URL
    n8n_base_url = os.getenv("N8N_BASE_URL")
    if not n8n_base_url:
        raise ValueError("N8N_BASE_URL environment variable not set")

    # Get workflow endpoint
    if action_id not in N8N_WORKFLOWS:
        raise KeyError(f"No n8n workflow found for action '{action_id}'")

    workflow_path = N8N_WORKFLOWS[action_id]
    workflow_url = f"{n8n_base_url}{workflow_path}"

    # Get auth token if configured
    auth_token = os.getenv("N8N_AUTH_TOKEN")

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        # Call n8n webhook
        async with httpx.AsyncClient() as client:
            response = await client.post(
                workflow_url,
                json=params,
                headers=headers,
                timeout=30.0,
            )

            # Check for errors
            response.raise_for_status()

            # Parse response
            result = response.json()

            return result

    except httpx.TimeoutException:
        raise Exception(f"n8n workflow timeout for action '{action_id}'")

    except httpx.HTTPStatusError as e:
        # Extract error message from response if available
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", str(e))
        except Exception:
            error_message = str(e)

        raise Exception(
            f"n8n workflow failed for action '{action_id}': {error_message}"
        )

    except httpx.RequestError as e:
        raise Exception(
            f"Failed to connect to n8n for action '{action_id}': {str(e)}"
        )

    except Exception as e:
        raise Exception(
            f"n8n dispatcher error for action '{action_id}': {str(e)}"
        )


__all__ = ["dispatch", "N8N_WORKFLOWS"]
