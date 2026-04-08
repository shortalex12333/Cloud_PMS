"""
Vessel Access Utilities
=======================

Shared functions for multi-vessel access validation.
Used by entity routes, action validators, search endpoints, and any
endpoint that needs to scope queries to a specific vessel.

Pattern:
  - Single-vessel user: no yacht_id param needed, uses auth['yacht_id']
  - Fleet user (overview mode): yacht_id param provided, validated against auth['vessel_ids']
"""

from fastapi import HTTPException, Query
from typing import Optional, List
import logging
import uuid as uuid_mod

logger = logging.getLogger(__name__)


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID v4 format."""
    try:
        uuid_mod.UUID(str(value), version=4)
        return True
    except (ValueError, AttributeError):
        return False


def resolve_yacht_id(auth: dict, requested_yacht_id: Optional[str] = None) -> str:
    """
    Resolve which yacht_id to use for a query.

    If requested_yacht_id is provided, validates it's in the user's vessel_ids.
    If not provided, returns the user's primary yacht_id.

    Args:
        auth: Auth context from get_authenticated_user()
        requested_yacht_id: Optional yacht_id from query param or request body

    Returns:
        The yacht_id to use for the query

    Raises:
        HTTPException 400 if requested yacht_id is not a valid UUID
        HTTPException 403 if requested yacht_id is not in user's vessel_ids
    """
    if not requested_yacht_id:
        return auth["yacht_id"]

    if not _is_valid_uuid(requested_yacht_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid yacht_id: must be a valid UUID"
        )

    vessel_ids = auth.get("vessel_ids", [auth.get("yacht_id")])
    if str(requested_yacht_id) not in [str(v) for v in vessel_ids]:
        raise HTTPException(
            status_code=403,
            detail="Access denied: yacht_id not in user's vessel list"
        )

    return requested_yacht_id


def resolve_vessel_ids(auth: dict, requested_vessel_ids: Optional[List[str]] = None) -> List[str]:
    """
    Resolve which vessel_ids to search across.

    If requested_vessel_ids provided, validates each is in auth['vessel_ids'].
    If not provided, returns [auth['yacht_id']] (single vessel).

    Used by search endpoints for multi-vessel fan-out.
    """
    if not requested_vessel_ids:
        return [auth["yacht_id"]]

    allowed = set(str(v) for v in auth.get("vessel_ids", [auth.get("yacht_id")]))
    for vid in requested_vessel_ids:
        if not _is_valid_uuid(vid):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid vessel_id: '{vid}' is not a valid UUID"
            )
        if str(vid) not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: vessel {vid} not in user's vessel list"
            )

    return requested_vessel_ids


def validate_vessel_id_format(vessel_id: str) -> None:
    """
    Validate that a vessel_id path parameter is either 'all' (overview mode) or a valid UUID.
    Use this in routes that accept vessel_id as a URL path parameter.

    Raises:
        HTTPException 400 if vessel_id is not 'all' and not a valid UUID
    """
    if vessel_id == "all":
        return
    if not _is_valid_uuid(vessel_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid vessel_id: must be 'all' or a valid UUID"
        )
