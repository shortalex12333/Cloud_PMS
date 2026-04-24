# apps/api/tests/test_attachment_comment_handlers.py
"""
Unit tests for AttachmentCommentHandlers (cohort-shared threaded comments
on pms_attachments, added 2026-04-24).

Mirrors DocumentCommentHandlers test surface where applicable. Uses a fake
fluent supabase stub — no DB, no HTTP.
"""

import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


YACHT = "yacht-uuid-1"
USER = "user-uuid-1"
OTHER_USER = "user-uuid-2"
ATT = "att-uuid-1"
COMMENT = "comment-uuid-1"


class _Q:
    def __init__(self, parent, tbl):
        self.parent = parent
        self.tbl = tbl
        self._op = None
        self._payload = None
        self._filters = []
        self._maybe_single = False

    def select(self, _cols): self._op = "select"; return self
    def update(self, p):     self._op = "update"; self._payload = p; return self
    def insert(self, p):     self._op = "insert"; self._payload = p; return self
    def eq(self, k, v):      self._filters.append(("eq", k, v)); return self
    def is_(self, k, v):     self._filters.append(("is_", k, v)); return self
    def order(self, *_a, **_kw): return self
    def limit(self, _):      return self

    def maybe_single(self):
        self._maybe_single = True
        return self

    def execute(self):
        self.parent.calls.append({
            "table": self.tbl, "op": self._op,
            "payload": self._payload, "filters": tuple(self._filters),
            "maybe_single": self._maybe_single,
        })
        # Canned responses are keyed (table, op, maybe_single).
        key = (self.tbl, self._op, self._maybe_single)
        canned = self.parent.canned.get(key)
        if canned is None and self._maybe_single:
            # "no row" for maybe_single → data=None
            return MagicMock(data=None)
        if canned is None:
            return MagicMock(data=[])
        if self._maybe_single:
            return MagicMock(data=canned.get("data"))
        return MagicMock(data=canned.get("data", []))


class _DB:
    def __init__(self):
        self.calls = []
        self.canned = {}
    def table(self, n): return _Q(self, n)


def _make_handler(db):
    from handlers.attachment_comment_handlers import AttachmentCommentHandlers
    return AttachmentCommentHandlers(supabase_client=db)


# ── add_attachment_comment ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_comment_happy_path():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {"data": {"id": ATT, "deleted_at": None}},
        ("pms_attachment_comments", "insert", False): {
            "data": [{"id": "new-1", "author_department": "engineering"}]
        },
    }
    h = _make_handler(db)
    out = await h.add_attachment_comment(
        attachment_id=ATT, yacht_id=YACHT, user_id=USER,
        comment="Panel open — wires crossed",
    )
    assert out["status"] == "success"
    assert out["attachment_id"] == ATT
    assert out["author_department"] == "engineering"

    inserts = [c for c in db.calls if c["table"] == "pms_attachment_comments" and c["op"] == "insert"]
    assert len(inserts) == 1
    assert inserts[0]["payload"]["comment"] == "Panel open — wires crossed"
    assert inserts[0]["payload"]["created_by"] == USER


@pytest.mark.asyncio
async def test_add_comment_rejects_empty_text():
    db = _DB()
    h = _make_handler(db)
    for blank in ("", "   ", None):
        out = await h.add_attachment_comment(
            attachment_id=ATT, yacht_id=YACHT, user_id=USER,
            comment=blank,  # type: ignore[arg-type]
        )
        assert out["status"] == "error"
        assert out["error_code"] == "VALIDATION_ERROR"
    # Zero DB writes.
    assert [c for c in db.calls if c["op"] == "insert"] == []


@pytest.mark.asyncio
async def test_add_comment_rejects_missing_attachment():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {"data": None},
    }
    h = _make_handler(db)
    out = await h.add_attachment_comment(
        attachment_id=ATT, yacht_id=YACHT, user_id=USER, comment="hello",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_add_comment_rejects_deleted_attachment():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {
            "data": {"id": ATT, "deleted_at": "2026-04-24T00:00:00Z"}
        },
    }
    h = _make_handler(db)
    out = await h.add_attachment_comment(
        attachment_id=ATT, yacht_id=YACHT, user_id=USER, comment="hello",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "INVALID_STATE"


@pytest.mark.asyncio
async def test_add_reply_validates_parent_thread():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {"data": {"id": ATT, "deleted_at": None}},
        ("pms_attachment_comments", "select", True): {"data": {"id": "parent-1"}},
        ("pms_attachment_comments", "insert", False): {
            "data": [{"id": "reply-1", "author_department": "engineering"}]
        },
    }
    h = _make_handler(db)
    out = await h.add_attachment_comment(
        attachment_id=ATT, yacht_id=YACHT, user_id=USER,
        comment="Confirm that reading",
        parent_comment_id="parent-1",
    )
    assert out["status"] == "success"
    # The INSERT payload carries the parent_comment_id
    inserts = [c for c in db.calls if c["op"] == "insert"]
    assert inserts[0]["payload"]["parent_comment_id"] == "parent-1"


@pytest.mark.asyncio
async def test_add_reply_rejects_unknown_parent():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {"data": {"id": ATT, "deleted_at": None}},
        ("pms_attachment_comments", "select", True): {"data": None},  # parent lookup returns nothing
    }
    h = _make_handler(db)
    out = await h.add_attachment_comment(
        attachment_id=ATT, yacht_id=YACHT, user_id=USER,
        comment="Reply to ghost", parent_comment_id="missing",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "NOT_FOUND"
    assert "Parent comment" in out["message"]


# ── update_attachment_comment ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_owner_happy_path():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": USER, "deleted_at": None}
        },
        ("pms_attachment_comments", "update", False): {
            "data": [{"id": COMMENT}]
        },
    }
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER,
        comment="Revised caption",
    )
    assert out["status"] == "success"
    updates = [c for c in db.calls if c["table"] == "pms_attachment_comments" and c["op"] == "update"]
    assert updates[0]["payload"]["comment"] == "Revised caption"
    assert updates[0]["payload"]["updated_by"] == USER


