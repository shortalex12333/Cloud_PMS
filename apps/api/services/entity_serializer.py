#!/usr/bin/env python3
"""
Entity Serializer — converts a known entity to a text string for embedding.

Used by Show Related V2 signal layer. The entity's attributes become the
search query, so the existing f1_search_cards RPC pipeline can discover
cross-domain related entities without any new ML infrastructure.

Pattern:
    entity_type + entity_id
        → DB fetch of entity attributes
        → text string (e.g. "ABC Engine Manual; doc_type: manual; equipment: main engine, C18")
        → generate_embeddings()    (existing cortex function)
        → call_hyper_search()     (existing RPC)
        → related entity results

See plan: Show Related V2 — Signal-Based Discovery Layer
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


async def serialize_entity(
    entity_type: str,
    entity_id: str,
    conn: asyncpg.Connection,
    yacht_id: str,
) -> Optional[str]:
    """
    Return a text representation of the entity suitable for embedding.

    Returns None if the entity is not found or no serializer is registered
    for the given type.
    """
    serializer = _SERIALIZERS.get(entity_type)
    if not serializer:
        logger.debug(f"[EntitySerializer] No serializer registered for type: {entity_type}")
        return None
    try:
        return await serializer(entity_id, conn, yacht_id)
    except Exception as e:
        logger.warning(
            f"[EntitySerializer] Failed to serialize {entity_type}/{entity_id}: {e}"
        )
        return None


# ---------------------------------------------------------------------------
# Per-type serializers
# ---------------------------------------------------------------------------

async def _serialize_work_order(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT wo.title, wo.description, wo.status, wo.priority,
               e.name AS equipment_name
        FROM pms_work_orders wo
        LEFT JOIN pms_equipment e ON e.id = wo.equipment_id
        WHERE wo.id = $1 AND wo.yacht_id = $2 AND wo.deleted_at IS NULL
        """,
        entity_id,
        yacht_id,
    )
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


async def _serialize_fault(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT f.title, f.description, f.severity,
               e.name AS equipment_name
        FROM pms_faults f
        LEFT JOIN pms_equipment e ON e.id = f.equipment_id
        WHERE f.id = $1 AND f.yacht_id = $2 AND f.deleted_at IS NULL
        """,
        entity_id,
        yacht_id,
    )
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


async def _serialize_equipment(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT name, manufacturer, model, system_type, location, criticality
        FROM pms_equipment
        WHERE id = $1 AND yacht_id = $2 AND deleted_at IS NULL
        """,
        entity_id,
        yacht_id,
    )
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


