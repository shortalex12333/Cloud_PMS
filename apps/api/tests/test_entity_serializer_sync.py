"""
Tests for services/entity_serializer_sync.py — psycopg2 mirror of entity_serializer.py.

Verifies:
  - each entity type serializes to the expected text format
  - equipment name resolution for manuals (ARRAY_AGG join)
  - not-found entity returns None (no crash)
  - unknown entity type returns None (no crash)
  - SUPPORTED_ENTITY_TYPES_SYNC equals SUPPORTED_ENTITY_TYPES (drift guard)
  - column name aliases (inventory→part, document→manual, handover_export→handover)

Runs in-memory: psycopg2 RealDictCursor is fully mocked.
No DB connection required.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
from services.entity_serializer_sync import serialize_entity_sync, SUPPORTED_ENTITY_TYPES_SYNC


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

YACHT_ID  = "85fe1119-b04c-41ac-80f1-829d23322598"
ENTITY_ID = "11111111-1111-1111-1111-111111111111"


def make_cur(fetchone_return=None, fetchall_return=None):
    """Build a minimal psycopg2 RealDictCursor mock."""
    cur = MagicMock()
    cur.fetchone = MagicMock(return_value=fetchone_return)
    cur.fetchall = MagicMock(return_value=fetchall_return or [])
    return cur


# ---------------------------------------------------------------------------
# work_order
# ---------------------------------------------------------------------------

def test_work_order_with_equipment():
    cur = make_cur(fetchone_return={
        "title": "Replace fuel filters",
        "description": "Annual maintenance on primary fuel filters",
        "status": "open",
        "priority": "high",
        "equipment_name": "Main Engine",
    })
    text = serialize_entity_sync("work_order", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Replace fuel filters" in text
    assert "equipment: Main Engine" in text
    assert "status: open" in text
    assert "priority: high" in text


def test_work_order_no_description_duplicate():
    """Description equal to title should not be repeated."""
    cur = make_cur(fetchone_return={
        "title": "Pump overhaul",
        "description": "Pump overhaul",
        "status": "open",
        "priority": None,
        "equipment_name": None,
    })
    text = serialize_entity_sync("work_order", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert text.count("Pump overhaul") == 1


# ---------------------------------------------------------------------------
# fault
# ---------------------------------------------------------------------------

def test_fault_full():
    cur = make_cur(fetchone_return={
        "title": "Hydraulic leak on thruster",
        "description": "Oil visible on port thruster housing",
        "severity": "high",
        "equipment_name": "Port Thruster",
    })
    text = serialize_entity_sync("fault", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Hydraulic leak on thruster" in text
    assert "equipment: Port Thruster" in text
    assert "severity: high" in text


# ---------------------------------------------------------------------------
# equipment
# ---------------------------------------------------------------------------

def test_equipment_full():
    cur = make_cur(fetchone_return={
        "name": "Main Generator",
        "manufacturer": "Kohler",
        "model": "KGH-60",
        "system_type": "electrical",
        "location": "engine room",
        "criticality": "critical",
    })
    text = serialize_entity_sync("equipment", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Main Generator" in text
    assert "manufacturer: Kohler" in text
    assert "criticality: critical" in text


# ---------------------------------------------------------------------------
# part / inventory alias
# ---------------------------------------------------------------------------

def test_part_full():
    cur = make_cur(fetchone_return={
        "name": "Oil Filter",
        "part_number": "OF-4567",
        "category": "filtration",
        "manufacturer": "Caterpillar",
    })
    text = serialize_entity_sync("part", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Oil Filter" in text
    assert "part_number: OF-4567" in text
    assert "manufacturer: Caterpillar" in text


def test_inventory_alias_calls_same_serializer():
    """inventory must produce identical output to part for the same row."""
    row = {
        "name": "Fuel Filter",
        "part_number": "FF-001",
        "category": "filtration",
        "manufacturer": "Parker",
    }
    cur_part = make_cur(fetchone_return=row)
    cur_inv  = make_cur(fetchone_return=row)
    text_part = serialize_entity_sync("part",      ENTITY_ID, cur_part, YACHT_ID)
    text_inv  = serialize_entity_sync("inventory", ENTITY_ID, cur_inv,  YACHT_ID)
    assert text_part == text_inv


# ---------------------------------------------------------------------------
# manual / document alias
# ---------------------------------------------------------------------------

def test_manual_with_equipment_names():
    cur = make_cur(fetchone_return={
        "filename": "Caterpillar C18 Service Manual.pdf",
        "doc_type": "service_manual",
        "equipment_names": ["Main Engine", "Generator 2"],
    })
    text = serialize_entity_sync("manual", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Caterpillar C18" in text
    assert "doc_type: service_manual" in text
    assert "Main Engine" in text


def test_document_alias_calls_same_serializer():
    row = {
        "filename": "Safety Manual.pdf",
        "doc_type": "safety",
        "equipment_names": None,
    }
    cur_m = make_cur(fetchone_return=row)
    cur_d = make_cur(fetchone_return=row)
    assert serialize_entity_sync("manual",   ENTITY_ID, cur_m, YACHT_ID) == \
           serialize_entity_sync("document", ENTITY_ID, cur_d, YACHT_ID)


# ---------------------------------------------------------------------------
# handover / handover_export alias
# ---------------------------------------------------------------------------

def test_handover_full():
    cur = make_cur(fetchone_return={
        "title": "March Handover",
        "content": "Port engine service due. Watermaker filter replaced.",
    })
    text = serialize_entity_sync("handover", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "March Handover" in text
    assert "Port engine service due" in text


def test_handover_export_alias():
    row = {"title": "April Export", "content": "Nothing critical."}
    cur_h = make_cur(fetchone_return=row)
    cur_e = make_cur(fetchone_return=row)
    assert serialize_entity_sync("handover",        ENTITY_ID, cur_h, YACHT_ID) == \
           serialize_entity_sync("handover_export", ENTITY_ID, cur_e, YACHT_ID)


# ---------------------------------------------------------------------------
# certificate
# ---------------------------------------------------------------------------

def test_certificate_full():
    cur = make_cur(fetchone_return={
        "certificate_name": "Lloyds Register Class",
        "certificate_type": "CLASS",
        "issuing_authority": "Lloyd's Register",
        "status": "valid",
        "certificate_number": "LR-2024-001",
    })
    text = serialize_entity_sync("certificate", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Lloyds Register Class" in text
    assert "type: CLASS" in text
    assert "authority: Lloyd's Register" in text
    assert "status: valid" in text


# ---------------------------------------------------------------------------
# receiving
# ---------------------------------------------------------------------------

def test_receiving_with_vendor():
    cur = make_cur(fetchone_return={
        "vendor_name": "Marine Parts Ltd",
        "vendor_reference": "PO-2024-0042",
        "status": "complete",
        "notes": "All items received in good condition",
    })
    text = serialize_entity_sync("receiving", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Marine Parts Ltd" in text
    assert "ref: PO-2024-0042" in text
    assert "status: complete" in text


def test_receiving_no_vendor_uses_fallback():
    cur = make_cur(fetchone_return={
        "vendor_name": None,
        "vendor_reference": None,
        "status": "pending",
        "notes": None,
    })
    text = serialize_entity_sync("receiving", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Receiving" in text
    assert "status: pending" in text


# ---------------------------------------------------------------------------
# handover_item
# ---------------------------------------------------------------------------

def test_handover_item_full():
    cur = make_cur(fetchone_return={
        "summary": "Main engine oil change due",
        "entity_type": "equipment",
        "section": "engineering",
        "category": "maintenance",
        "action_summary": "Oil change at next port",
    })
    text = serialize_entity_sync("handover_item", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Main engine oil change due" in text
    assert "section: engineering" in text
    assert "category: maintenance" in text


# ---------------------------------------------------------------------------
# shopping_item
# ---------------------------------------------------------------------------

def test_shopping_item_full():
    cur = make_cur(fetchone_return={
        "part_name": "Hydraulic Oil",
        "part_number": "HO-46",
        "manufacturer": "Shell",
        "urgency": "high",
        "status": "approved",
    })
    text = serialize_entity_sync("shopping_item", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Hydraulic Oil" in text
    assert "manufacturer: Shell" in text
    assert "urgency: high" in text
    assert "status: approved" in text


def test_shopping_item_minimal_fields():
    """Item with only part_name and status should still produce text."""
    cur = make_cur(fetchone_return={
        "part_name": "Crew Request Item",
        "part_number": None,
        "manufacturer": None,
        "urgency": None,
        "status": "candidate",
    })
    text = serialize_entity_sync("shopping_item", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Crew Request Item" in text
    assert "status: candidate" in text


# ---------------------------------------------------------------------------
# email
# ---------------------------------------------------------------------------

def test_email_full():
    cur = make_cur(fetchone_return={
        "subject": "Re: WO–0007 status",
        "from_display_name": "Alex Short",
        "folder": "inbox",
        "preview_text": "Checking on work order WO–0007 completion date.",
    })
    text = serialize_entity_sync("email", ENTITY_ID, cur, YACHT_ID)
    assert text is not None
    assert "Re: WO–0007 status" in text
    assert "from: Alex Short" in text
    assert "folder: inbox" in text
    assert "Checking on work order" in text


# ---------------------------------------------------------------------------
# Not-found and unknown type
# ---------------------------------------------------------------------------

def test_not_found_returns_none():
    cur = make_cur(fetchone_return=None)
    result = serialize_entity_sync("work_order", ENTITY_ID, cur, YACHT_ID)
    assert result is None


def test_unknown_type_returns_none():
    cur = make_cur()
    result = serialize_entity_sync("unknown_entity_type", ENTITY_ID, cur, YACHT_ID)
    assert result is None
    # Cursor should never have been called
    cur.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Drift guard — sync and async type sets must match exactly
# ---------------------------------------------------------------------------

def test_type_sets_match():
    """SUPPORTED_ENTITY_TYPES_SYNC must equal SUPPORTED_ENTITY_TYPES."""
    from services.entity_serializer import SUPPORTED_ENTITY_TYPES
    diff = SUPPORTED_ENTITY_TYPES_SYNC ^ SUPPORTED_ENTITY_TYPES
    assert not diff, (
        f"Sync/async type set mismatch — add missing types to both files: {diff}"
    )
