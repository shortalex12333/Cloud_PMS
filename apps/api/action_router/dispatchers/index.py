"""
Action dispatcher index — INTERNAL_HANDLERS adapter shim.

STATUS: PARTIAL MIGRATION IN PROGRESS
--------------------------------------
Originally this file merged all domain HANDLERS dicts. Most domains have been
migrated to Phase 4 flat functions and wired directly in routes/handlers/__init__.py.

LIVE TRAFFIC (still flows through this file via internal_adapter.py):
  13 actions reach INTERNAL_HANDLERS through the adapter shim:

  Document domain (8):
    add_document_comment  → dispatchers/document.py  → DocumentCommentHandlers
    add_document_note     → dispatchers/shared.py     → pms_notes INSERT (generic)
    archive_document      → soft_delete_entity        → pms_doc_metadata.deleted_at
    delete_document_comment → dispatchers/document.py → DocumentCommentHandlers
    list_document_comments  → dispatchers/document.py → DocumentCommentHandlers
    open_document         → dispatchers/shared.py     → signed URL (pms-documents bucket)
    update_document_comment → dispatchers/document.py → DocumentCommentHandlers
    view_document         → dispatchers/p3.py         → P3ReadOnlyHandlers

  Parts/shared domain (5):
    add_note              → dispatchers/shared.py     → pms_notes INSERT (generic)
    add_part_note         → dispatchers/shared.py     → pms_notes INSERT (alias)
    archive_part          → soft_delete_entity        → pms_parts.deleted_at
    delete_part           → soft_delete_entity        → pms_parts.deleted_at
    suggest_parts         → not_yet_implemented stub

DEAD IN INTERNAL_HANDLERS (Phase 4 now serves these — entries below are unreachable):
  All warranty actions    → WARRANTY_HANDLERS in routes/handlers/__init__.py
  All equipment actions   → EQUIP_HANDLERS
  All handover actions    → HAND_HANDLERS
  All HoR actions         → HOR_HANDLERS
  All receiving actions   → RECV_HANDLERS
  All P1/P2 actions       → WO_HANDLERS / PO_HANDLERS / MEDIA_HANDLERS

MIGRATION PLAN (to fully eliminate INTERNAL_HANDLERS):
  Step A — Document (8 actions):
    1. Implement add_document_comment / update_ / delete_ / list_ as Phase 4 flat functions
       in handlers/document_handler.py (they call document_comment_handlers.py; thin wrappers).
    2. Implement view_document as Phase 4 in handlers/document_handler.py (delegates to
       P3ReadOnlyHandlers.view_document_execute — one-liner).
    3. Implement open_document as Phase 4 (generate signed URL from storage_path).
    4. add_document_note + archive_document already have Phase 4 equivalents in other handlers;
       add aliases to document_handler.py HANDLERS dict.
    5. Remove all 8 from internal_adapter.py::_ACTIONS_TO_ADAPT.

  Step B — Parts/shared (5 actions):
    1. add_note / add_part_note: move shared note logic into part_handlers.py as _p4_add_note.
    2. archive_part / delete_part: add Phase 4 soft-delete wrappers in part_handlers.py
       (calls universal_handlers.soft_delete_entity with entity_type="part").
    3. suggest_parts: stub is fine — add it to part_handlers.py HANDLERS as not_yet_implemented.
    4. Remove all 5 from internal_adapter.py::_ACTIONS_TO_ADAPT.

  After Steps A + B:
    - internal_adapter.py is empty → delete it.
    - This file (dispatchers/index.py) has no callers → delete it.
    - action_router/dispatchers/ can be deleted (only registry.py etc. remain in action_router/).
"""

from typing import Dict, Any
import logging

from handlers.universal_handlers import soft_delete_entity as _soft_delete_entity
from handlers.stub_handlers import not_yet_implemented as _not_yet_implemented

# Only the 4 dispatcher modules that still serve live adapter traffic.
# All other domain dispatchers have been superseded by Phase 4 handlers.
from .shared import HANDLERS as _shared       # add_note, open_document, etc.
from .document import HANDLERS as _document   # add_document_comment, etc.
from .parts import HANDLERS as _parts         # archive_part (None), delete_part (None), suggest_parts (None)
from .p3 import HANDLERS as _p3              # view_document

logger = logging.getLogger(__name__)

# Merge the 4 active domains. Later dicts win on key collision.
_merged: Dict[str, Any] = {}
for _domain in (_shared, _p3, _document, _parts):
    _merged.update(_domain)

_NOT_YET_IMPLEMENTED = {"suggest_parts"}

INTERNAL_HANDLERS: Dict[str, Any] = {
    k: (_not_yet_implemented if (v is None and k in _NOT_YET_IMPLEMENTED) else
        _soft_delete_entity   if v is None else v)
    for k, v in _merged.items()
}


async def dispatch(action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy dispatch function — no live HTTP callers. Kept for test compatibility."""
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
