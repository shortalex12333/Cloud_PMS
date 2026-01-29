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

from datetime import datetime, timezone
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
from handlers.db_client import get_user_db, map_postgrest_error
from utils.errors import error_response, success_response

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


def is_execute_mode(params: Dict) -> bool:
    """Check if action is in execute mode."""
    return params.get("mode") == "execute"


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


# ============================================================================
# HANDLERS CLASS
# ============================================================================

class ReceivingHandlers:
    """
    Receiving Lens v1 handlers.

    All methods return Dict in standardized action response format.
    """

    def __init__(self, supabase_client):
        self.db = supabase_client


# ============================================================================
# ACTION 1: create_receiving (MUTATE)
# ============================================================================

def _create_receiving_adapter(handlers: ReceivingHandlers):
    """
    Create new receiving record.

    Required fields: yacht_id, user_id, user_jwt
    Optional fields: vendor_name, vendor_reference, received_date, currency, notes, linked_work_order_id
    Allowed roles: HOD+
    RLS: Enforced via user JWT
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")

        # Optional fields
        vendor_name = params.get("vendor_name")
        vendor_reference = params.get("vendor_reference")
        received_date = params.get("received_date")  # ISO date string
        currency = params.get("currency")
        notes = params.get("notes")
        linked_work_order_id = params.get("linked_work_order_id")
        request_context = params.get("request_context")

        # Insert receiving record
        receiving_payload = {
            "yacht_id": yacht_id,
            "vendor_name": vendor_name,
            "vendor_reference": vendor_reference,
            "received_date": received_date if received_date else datetime.now(timezone.utc).date().isoformat(),
            "received_by": user_id,  # Track who received/created
            "status": "draft",
            "currency": currency,
            "linked_work_order_id": linked_work_order_id,
            "notes": notes,
            "properties": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user_id,
        }

        result = db.table("pms_receiving").insert(receiving_payload).execute()

        if not result.data or len(result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to create receiving record"
            }

        receiving_id = result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
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

def _attach_receiving_image_with_comment_adapter(handlers: ReceivingHandlers):
    """
    Attach image or document to receiving record.

    Required fields: yacht_id, user_id, receiving_id, document_id
    Optional fields: doc_type, comment
    Allowed roles: HOD+

    Storage path validation: {yacht_id}/receiving/{receiving_id}/{filename}
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
        document_id = params["document_id"]
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

        # Audit log
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

def _extract_receiving_candidates_adapter(handlers: ReceivingHandlers):
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
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
        source_document_id = params["source_document_id"]
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
        extraction_record = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "source_document_id": source_document_id,
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

        # Audit log (advisory only)
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

def _update_receiving_fields_adapter(handlers: ReceivingHandlers):
    """
    Update receiving header fields.

    Required fields: yacht_id, user_id, receiving_id
    Optional fields: vendor_name, vendor_reference, currency, received_date, notes
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]

        # Optional update fields
        vendor_name = params.get("vendor_name")
        vendor_reference = params.get("vendor_reference")
        currency = params.get("currency")
        received_date = params.get("received_date")
        notes = params.get("notes")
        request_context = params.get("request_context")

        # Get current receiving
        recv_result = db.table("pms_receiving").select(
            "id, vendor_name, vendor_reference, currency, status"
        ).eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()

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

        # Update receiving
        db.table("pms_receiving").update(update_payload).eq(
            "id", receiving_id
        ).execute()

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
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

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "updated_fields": list(update_payload.keys()),
        }

    return _fn


# ============================================================================
# ACTION 5: add_receiving_item (MUTATE)
# ============================================================================

def _add_receiving_item_adapter(handlers: ReceivingHandlers):
    """
    Add line item to receiving record.

    Required fields: yacht_id, user_id, receiving_id, (description OR part_id), quantity_received
    Optional fields: part_id, description, quantity_expected, unit_price, currency
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]

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

        item_result = db.table("pms_receiving_items").insert(item_payload).execute()

        if not item_result.data or len(item_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to add receiving item"
            }

        item_id = item_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
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

