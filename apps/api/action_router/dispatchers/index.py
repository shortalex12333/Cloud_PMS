"""
Action dispatcher index.

Merges all domain HANDLERS dicts into a single INTERNAL_HANDLERS mapping
and exposes a dispatch() function. Replaces the monolithic internal_dispatcher.py.
"""

from typing import Dict, Any
import logging

from handlers.universal_handlers import soft_delete_entity as _soft_delete_entity
from handlers.stub_handlers import not_yet_implemented as _not_yet_implemented

from .shared import HANDLERS as _shared
from .equipment import HANDLERS as _equipment
from .document import HANDLERS as _document
from .warranty import HANDLERS as _warranty
from .parts import HANDLERS as _parts
from .receiving import HANDLERS as _receiving
from .p3 import HANDLERS as _p3
from .p1_p2 import HANDLERS as _p1_p2
from .handover import HANDLERS as _handover

logger = logging.getLogger(__name__)

# Merge all domain dicts. Later dicts win on key collision (intentional for overrides).
_merged: Dict[str, Any] = {}
for _domain in (
    _shared,
    _p3,
    _p1_p2,
    _document,
    _warranty,
    _parts,
    _receiving,
    _handover,
    _equipment,  # last — wins any overlapping read-aliases (view_equipment_parts, view_linked_faults)
):
    _merged.update(_domain)

# Actions that are not-yet-implemented (stub) rather than soft-delete
_NOT_YET_IMPLEMENTED = {"suggest_parts"}

# Replace None placeholders: stub actions → not_yet_implemented, rest → soft_delete
INTERNAL_HANDLERS: Dict[str, Any] = {
    k: (_not_yet_implemented if (v is None and k in _NOT_YET_IMPLEMENTED) else
        _soft_delete_entity   if v is None else v)
    for k, v in _merged.items()
}


async def dispatch(action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if action_id not in INTERNAL_HANDLERS:
        raise KeyError(f"No internal handler found for action '{action_id}'")

    handler = INTERNAL_HANDLERS[action_id]

    try:
        return await handler(params)
    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise Exception(f"Internal handler failed: {str(e)}")


__all__ = ["dispatch", "INTERNAL_HANDLERS"]
