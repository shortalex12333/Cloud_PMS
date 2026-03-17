"""
Tests for services/entity_serializer.py — Show Related signal layer.

Verifies:
  - each entity type serializes to the expected text format
  - equipment name resolution for documents (equipment_ids[])
  - not-found entity returns None (no crash)
  - unknown entity type returns None (no crash)

Runs in-memory (LAW 17): asyncpg connection is fully mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.entity_serializer import serialize_entity


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
ENTITY_ID = "11111111-1111-1111-1111-111111111111"
EQ_ID_1   = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EQ_ID_2   = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def make_conn(fetchrow_return=None, fetch_return=None):
    """Build a minimal asyncpg connection mock."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.fetch = AsyncMock(return_value=fetch_return or [])
    return conn


# ---------------------------------------------------------------------------
# work_order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_work_order_with_equipment():
    row = {
        "title": "Replace fuel filters",
        "description": "Annual maintenance on primary fuel filters",
        "status": "open",
        "priority": "high",
        "equipment_name": "Main Engine",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("work_order", ENTITY_ID, conn, YACHT_ID)

    assert text is not None
    assert "Replace fuel filters" in text
    assert "equipment: Main Engine" in text
    assert "status: open" in text
    assert "priority: high" in text
    assert "Annual maintenance" in text


@pytest.mark.asyncio
async def test_work_order_without_equipment():
    row = {
        "title": "General inspection",
        "description": None,
        "status": "scheduled",
        "priority": None,
        "equipment_name": None,
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("work_order", ENTITY_ID, conn, YACHT_ID)

    assert text == "General inspection; status: scheduled"


@pytest.mark.asyncio
async def test_work_order_not_found():
    conn = make_conn(fetchrow_return=None)
    text = await serialize_entity("work_order", ENTITY_ID, conn, YACHT_ID)
    assert text is None


# ---------------------------------------------------------------------------
# fault
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fault_with_equipment():
    row = {
        "title": "Engine overheat",
        "description": "Temperature exceeded 100°C",
        "severity": "critical",
        "equipment_name": "Caterpillar C18",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("fault", ENTITY_ID, conn, YACHT_ID)

    assert "Engine overheat" in text
    assert "equipment: Caterpillar C18" in text
    assert "severity: critical" in text


# ---------------------------------------------------------------------------
# equipment
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_equipment_full():
    # pms_equipment uses system_type + criticality, not category
    row = {
        "name": "Main Engine",
        "manufacturer": "Caterpillar",
        "model": "C18",
        "system_type": "propulsion",
        "location": "engine room",
        "criticality": "critical",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("equipment", ENTITY_ID, conn, YACHT_ID)

    assert "Main Engine" in text
    assert "manufacturer: Caterpillar" in text
    assert "model: C18" in text
    assert "system_type: propulsion" in text
    assert "location: engine room" in text
    assert "criticality: critical" in text


# ---------------------------------------------------------------------------
# manual / document — equipment_ids[] resolution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_with_single_equipment():
    doc_row = {
        "filename": "C18 Engine Manual.pdf",
        "doc_type": "manual",
        "equipment_ids": [EQ_ID_1],
    }
    eq_rows = [{"name": "Main Engine"}]
    conn = make_conn(fetchrow_return=doc_row, fetch_return=eq_rows)

    text = await serialize_entity("manual", ENTITY_ID, conn, YACHT_ID)

    assert "C18 Engine Manual.pdf" in text
    assert "doc_type: manual" in text
    assert "equipment: Main Engine" in text


@pytest.mark.asyncio
async def test_manual_with_multiple_equipment():
    doc_row = {
        "filename": "Dual Engine Manual.pdf",
        "doc_type": "manual",
        "equipment_ids": [EQ_ID_1, EQ_ID_2],
    }
    eq_rows = [{"name": "Port Engine"}, {"name": "Starboard Engine"}]
    conn = make_conn(fetchrow_return=doc_row, fetch_return=eq_rows)

    text = await serialize_entity("manual", ENTITY_ID, conn, YACHT_ID)

    assert "Port Engine" in text
    assert "Starboard Engine" in text


@pytest.mark.asyncio
async def test_manual_no_equipment_ids():
    doc_row = {
        "filename": "General Safety Manual.pdf",
        "doc_type": "manual",
        "equipment_ids": [],
    }
    conn = make_conn(fetchrow_return=doc_row)

    text = await serialize_entity("manual", ENTITY_ID, conn, YACHT_ID)

    assert "General Safety Manual.pdf" in text
    assert "equipment:" not in text


@pytest.mark.asyncio
async def test_document_alias_same_as_manual():
    """'document' is an alias for 'manual' serializer."""
    doc_row = {
        "filename": "Compliance Doc.pdf",
        "doc_type": "certificate",
        "equipment_ids": [],
    }
    conn = make_conn(fetchrow_return=doc_row)

    text = await serialize_entity("document", ENTITY_ID, conn, YACHT_ID)

    assert "Compliance Doc.pdf" in text


# ---------------------------------------------------------------------------
# handover
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handover_serialization():
    row = {
        "title": "Main Engine Handover — March 2026",
        "content": "Fuel filters replaced. Injectors checked. Next service: 500h.",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("handover", ENTITY_ID, conn, YACHT_ID)

    assert "Main Engine Handover" in text
    assert "Fuel filters replaced" in text


@pytest.mark.asyncio
async def test_handover_not_found():
    conn = make_conn(fetchrow_return=None)
    text = await serialize_entity("handover", ENTITY_ID, conn, YACHT_ID)
    assert text is None


# ---------------------------------------------------------------------------
# Unknown type + error resilience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_entity_type_returns_none():
    conn = make_conn()
    text = await serialize_entity("invoice", ENTITY_ID, conn, YACHT_ID)
    assert text is None


@pytest.mark.asyncio
async def test_db_exception_returns_none():
    """DB error should return None, not raise."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=Exception("connection error"))

    text = await serialize_entity("work_order", ENTITY_ID, conn, YACHT_ID)

    assert text is None