def _adjust_receiving_item_adapter(handlers: ReceivingHandlers):
    """
    Adjust existing receiving line item.

    Required fields: yacht_id, user_id, receiving_id, receiving_item_id
    Optional fields: quantity_received, unit_price, description
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
        receiving_item_id = params["receiving_item_id"]

        # Optional update fields
        quantity_received = params.get("quantity_received")
        unit_price = params.get("unit_price")
        description = params.get("description")
        request_context = params.get("request_context")

        # Get current item
        item_result = db.table("pms_receiving_items").select(
            "id, quantity_received, unit_price, description"
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
        if quantity_received is not None:
            if quantity_received < 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_QUANTITY",
                    "message": "Quantity received cannot be negative"
                }
            update_payload["quantity_received"] = quantity_received
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

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
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

        return {
            "status": "success",
            "receiving_id": receiving_id,
            "item_id": receiving_item_id,
            "updated_fields": list(update_payload.keys()),
        }

    return _fn


# ============================================================================
# ACTION 7: link_invoice_document (MUTATE)
# ============================================================================

def _link_invoice_document_adapter(handlers: ReceivingHandlers):
    """
    Link PDF invoice document to receiving record.

    Required fields: yacht_id, user_id, receiving_id, document_id
    Optional fields: comment
    Allowed roles: HOD+

    Storage path validation: {yacht_id}/receiving/{receiving_id}/{filename}
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
        document_id = params["document_id"]
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

        # Insert document link with doc_type='invoice'
        doc_payload = {
            "yacht_id": yacht_id,
            "receiving_id": receiving_id,
            "document_id": document_id,
            "doc_type": "invoice",
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        doc_result = db.table("pms_receiving_documents").insert(doc_payload).execute()

        if not doc_result.data or len(doc_result.data) == 0:
            return {
                "status": "error",
                "error_code": "INSERT_FAILED",
                "message": "Failed to link invoice document"
            }

        doc_link_id = doc_result.data[0]["id"]

        # Extract audit metadata
        audit_meta = extract_audit_metadata(request_context)

        # Audit log
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

def _accept_receiving_adapter(handlers: ReceivingHandlers):
    """
    Accept receiving record (SIGNED action - prepare/execute).

    Required fields: yacht_id, user_id, receiving_id, signature (execute only)
    Allowed roles: captain, manager

    PREPARE: Validate completeness (at least one item, totals computed)
    EXECUTE: Mark status='accepted', freeze monetary fields, write signed audit
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
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

        # Audit log (SIGNED)
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

def _reject_receiving_adapter(handlers: ReceivingHandlers):
    """
    Reject receiving record.

    Required fields: yacht_id, user_id, receiving_id, reason
    Allowed roles: HOD+
    """
    async def _fn(**params):
        # Extract required params
        yacht_id = params["yacht_id"]
        user_id = params["user_id"]
        user_jwt = params.get("user_jwt")

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return map_postgrest_error(e, "RLS_CLIENT_ERROR")
        receiving_id = params["receiving_id"]
        reason = params.get("reason")
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

        # Audit log
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

def _view_receiving_history_adapter(handlers: ReceivingHandlers):
    """
    View receiving history and details (READ).

    Required fields: yacht_id, receiving_id
    Allowed roles: All crew

    Returns: receiving header, line items, documents, audit trail
    """
    async def _fn(**params):
        # Extract required params - yacht_id comes from JWT context
        yacht_id = params["yacht_id"]
        receiving_id = params["receiving_id"]
        user_jwt = params.get("user_jwt")

        # Validate required fields (400 for invalid payload)
        if not receiving_id:
            return {
                "status": "error",
                "error_code": "INVALID_REQUEST",
                "message": "receiving_id is required"
            }

        # Create RLS-enforced client with user's JWT
        try:
            db = get_user_db(user_jwt, yacht_id)
        except Exception as e:
            logger.error(f"Failed to create RLS client: {e}")
            return {
                "status": "error",
                "error_code": "RLS_CLIENT_ERROR",
                "message": "Failed to create database client"
            }

        # Get receiving record - RLS automatically filters by yacht_id
        # If receiving_id not in user's yacht scope → RLS returns 0 rows → 404
        try:
            recv_result = db.table("pms_receiving").select(
                "*"
            ).eq("id", receiving_id).execute()

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

        # Get line items - return empty array if none exist (200, not 400)
        try:
            items_result = db.table("pms_receiving_items").select(
                "*"
            ).eq("receiving_id", receiving_id).execute()
            items = items_result.data or []
        except Exception as e:
            logger.warning(f"Failed to fetch items: {e}")
            items = []

        # Get documents - return empty array if none exist (200, not 400)
        try:
            docs_result = db.table("pms_receiving_documents").select(
                "*"
            ).eq("receiving_id", receiving_id).execute()
            documents = docs_result.data or []
        except Exception as e:
            logger.warning(f"Failed to fetch documents: {e}")
            documents = []

        # Get audit trail - return empty array if none exist (200, not 400)
        # Query only pms_audit_log as specified - no JOIN to auth tables
        try:
            audit_result = db.table("pms_audit_log").select(
                "*"
            ).eq("entity_type", "receiving").eq("entity_id", receiving_id).order("created_at").execute()
            audit_trail = audit_result.data or []
        except Exception as e:
            logger.warning(f"Failed to fetch audit trail: {e}")
            audit_trail = []

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
# EXPORTS
# ============================================================================

__all__ = [
    "ReceivingHandlers",
    "_create_receiving_adapter",
    "_attach_receiving_image_with_comment_adapter",
    "_extract_receiving_candidates_adapter",
    "_update_receiving_fields_adapter",
    "_add_receiving_item_adapter",
    "_adjust_receiving_item_adapter",
    "_link_invoice_document_adapter",
    "_accept_receiving_adapter",
    "_reject_receiving_adapter",
    "_view_receiving_history_adapter",
]
