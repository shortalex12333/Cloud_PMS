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
        "file_name": "engineering_handover_20260320.pdf",
        "department": "engineering",
        "export_type": "pdf",
        "status": "completed",
        "email_subject": None,
        "storage_path": "handovers/abc/engineering_handover_20260320.pdf",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("handover", ENTITY_ID, conn, YACHT_ID)

    assert "engineering_handover_20260320.pdf" in text
    assert "department: engineering" in text
    assert "format: pdf" in text


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


# ---------------------------------------------------------------------------
# certificate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_certificate_full():
    row = {
        "certificate_name": "Lloyds Register Class",
        "certificate_number": "LR-2026-001",
        "certificate_type": "CLASS",
        "issuing_authority": "Lloyds",
        "status": "active",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("certificate", ENTITY_ID, conn, YACHT_ID)

    assert text is not None
    assert "Lloyds Register Class" in text
    assert "type: CLASS" in text
    assert "authority: Lloyds" in text
    assert "status: active" in text
    assert "number: LR-2026-001" in text


# ---------------------------------------------------------------------------
# receiving
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_receiving_with_vendor():
    row = {
        "vendor_name": "Marine Parts Co",
        "vendor_reference": "REF-001",
        "notes": None,
        "status": "draft",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("receiving", ENTITY_ID, conn, YACHT_ID)

    assert "Receiving from Marine Parts Co" in text
    assert "ref: REF-001" in text
    assert "status: draft" in text


@pytest.mark.asyncio
async def test_receiving_no_vendor_uses_fallback():
    row = {"vendor_name": None, "vendor_reference": None, "notes": None, "status": "draft"}
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("receiving", ENTITY_ID, conn, YACHT_ID)

    assert text is not None
    assert text.startswith("Receiving")


# ---------------------------------------------------------------------------
# handover_item
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handover_item_full():
    row = {
        "summary": "Engine inspection overdue",
        "entity_type": "note",
        "entity_id": None,
        "section": "Engineering",
        "category": "urgent",
        "action_summary": "Schedule within 48 hours",
        "is_critical": True,
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("handover_item", ENTITY_ID, conn, YACHT_ID)

    assert "Engine inspection overdue" in text
    assert "CRITICAL" in text
    assert "type: note" in text
    assert "section: Engineering" in text
    assert "category: urgent" in text
    assert "Schedule within 48 hours" in text


# ---------------------------------------------------------------------------
# shopping_item
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shopping_item_full():
    row = {
        "part_name": "Fuel Filter",
        "part_number": "FF-4400",
        "manufacturer": "Racor",
        "status": "approved",
        "urgency": "high",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("shopping_item", ENTITY_ID, conn, YACHT_ID)

    assert "Fuel Filter" in text
    assert "part_number: FF-4400" in text
    assert "manufacturer: Racor" in text
    assert "urgency: high" in text
    assert "status: approved" in text


# ---------------------------------------------------------------------------
# email
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_full():
    row = {
        "subject": "Maintenance needed: Watermaker",
        "preview_text": "Please schedule service for serial SN104999.",
        "from_display_name": "Fleet Manager",
        "folder": "inbox",
    }
    conn = make_conn(fetchrow_return=row)

    text = await serialize_entity("email", ENTITY_ID, conn, YACHT_ID)

    assert "Maintenance needed: Watermaker" in text
    assert "from: Fleet Manager" in text
    assert "folder: inbox" in text
    assert "SN104999" in text
