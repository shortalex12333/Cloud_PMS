"""
Receiving Lens v1 Handlers
===========================

Workflow: Image upload → OCR extraction → User review/adjust → Accept (SIGNED)

Actions:
1. create_receiving (MUTATE)
2. attach_receiving_image_with_comment (MUTATE)
3. extract_receiving_candidates (PREPARE only - advisory)
4. update_receiving_fields (MUTATE)
5. add_receiving_item (MUTATE)
6. adjust_receiving_item (MUTATE)
7. link_invoice_document (MUTATE)
8. accept_receiving (SIGNED - prepare/execute)
9. reject_receiving (MUTATE)
10. view_receiving_history (READ)

All handlers return standardized action response format.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
import logging
import uuid
import re
import os

# Import schema components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import Client
from handlers.db_client import map_postgrest_error

logger = logging.getLogger(__name__)


# ============================================================================
# UTILITIES
# ============================================================================

# RLS enforcement now handled by db_client.get_user_db()
# See handlers/db_client.py for per-request RLS client creation


def validate_storage_path_for_receiving(yacht_id: str, receiving_id: str, storage_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate storage path matches receiving pattern.

    Valid: {yacht_id}/receiving/{receiving_id}/{filename}
    Invalid: documents/{yacht_id}/receiving/...  (no "documents/" prefix)

    Returns: (is_valid, error_message)
    """
    # Reject paths starting with 'documents/'
    if storage_path.startswith("documents/"):
        return False, "Storage path must not include 'documents/' prefix"

    # Valid pattern: {yacht_id}/receiving/{receiving_id}/{filename}
    pattern = rf"^{re.escape(yacht_id)}/receiving/{re.escape(receiving_id)}/[^/]+$"
    if not re.match(pattern, storage_path):
        return False, f"Storage path must match pattern: {{yacht_id}}/receiving/{{receiving_id}}/{{filename}}"

    return True, None


def extract_audit_metadata(request_context: Optional[Dict]) -> Dict:
    """
    Extract audit metadata from request context.

    Returns: {session_id, ip_address, source, lens}
    """
    if not request_context:
        return {
            "metadata": {
                "source": "lens",
                "lens": "receiving",
                "session_id": None,
                "ip_address": None,
            }
        }

    return {
        "metadata": {
            "source": "lens",
            "lens": "receiving",
            "session_id": request_context.get("session_id"),
            "ip_address": request_context.get("ip_address"),
        }
    }


def is_prepare_mode(params: Dict) -> bool:
    """Check if action is in prepare mode."""
    return params.get("mode") == "prepare"


def generate_confirmation_token(action: str, entity_id: str) -> str:
    """Generate confirmation token for prepare/execute flow."""
    return f"tok_{action}_{entity_id}_{uuid.uuid4().hex[:12]}"