async def _serialize_part(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT name, part_number, category, manufacturer
        FROM pms_parts
        WHERE id = $1 AND yacht_id = $2 AND deleted_at IS NULL
        """,
        entity_id,
        yacht_id,
    )
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


async def _serialize_manual(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        """
        SELECT filename, doc_type, equipment_ids
        FROM doc_metadata
        WHERE id = $1 AND yacht_id = $2 AND deleted_at IS NULL
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = [row["filename"] or "Document"]
    if row["doc_type"]:
        parts.append(f"doc_type: {row['doc_type']}")
    # Resolve equipment names from equipment_ids array (GIN-indexed)
    eq_ids = row["equipment_ids"] or []
    if eq_ids:
        eq_rows = await conn.fetch(
            """
            SELECT name FROM pms_equipment
            WHERE id = ANY($1) AND yacht_id = $2 AND deleted_at IS NULL
            """,
            eq_ids,
            yacht_id,
        )
        if eq_rows:
            eq_names = ", ".join(r["name"] for r in eq_rows if r["name"])
            if eq_names:
                parts.append(f"equipment: {eq_names}")
    return "; ".join(parts)


async def _serialize_handover(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    # handover_exports has NO deleted_at (hard delete only)
    # No title/content columns — real columns are file_name, department, export_type, etc.
    row = await conn.fetchrow(
        """
        SELECT file_name, department, export_type, status, email_subject, storage_path
        FROM handover_exports
        WHERE id = $1 AND yacht_id = $2
        """,
        entity_id,
        yacht_id,
    )
    if not row:
        return None
    parts = []
    if row["file_name"]:
        parts.append(row["file_name"])
    elif row["email_subject"]:
        parts.append(row["email_subject"])
    else:
        parts.append("Handover export")
    if row["department"]:
        parts.append(f"department: {row['department']}")
    if row["export_type"]:
        parts.append(f"format: {row['export_type']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    return "; ".join(parts)


async def _serialize_certificate(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT certificate_name, certificate_number, certificate_type, "
        "issuing_authority, status "
        "FROM pms_vessel_certificates WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
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


async def _serialize_receiving(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT vendor_name, vendor_reference, notes, status "
        "FROM pms_receiving WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
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


async def _serialize_purchase_order(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT po.po_number, po.status, po.approval_notes, po.receiving_notes, "
        "s.name AS supplier_name "
        "FROM pms_purchase_orders po "
        "LEFT JOIN pms_suppliers s ON s.id = po.supplier_id "
        "WHERE po.id = $1 AND po.yacht_id = $2",
        entity_id, yacht_id,
    )
    if not row:
        return None
    parts = [f"Purchase Order {row['po_number']}" if row.get("po_number") else "Purchase Order"]
    if row["supplier_name"]:
        parts.append(f"supplier: {row['supplier_name']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["approval_notes"]:
        parts.append(str(row["approval_notes"])[:200])
    if row["receiving_notes"]:
        parts.append(str(row["receiving_notes"])[:200])
    return "; ".join(parts)


async def _serialize_handover_item(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT summary, entity_type, entity_id, section, category, "
        "action_summary, is_critical "
        "FROM handover_items WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
    if not row:
        return None
    summary = row["summary"] or ""
    # "Document attached" is a placeholder — resolve the actual document name
    if summary in ("Document attached", "") and row["entity_id"]:
        doc_row = await conn.fetchrow(
            "SELECT filename FROM doc_metadata WHERE id = $1 AND yacht_id = $2",
            row["entity_id"], yacht_id,
        )
        if doc_row and doc_row["filename"]:
            summary = f"Document: {doc_row['filename']}"
        elif not summary:
            summary = "Handover item"
    parts = [summary or "Handover item"]
    if row["is_critical"]:
        parts.append("CRITICAL")
    if row["entity_type"]:
        parts.append(f"type: {row['entity_type']}")
    if row["section"]:
        parts.append(f"section: {row['section']}")
    if row["category"]:
        parts.append(f"category: {row['category']}")
    if row["action_summary"]:
        parts.append(str(row["action_summary"])[:200])
    return "; ".join(parts)


async def _serialize_inventory(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    # pms_inventory_stock has part_id FK → pms_parts for the name
    row = await conn.fetchrow(
        """
        SELECT s.location, s.quantity, s.min_quantity,
               p.name AS part_name, p.part_number, p.manufacturer
        FROM pms_inventory_stock s
        LEFT JOIN pms_parts p ON p.id = s.part_id AND p.yacht_id = s.yacht_id
        WHERE s.id = $1 AND s.yacht_id = $2 AND s.deleted_at IS NULL
        """,
        entity_id, yacht_id,
    )
    if not row:
        return None
    parts = [row["part_name"] or "Inventory item"]
    if row["part_number"]:
        parts.append(f"part_number: {row['part_number']}")
    if row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    if row["location"]:
        parts.append(f"location: {row['location']}")
    if row["quantity"] is not None:
        parts.append(f"qty: {row['quantity']}")
        if row["min_quantity"] is not None and row["quantity"] <= row["min_quantity"]:
            parts.append("LOW STOCK")
    return "; ".join(parts)


async def _serialize_shopping_item(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT part_name, part_number, manufacturer, status, urgency "
        "FROM pms_shopping_list_items WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
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


async def _serialize_warranty(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT title, description, claim_number, status, vendor_name, manufacturer "
        "FROM pms_warranty_claims WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
    if not row:
        return None
    parts: list[str] = []
    if row["title"]:
        parts.append(f"Warranty: {row['title']}")
    if row["claim_number"]:
        parts.append(f"ref: {row['claim_number']}")
    if row["status"]:
        parts.append(f"status: {row['status']}")
    if row["vendor_name"]:
        parts.append(f"vendor: {row['vendor_name']}")
    elif row["manufacturer"]:
        parts.append(f"manufacturer: {row['manufacturer']}")
    if row["description"]:
        parts.append(row["description"][:200])
    return " | ".join(parts) if parts else "Warranty claim"


async def _serialize_email(
    entity_id: str, conn: asyncpg.Connection, yacht_id: str
) -> Optional[str]:
    row = await conn.fetchrow(
        "SELECT subject, preview_text, from_display_name, folder "
        "FROM email_messages WHERE id = $1 AND yacht_id = $2",
        entity_id, yacht_id,
    )
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
# Serializer registry
# ---------------------------------------------------------------------------

_SERIALIZERS: Dict[str, Callable] = {
    "work_order": _serialize_work_order,
    "fault": _serialize_fault,
    "equipment": _serialize_equipment,
    "part": _serialize_part,
    "inventory": _serialize_inventory,
    "manual": _serialize_manual,
    "document": _serialize_manual,         # alias
    "handover": _serialize_handover,
    "handover_export": _serialize_handover, # explicit alias
    "certificate": _serialize_certificate,
    "receiving": _serialize_receiving,
    "purchase_order": _serialize_purchase_order,
    "handover_item": _serialize_handover_item,
    "shopping_item": _serialize_shopping_item,
    "warranty": _serialize_warranty,
    "email": _serialize_email,
}

# Public constant — import this instead of accessing _SERIALIZERS directly.
# Routes and other consumers derive their allowed-types list from here so
# the gate can never drift from the serializer registry.
SUPPORTED_ENTITY_TYPES: frozenset = frozenset(_SERIALIZERS.keys())


__all__ = ["serialize_entity", "SUPPORTED_ENTITY_TYPES"]
