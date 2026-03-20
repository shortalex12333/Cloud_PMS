"""
Stub Handlers — placeholder for actions that are registered but not yet implemented.

Returns a structured NOT_IMPLEMENTED error so the frontend can display a user-friendly
message instead of a 500.
"""


async def not_yet_implemented(params: dict) -> dict:
    """Placeholder handler for planned but unimplemented actions."""
    return {
        "status": "error",
        "error_code": "NOT_IMPLEMENTED",
        "message": "This action is planned but not yet available.",
    }
