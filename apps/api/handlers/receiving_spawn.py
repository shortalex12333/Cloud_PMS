"""
Receiving auto-spawn from PO approval.

Called by approve_purchase_order and update_purchase_status (ordered transition).
Inserts pms_receiving + pms_receiving_items using service-role client — bypasses
the RPC which has HOD auth check and doesn't accept po_id.

Idempotent: skips if a non-deleted receiving already exists for the po_id.
"""
import uuid
import logging
from datetime import datetime, timezone

from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


def spawn_receiving_from_po(
    db: Client,
    po_id: str,
    yacht_id: str,
    user_id: str,
) -> dict:
    """
    Create a receiving record pre-populated from an approved PO.
    Returns {"spawned": True, "receiving_id": ...} or {"spawned": False, "reason": ...}.
    """
    # Idempotency guard
    existing = db.table("pms_receiving").select("id").eq(
        "po_id", po_id
    ).eq("yacht_id", yacht_id).is_("deleted_at", "null").limit(1).execute()
    if existing.data:
        return {"spawned": False, "reason": "already_exists", "receiving_id": existing.data[0]["id"]}

    # Fetch PO + supplier name
    po = db.table("pms_purchase_orders").select(
        "id, po_number, supplier_id, pms_suppliers(name)"
    ).eq("id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not po.data:
        logger.warning(f"[spawn_receiving] PO {po_id} not found, skipping spawn")
        return {"spawned": False, "reason": "po_not_found"}

    po_data = po.data
    po_number = po_data.get("po_number") or ""
    supplier_data = po_data.get("pms_suppliers") or {}
    vendor_name = supplier_data.get("name") or "Supplier"

    now = datetime.now(timezone.utc).isoformat()
    receiving_id = str(uuid.uuid4())

    recv_row = {
        "id": receiving_id,
        "yacht_id": yacht_id,
        "po_id": po_id,
        "po_number": po_number,
        "vendor_name": vendor_name,
        "vendor_reference": po_number,
        "received_by": user_id,
        "created_by": user_id,
        "status": "awaiting",
        "is_seed": False,
        "created_at": now,
    }

    ins = db.table("pms_receiving").insert(recv_row).execute()
    if not ins.data:
        logger.error(f"[spawn_receiving] INSERT pms_receiving failed for PO {po_id}")
        return {"spawned": False, "reason": "insert_failed"}

    # Fetch PO line items
    items_res = db.table("pms_purchase_order_items").select(
        "id, description, quantity_ordered, part_id, unit_price"
    ).eq("purchase_order_id", po_id).eq("yacht_id", yacht_id).execute()
    items = items_res.data or []

    receiving_items = []
    for item in items:
        receiving_items.append({
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "description": item.get("description") or "Item",
            "part_id": item.get("part_id"),
            "quantity_expected": item.get("quantity_ordered") or 0,
            "quantity_received": 0,
            "quantity_accepted": 0,
            "quantity_rejected": 0,
            "disposition": "pending",
            "unit_price": item.get("unit_price"),
        })

    if receiving_items:
        db.table("pms_receiving_items").insert(receiving_items).execute()

    try:
        ledger_row = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="create",
            entity_type="receiving",
            entity_id=receiving_id,
            action="spawn_receiving_from_po",
            change_summary=f"Receiving auto-created from PO {po_number} ({len(receiving_items)} items)",
            metadata={"po_id": po_id, "po_number": po_number, "item_count": len(receiving_items)},
        )
        db.table("ledger_events").insert(ledger_row).execute()
    except Exception as e:
        logger.warning(f"[spawn_receiving] Ledger event failed (non-fatal): {e}")

    logger.info(f"[spawn_receiving] Spawned receiving {receiving_id} from PO {po_id} ({len(receiving_items)} items)")
    return {"spawned": True, "receiving_id": receiving_id, "item_count": len(receiving_items)}
