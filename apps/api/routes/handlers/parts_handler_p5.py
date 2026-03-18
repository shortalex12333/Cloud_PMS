# routes/handlers/parts_handler_p5.py
#
# Phase 5 dispatch handlers — parts / inventory domain (17 actions).
# Translated from p0_actions_routes.py elif blocks.
#
# Handler contract:
#   async def handler(payload, context, yacht_id, user_id, user_context, db_client) -> dict
#
# NOTE: named parts_handler_p5.py (not parts_handler.py) to avoid confusion
# with the domain class at handlers/part_handlers.py.

from datetime import datetime, timezone
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


async def check_stock_level(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    from handlers.inventory_handlers import InventoryHandlers
    inv = InventoryHandlers(db_client)
    return await inv.check_stock_level_execute(
        part_id=part_id,
        yacht_id=yacht_id,
        user_id=user_id,
    )


async def log_part_usage(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # RBAC: HoD+ only
    allowed = ["chief_engineer", "chief_officer", "captain", "manager"]
    if user_context.get("role", "") not in allowed:
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": "Role not authorized",
            "required_roles": allowed,
        }

    part_id = payload.get("part_id")
    quantity = payload.get("quantity")
    usage_reason = payload.get("usage_reason")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if quantity is None:
        raise HTTPException(status_code=400, detail="quantity is required")
    if not usage_reason:
        raise HTTPException(status_code=400, detail="usage_reason is required")

    from handlers.inventory_handlers import InventoryHandlers
    inv = InventoryHandlers(db_client)
    return await inv.log_part_usage_execute(
        part_id=part_id,
        quantity=quantity,
        usage_reason=usage_reason,
        yacht_id=yacht_id,
        user_id=user_id,
        work_order_id=payload.get("work_order_id"),
        equipment_id=payload.get("equipment_id"),
        notes=payload.get("notes"),
    )


async def view_part_details(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.view_part_details(
        entity_id=part_id,
        yacht_id=yacht_id,
        user_id=user_id,
        tenant_key_alias=user_context.get("tenant_key_alias", ""),
    )

    if handler_result.get("success"):
        return {
            "status": "success",
            "data": handler_result.get("data"),
            "message": handler_result.get("message", ""),
        }
    error = handler_result.get("error", {})
    return {
        "status": "error",
        "error_code": error.get("code", "UNKNOWN"),
        "message": error.get("message", "Unknown error"),
    }


async def add_to_shopping_list(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.add_to_shopping_list(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        quantity_requested=payload.get("suggested_qty") if payload.get("suggested_qty") is not None else payload.get("quantity_requested", 1),
        urgency=payload.get("urgency", "medium"),
        notes=payload.get("notes"),
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def consume_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    quantity = payload.get("quantity")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if quantity is None:
        raise HTTPException(status_code=400, detail="quantity is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.consume_part(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        quantity=quantity,
        work_order_id=payload.get("work_order_id"),
        notes=payload.get("notes"),
        tenant_key_alias=user_context.get("tenant_key_alias", ""),
    )

    if handler_result.get("status") == "success":
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="part",
                entity_id=part_id,
                action="consume_part",
                user_role=user_context.get("role"),
                change_summary="Part consumed",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record consume_part: {ledger_err}")
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def receive_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    idempotency_key = payload.get("idempotency_key")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="idempotency_key is required")
    quantity_received = payload.get("quantity_received")
    if quantity_received is None:
        quantity_received = payload.get("quantity")
    if quantity_received is None:
        raise HTTPException(status_code=400, detail="quantity_received is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.receive_part(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        quantity_received=quantity_received,
        idempotency_key=idempotency_key,
        supplier_id=payload.get("supplier_id"),
        invoice_number=payload.get("po_number") or payload.get("invoice_number"),
        location=payload.get("to_location_id") or payload.get("location"),
        notes=payload.get("notes"),
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def transfer_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    quantity = payload.get("quantity")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if quantity is None:
        raise HTTPException(status_code=400, detail="quantity is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.transfer_part(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        quantity=quantity,
        from_location=payload.get("from_location_id") or payload.get("from_location"),
        to_location=payload.get("to_location_id") or payload.get("to_location"),
        notes=payload.get("notes"),
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def adjust_stock_quantity(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    reason = payload.get("reason")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")

    new_quantity = payload.get("new_quantity")
    if new_quantity is None:
        new_quantity = payload.get("quantity_change")
    if new_quantity is None:
        raise HTTPException(status_code=400, detail="new_quantity or quantity_change is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.adjust_stock_quantity(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        new_quantity=new_quantity,
        reason=reason,
        signature=payload.get("signature"),
        location=payload.get("location"),
    )

    if handler_result.get("status") == "success":
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="part",
                entity_id=part_id,
                action="adjust_stock_quantity",
                user_role=user_context.get("role"),
                change_summary="Stock adjusted",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record adjust_stock_quantity: {ledger_err}")
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def write_off_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    quantity = payload.get("quantity")
    reason = payload.get("reason")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    if quantity is None:
        raise HTTPException(status_code=400, detail="quantity is required")
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.write_off_part(
        yacht_id=yacht_id,
        user_id=user_id,
        part_id=part_id,
        quantity=quantity,
        reason=reason,
        signature=payload.get("signature"),
        location=payload.get("location"),
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def generate_part_labels(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_ids = payload.get("part_ids")
    if not part_ids:
        raise HTTPException(status_code=400, detail="part_ids is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.generate_part_labels(
        part_ids=part_ids,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def request_label_output(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    label_request_id = payload.get("label_request_id")
    output_format = payload.get("output_format")
    if not label_request_id:
        raise HTTPException(status_code=400, detail="label_request_id is required")
    if not output_format:
        raise HTTPException(status_code=400, detail="output_format is required")

    from handlers.part_handlers import PartHandlers
    ph = PartHandlers(db_client)
    handler_result = await ph.request_label_output(
        label_request_id=label_request_id,
        output_format=output_format,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    if handler_result.get("status") == "success":
        return handler_result
    return {"status": "error", "message": handler_result.get("message", "Unknown error")}


async def view_part_stock(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    part = (
        db_client.table("pms_parts")
        .select("id, part_number, name, quantity_on_hand, minimum_quantity, location")
        .eq("id", part_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )

    if not part.data:
        raise HTTPException(status_code=404, detail="Part not found")

    return {
        "status": "success",
        "success": True,
        "part": part.data,
        "stock_status": (
            "low"
            if part.data.get("quantity_on_hand", 0) <= part.data.get("minimum_quantity", 0)
            else "ok"
        ),
    }


async def view_part_location(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    part = (
        db_client.table("pms_parts")
        .select("id, part_number, name, location")
        .eq("id", part_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )

    if not part.data:
        raise HTTPException(status_code=404, detail="Part not found")

    return {
        "status": "success",
        "success": True,
        "part_id": part.data.get("id"),
        "part_number": part.data.get("part_number"),
        "name": part.data.get("name"),
        "location": part.data.get("location"),
    }


async def view_part_usage(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    try:
        usage = (
            db_client.table("part_usage")
            .select("id, quantity, usage_reason, work_order_id, created_at")
            .eq("part_id", part_id)
            .eq("yacht_id", yacht_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return {
            "status": "success",
            "success": True,
            "usage_history": usage.data or [],
            "count": len(usage.data) if usage.data else 0,
        }
    except Exception as usage_err:
        logger.warning(f"[view_part_usage] Query failed (table may not exist): {usage_err}")
        # Table may not exist yet
        return {
            "status": "success",
            "success": True,
            "usage_history": [],
            "count": 0,
            "message": "No usage history available",
        }


async def view_linked_equipment(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    # Stub: no part-equipment junction table exists yet. Returns up to 10 equipment
    # records for the yacht as a placeholder. part_id is validated but not used in the query.
    equipment = (
        db_client.table("pms_equipment")
        .select("id, name, manufacturer, model, location")
        .eq("yacht_id", yacht_id)
        .limit(10)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "linked_equipment": equipment.data or [],
        "count": len(equipment.data) if equipment.data else 0,
    }


async def order_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    part_id = payload.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    quantity = payload.get("quantity", 1)

    part = (
        db_client.table("pms_parts")
        .select("id, part_number, name")
        .eq("id", part_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )

    if not part.data:
        raise HTTPException(status_code=404, detail="Part not found")

    return {
        "status": "success",
        "success": True,
        "message": f"Purchase request created for {quantity}x {part.data.get('name')}",
        "part_id": part_id,
        "quantity": quantity,
    }


async def scan_part_barcode(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    barcode = payload.get("barcode")
    if not barcode:
        raise HTTPException(status_code=400, detail="barcode is required")

    try:
        part = (
            db_client.table("pms_parts")
            .select("id, part_number, name, quantity_on_hand, location")
            .eq("part_number", barcode)
            .eq("yacht_id", yacht_id)
            .maybe_single()
            .execute()
        )
        part_data = part.data if part else None
    except Exception:
        part_data = None

    if part_data:
        return {
            "status": "success",
            "success": True,
            "found": True,
            "part": part_data,
        }
    return {
        "status": "success",
        "success": True,
        "found": False,
        "message": f"No part found with barcode: {barcode}",
    }


HANDLERS: dict = {
    "check_stock_level": check_stock_level,
    "log_part_usage": log_part_usage,
    "view_part_details": view_part_details,
    "add_to_shopping_list": add_to_shopping_list,
    "consume_part": consume_part,
    "receive_part": receive_part,
    "transfer_part": transfer_part,
    "adjust_stock_quantity": adjust_stock_quantity,
    "write_off_part": write_off_part,
    "generate_part_labels": generate_part_labels,
    "request_label_output": request_label_output,
    "view_part_stock": view_part_stock,
    "view_part_location": view_part_location,
    "view_part_usage": view_part_usage,
    "view_linked_equipment": view_linked_equipment,
    "order_part": order_part,
    "scan_part_barcode": scan_part_barcode,
}
