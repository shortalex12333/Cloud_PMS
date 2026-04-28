"""
Tests for handlers/related_handlers.py — Show Related feature.

Coverage:
  - get_related: response shape, group construction, handles empty result
  - add_related: validation (entity type, link type, self-link), happy path,
                 duplicate detection (409), HOD role gating (403)

Runs in-memory (LAW 17): no real DB, Supabase client is fully mocked.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.related_handlers import RelatedHandlers


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

YACHT_ID   = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID    = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
WO_ID      = "11111111-1111-1111-1111-111111111111"
FAULT_ID   = "22222222-2222-2222-2222-222222222222"
PART_ID    = "33333333-3333-3333-3333-333333333333"
LINK_ID    = "99999999-9999-9999-9999-999999999999"


def make_db_mock(
    *,
    is_hod: bool = True,
    source_exists: bool = True,
    target_exists: bool = True,
    existing_link: bool = False,
    link_insert_data: dict | None = None,
    audit_insert_data: dict | None = None,
    explicit_source_links: list | None = None,
    explicit_target_links: list | None = None,
) -> MagicMock:
    """
    Build a mocked Supabase client that answers:
      - auth_users_roles query (for is_hod_or_manager)
      - entity existence checks
      - duplicate link check
      - pms_entity_links insert
      - pms_audit_log insert
      - explicit links queries (both directions)
    """
    db = MagicMock()

    def chain(*args, **kwargs):
        """Return a chain mock whose .execute() returns a result with .data."""
        c = MagicMock()
        c.select.return_value = c
        c.insert.return_value = c
        c.eq.return_value = c
        c.neq.return_value = c
        c.gte.return_value = c
        c.limit.return_value = c
        c.order.return_value = c
        c.single.return_value = c
        c.execute.return_value = MagicMock(data=[])
        return c

    db.table.side_effect = lambda name: chain()

    # We patch individual table calls by making table() side_effect smart
    call_counts: dict[str, int] = {}

    def table_factory(name: str) -> MagicMock:
        c = chain()

        if name == "auth_users_roles":
            role_data = [{"role": "hod"}] if is_hod else []
            c.execute.return_value = MagicMock(data=role_data)

        elif name == "pms_entity_links":
            # We need multiple different responses depending on call context.
            # Use a counter to distinguish insert vs duplicate check vs explicit queries.
            call_counts[name] = call_counts.get(name, 0)

            def eq_chain_factory(*args, **kwargs):
                """eq() returns a new chain with customized execute."""
                inner = chain()

                def inner_execute():
                    call_counts[name] += 1
                    n = call_counts[name]
                    if n == 1:  # duplicate check
                        dup_data = [{"id": LINK_ID}] if existing_link else []
                        return MagicMock(data=dup_data)
                    elif n == 2:  # insert
                        insert_data = link_insert_data or [{"id": LINK_ID, "created_at": "2026-01-01T00:00:00Z"}]
                        return MagicMock(data=insert_data)
                    elif n == 3:  # explicit source query (get_related)
                        return MagicMock(data=explicit_source_links or [])
                    elif n == 4:  # explicit target query (GAP-06)
                        return MagicMock(data=explicit_target_links or [])
                    else:
                        return MagicMock(data=[])
                inner.execute.side_effect = inner_execute
                inner.eq.return_value = inner
                inner.neq.return_value = inner
                inner.order.return_value = inner
                inner.limit.return_value = inner
                return inner

            c.eq.side_effect = eq_chain_factory
            c.select.return_value = c
            c.insert.return_value = c

        elif name == "pms_audit_log":
            insert_data = audit_insert_data or [{"id": "audit-uuid"}]
            c.execute.return_value = MagicMock(data=insert_data)

        else:
            # Entity existence checks — works for any entity table
            if source_exists and target_exists:
                c.execute.return_value = MagicMock(data=[{"id": "some-id"}])
            else:
                c.execute.return_value = MagicMock(data=[])

        return c

    db.table.side_effect = table_factory
    return db


# ---------------------------------------------------------------------------
# get_related: response shape
# ---------------------------------------------------------------------------

class TestGetRelated:
    """Unit tests for RelatedHandlers.get_related()"""

    @pytest.mark.asyncio
    async def test_returns_success_with_groups_key(self):
        """get_related must return dict with status='success' and groups list."""
        db = MagicMock()

        # Mock all DB calls to return empty data (simple path)
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain

        handlers = RelatedHandlers(db)
        result = await handlers.get_related(
            yacht_id=YACHT_ID,
            entity_type="work_order",
            entity_id=WO_ID,
            user_id=USER_ID,
        )

        assert result["status"] == "success"
        assert isinstance(result["groups"], list)
        assert "add_related_enabled" in result
        assert "group_counts" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_unsupported_entity_type_raises_400(self):
        """Unknown entity_type must raise 400, not 500."""
        db = MagicMock()
        db.table.return_value = MagicMock(
            select=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    execute=MagicMock(return_value=MagicMock(data=[]))
                ))
            ))
        )
        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.get_related(
                yacht_id=YACHT_ID,
                entity_type="invoice",  # not in VALID_ENTITY_TYPES
                entity_id=WO_ID,
                user_id=USER_ID,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_groups_have_required_fields(self):
        """Each group returned must have group_key, label, count, items."""
        db = MagicMock()

        # Return one WO-related part via FK
        part_row = {
            "id": PART_ID,
            "name": "Test Part",
            "part_number": "P-001",
            "quantity_on_hand": 5,
        }

        call_count = [0]
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain

        def execute():
            call_count[0] += 1
            # First call returns a part for the WO parts query
            if call_count[0] == 1:
                return MagicMock(data=[{
                    "pms_parts": part_row,
                    "quantity": 2,
                }])
            return MagicMock(data=[])

        chain.execute.side_effect = execute
        db.table.return_value = chain

        handlers = RelatedHandlers(db)
        result = await handlers.get_related(
            yacht_id=YACHT_ID,
            entity_type="work_order",
            entity_id=WO_ID,
            user_id=USER_ID,
        )

        for group in result["groups"]:
            assert "group_key" in group
            assert "label" in group
            assert "count" in group
            assert "items" in group
            assert isinstance(group["items"], list)


# ---------------------------------------------------------------------------
# add_related: validation
# ---------------------------------------------------------------------------

class TestAddRelatedValidation:
    """Unit tests for RelatedHandlers.add_related() — validation paths."""

    @pytest.mark.asyncio
    async def test_invalid_source_entity_type_raises_400(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = MagicMock(data={"role": "hod"})
        db.table.return_value = chain
        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="invoice",  # invalid
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="related",
            )
        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_link_type_raises_400(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = MagicMock(data={"role": "hod"})
        db.table.return_value = chain

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="explicit",  # invalid — GAP-01: not in VALID_LINK_TYPES
            )
        assert exc_info.value.status_code == 400
        assert "link_type" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_self_link_raises_400(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = MagicMock(data={"role": "hod"})
        db.table.return_value = chain

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="work_order",
                target_entity_id=WO_ID,  # same ID as source
                link_type="related",
            )
        assert exc_info.value.status_code == 400
        assert "self" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_note_over_500_chars_raises_400(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = MagicMock(data={"role": "hod"})
        db.table.return_value = chain

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="related",
                note="x" * 501,  # over 500 char limit
            )
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# add_related: role gating
# ---------------------------------------------------------------------------

class TestAddRelatedRoleGating:
    """Role-gate: only HOD/manager/captain can create links."""

    @pytest.mark.asyncio
    async def test_crew_role_raises_403(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        # auth_users_roles returns crew role (not HOD/manager)
        chain.execute.return_value = MagicMock(data={"role": "crew"})
        db.table.return_value = chain

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="related",
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_role_row_raises_403(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.maybe_single.return_value = chain
        chain.execute.return_value = MagicMock(data=None)  # no role row at all
        db.table.return_value = chain

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="related",
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# add_related: happy path
# ---------------------------------------------------------------------------

class TestAddRelatedHappyPath:
    """add_related happy path: HOD creates valid link — returns correct shape."""

    @pytest.mark.asyncio
    async def test_returns_success_shape(self):
        """add_related must return { status, link_id, created_at }."""
        call_counts: dict[str, int] = {}

        def table_factory(name: str) -> MagicMock:
            c = MagicMock()
            c.select.return_value = c
            c.insert.return_value = c
            c.eq.return_value = c
            c.neq.return_value = c
            c.order.return_value = c
            c.limit.return_value = c
            c.single.return_value = c

            if name == "auth_users_roles":
                c.maybe_single.return_value = c
                c.execute.return_value = MagicMock(data={"role": "hod"})
            elif name == "pms_entity_links":
                call_counts[name] = call_counts.get(name, 0)

                def execute():
                    call_counts[name] += 1
                    n = call_counts[name]
                    if n == 1:  # duplicate check → empty (no duplicate)
                        return MagicMock(data=[])
                    else:       # insert
                        return MagicMock(data=[{"id": LINK_ID, "created_at": "2026-01-01T00:00:00Z"}])

                c.execute.side_effect = execute
            elif name == "pms_audit_log":
                c.execute.return_value = MagicMock(data=[{"id": "audit-id"}])
            else:
                # Entity existence checks
                c.execute.return_value = MagicMock(data=[{"id": "entity-id"}])

            return c

        db = MagicMock()
        db.table.side_effect = table_factory

        handlers = RelatedHandlers(db)
        result = await handlers.add_related(
            yacht_id=YACHT_ID,
            user_id=USER_ID,
            source_entity_type="work_order",
            source_entity_id=WO_ID,
            target_entity_type="fault",
            target_entity_id=FAULT_ID,
            link_type="related",
            note="Test explicit link",
        )

        assert result["status"] == "success"
        assert result["link_id"] == LINK_ID
        assert isinstance(result["created_at"], str)
        assert len(result["created_at"]) > 0

    @pytest.mark.asyncio
    async def test_duplicate_raises_409(self):
        """add_related must raise 409 if link already exists."""
        call_counts: dict[str, int] = {}

        def table_factory(name: str) -> MagicMock:
            c = MagicMock()
            c.select.return_value = c
            c.insert.return_value = c
            c.eq.return_value = c
            c.neq.return_value = c
            c.order.return_value = c
            c.limit.return_value = c

            if name == "auth_users_roles":
                c.maybe_single.return_value = c
                c.execute.return_value = MagicMock(data={"role": "hod"})
            elif name == "pms_entity_links":
                call_counts[name] = call_counts.get(name, 0)

                def execute():
                    call_counts[name] += 1
                    # First call = duplicate check → returns existing row
                    return MagicMock(data=[{"id": LINK_ID}])

                c.execute.side_effect = execute
            else:
                c.execute.return_value = MagicMock(data=[{"id": "entity-id"}])

            return c

        db = MagicMock()
        db.table.side_effect = table_factory

        handlers = RelatedHandlers(db)

        with pytest.raises(HTTPException) as exc_info:
            await handlers.add_related(
                yacht_id=YACHT_ID,
                user_id=USER_ID,
                source_entity_type="work_order",
                source_entity_id=WO_ID,
                target_entity_type="fault",
                target_entity_id=FAULT_ID,
                link_type="related",
            )
        assert exc_info.value.status_code == 409