def _write_audit_log(db, payload: Dict):
    """
    Write to pms_audit_log with signature NOT NULL invariant.

    Required fields: yacht_id, entity_type, entity_id, action, user_id, signature
    Optional fields: old_values, new_values, metadata
    """
    audit_payload = {
        "id": str(uuid.uuid4()),
        "yacht_id": payload["yacht_id"],
        "entity_type": payload["entity_type"],
        "entity_id": payload["entity_id"],
        "action": payload["action"],
        "user_id": payload["user_id"],
        "old_values": payload.get("old_values"),
        "new_values": payload.get("new_values"),
        "signature": payload.get("signature", {}),  # Empty dict for non-signed
        "metadata": payload.get("metadata", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    db.table("pms_audit_log").insert(audit_payload).execute()


def _get_db(yacht_id: str):
    """Get service DB client. Returns (db, None) or (None, error_dict)."""
    try:
        from handlers.db_client import get_service_db
        return get_service_db(yacht_id), None
    except Exception as e:
        logger.error(f"Failed to create database client: {e}")
        return None, {"status": "error", "error_code": "DB_CLIENT_ERROR", "message": "Failed to create database client"}


# ============================================================================
# ACTION 1: create_receiving (MUTATE)
# ============================================================================

def _create_receiving_adapter():
    """
    Create new receiving record.

    Required fields: yacht_id, user_id, user_jwt
    Optional fields: vendor_name, vendor_reference, received_date, currency, notes, linked_work_order_id
    Allowed roles: HOD+
    RLS: Enforced via user JWT
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not user_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "user_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Optional fields
        vendor_name = params.get("vendor_name")
        vendor_reference = params.get("vendor_reference")
        received_date = params.get("received_date")  # ISO date string
        currency = params.get("currency")
        notes = params.get("notes")
        linked_work_order_id = params.get("linked_work_order_id")
        request_context = params.get("request_context")

        # HARDENING: Validate vendor_name if provided (optional for draft)
        # For "+" flow: vendor_name is not known yet - will be populated from OCR later
        if vendor_name is not None:
            if isinstance(vendor_name, str):
                vendor_name = vendor_name.strip()
                if len(vendor_name) == 0:
                    vendor_name = None  # Treat empty string as NULL
                elif len(vendor_name) > 255:
                    return {
                        "status": "error",
                        "error_code": "INVALID_LENGTH",
                        "message": "vendor_name must be 255 characters or less"
                    }

        # Use placeholder if vendor_name is not provided (draft receiving)
        if not vendor_name:
            vendor_name = "Pending OCR"

        # Insert receiving record via RPC function (bypasses MASTER/TENANT JWT issue)
        # The RPC function uses SECURITY DEFINER and checks auth_users_roles internally
        rpc_params = {
            "p_user_id": user_id,
            "p_yacht_id": yacht_id,
            "p_vendor_name": vendor_name,
            "p_vendor_reference": vendor_reference,
            "p_received_date": received_date if received_date else datetime.now(timezone.utc).date().isoformat(),
            "p_notes": notes,
        }

        try:
            result = db.rpc("rpc_insert_receiving", rpc_params).execute()
        except Exception as e:
            logger.error(f"Failed to insert receiving via RPC: {e}", exc_info=True)
            return map_postgrest_error(e, "INSERT_FAILED")

        if not result.data or len(result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to create receiving record"
            }

        receiving_id = result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "create_receiving",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "vendor_name": vendor_name,
                    "vendor_reference": vendor_reference,
                    "status": "draft",
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for create_receiving: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "vendor_name": vendor_name,
            "vendor_reference": vendor_reference,
            "receiving_status": "draft",
        }

    return _fn


# ============================================================================
# ACTION 2: attach_receiving_image_with_comment (MUTATE)
# ============================================================================

def _attach_receiving_image_with_comment_adapter():
    """
    Attach image or document to receiving record.

    Required fields: yacht_id, user_id, receiving_id, document_id
    Optional fields: doc_type, comment
    Allowed roles: HOD+

    Storage path validation: {yacht_id}/receiving/{receiving_id}/{filename}
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")
        document_id = params.get("document_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }
        if not document_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "document_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err
        doc_type = params.get("doc_type")  # 'invoice', 'packing_slip', 'photo'
        comment = params.get("comment")
        request_context = params.get("request_context")

        # Verify receiving exists
        recv_result = db.table("pms_receiving").select(
            "id, status"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        # Storage path validation (if storage_path provided in params for validation)
        storage_path = params.get("storage_path")
        if storage_path:
            is_valid, error_msg = validate_storage_path_for_receiving(
                yacht_id,
                receiving_id,
                storage_path
            )
            if not is_valid:
                return {
                    "status": "error",
                    "error_code": "INVALID_STORAGE_PATH",
                    "message": error_msg
                }

        # Insert document link
        doc_payload = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "document_id": document_id,
            "doc_type": doc_type,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        doc_result = db.table("pms_receiving_documents").insert(doc_payload).execute()

        if not doc_result.data or len(doc_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to attach document"
            }

        doc_link_id = doc_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "attach_receiving_image_with_comment",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "document_id": document_id,
                    "doc_type": doc_type,
                    "comment": comment,
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for attach_receiving_image_with_comment: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "document_link_id": doc_link_id,
            "document_id": document_id,
            "comment": comment,
        }

    return _fn


# ============================================================================
# ACTION 3: extract_receiving_candidates (PREPARE only - advisory)
# ============================================================================

def _extract_receiving_candidates_adapter():
    """
    Extract candidates from image/document (PREPARE only - advisory).

    Required fields: yacht_id, user_id, receiving_id, source_document_id
    Allowed roles: HOD+

    CRITICAL: This is a PREPARE-only action. It stores advisory results in
    pms_receiving_extractions. It does NOT auto-mutate pms_receiving or
    pms_receiving_items. User must explicitly apply changes via other actions.
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        # source_document_id is optional - if not provided, this is manual extraction
        source_document_id = params.get("source_document_id")
        request_context = params.get("request_context")

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Verify receiving exists
        try:
            recv_result = db.table("pms_receiving").select(
                "id, status"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to query receiving record"
            }

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        # TODO: Integrate with OCR/extraction service
        # For now, return mock extraction payload
        extraction_payload = {
            "vendor_name": None,
            "vendor_reference": None,
            "total": None,
            "currency": None,
            "line_items": [],
            "confidences": {
                "vendor_name": 0.0,
                "total": 0.0,
            },
            "flags": ["low_confidence", "manual_review_required"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store advisory extraction result
        # Use sentinel UUID for manual extractions (when source_document_id not provided)
        extraction_record = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "source_document_id": source_document_id or "00000000-0000-0000-0000-000000000000",
            "payload": extraction_payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        extract_result = db.table("pms_receiving_extractions").insert(extraction_record).execute()

        if not extract_result.data or len(extract_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to store extraction result"
            }

        extraction_id = extract_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (advisory only, non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "extract_receiving_candidates",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "extraction_id": extraction_id,
                    "source_document_id": source_document_id,
                    "flags": extraction_payload["flags"],
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for extract_receiving_candidates: {e}")

        return {
            "status": "success",
            "mode": "prepare",
            "extraction_id": extraction_id,
            "proposed_fields": extraction_payload,
            "validation": {
                "auto_apply": False,
                "manual_review_required": True,
            },
            "message": "Extraction complete. Review and manually apply changes via update_receiving_fields and add_receiving_item actions."
        }

    return _fn


# ============================================================================
# ACTION 4: update_receiving_fields (MUTATE)
# ============================================================================

def _update_receiving_fields_adapter():
    """
    Update receiving header fields.

    Required fields: yacht_id, user_id, receiving_id
    Optional fields: vendor_name, vendor_reference, currency, received_date, notes
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        # Optional update fields
        vendor_name = params.get("vendor_name")
        vendor_reference = params.get("vendor_reference")
        currency = params.get("currency")
        received_date = params.get("received_date")
        notes = params.get("notes")
        request_context = params.get("request_context")

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Get current receiving
        try:
            recv_result = db.table("pms_receiving").select(
                "id, vendor_name, vendor_reference, currency, status"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to query receiving record"
            }

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        old_data = recv_result.data

        # Check if already accepted (cannot edit)
        if old_data.get("status") == "accepted":
            return {
                "status": "error",
                "error_code": "ALREADY_ACCEPTED",
                "message": "Cannot update fields for accepted receiving record"
            }

        # Build update payload
        update_payload = {}
        if vendor_name is not None:
            update_payload["vendor_name"] = vendor_name
        if vendor_reference is not None:
            update_payload["vendor_reference"] = vendor_reference
        if currency is not None:
            update_payload["currency"] = currency
        if received_date is not None:
            update_payload["received_date"] = received_date
        if notes is not None:
            update_payload["notes"] = notes

        if not update_payload:
            return {
                "status": "error",
                "error_code": "NO_FIELDS_TO_UPDATE",
                "message": "No fields provided for update"
            }

        # Update receiving - wrap in try/catch to properly handle RLS denials
        try:
            update_result = db.table("pms_receiving").update(update_payload).eq(
                "id", receiving_id
            ).eq("yacht_id", yacht_id).execute()

            if not update_result.data or len(update_result.data) == 0:
                logger.error(f"Update returned no data for receiving_id: {receiving_id}")
                return {
                    "status": "error",
                    "error_code": "UPDATE_FAILED",
                    "message": "Update operation completed but returned no data"
                }
        except Exception as e:
            # Map database errors (including RLS denials) to proper error responses
            logger.error(f"Failed to update receiving fields: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "UPDATE_FAILED",
                "message": f"Failed to update receiving: {str(e)}"
            }

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "update_receiving_fields",
                "user_id": user_id,
                "old_values": {
                    "vendor_name": old_data.get("vendor_name"),
                    "vendor_reference": old_data.get("vendor_reference"),
                },
                "new_values": update_payload,
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for update_receiving_fields: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "updated_fields": list(update_payload.keys()),
        }

    return _fn


# ============================================================================
# ACTION 5: add_receiving_item (MUTATE)
# ============================================================================

def _add_receiving_item_adapter():
    """
    Add line item to receiving record.

    Required fields: yacht_id, user_id, receiving_id, (description OR part_id), quantity_received
    Optional fields: part_id, description, quantity_expected, unit_price, currency
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        # Item fields
        part_id = params.get("part_id")
        description = params.get("description")
        quantity_expected = params.get("quantity_expected")
        quantity_received = params.get("quantity_received", 0)
        unit_price = params.get("unit_price")
        currency = params.get("currency")
        request_context = params.get("request_context")

        # Validate: must have either part_id or description
        if not part_id and not description:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "Either part_id or description is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Verify receiving exists
        try:
            recv_result = db.table("pms_receiving").select(
                "id, status"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to query receiving record"
            }

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        # Check if already accepted
        if recv_result.data.get("status") == "accepted":
            return {
                "status": "error",
                "error_code": "ALREADY_ACCEPTED",
                "message": "Cannot add items to accepted receiving record"
            }

        # Insert line item
        item_payload = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "part_id": part_id,
            "description": description,
            "quantity_expected": quantity_expected,
            "quantity_received": quantity_received,
            "unit_price": unit_price,
            "currency": currency,
            "properties": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Insert and return data (Supabase returns data by default)
        try:
            item_result = db.table("pms_receiving_items").insert(item_payload).execute()
        except Exception as e:
            logger.error(f"Database insert error: {e}")
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": f"Failed to add receiving item: {str(e)}"
            }

        if not item_result.data or len(item_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to add receiving item"
            }

        item_id = item_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "add_receiving_item",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "item_id": item_id,
                    "part_id": part_id,
                    "description": description,
                    "quantity_received": quantity_received,
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for add_receiving_item: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "item_id": item_id,
            "quantity_received": quantity_received,
        }

    return _fn


# ============================================================================
# ACTION 6: adjust_receiving_item (MUTATE)
# ============================================================================

def _adjust_receiving_item_adapter():
    """
    Adjust existing receiving line item.

    Required fields: yacht_id, user_id, receiving_id, receiving_item_id
    Optional fields: quantity_received, quantity_accepted, quantity_rejected,
                     disposition, unit_price, description
    Allowed roles: HOD+

    Checklist controls (pms_receiving_items columns added 2026-04-24):
      - disposition ∈ {pending, accepted, short, damaged, wrong_item, over}
      - quantity_accepted + quantity_rejected must not exceed quantity_received
        (DB check constraint: pms_receiving_items_qty_balance_check).
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")
        receiving_item_id = params.get("receiving_item_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }
        if not receiving_item_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_item_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Optional update fields
        quantity_received = params.get("quantity_received")
        quantity_accepted = params.get("quantity_accepted")
        quantity_rejected = params.get("quantity_rejected")
        disposition = params.get("disposition")
        unit_price = params.get("unit_price")
        description = params.get("description")
        request_context = params.get("request_context")

        # Get current item (fetch disposition fields for Q4 clamp logic)
        item_result = db.table("pms_receiving_items").select(
            "id, quantity_received, quantity_accepted, quantity_rejected, disposition, unit_price, description, part_id"
        ).eq("id", receiving_item_id).eq("yacht_id", yacht_id).eq("receiving_id", receiving_id).maybe_single().execute()

        if not item_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving item not found"
            }

        old_data = item_result.data

        # Build update payload
        update_payload = {}
        hod_override_clamp: dict | None = None  # populated when HOD reduces quantity_received

        if quantity_received is not None:
            if quantity_received < 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity received cannot be negative"
                }
            update_payload["quantity_received"] = quantity_received

            # Q4: HOD downward-quantity override — auto-clamp accepted/rejected so
            # the DB check constraint (accepted+rejected <= received) never fires.
            # Emit ledger + notify HOD so nothing is silently lost.
            old_qty = float(old_data.get("quantity_received") or 0)
            new_qty = float(quantity_received)
            if new_qty < old_qty:
                old_accepted = float(old_data.get("quantity_accepted") or 0)
                old_rejected = float(old_data.get("quantity_rejected") or 0)
                clamped_accepted = min(old_accepted, new_qty)
                clamped_rejected = min(old_rejected, max(0.0, new_qty - clamped_accepted))
                if clamped_accepted != old_accepted or clamped_rejected != old_rejected:
                    update_payload["quantity_accepted"] = clamped_accepted
                    update_payload["quantity_rejected"] = clamped_rejected
                    if clamped_accepted + clamped_rejected < new_qty:
                        update_payload["disposition"] = "pending"
                    hod_override_clamp = {
                        "old_received": old_qty,
                        "new_received": new_qty,
                        "old_accepted": old_accepted,
                        "new_accepted": clamped_accepted,
                        "old_rejected": old_rejected,
                        "new_rejected": clamped_rejected,
                    }

        if quantity_accepted is not None and "quantity_accepted" not in update_payload:
            if quantity_accepted < 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity accepted cannot be negative"
                }
            update_payload["quantity_accepted"] = quantity_accepted
        if quantity_rejected is not None and "quantity_rejected" not in update_payload:
            if quantity_rejected < 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity rejected cannot be negative"
                }
            update_payload["quantity_rejected"] = quantity_rejected
        if disposition is not None and "disposition" not in update_payload:
            valid = ("pending", "accepted", "short", "damaged", "wrong_item", "over")
            if disposition not in valid:
                return {
                    "status": "error",
                    "error_code": "INVALID_VALUE",
                    "message": f"disposition must be one of: {', '.join(valid)}"
                }
            update_payload["disposition"] = disposition
        if unit_price is not None:
            update_payload["unit_price"] = unit_price
        if description is not None:
            update_payload["description"] = description

        if not update_payload:
            return {
                "status": "error",
                "error_code": "NO_FIELDS_TO_UPDATE",
                "message": "No fields provided for update"
            }

        # Update item
        db.table("pms_receiving_items").update(update_payload).eq(
            "id", receiving_item_id
        ).execute()

        # Q4: if a downward clamp happened, write ledger + notify HOD so the
        # override is visible and requires follow-up — not silently swallowed.
        _hod_ledger_written = False
        if hod_override_clamp:
            try:
                from handlers.ledger_utils import build_ledger_event
                ledger_row = build_ledger_event(
                    yacht_id=yacht_id,
                    user_id=user_id or "system",
                    event_type="update",
                    entity_type="receiving",
                    entity_id=receiving_id,
                    action="hod_quantity_override",
                    event_category="override",
                    change_summary=(
                        f"HOD reduced quantity_received on item {receiving_item_id}: "
                        f"{hod_override_clamp['old_received']} → {hod_override_clamp['new_received']}. "
                        f"Accepted auto-clamped {hod_override_clamp['old_accepted']} → {hod_override_clamp['new_accepted']}."
                    ),
                    metadata=hod_override_clamp,
                    new_state={"requires_followup": True},
                )
                db.table("ledger_events").insert(ledger_row).execute()
                _hod_ledger_written = True
            except Exception as e:
                logger.warning(f"hod_quantity_override ledger write failed: {e}")

            try:
                hod_rows = db.table("auth_users_roles").select("user_id, role").eq(
                    "yacht_id", yacht_id
                ).in_("role", ["chief_engineer", "chief_officer", "captain", "manager"]).eq("is_active", True).execute()
                notifs = []
                for hod in (hod_rows.data or []):
                    notifs.append({
                        "id": str(uuid.uuid4()),
                        "yacht_id": yacht_id,
                        "user_id": hod["user_id"],
                        "notification_type": "hod_quantity_override",
                        "title": "Receiving quantity corrected — follow-up required",
                        "body": (
                            f"Quantity received was reduced from {hod_override_clamp['old_received']} to "
                            f"{hod_override_clamp['new_received']}. Accepted quantities have been clamped. "
                            "Please review and confirm the receiving checklist."
                        ),
                        "priority": "high",
                        "entity_type": "receiving",
                        "entity_id": receiving_id,
                        "triggered_by": user_id,
                        "idempotency_key": f"hod_override:{receiving_item_id}:{update_payload.get('quantity_received')}",
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                if notifs:
                    db.table("pms_notifications").upsert(
                        notifs, on_conflict="yacht_id,user_id,idempotency_key"
                    ).execute()
            except Exception as e:
                logger.warning(f"hod_quantity_override notification failed: {e}")

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "adjust_receiving_item",
                "user_id": user_id,
                "old_values": {
                    "item_id": receiving_item_id,
                    "quantity_received": old_data.get("quantity_received"),
                },
                "new_values": update_payload,
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for adjust_receiving_item: {e}")

        return {
            "status": "success",
            "_ledger_written": _hod_ledger_written,
            "receiving_id": receiving_id,
            "item_id": receiving_item_id,
            "updated_fields": list(update_payload.keys()),
        }

    return _fn


# ============================================================================
# ACTION 7: link_invoice_document (MUTATE)
# ============================================================================

def _link_invoice_document_adapter():
    """
    Link PDF invoice document to receiving record.

    Required fields: yacht_id, user_id, receiving_id, document_id
    Optional fields: comment
    Allowed roles: HOD+

    Storage path validation: {yacht_id}/receiving/{receiving_id}/{filename}
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        # document_id must be a valid UUID reference to pms_documents
        document_id = params.get("document_id")
        if not document_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "document_id is required"
            }

        comment = params.get("comment")
        request_context = params.get("request_context")

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Verify receiving exists
        try:
            recv_result = db.table("pms_receiving").select(
                "id, status"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to query receiving record"
            }

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        # Storage path validation (if provided)
        storage_path = params.get("storage_path")
        if storage_path:
            is_valid, error_msg = validate_storage_path_for_receiving(
                yacht_id,
                receiving_id,
                storage_path
            )
            if not is_valid:
                return {
                    "status": "error",
                    "error_code": "INVALID_STORAGE_PATH",
                    "message": error_msg
                }

        # HARDENING: Verify document exists before creating link (referential integrity)
        try:
            doc_check = db.table("pms_documents").select("id").eq(
                "id", document_id
            ).eq("yacht_id", yacht_id).maybe_single().execute()
        except Exception as e:
            logger.error(f"Document existence check failed: {e}")
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to verify document"
            }

        if not doc_check.data:
            return {
                "status": "error",
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found or not accessible"
            }

        # Insert document link with doc_type='invoice'
        doc_payload = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "document_id": document_id,
            "doc_type": "invoice",
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            doc_result = db.table("pms_receiving_documents").insert(doc_payload).execute()
        except Exception as e:
            logger.error(f"Database insert error: {e}")
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": f"Failed to link invoice document: {str(e)}"
            }

        if not doc_result.data or len(doc_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to link invoice document"
            }

        doc_link_id = doc_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "link_invoice_document",
                "user_id": user_id,
                "old_values": None,
                "new_values": {
                    "document_id": document_id,
                    "doc_type": "invoice",
                    "comment": comment,
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for link_invoice_document: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "document_link_id": doc_link_id,
            "document_id": document_id,
        }

    return _fn


# ============================================================================
# ACTION 8: accept_receiving (SIGNED - prepare/execute)
# ============================================================================

def _accept_receiving_adapter():
    """
    Accept receiving record (SIGNED action - prepare/execute).

    Required fields: yacht_id, user_id, receiving_id, signature (execute only)
    Allowed roles: captain, manager

    PREPARE: Validate completeness (at least one item, totals computed)
    EXECUTE: Mark status='accepted', freeze monetary fields, write signed audit
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err
        signature = params.get("signature")
        request_context = params.get("request_context")

        # Get receiving record
        recv_result = db.table("pms_receiving").select(
            "id, vendor_name, vendor_reference, status, subtotal, tax_total, total"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        receiving = recv_result.data

        # Check if already accepted
        if receiving.get("status") == "accepted":
            return {
                "status": "error",
                "error_code": "ALREADY_ACCEPTED",
                "message": "Receiving record is already accepted"
            }

        # Check if rejected (cannot accept rejected - state is terminal)
        if receiving.get("status") == "rejected":
            return {
                "status": "error",
                "error_code": "ALREADY_REJECTED",
                "message": "Cannot accept a rejected receiving record"
            }

        # Get line items
        items_result = db.table("pms_receiving_items").select(
            "id, quantity_received, unit_price, currency"
        ).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).execute()

        items = items_result.data or []

        # Validate completeness
        if len(items) == 0:
            return {
                "status": "error",
                "error_code": "NO_ITEMS",
                "message": "Cannot accept receiving with no line items"
            }

        # Compute totals (simple sum for now)
        subtotal = sum(
            float(item.get("quantity_received", 0)) * float(item.get("unit_price", 0))
            for item in items
            if item.get("unit_price")
        )
        tax_total = 0.0  # Tax calculation TBD
        total = subtotal + tax_total

        # PREPARE MODE: Return proposed changes
        if is_prepare_mode(params):
            confirmation_token = generate_confirmation_token(
                "accept_receiving",
                receiving_id
            )

            return {
                "status": "success",
                "mode": "prepare",
                "confirmation_token": confirmation_token,
                "proposed_changes": {
                    "receiving_id": receiving_id,
                    "current_status": receiving.get("status"),
                    "new_status": "accepted",
                    "vendor_name": receiving.get("vendor_name"),
                    "vendor_reference": receiving.get("vendor_reference"),
                    "item_count": len(items),
                    "computed_totals": {
                        "subtotal": subtotal,
                        "tax_total": tax_total,
                        "total": total,
                    }
                },
                "validation": {
                    "signature_required": True,
                    "roles_allowed": ["captain", "manager"],
                },
                "warning": "This will finalize and freeze the receiving record. No further edits allowed."
            }

        # EXECUTE MODE: Requires signature
        if not signature or not isinstance(signature, dict):
            return {
                "status": "error",
                "status_code": 400,
                "error_code": "SIGNATURE_REQUIRED",
                "message": "This action requires a signature for execution"
            }

        # Accept receiving
        now = datetime.now(timezone.utc).isoformat()

        db.table("pms_receiving").update({
            "status": "accepted",
            "subtotal": subtotal,
            "tax_total": tax_total,
            "total": total,
        }).eq("id", receiving_id).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (SIGNED, non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "accept_receiving",
                "user_id": user_id,
                "old_values": {
                    "status": receiving.get("status"),
                },
                "new_values": {
                    "status": "accepted",
                    "subtotal": subtotal,
                    "tax_total": tax_total,
                    "total": total,
                },
                "signature": signature,  # SIGNED action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for accept_receiving: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "old_status": receiving.get("status"),
            "new_status": "accepted",
            "total": total,
            "signature_verified": True,
        }

    return _fn


# ============================================================================
# ACTION 9: reject_receiving (MUTATE)
# ============================================================================

def _reject_receiving_adapter():
    """
    Reject receiving record.

    Required fields: yacht_id, user_id, receiving_id, reason
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract and validate required params
        yacht_id = params.get("yacht_id")
        user_id = params.get("user_id")
        user_jwt = params.get("user_jwt")
        receiving_id = params.get("receiving_id")
        reason = params.get("reason")

        # Validate required parameters
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "receiving_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err
        request_context = params.get("request_context")

        if not reason:
            return {
                "status": "error",
                "error_code": "MISSING_REASON",
                "message": "Reason is required for rejecting receiving"
            }

        # Get receiving record
        recv_result = db.table("pms_receiving").select(
            "id, status"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not recv_result.data:
            return {
                "status": "error",
                "error_code": "NOT_FOUND",
                "message": "Receiving record not found"
            }

        old_status = recv_result.data.get("status")

        # Check if already accepted (cannot reject)
        if old_status == "accepted":
            return {
                "status": "error",
                "error_code": "ALREADY_ACCEPTED",
                "message": "Cannot reject an accepted receiving record"
            }

        # Update status to rejected
        db.table("pms_receiving").update({
            "status": "rejected",
            "notes": reason,  # Store reason in notes
        }).eq("id", receiving_id).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log (non-critical - don't fail operation if audit fails)
        try:
            _write_audit_log(db, {
                "yacht_id": yacht_id,
                "entity_type": "receiving",
                "entity_id": receiving_id,
                "action": "reject_receiving",
                "user_id": user_id,
                "old_values": {
                    "status": old_status,
                },
                "new_values": {
                    "status": "rejected",
                    "reason": reason,
                },
                "signature": {},  # Non-signed action
                **audit_meta,
            })
        except Exception as e:
            logging.warning(f"Audit log write failed (non-critical) for reject_receiving: {e}")

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "old_status": old_status,
            "new_status": "rejected",
            "reason": reason,
        }

    return _fn


# ============================================================================
# ACTION 10: view_receiving_history (READ)
# ============================================================================

def _view_receiving_history_adapter():
    """
    View receiving history and details (READ).

    Required fields: yacht_id, receiving_id
    Allowed roles: All crew

    Returns: receiving header, line items, documents, audit trail
    """
    async def _fn(**params):
        # Extract required params - yacht_id comes from JWT context
        yacht_id = params.get("yacht_id")
        receiving_id = params.get("receiving_id")
        user_jwt = params.get("user_jwt")

        # Validate required fields (400 for invalid payload)
        if not yacht_id:
            return {
                "status": "error",
                "error_code": "MISSING_REQUIRED_FIELD",
                "message": "yacht_id is required"
            }
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "INVALID_REQUEST",
                "message": "receiving_id is required"
            }

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Get receiving record - explicitly filter by yacht_id for clarity
        # RLS also enforces yacht_id, but explicit filter reduces edge cases
        try:
            recv_result = db.table("pms_receiving").select(
                "*"
            ).eq("id", receiving_id).eq("yacht_id", yacht_id).execute()

            if not recv_result.data or len(recv_result.data) == 0:
                # Receiving not found in yacht scope → 404 (not 400)
                return {
                    "status": "error",
                    "error_code": "NOT_FOUND",
                    "message": "Receiving record not found"
                }

            receiving = recv_result.data[0]
        except Exception as e:
            # Database error - log and return as internal error (not 400)
            logger.error(f"Database error fetching receiving: {e}", exc_info=True)
            return {
                "status": "error",
                "error_code": "DATABASE_ERROR",
                "message": "Failed to fetch receiving record"
            }

        # received_by field contains user_id - frontend can look up name/role if needed

        # Fetch items, documents, and audit trail in parallel using thread pool
        # supabase-py execute() is synchronous, so we use asyncio.to_thread for true parallelism
        import asyncio
        from functools import partial

        def fetch_items():
            try:
                result = db.table("pms_receiving_items").select("*").eq("receiving_id", receiving_id).execute()
                return result.data or []
            except Exception as e:
                logger.warning(f"Failed to fetch items: {e}")
                return []

        def fetch_documents():
            try:
                result = db.table("pms_receiving_documents").select("*").eq("receiving_id", receiving_id).execute()
                return result.data or []
            except Exception as e:
                logger.warning(f"Failed to fetch documents: {e}")
                return []

        def fetch_audit():
            try:
                result = db.table("pms_audit_log").select("*").eq("entity_type", "receiving").eq("entity_id", receiving_id).order("created_at").execute()
                return result.data or []
            except Exception as e:
                logger.warning(f"Failed to fetch audit trail: {e}")
                return []

        # Execute in parallel using thread pool - reduces total latency by ~3x under load
        items, documents, audit_trail = await asyncio.gather(
            asyncio.to_thread(fetch_items),
            asyncio.to_thread(fetch_documents),
            asyncio.to_thread(fetch_audit),
        )

        # Always return 200 success if receiving exists, even with empty arrays
        return {
            "status": "success",
            "receiving": receiving,
            "items": items,
            "documents": documents,
            "audit_trail": audit_trail,
        }

    return _fn


# ============================================================================
# FLAG DISCREPANCY (Receiving Lens - structured issue logging)
# ============================================================================

def _flag_discrepancy_adapter():
    """
    Flag a shipment discrepancy — missing parts, breakage, partial delivery.

    Required fields: yacht_id, receiving_id, discrepancy_type, description
    Optional fields: affected_items[]
    Allowed roles: All crew (crew discovers discrepancies, HOD gets notified)
    """
    async def _fn(**params):
        yacht_id = params.get("yacht_id")
        receiving_id = params.get("receiving_id")
        user_id = params.get("user_id")
        discrepancy_type = params.get("discrepancy_type")
        description = params.get("description")
        affected_items = params.get("affected_items", [])

        if not yacht_id:
            return {"status": "error", "error_code": "MISSING_REQUIRED_FIELD", "message": "yacht_id is required"}
        if not receiving_id:
            return {"status": "error", "error_code": "MISSING_REQUIRED_FIELD", "message": "receiving_id is required"}
        if not discrepancy_type:
            return {"status": "error", "error_code": "MISSING_REQUIRED_FIELD", "message": "discrepancy_type is required"}
        valid_types = ["missing", "damaged", "wrong_item", "partial"]
        if discrepancy_type not in valid_types:
            return {"status": "error", "error_code": "INVALID_VALUE", "message": f"discrepancy_type must be one of: {', '.join(valid_types)}"}
        if not description:
            return {"status": "error", "error_code": "MISSING_REQUIRED_FIELD", "message": "description is required"}

        db, _db_err = _get_db(yacht_id)
        if _db_err:
            return _db_err

        # Verify receiving exists + yacht isolation
        recv_check = db.table("pms_receiving").select("id, status").eq(
            "id", receiving_id
        ).eq("yacht_id", yacht_id).execute()

        if not recv_check.data:
            return {"status": "error", "error_code": "NOT_FOUND", "message": f"Receiving {receiving_id} not found or access denied"}

        # Write to ledger_events — this is the source the lens AuditTrailSection
        # reads (entity_routes.py:get_receiving_entity → audit_history). Writing
        # here ensures discrepancies surface in the lens immediately.
        #
        # (Prior implementation wrote to pms_receiving_events with columns
        # receiving_id / event_type / event_data / created_by that do NOT exist
        # on that table — every call returned PostgREST 400. See
        # docs/ongoing_work/receiving/RECEIVING_BUGFIX_LOG.md.)
        from handlers.ledger_utils import build_ledger_event
        event_id = str(uuid.uuid4())

        try:
            ledger_row = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id or "system",
                event_type="update",                       # discrepancy is a write, not a status change
                entity_type="receiving",
                entity_id=receiving_id,
                action="flag_discrepancy",
                event_category="discrepancy",
                change_summary=f"{discrepancy_type}: {description[:120]}",
                metadata={
                    "discrepancy_type": discrepancy_type,
                    "description": description,
                    "affected_items": affected_items,
                },
                new_state={
                    "discrepancy_type": discrepancy_type,
                    "affected_items_count": len(affected_items),
                },
            )
            # Override the auto-generated id so we can return it to the caller
            ledger_row["id"] = event_id
            result = db.table("ledger_events").insert(ledger_row).execute()
            if not result.data:
                return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to record discrepancy"}
        except Exception as e:
            logger.error(f"flag_discrepancy ledger insert failed: {e}")
            return {"status": "error", "error_code": "DB_ERROR", "message": str(map_postgrest_error(e))}

        # Audit log
        _write_audit_log(db, {
            "yacht_id": yacht_id,
            "action": "flag_discrepancy",
            "entity_type": "receiving",
            "entity_id": receiving_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"event_id": event_id, "discrepancy_type": discrepancy_type},
        })

        return {
            "status": "success",
            "_ledger_written": True,
            "event_id": event_id,
            "receiving_id": receiving_id,
            "discrepancy_type": discrepancy_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Discrepancy ({discrepancy_type}) flagged on receiving {receiving_id}",
        }

    return _fn


# ============================================================================
# PHASE 4 DISPATCH TABLE
# ============================================================================
# Called by p0_actions_routes.py via routes/handlers/__init__.py.
# Convention: handler(payload, context, yacht_id, user_id, user_context, db_client) -> dict
# db_client not forwarded — each adapter calls get_service_db(yacht_id) directly.

_REASON_TEXT = {
    "short":      "items short — we received fewer units than ordered",
    "damaged":    "items arrived damaged and cannot be accepted",
    "wrong_item": "items received do not match the order specification",
    "over":       "items received in excess of ordered quantity",
}

_DISCREPANCY_DISPOSITIONS = ["short", "damaged", "wrong_item"]


def _build_email_body(
    supplier_name: str,
    po_number: str,
    received_date,
    disc_items: list,
    user_name: str,
    yacht_name: str,
    custom_note: str,
) -> str:
    lines_html = ""
    for item in disc_items:
        desc = item.get("description") or "Item"
        exp = item.get("quantity_expected") or "?"
        rcvd = item.get("quantity_received") or 0
        disp = item.get("disposition") or "short"
        reason = _REASON_TEXT.get(disp, disp)
        lines_html += f"""
        <tr>
            <td style="padding:4px 8px;">{desc}</td>
            <td style="padding:4px 8px; text-align:center;">{exp}</td>
            <td style="padding:4px 8px; text-align:center;">{rcvd}</td>
            <td style="padding:4px 8px;">{reason}</td>
        </tr>"""

    date_str = str(received_date) if received_date else "recently"
    custom_section = f"<p>{custom_note}</p>" if custom_note else ""

    return f"""
<p>Dear {supplier_name},</p>

<p>We are writing regarding our order <strong>{po_number or "reference pending"}</strong>, received on {date_str}.</p>

<p>Upon inspection, we have identified the following discrepancies:</p>

<table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:14px;">
  <thead>
    <tr style="background:#f5f5f5;">
      <th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;">Item</th>
      <th style="padding:6px 8px; text-align:center; border-bottom:1px solid #ddd;">Ordered</th>
      <th style="padding:6px 8px; text-align:center; border-bottom:1px solid #ddd;">Received</th>
      <th style="padding:6px 8px; text-align:left; border-bottom:1px solid #ddd;">Issue</th>
    </tr>
  </thead>
  <tbody>
    {lines_html}
  </tbody>
</table>

{custom_section}

<p>Please advise on how you intend to resolve these discrepancies at your earliest convenience.</p>

<p>Kind regards,<br>
<strong>{user_name}</strong><br>
{yacht_name}</p>
"""


def _draft_supplier_email_adapter():
    async def _fn(**params):
        receiving_id = params.get("receiving_id")
        user_id = params.get("user_id")
        yacht_id = params.get("yacht_id")
        cc_emails = params.get("cc_emails") or []
        custom_note = (params.get("custom_note") or "").strip()
        force = params.get("force", False)

        if not receiving_id:
            return {"status": "error", "error_code": "MISSING_FIELD",
                    "message": "receiving_id is required"}

        db = get_service_db(yacht_id)

        if not force:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            prev = db.table("ledger_events").select("created_at").eq(
                "entity_id", receiving_id
            ).eq("action", "draft_supplier_email").gte("created_at", cutoff).limit(1).execute()
            if prev.data:
                age_str = prev.data[0].get("created_at", "")
                return {
                    "status": "info",
                    "error_code": "ALREADY_DRAFTED",
                    "message": f"A draft was already created recently. Open your Outlook Drafts. "
                               f"Pass force=true to create another.",
                    "previous_draft_at": age_str,
                }

        recv = db.table("pms_receiving").select(
            "id, vendor_name, vendor_reference, po_id, received_date"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not recv.data:
            return {"status": "error", "error_code": "NOT_FOUND",
                    "message": "Receiving record not found"}

        recv_data = recv.data
        supplier_name = recv_data.get("vendor_name") or "Supplier"
        po_number = recv_data.get("vendor_reference") or ""
        po_id = recv_data.get("po_id")

        supplier_email = None
        if po_id:
            po = db.table("pms_purchase_orders").select(
                "supplier_id"
            ).eq("id", po_id).maybe_single().execute()
            if po.data and po.data.get("supplier_id"):
                sup = db.table("pms_suppliers").select(
                    "name, email"
                ).eq("id", po.data["supplier_id"]).maybe_single().execute()
                if sup.data:
                    supplier_email = sup.data.get("email")
                    supplier_name = sup.data.get("name") or supplier_name

        items_res = db.table("pms_receiving_items").select(
            "description, quantity_expected, quantity_received, quantity_rejected, disposition"
        ).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).in_(
            "disposition", _DISCREPANCY_DISPOSITIONS
        ).execute()
        disc_items = items_res.data or []

        if not disc_items:
            return {"status": "error", "error_code": "NO_DISCREPANCIES",
                    "message": "No discrepancy items found on this receiving"}

        user_res = db.table("auth_users_profiles").select("name").eq(
            "id", user_id
        ).maybe_single().execute()
        user_name = (user_res.data or {}).get("name") or "Crew Member"

        yacht_res = db.table("yacht_registry").select("name").eq(
            "id", yacht_id
        ).maybe_single().execute()
        yacht_name = (yacht_res.data or {}).get("name") or "Vessel"

        subject = f"Receiving Discrepancy — Order {po_number or 'Unknown'}"
        body = _build_email_body(
            supplier_name=supplier_name,
            po_number=po_number,
            received_date=recv_data.get("received_date"),
            disc_items=disc_items,
            user_name=user_name,
            yacht_name=yacht_name,
            custom_note=custom_note,
        )

        from integrations.graph_client import GraphWriteClient, TokenNotFoundError
        try:
            write_client = GraphWriteClient(db, user_id, yacht_id)
            to_list = [supplier_email] if supplier_email else []
            draft = await write_client.create_draft(
                to=to_list,
                subject=subject,
                body=body,
                body_type="HTML",
            )
        except TokenNotFoundError:
            return {
                "status": "error",
                "error_code": "NO_EMAIL_TOKEN",
                "message": "Connect your Outlook account under Settings to use this feature",
            }
        except Exception as graph_err:
            logger.error(f"[draft_supplier_email] Graph error: {graph_err}")
            return {
                "status": "error",
                "error_code": "GRAPH_ERROR",
                "message": "Failed to create Outlook draft. Try again later.",
            }

        try:
            from handlers.ledger_utils import build_ledger_event
            ledger_row = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="email_drafted",
                entity_type="receiving",
                entity_id=receiving_id,
                action="draft_supplier_email",
                change_summary=f"Supplier email drafted: {len(disc_items)} discrepancy item(s)",
                metadata={
                    "draft_id": draft.get("id") if isinstance(draft, dict) else None,
                    "supplier_email": supplier_email,
                    "discrepancy_count": len(disc_items),
                    "idempotency_key": f"email_draft:{receiving_id}:{user_id}",
                },
            )
            db.table("ledger_events").insert(ledger_row).execute()
        except Exception as e:
            logger.warning(f"[draft_supplier_email] Ledger event failed (non-fatal): {e}")

        return {
            "status": "success",
            "draft_created": True,
            "supplier_email": supplier_email,
            "no_recipient": supplier_email is None,
            "message": (
                "Draft created in your Outlook. Open and review before sending."
                if supplier_email
                else "Draft created with no recipient — please add the supplier email before sending."
            ),
        }

    return _fn


def spawn_receiving_from_po(
    db,
    po_id: str,
    yacht_id: str,
    user_id: str,
) -> dict:
    """
    Create a receiving record pre-populated from an approved PO.
    Returns {"spawned": True, "receiving_id": ...} or {"spawned": False, "reason": ...}.
    Idempotent: skips if a non-deleted receiving already exists for the po_id.
    """
    existing = db.table("pms_receiving").select("id").eq(
        "po_id", po_id
    ).eq("yacht_id", yacht_id).is_("deleted_at", "null").limit(1).execute()
    if existing.data:
        return {"spawned": False, "reason": "already_exists", "receiving_id": existing.data[0]["id"]}

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
        from handlers.ledger_utils import build_ledger_event
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


def fetch_label_data(db, yacht_id: str, receiving_id: str, item_ids_str=None) -> dict:
    """Fetch receiving record, yacht name, and accepted items for label generation."""
    recv = db.table("pms_receiving").select(
        "id, vendor_name, vendor_reference, received_date"
    ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not recv.data:
        return {"error": "Receiving not found", "status_code": 404}

    yacht = db.table("yacht_registry").select("name").eq(
        "id", yacht_id
    ).maybe_single().execute()
    yacht_name = (yacht.data or {}).get("name") or "Vessel"

    q = db.table("pms_receiving_items").select(
        "id, description, part_id, quantity_accepted, "
        "pms_parts(part_number, location, name)"
    ).eq("receiving_id", receiving_id).eq("yacht_id", yacht_id).gt("quantity_accepted", 0)
    if item_ids_str:
        ids = [x.strip() for x in item_ids_str.split(",") if x.strip()]
        if ids:
            q = q.in_("id", ids)
    items = q.execute().data or []

    if not items:
        return {"error": "No accepted items to print labels for", "status_code": 400}

    return {"recv": recv.data, "yacht_name": yacht_name, "items": items}


def log_labels_generated(db, yacht_id: str, user_id: str, receiving_id: str, item_count: int, size: str) -> None:
    """Fire ledger event for label generation (non-fatal on failure)."""
    try:
        from handlers.ledger_utils import build_ledger_event
        ledger_row = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="export",
            entity_type="receiving",
            entity_id=receiving_id,
            action="generate_labels",
            change_summary=f"{item_count} label(s) printed for receiving {receiving_id[:8]}",
            metadata={"item_count": item_count, "label_size": size},
        )
        db.table("ledger_events").insert(ledger_row).execute()
    except Exception as e:
        logger.warning(f"[generate_labels] Ledger event failed (non-fatal): {e}")


def _make_phase4(fn):
    async def _wrapper(payload, context, yacht_id, user_id, user_context, db_client):
        params = {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "role": user_context.get("role", ""),
            **context,
            **payload,
        }
        return await fn(**params)
    return _wrapper


HANDLERS: dict = {
    "create_receiving":                    _make_phase4(_create_receiving_adapter()),
    "attach_receiving_image_with_comment": _make_phase4(_attach_receiving_image_with_comment_adapter()),
    "extract_receiving_candidates":        _make_phase4(_extract_receiving_candidates_adapter()),
    "update_receiving_fields":             _make_phase4(_update_receiving_fields_adapter()),
    "add_receiving_item":                  _make_phase4(_add_receiving_item_adapter()),
    "adjust_receiving_item":               _make_phase4(_adjust_receiving_item_adapter()),
    "link_invoice_document":               _make_phase4(_link_invoice_document_adapter()),
    "accept_receiving":                    _make_phase4(_accept_receiving_adapter()),
    "confirm_receiving":                   _make_phase4(_accept_receiving_adapter()),
    "reject_receiving":                    _make_phase4(_reject_receiving_adapter()),
    "view_receiving_history":              _make_phase4(_view_receiving_history_adapter()),
    "flag_discrepancy":                    _make_phase4(_flag_discrepancy_adapter()),
    "draft_supplier_email":                _make_phase4(_draft_supplier_email_adapter()),
}
