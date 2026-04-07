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

logger = logging.getLogger(__name__)


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
        HTTPException 403 if requested yacht_id is not in user's vessel_ids
    """
    if not requested_yacht_id:
        return auth["yacht_id"]

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
        if str(vid) not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: vessel {vid} not in user's vessel list"
            )

    return requested_vessel_ids
