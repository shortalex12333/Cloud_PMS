"""
Standardized Error Responses
=============================

Uniform error contract for all action handlers.

Usage:
    from utils.errors import raise_http_error

    # 400 Bad Request
    raise_http_error(400, "INVALID_STORAGE_PATH", "Storage path must not include 'documents/' prefix")

    # 403 Forbidden
    raise_http_error(403, "RLS_DENIED", "Access denied by row-level security")

    # 404 Not Found
    raise_http_error(404, "NOT_FOUND", "Receiving record not found")
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException


# Standard error codes by HTTP status
ERROR_CODES = {
    # 400 Bad Request
    400: [
        "INVALID_STORAGE_PATH",
        "INVALID_SIGNATURE",
        "INVALID_MODE",
        "MISSING_REQUIRED_FIELD",
        "EXTRACT_PREPARE_ONLY",
        "INVALID_STATUS_TRANSITION",
        "ALREADY_ACCEPTED",
        "INVALID_CONFIRMATION_TOKEN",
        "AT_LEAST_ONE_ITEM_REQUIRED",
    ],
    # 403 Forbidden
    403: [
        "RLS_DENIED",
        "SIGNATURE_REQUIRED",
        "INSUFFICIENT_PERMISSIONS",
    ],
    # 404 Not Found
    404: [
        "NOT_FOUND",
        "RECEIVING_NOT_FOUND",
        "DOCUMENT_NOT_FOUND",
    ],
    # 409 Conflict
    409: [
        "CONFLICT",
        "DUPLICATE_RECORD",
    ],
}


def raise_http_error(
    status: int,
    error_code: str,
    message: str,
    hint: Optional[str] = None
) -> HTTPException:
    """
    Raise standardized HTTP error with consistent JSON shape.

    Returns HTTPException with detail containing:
        {
            "status": "error",
            "error_code": "...",
            "message": "...",
            "hint": "..." (optional)
        }

    Args:
        status: HTTP status code (400, 403, 404, 409)
        error_code: Machine-readable error code (e.g., "INVALID_STORAGE_PATH")
        message: Human-readable error message
        hint: Optional hint for resolution

    Returns:
        HTTPException to be raised

    Example:
        raise raise_http_error(
            400,
            "INVALID_STORAGE_PATH",
            "Storage path must not include 'documents/' prefix",
            "Use format: {yacht_id}/receiving/{receiving_id}/{filename}"
        )
    """
    detail: Dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "message": message,
    }

    if hint:
        detail["hint"] = hint

    return HTTPException(status_code=status, detail=detail)


def error_response(
    error_code: str,
    message: str,
    hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create error response dict without raising (for handler returns).

    Returns:
        {
            "status": "error",
            "error_code": "...",
            "message": "...",
            "hint": "..." (optional)
        }

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        hint: Optional hint for resolution

    Example:
        return error_response(
            "INVALID_SIGNATURE",
            "Signature validation failed",
            "Ensure signature contains: signed_at, user_id, role_at_signing"
        )
    """
    response: Dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "message": message,
    }

    if hint:
        response["hint"] = hint

    return response


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create success response dict with consistent shape.

    Returns:
        {
            "status": "success",
            ...data
        }

    Args:
        data: Response data to merge

    Example:
        return success_response({
            "receiving_id": "...",
            "vendor_name": "..."
        })
    """
    return {
        "status": "success",
        **data
    }
