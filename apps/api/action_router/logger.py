"""
Action Logger

Logs all action executions to Supabase for audit trail and analytics.
"""

from typing import Dict, Any, Optional
import os
from datetime import datetime
from supabase import Client
import json

# Import centralized Supabase client factory
from integrations.supabase import get_supabase_client


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data from payload before logging.

    Removes or masks sensitive fields like passwords, tokens, etc.
    """
    sensitive_fields = [
        "password",
        "token",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
    ]

    sanitized = payload.copy()

    for key in list(sanitized.keys()):
        # Check if key contains sensitive field name
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            sanitized[key] = "***REDACTED***"

    return sanitized


async def log_action(
    action_id: str,
    action_label: str,
    yacht_id: str,
    user_id: str,
    payload: Dict[str, Any],
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    execution_id: Optional[str] = None,
) -> None:
    """
    Log action execution to Supabase.

    Args:
        action_id: ID of the action
        action_label: Human-readable label
        yacht_id: UUID of the yacht
        user_id: UUID of the user
        payload: Action payload (will be sanitized)
        status: 'success' or 'error'
        result: Result data (optional)
        error_message: Error message if status='error'
        duration_ms: Execution duration in milliseconds
        execution_id: Unique ID for this execution
    """
    try:
        supabase = get_supabase_client()

        # Sanitize payload
        sanitized_payload = sanitize_payload(payload)

        # Prepare log entry
        log_entry = {
            "action_id": action_id,
            "action_label": action_label,
            "yacht_id": yacht_id,
            "user_id": user_id,
            "payload": json.dumps(sanitized_payload),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if execution_id:
            log_entry["execution_id"] = execution_id

        # Add optional fields
        if result:
            # Don't log full result if it's large, just summary
            if isinstance(result, dict):
                result_summary = {k: v for k, v in result.items() if k in ["id", "note_id", "work_order_id", "handover_id", "signed_url"]}
                log_entry["result"] = json.dumps(result_summary)
            else:
                log_entry["result"] = json.dumps(result)

        if error_message:
            log_entry["error_message"] = error_message[:500]  # Truncate long errors

        if duration_ms is not None:
            log_entry["duration_ms"] = duration_ms

        # Insert log
        supabase.table("action_logs").insert(log_entry).execute()

    except Exception as e:
        # Log errors should not break the action execution
        # Just print to stderr for debugging
        import sys
        print(f"WARNING: Failed to log action: {str(e)}", file=sys.stderr)


async def get_action_stats(yacht_id: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get action execution statistics for a yacht.

    Args:
        yacht_id: UUID of the yacht
        hours: Number of hours to look back

    Returns:
        Dictionary with stats:
        - total_actions: Total number of actions
        - success_rate: Percentage of successful actions
        - actions_by_type: Count by action_id
        - recent_errors: List of recent errors
    """
    try:
        supabase = get_supabase_client()

        # Calculate timestamp for N hours ago
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        # Get all logs for yacht in time range
        result = supabase.table("action_logs").select("*").eq(
            "yacht_id", yacht_id
        ).gte("timestamp", cutoff).execute()

        logs = result.data

        # Calculate stats
        total_actions = len(logs)
        successful_actions = len([log for log in logs if log["status"] == "success"])
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0

        # Count by action type
        actions_by_type = {}
        for log in logs:
            action_id = log["action_id"]
            actions_by_type[action_id] = actions_by_type.get(action_id, 0) + 1

        # Get recent errors
        recent_errors = [
            {
                "action_id": log["action_id"],
                "error_message": log["error_message"],
                "timestamp": log["timestamp"],
            }
            for log in logs
            if log["status"] == "error"
        ][:10]  # Last 10 errors

        return {
            "total_actions": total_actions,
            "success_rate": round(success_rate, 2),
            "actions_by_type": actions_by_type,
            "recent_errors": recent_errors,
            "time_range_hours": hours,
        }

    except Exception as e:
        raise Exception(f"Failed to get action stats: {str(e)}")


__all__ = ["log_action", "get_action_stats", "sanitize_payload"]
