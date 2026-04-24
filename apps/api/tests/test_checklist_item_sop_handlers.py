# apps/api/tests/test_checklist_item_sop_handlers.py
"""
Unit tests for PR-WO-4 additions on P2MutationLightHandlers:
    * add_checklist_item_execute — user A appends a checkpoint to the WO's
      metadata.checklist[] array.
    * upsert_sop_execute         — stores SOP text and/or linked document id
      on the WO's metadata.sop{} object.

Both handlers read + write `pms_work_orders.metadata` as a JSON blob (the
canonical storage path today — see p3_read_only_handlers.view_checklist_execute
+ p2_mutation_light_handlers.mark_checklist_item_complete_execute). The real
`pms_checklists` / `pms_checklist_items` tables are unused by the live code
path; migration to them is deferred (documented in
docs/ongoing_work/work_orders/PLAN.md).
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


YACHT = "yacht-uuid-1"
USER = "user-uuid-1"
WO = "wo-uuid-1"


class _Q:
    """Minimal fluent supabase stub."""

    def __init__(self, parent, tbl):
        self.parent = parent
        self.tbl = tbl
        self._op = None
        self._payload = None
        self._filters = []

    def select(self, _cols): self._op = "select"; return self
    def update(self, p):     self._op = "update"; self._payload = p; return self
    def insert(self, p):     self._op = "insert"; self._payload = p; return self
    def eq(self, k, v):      self._filters.append(("eq", k, v)); return self
    def limit(self, _):      return self

    def execute(self):
        self.parent.calls.append({
            "table": self.tbl, "op": self._op,
            "payload": self._payload, "filters": tuple(self._filters),
        })
        canned = self.parent.canned.get((self.tbl, self._op), {"data": [], "count": 0})
        return MagicMock(data=canned["data"], count=canned["count"])


class _DB:
    def __init__(self):
        self.calls = []
        self.canned = {}
    def table(self, n): return _Q(self, n)


def _make_handler(db, initial_metadata):
    from handlers.p2_mutation_light_handlers import P2MutationLightHandlers
    db.canned = {
        ("pms_work_orders", "select"): {
            "data": [{"id": WO, "wo_number": "WO-0001", "metadata": initial_metadata}],
            "count": 1,
        },
        ("pms_work_orders", "update"): {
            "data": [{"id": WO}], "count": 1,
        },
    }
    h = P2MutationLightHandlers(supabase_client=db)
    # _create_audit_log is async and off-critical-path for this test surface.
    h._create_audit_log = AsyncMock(return_value=None)
    return h


# ── add_checklist_item ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_checklist_item_appends_to_metadata_array():
    db = _DB()
    handler = _make_handler(db, {"checklist": []})

    result = await handler.add_checklist_item_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        title="Lock out breaker 17B",
        description="Behind portside dresser back panel",
        category="safety",
        is_required=True,
        requires_photo=True,
    )

    assert result["status"] == "success"
    assert result["result"]["title"] == "Lock out breaker 17B"
    assert result["result"]["category"] == "safety"
    assert result["result"]["total_items"] == 1
    assert result["result"]["sequence"] == 1  # first item gets seq 1

    # The UPDATE call carries the full checklist with our new item.
    updates = [c for c in db.calls if c["op"] == "update"]
    assert len(updates) == 1
    written = updates[0]["payload"]["metadata"]["checklist"]
    assert len(written) == 1
    item = written[0]
    assert item["title"] == "Lock out breaker 17B"
    assert item["category"] == "safety"
    assert item["is_required"] is True
    assert item["requires_photo"] is True
    assert item["is_completed"] is False
    assert item["created_by"] == USER


@pytest.mark.asyncio
async def test_add_checklist_item_auto_increments_sequence():
    db = _DB()
    existing = [
        {"id": "a", "title": "Step 1", "sequence": 1, "is_completed": True},
        {"id": "b", "title": "Step 2", "sequence": 2, "is_completed": False},
    ]
    handler = _make_handler(db, {"checklist": existing})

    result = await handler.add_checklist_item_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        title="Step 3",
    )
    assert result["result"]["sequence"] == 3
    assert result["result"]["total_items"] == 3


@pytest.mark.asyncio
async def test_add_checklist_item_rejects_empty_title():
    db = _DB()
    handler = _make_handler(db, {"checklist": []})
    result = await handler.add_checklist_item_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        title="   ",  # whitespace-only
    )
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_TITLE"
    # No writes should have fired.
    assert [c for c in db.calls if c["op"] == "update"] == []


@pytest.mark.asyncio
async def test_add_checklist_item_preserves_existing_metadata_keys():
    db = _DB()
    handler = _make_handler(db, {
        "checklist": [],
        "sop": {"text": "Don't electrocute yourself", "updated_by": USER},
        "custom_field": 42,
    })
    await handler.add_checklist_item_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER, title="X",
    )
    updates = [c for c in db.calls if c["op"] == "update"]
    meta = updates[0]["payload"]["metadata"]
    # Append must not clobber sibling keys.
    assert meta["sop"]["text"] == "Don't electrocute yourself"
    assert meta["custom_field"] == 42


@pytest.mark.asyncio
async def test_add_checklist_item_wo_not_found():
    db = _DB()
    db.canned = {
        ("pms_work_orders", "select"): {"data": [], "count": 0},
    }
    from handlers.p2_mutation_light_handlers import P2MutationLightHandlers
    handler = P2MutationLightHandlers(supabase_client=db)
    result = await handler.add_checklist_item_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER, title="X",
    )
    assert result["status"] == "error"
    assert result["error_code"] == "WORK_ORDER_NOT_FOUND"


# ── upsert_sop ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_sop_text_only():
    db = _DB()
    handler = _make_handler(db, {})
    result = await handler.upsert_sop_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        sop_text="Isolate both breakers before opening unit.",
    )
    assert result["status"] == "success"
    sop = result["result"]["sop"]
    assert sop["text"] == "Isolate both breakers before opening unit."
    assert "document_id" not in sop
    assert sop["updated_by"] == USER


@pytest.mark.asyncio
async def test_upsert_sop_document_only():
    db = _DB()
    handler = _make_handler(db, {})
    result = await handler.upsert_sop_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        sop_document_id="doc-uuid-99",
    )
    assert result["result"]["sop"]["document_id"] == "doc-uuid-99"
    assert "text" not in result["result"]["sop"]


@pytest.mark.asyncio
async def test_upsert_sop_partial_update_keeps_other_field():
    db = _DB()
    handler = _make_handler(db, {
        "sop": {"text": "old text", "document_id": "old-doc", "updated_by": "old-user"},
    })
    # Update only document_id; text must be preserved.
    result = await handler.upsert_sop_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
        sop_document_id="new-doc",
    )
    sop = result["result"]["sop"]
    assert sop["text"] == "old text"
    assert sop["document_id"] == "new-doc"
    assert sop["updated_by"] == USER


@pytest.mark.asyncio
async def test_upsert_sop_rejects_empty_input():
    db = _DB()
    handler = _make_handler(db, {})
    result = await handler.upsert_sop_execute(
        work_order_id=WO, yacht_id=YACHT, user_id=USER,
    )
    assert result["status"] == "error"
    assert result["error_code"] == "NOTHING_TO_UPDATE"
    assert [c for c in db.calls if c["op"] == "update"] == []
