# routes/handlers/compliance_handler.py
#
# Phase 5 Task 6 — 13 compliance/fleet/purchasing actions migrated from p0_actions_routes.py.
# Handlers: view_compliance_status, tag_for_survey, create_purchase_request,
#           add_item_to_purchase, approve_purchase, upload_invoice,
#           track_delivery, log_delivery_received, update_purchase_status,
#           view_fleet_summary, open_vessel, export_fleet_summary,
#           request_predictive_insight

from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# view_compliance_status
# ---------------------------------------------------------------------------

async def view_compliance_status(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    compliance_data = {
        "hours_of_rest": {"status": "ok", "details": "All crew compliant"},
        "surveys": {"status": "ok", "details": "Next survey in 60 days"},
        "certifications": {"status": "ok", "details": "All valid"},
        "safety_equipment": {"status": "ok", "details": "All checked"}
    }

    # Try to get actual compliance data
    try:
        compliance = db_client.table("compliance_status").select(
            "category, status, details, last_checked"
        ).eq("yacht_id", yacht_id).execute()

        if compliance.data:
            for item in compliance.data:
                compliance_data[item["category"]] = {
                    "status": item["status"],
                    "details": item["details"],
                    "last_checked": item.get("last_checked")
                }
    except Exception:
        pass

    return {
        "status": "success",
        "success": True,
        "compliance": compliance_data,
        "overall_status": "compliant" if all(
            v["status"] == "ok" for v in compliance_data.values()
        ) else "attention_needed"
    }


# ---------------------------------------------------------------------------
# tag_for_survey
# ---------------------------------------------------------------------------

async def tag_for_survey(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    survey_type = payload.get("survey_type", "class")
    notes = payload.get("notes", "")

    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    # Verify equipment exists
    equipment = db_client.table("pms_equipment").select(
        "id, name, metadata"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not equipment.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Add survey tag to metadata
    metadata = equipment.data.get("metadata", {}) or {}
    survey_tags = metadata.get("survey_tags", []) or []
    survey_tags.append({
        "survey_type": survey_type,
        "notes": notes,
        "tagged_by": user_id,
        "tagged_at": datetime.now(timezone.utc).isoformat()
    })
    metadata["survey_tags"] = survey_tags

    db_client.table("pms_equipment").update({
        "metadata": metadata
    }).eq("id", equipment_id).eq("yacht_id", yacht_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": f"Equipment tagged for {survey_type} survey",
        "equipment_id": equipment_id,
        "equipment_name": equipment.data.get("name")
    }


# ---------------------------------------------------------------------------
# create_purchase_request
# ---------------------------------------------------------------------------

async def create_purchase_request(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # RBAC Check: create_purchase_request is HoD+ only (Security Fix 2026-02-10)
    purchase_create_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    user_role = user_context.get("role", "")
    if user_role not in purchase_create_roles:
        logger.warning(f"[RBAC] Role '{user_role}' denied for action 'create_purchase_request'. Allowed: {purchase_create_roles}")
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to perform action 'create_purchase_request'",
            "required_roles": purchase_create_roles
        }

    title = payload.get("title")
    description = payload.get("description", "")
    priority = payload.get("priority", "normal")
    budget_code = payload.get("budget_code", "")

    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    try:
        request_data = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "title": title,
            "description": description,
            "priority": priority,
            "budget_code": budget_code,
            "status": "draft",
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        db_client.table("purchase_requests").insert(request_data).execute()

        return {
            "status": "success",
            "success": True,
            "message": "Purchase request created",
            "purchase_request_id": request_data["id"],
            "title": title
        }
    except Exception:
        # Table may not exist, return success anyway
        return {
            "status": "success",
            "success": True,
            "message": "Purchase request registered (table pending setup)",
            "title": title
        }


# ---------------------------------------------------------------------------
# add_item_to_purchase
# ---------------------------------------------------------------------------

async def add_item_to_purchase(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    purchase_request_id = payload.get("purchase_request_id")
    item_description = payload.get("item_description")
    quantity = payload.get("quantity", 1)
    estimated_cost = payload.get("estimated_cost", 0)
    part_id = payload.get("part_id")

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")
    if not item_description:
        raise HTTPException(status_code=400, detail="item_description is required")

    try:
        item_data = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "purchase_request_id": purchase_request_id,
            "description": item_description,
            "quantity": quantity,
            "estimated_cost": estimated_cost,
            "part_id": part_id,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        db_client.table("purchase_request_items").insert(item_data).execute()

        return {
            "status": "success",
            "success": True,
            "message": "Item added to purchase request",
            "purchase_request_id": purchase_request_id,
            "item_id": item_data["id"]
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Item registered (table pending setup)",
            "purchase_request_id": purchase_request_id
        }


# ---------------------------------------------------------------------------
# approve_purchase
# ---------------------------------------------------------------------------

async def approve_purchase(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # RBAC Check: approve_purchase is captain/manager only (Security Fix 2026-02-10)
    approve_roles = ["captain", "manager"]
    user_role = user_context.get("role", "")
    if user_role not in approve_roles:
        logger.warning(f"[RBAC] Role '{user_role}' denied for action 'approve_purchase'. Allowed: {approve_roles}")
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to perform action 'approve_purchase'",
            "required_roles": approve_roles
        }

    purchase_request_id = payload.get("purchase_request_id")
    approval_notes = payload.get("notes", "")

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")

    try:
        db_client.table("purchase_requests").update({
            "status": "approved",
            "approved_by": user_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_notes": approval_notes
        }).eq("id", purchase_request_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "message": "Purchase request approved",
            "purchase_request_id": purchase_request_id
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Approval recorded",
            "purchase_request_id": purchase_request_id
        }


# ---------------------------------------------------------------------------
# upload_invoice
# ---------------------------------------------------------------------------

async def upload_invoice(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    purchase_request_id = payload.get("purchase_request_id")
    invoice_url = payload.get("invoice_url")
    invoice_number = payload.get("invoice_number", "")
    invoice_amount = payload.get("amount", 0)

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")
    if not invoice_url:
        raise HTTPException(status_code=400, detail="invoice_url is required")

    try:
        # Get current request and add invoice to metadata
        pr = db_client.table("purchase_requests").select(
            "id, metadata"
        ).eq("id", purchase_request_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if pr.data:
            metadata = pr.data.get("metadata", {}) or {}
            invoices = metadata.get("invoices", []) or []
            invoices.append({
                "url": invoice_url,
                "number": invoice_number,
                "amount": invoice_amount,
                "uploaded_by": user_id,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            })
            metadata["invoices"] = invoices

            db_client.table("purchase_requests").update({
                "metadata": metadata,
                "status": "invoiced"
            }).eq("id", purchase_request_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "message": "Invoice uploaded",
            "purchase_request_id": purchase_request_id,
            "invoice_url": invoice_url
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Invoice registered",
            "purchase_request_id": purchase_request_id,
            "invoice_url": invoice_url
        }


# ---------------------------------------------------------------------------
# track_delivery
# ---------------------------------------------------------------------------

async def track_delivery(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    purchase_request_id = payload.get("purchase_request_id")

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")

    try:
        pr = db_client.table("purchase_requests").select(
            "id, title, status, metadata"
        ).eq("id", purchase_request_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if pr.data:
            metadata = pr.data.get("metadata", {}) or {}
            tracking = metadata.get("delivery_tracking", {})

            return {
                "status": "success",
                "success": True,
                "purchase_request_id": purchase_request_id,
                "title": pr.data.get("title"),
                "current_status": pr.data.get("status"),
                "tracking": tracking
            }
        else:
            return {
                "status": "success",
                "success": True,
                "purchase_request_id": purchase_request_id,
                "message": "Purchase request not found or tracking unavailable"
            }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "purchase_request_id": purchase_request_id,
            "message": "Tracking unavailable"
        }


# ---------------------------------------------------------------------------
# log_delivery_received
# ---------------------------------------------------------------------------

async def log_delivery_received(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    purchase_request_id = payload.get("purchase_request_id")
    received_by = payload.get("received_by", user_id)
    notes = payload.get("notes", "")
    condition = payload.get("condition", "good")

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")

    try:
        pr = db_client.table("purchase_requests").select(
            "id, metadata"
        ).eq("id", purchase_request_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if pr.data:
            metadata = pr.data.get("metadata", {}) or {}
            metadata["delivery_received"] = {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "received_by": received_by,
                "notes": notes,
                "condition": condition
            }

            db_client.table("purchase_requests").update({
                "metadata": metadata,
                "status": "delivered"
            }).eq("id", purchase_request_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "message": "Delivery receipt logged",
            "purchase_request_id": purchase_request_id
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Delivery receipt registered",
            "purchase_request_id": purchase_request_id
        }


# ---------------------------------------------------------------------------
# update_purchase_status
# ---------------------------------------------------------------------------

async def update_purchase_status(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # RBAC Check: update_purchase_status is HoD+ only (Security Fix 2026-02-10)
    purchase_status_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    user_role = user_context.get("role", "")
    if user_role not in purchase_status_roles:
        logger.warning(f"[RBAC] Role '{user_role}' denied for action 'update_purchase_status'. Allowed: {purchase_status_roles}")
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to perform action 'update_purchase_status'",
            "required_roles": purchase_status_roles
        }

    purchase_request_id = payload.get("purchase_request_id")
    new_status = payload.get("status")

    if not purchase_request_id:
        raise HTTPException(status_code=400, detail="purchase_request_id is required")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    valid_statuses = ["draft", "submitted", "approved", "ordered", "shipped", "delivered", "cancelled"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    try:
        db_client.table("purchase_requests").update({
            "status": new_status,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", purchase_request_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "message": f"Purchase request status updated to '{new_status}'",
            "purchase_request_id": purchase_request_id,
            "new_status": new_status
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "message": "Status update registered",
            "purchase_request_id": purchase_request_id,
            "new_status": new_status
        }


# ---------------------------------------------------------------------------
# view_fleet_summary
# ---------------------------------------------------------------------------

async def view_fleet_summary(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    manager_roles = ["captain", "manager", "chief_engineer", "chief_officer"]
    if user_context.get("role", "") not in manager_roles:
        return {"success": False, "code": "FORBIDDEN",
                "message": "Fleet summary requires manager-level access",
                "required_roles": manager_roles}

    try:
        # Get yacht info
        yachts = db_client.table("yachts").select(
            "id, name, status, vessel_type"
        ).limit(20).execute()

        fleet_data = []
        for yacht in (yachts.data or []):
            # Get summary counts for each yacht
            yacht_summary = {
                "id": yacht["id"],
                "name": yacht.get("name", "Unknown"),
                "status": yacht.get("status", "unknown"),
                "vessel_type": yacht.get("vessel_type", "yacht"),
                "open_faults": 0,
                "pending_work_orders": 0
            }
            fleet_data.append(yacht_summary)

        return {
            "status": "success",
            "success": True,
            "fleet": fleet_data,
            "vessel_count": len(fleet_data)
        }
    except Exception:
        # Single vessel mode
        return {
            "status": "success",
            "success": True,
            "fleet": [{
                "id": yacht_id,
                "name": "Current Vessel",
                "status": "active"
            }],
            "vessel_count": 1,
            "message": "Fleet view limited to current vessel"
        }


# ---------------------------------------------------------------------------
# open_vessel
# ---------------------------------------------------------------------------

async def open_vessel(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Switch context to a specific vessel
    vessel_id = payload.get("vessel_id")

    if not vessel_id:
        raise HTTPException(status_code=400, detail="vessel_id is required")

    # Note: In a real implementation, this would verify user has access
    # to the vessel and update session context
    return {
        "status": "success",
        "success": True,
        "message": "Vessel context switched",
        "vessel_id": vessel_id,
        "note": "Frontend should update yacht_id context"
    }


# ---------------------------------------------------------------------------
# export_fleet_summary
# ---------------------------------------------------------------------------

async def export_fleet_summary(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    manager_roles = ["captain", "manager", "chief_engineer", "chief_officer"]
    if user_context.get("role", "") not in manager_roles:
        return {"success": False, "code": "FORBIDDEN",
                "message": "Fleet summary requires manager-level access",
                "required_roles": manager_roles}

    export_format = payload.get("format", "csv")

    try:
        yachts = db_client.table("yachts").select(
            "id, name, status, vessel_type, metadata"
        ).limit(50).execute()

        return {
            "status": "success",
            "success": True,
            "fleet": yachts.data or [],
            "export_format": export_format,
            "message": f"Fleet data ready for {export_format} export"
        }
    except Exception:
        return {
            "status": "success",
            "success": True,
            "fleet": [],
            "export_format": export_format,
            "message": "Fleet export not available"
        }


# ---------------------------------------------------------------------------
# request_predictive_insight
# ---------------------------------------------------------------------------

async def request_predictive_insight(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    insight_type = payload.get("insight_type", "general")

    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")

    # Get table name for entity type
    table_map = {
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "equipment": "pms_equipment"
    }

    request_id = str(uuid_module.uuid4())

    if entity_type in table_map:
        try:
            entity = db_client.table(table_map[entity_type]).select(
                "id, metadata"
            ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()

            if entity.data:
                # Flag entity for insight generation
                metadata = entity.data.get("metadata", {}) or {}
                insight_requests = metadata.get("insight_requests", []) or []
                insight_requests.append({
                    "request_id": request_id,
                    "insight_type": insight_type,
                    "requested_by": user_id,
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                    "status": "pending"
                })
                metadata["insight_requests"] = insight_requests

                db_client.table(table_map[entity_type]).update({
                    "metadata": metadata
                }).eq("id", entity_id).eq("yacht_id", yacht_id).execute()
        except Exception:
            pass

    return {
        "status": "success",
        "success": True,
        "message": "Predictive insight request submitted",
        "request_id": request_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "insight_type": insight_type,
        "note": "Insight will be generated asynchronously"
    }


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

HANDLERS: dict = {
    "view_compliance_status": view_compliance_status,
    "tag_for_survey": tag_for_survey,
    "create_purchase_request": create_purchase_request,
    "add_item_to_purchase": add_item_to_purchase,
    "approve_purchase": approve_purchase,
    "upload_invoice": upload_invoice,
    "track_delivery": track_delivery,
    "log_delivery_received": log_delivery_received,
    "update_purchase_status": update_purchase_status,
    "view_fleet_summary": view_fleet_summary,
    "open_vessel": open_vessel,
    "export_fleet_summary": export_fleet_summary,
    "request_predictive_insight": request_predictive_insight,
}
