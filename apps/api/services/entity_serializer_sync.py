#!/usr/bin/env python3
"""
Entity Serializer Sync — psycopg2-compatible mirror of entity_serializer.py.

Used by the projection worker (which is synchronous, psycopg2-based) to build
search_text from entity attributes. Replaces the legacy build_search_text()
column-concatenation approach with the same rich text produced by the async
serializer used at query time.

This ensures both pipelines stay in sync:
    - Query time  (show_related):    entity_serializer.py     (asyncpg)
    - Index time  (projection_worker): entity_serializer_sync.py (psycopg2)

Rules:
    - NEVER run a second cur.execute() inside a serializer — use JOINs.
    - Positional params use %s, not $1/$2.
    - SUPPORTED_ENTITY_TYPES_SYNC must equal SUPPORTED_ENTITY_TYPES.

See plan: Piece B — Projection-Serializer Convergence
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


def serialize_entity_sync(
    entity_type: str,
    entity_id: str,
    cur,          # psycopg2 RealDictCursor
    yacht_id: str,
) -> Optional[str]:
    """
    Sync version of serialize_entity() for projection_worker.
    Returns a text representation of the entity suitable for embedding.
    Returns None if the entity type is unknown or the entity is not found.
    """
    fn = _SERIALIZERS_SYNC.get(entity_type)
    if not fn:
        return None
    try:
        return fn(entity_id, cur, yacht_id)
    except Exception as e:
        logger.warning(f"[EntitySerializerSync] Failed {entity_type}/{entity_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Per-type serializers (prefix _s_ to avoid grep collision with async version)
# ---------------------------------------------------------------------------

def _s_work_order(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT wo.title, wo.description, wo.status, wo.priority,
               e.name AS equipment_name
        FROM pms_work_orders wo
        LEFT JOIN pms_equipment e ON e.id = wo.equipment_id
        WHERE wo.id = %s AND wo.yacht_id = %s AND wo.deleted_at IS NULL
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["title"] or "Work Order"]
    if row["equipment_name"]:
        parts.append(f"equipment: {row['equipment_name']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["priority"]:
        parts.append(f"priority: {row['priority']}")
    desc = str(row["description"] or "").strip()
    if desc and desc != (row["title"] or "").strip():
        parts.append(desc[:200])
    return "; ".join(parts)


def _s_fault(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT f.title, f.description, f.severity,
               e.name AS equipment_name
        FROM pms_faults f
        LEFT JOIN pms_equipment e ON e.id = f.equipment_id
        WHERE f.id = %s AND f.yacht_id = %s AND f.deleted_at IS NULL
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["title"] or "Fault"]
    if row["equipment_name"]:
        parts.append(f"equipment: {row['equipment_name']}")
    if row["severity"]:
        parts.append(f"severity: {row['severity']}")
    desc = str(row["description"] or "").strip()
    if desc and desc != (row["title"] or "").strip():
        parts.append(desc[:200])
    return "; ".join(parts)


def _s_equipment(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT name, manufacturer, model, system_type, location, criticality
        FROM pms_equipment
        WHERE id = %s AND yacht_id = %s AND deleted_at IS NULL
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["name"] or "Equipment"]
    if row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    if row["model"]:
        parts.append(f"model: {row['model']}")
    if row["system_type"]:
        parts.append(f"system_type: {row['system_type']}")
    if row["location"]:
        parts.append(f"location: {row['location']}")
    if row["criticality"]:
        parts.append(f"criticality: {row['criticality']}")
    return "; ".join(parts)


def _s_part(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT name, part_number, category, manufacturer
        FROM pms_parts
        WHERE id = %s AND yacht_id = %s AND deleted_at IS NULL
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["name"] or "Part"]
    if row["part_number"]:
        parts.append(f"part_number: {row['part_number']}")
    if row["category"]:
        parts.append(f"category: {row['category']}")
    if row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    return "; ".join(parts)


def _s_manual(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    # Single query with aggregated equipment names — avoids second cur.execute().
    cur.execute("""
        SELECT d.filename, d.doc_type,
               ARRAY_AGG(e.name) FILTER (WHERE e.name IS NOT NULL) AS equipment_names
        FROM doc_metadata d
        LEFT JOIN pms_equipment e
            ON e.id = ANY(d.equipment_ids)
            AND e.yacht_id = %s
            AND e.deleted_at IS NULL
        WHERE d.id = %s AND d.yacht_id = %s AND d.deleted_at IS NULL
        GROUP BY d.filename, d.doc_type
    """, (yacht_id, entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["filename"] or "Document"]
    if row["doc_type"]:
        parts.append(f"doc_type: {row['doc_type']}")
    eq_names = row.get("equipment_names") or []
    if eq_names:
        parts.append(f"equipment: {', '.join(eq_names)}")
    return "; ".join(parts)


def _s_handover(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT title, content
        FROM handover_exports
        WHERE id = %s AND yacht_id = %s AND (deleted_at IS NULL)
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["title"] or "Handover"]
    if row["content"]:
        parts.append(str(row["content"])[:300])
    return "; ".join(parts)


def _s_certificate(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT certificate_name, certificate_number, certificate_type,
               issuing_authority, status
        FROM pms_vessel_certificates
        WHERE id = %s AND yacht_id = %s AND (deleted_at IS NULL)
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["certificate_name"] or "Certificate"]
    if row["certificate_type"]:
        parts.append(f"type: {row['certificate_type']}")
    if row["issuing_authority"]:
        parts.append(f"authority: {row['issuing_authority']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["certificate_number"]:
        parts.append(f"number: {row['certificate_number']}")
    return "; ".join(parts)


def _s_receiving(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT vendor_name, vendor_reference, notes, status
        FROM pms_receiving
        WHERE id = %s AND yacht_id = %s AND (deleted_at IS NULL)
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [f"Receiving from {row['vendor_name']}" if row.get("vendor_name") else "Receiving"]
    if row["vendor_reference"]:
        parts.append(f"ref: {row['vendor_reference']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["notes"]:
        parts.append(str(row["notes"])[:200])
    return "; ".join(parts)


def _s_handover_item(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT summary, entity_type, section, category, action_summary
        FROM handover_items
        WHERE id = %s AND yacht_id = %s
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["summary"] or "Handover item"]
    if row["entity_type"]:
        parts.append(f"type: {row['entity_type']}")
    if row["section"]:
        parts.append(f"section: {row['section']}")
    if row["category"]:
        parts.append(f"category: {row['category']}")
    if row["action_summary"]:
        parts.append(str(row["action_summary"])[:200])
    return "; ".join(parts)


def _s_shopping_item(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT part_name, part_number, manufacturer, status, urgency
        FROM pms_shopping_list_items
        WHERE id = %s AND yacht_id = %s
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["part_name"] or "Shopping item"]
    if row["part_number"]:
        parts.append(f"part_number: {row['part_number']}")
    if row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    if row["urgency"]:
        parts.append(f"urgency: {row['urgency']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    return "; ".join(parts)


def _s_email(entity_id: str, cur, yacht_id: str) -> Optional[str]:
    cur.execute("""
        SELECT subject, preview_text, from_display_name, folder
        FROM email_messages
        WHERE id = %s AND yacht_id = %s
    """, (entity_id, yacht_id))
    row = cur.fetchone()
    if not row:
        return None
    parts = [row["subject"] or "Email"]
    if row["from_display_name"]:
        parts.append(f"from: {row['from_display_name']}")
    if row["folder"]:
        parts.append(f"folder: {row['folder']}")
    if row["preview_text"]:
        parts.append(str(row["preview_text"])[:200])
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Serializer registry — must mirror _SERIALIZERS in entity_serializer.py
# ---------------------------------------------------------------------------

_SERIALIZERS_SYNC: Dict[str, Callable] = {
    "work_order":      _s_work_order,
    "fault":           _s_fault,
    "equipment":       _s_equipment,
    "part":            _s_part,
    "inventory":       _s_part,           # alias — same table as part
    "manual":          _s_manual,
    "document":        _s_manual,         # alias
    "handover":        _s_handover,
    "handover_export": _s_handover,       # explicit alias
    "certificate":     _s_certificate,
    "receiving":       _s_receiving,
    "handover_item":   _s_handover_item,
    "shopping_item":   _s_shopping_item,
    "email":           _s_email,
}

# Public constant — import this to gate entity type checks.
# Must equal SUPPORTED_ENTITY_TYPES from entity_serializer.py.
SUPPORTED_ENTITY_TYPES_SYNC: frozenset = frozenset(_SERIALIZERS_SYNC.keys())


__all__ = ["serialize_entity_sync", "SUPPORTED_ENTITY_TYPES_SYNC"]