@pytest.mark.asyncio
async def test_update_non_owner_crew_forbidden():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": OTHER_USER, "deleted_at": None}
        },
        ("auth_users_roles", "select", True): {"data": {"role": "crew"}},
    }
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER, comment="Nope",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_update_non_owner_captain_allowed():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": OTHER_USER, "deleted_at": None}
        },
        ("auth_users_roles", "select", True): {"data": {"role": "captain"}},
        ("pms_attachment_comments", "update", False): {"data": [{"id": COMMENT}]},
    }
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER, comment="Captain edit",
    )
    assert out["status"] == "success"


@pytest.mark.asyncio
async def test_update_missing_comment_returns_not_found():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {"data": None},
    }
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER, comment="x",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_update_already_deleted_rejected():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": USER, "deleted_at": "2026-04-24T00:00:00Z"}
        },
    }
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER, comment="x",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "INVALID_STATE"


@pytest.mark.asyncio
async def test_update_empty_text_rejected():
    db = _DB()
    h = _make_handler(db)
    out = await h.update_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER, comment="   ",
    )
    assert out["status"] == "error"
    assert out["error_code"] == "VALIDATION_ERROR"


# ── delete_attachment_comment ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_owner_happy_path():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": USER, "deleted_at": None}
        },
        ("pms_attachment_comments", "update", False): {"data": [{"id": COMMENT}]},
    }
    h = _make_handler(db)
    out = await h.delete_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER,
    )
    assert out["status"] == "success"
    updates = [c for c in db.calls if c["op"] == "update"]
    assert updates[0]["payload"]["deleted_by"] == USER
    assert "deleted_at" in updates[0]["payload"]


@pytest.mark.asyncio
async def test_delete_non_owner_non_hod_forbidden():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": OTHER_USER, "deleted_at": None}
        },
        ("auth_users_roles", "select", True): {"data": {"role": "crew"}},
    }
    h = _make_handler(db)
    out = await h.delete_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER,
    )
    assert out["status"] == "error"
    assert out["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_delete_already_deleted_rejected():
    db = _DB()
    db.canned = {
        ("pms_attachment_comments", "select", True): {
            "data": {"id": COMMENT, "created_by": USER, "deleted_at": "2026-04-24T00:00:00Z"}
        },
    }
    h = _make_handler(db)
    out = await h.delete_attachment_comment(
        comment_id=COMMENT, yacht_id=YACHT, user_id=USER,
    )
    assert out["status"] == "error"
    assert out["error_code"] == "INVALID_STATE"


# ── list_attachment_comments + thread assembly ─────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_flat_list_when_include_threads_false():
    db = _DB()
    flat = [
        {"id": "1", "comment": "A", "parent_comment_id": None, "created_by": USER,  "created_at": "2026-04-24T01:00:00Z"},
        {"id": "2", "comment": "B", "parent_comment_id": "1",  "created_by": OTHER_USER, "created_at": "2026-04-24T02:00:00Z"},
    ]
    db.canned = {
        ("pms_attachments", "select", True): {"data": {"id": ATT}},
        ("pms_attachment_comments", "select", False): {"data": flat},
    }
    h = _make_handler(db)
    out = await h.list_attachment_comments(
        attachment_id=ATT, yacht_id=YACHT, include_threads=False,
    )
    assert out["status"] == "success"
    assert out["total_count"] == 2
    assert out["comments"] == flat  # unchanged


@pytest.mark.asyncio
async def test_list_builds_thread_tree_when_include_threads_true():
    db = _DB()
    flat = [
        {"id": "root", "comment": "Root", "parent_comment_id": None, "created_by": USER,  "created_at": "t1"},
        {"id": "r1",   "comment": "Reply 1", "parent_comment_id": "root", "created_by": OTHER_USER, "created_at": "t2"},
        {"id": "r2",   "comment": "Reply 2", "parent_comment_id": "root", "created_by": OTHER_USER, "created_at": "t3"},
        {"id": "orph", "comment": "Orphan",  "parent_comment_id": "missing-parent", "created_by": USER, "created_at": "t4"},
    ]
    db.canned = {
        ("pms_attachments", "select", True): {"data": {"id": ATT}},
        ("pms_attachment_comments", "select", False): {"data": flat},
    }
    h = _make_handler(db)
    out = await h.list_attachment_comments(
        attachment_id=ATT, yacht_id=YACHT, include_threads=True,
    )
    assert out["status"] == "success"
    # `total_count` reflects the flat row count, not tree size.
    assert out["total_count"] == 4
    roots = out["comments"]
    # "root" has two replies; "orph" surfaces as a root because its parent was missing.
    root_ids = sorted(r["id"] for r in roots)
    assert root_ids == ["orph", "root"]
    root = next(r for r in roots if r["id"] == "root")
    assert sorted(rep["id"] for rep in root["replies"]) == ["r1", "r2"]
    orph = next(r for r in roots if r["id"] == "orph")
    assert orph["replies"] == []


@pytest.mark.asyncio
async def test_list_returns_not_found_for_unknown_attachment():
    db = _DB()
    db.canned = {
        ("pms_attachments", "select", True): {"data": None},
    }
    h = _make_handler(db)
    out = await h.list_attachment_comments(
        attachment_id=ATT, yacht_id=YACHT,
    )
    assert out["status"] == "error"
    assert out["error_code"] == "NOT_FOUND"
