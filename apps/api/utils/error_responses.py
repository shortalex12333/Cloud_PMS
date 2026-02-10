"""
Standardized Error Responses

Provides consistent error response formats across all API endpoints.
Security Fix: 2026-02-10 (Day 6)
"""

from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any


# Map error codes to HTTP status codes
ERROR_STATUS_CODES = {
    # Auth/Authorization Errors (4xx)
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "RLS_DENIED": 403,
    "INSUFFICIENT_PERMISSIONS": 403,

    # Not Found Errors (404)
    "NOT_FOUND": 404,
    "ENTITY_NOT_FOUND": 404,

    # Validation Errors (400)
    "VALIDATION_FAILED": 400,
    "MISSING_REQUIRED_FIELD": 400,
    "INVALID_UUID": 400,
    "INVALID_QUANTITY": 400,

    # State/Logic Errors (400)
    "INVALID_STATE_TRANSITION": 400,
    "DUPLICATE_ACTION": 400,
    "CONSTRAINT_VIOLATION": 400,

    # Server Errors (500)
    "INTERNAL_ERROR": 500,
    "DATABASE_ERROR": 500,
    "HANDLER_ERROR": 500,
}


def error_response(
    code: str,
    message: str,
    status_code: Optional[int] = None,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        code: Error code (e.g., "FORBIDDEN", "NOT_FOUND", "VALIDATION_FAILED")
        message: Human-readable error message
        status_code: HTTP status code (auto-detected from code if not provided)
        field: Optional field name for validation errors
        details: Optional additional error details

    Returns:
        JSONResponse with standardized error format
    """
    if status_code is None:
        status_code = ERROR_STATUS_CODES.get(code, 400)

    content = {
        "success": False,
        "code": code,
        "message": message
    }

    if field:
        content["field"] = field

    if details:
        content["details"] = details

    return JSONResponse(status_code=status_code, content=content)


def error_dict(
    code: str,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error dictionary (for returning from handlers).

    Args:
        code: Error code
        message: Human-readable error message
        field: Optional field name for validation errors
        details: Optional additional error details

    Returns:
        Dict with standardized error format
    """
    result = {
        "success": False,
        "code": code,
        "message": message
    }

    if field:
        result["field"] = field

    if details:
        result.update(details)

    return result


def success_response(
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Optional response data
        message: Optional success message

    Returns:
        Dict with standardized success format
    """
    result = {
        "success": True,
        "status": "success"
    }

    if message:
        result["message"] = message

    if data:
        result["data"] = data

    return result


__all__ = [
    "error_response",
    "error_dict",
    "success_response",
    "ERROR_STATUS_CODES",
]
