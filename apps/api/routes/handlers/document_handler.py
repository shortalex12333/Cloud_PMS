"""
Document Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 5).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

Block 1 (L4648-4700): view_related_documents — inline query.
Block 2 (L4702-4748): view_document_section — inline query.
Block 3 (L5037-5078): upload_document, update_document, delete_document, add_document_tags,
    get_document_url, list_documents — delegates to handlers.document_handlers via get_document_handlers().
"""
import logging
import uuid

from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


def _push_doc_notification(
    db_client: Client,
    yacht_id: str,
    user_id: str,
    action: str,
    title: str,
    body: str,
    entity_id: str,
    user_role: str = None,
) -> None:
    try:
        db_client.table("pms_notifications").insert({
            "yacht_id": yacht_id,
            "user_id": user_id,
            "notification_type": f"document_{action}",
            "title": title,
            "body": body,
            "priority": "normal",
            "entity_type": "document",
            "entity_id": entity_id,
            "cta_action_id": "get_document_url",
            "cta_payload": {"document_id": entity_id},
            "idempotency_key": f"doc_{action}_{entity_id}_{str(uuid.uuid4())[:8]}",
            "is_read": False,
            "triggered_by": user_id,
            "metadata": {"source": "document_lens", "role": user_role or ""},
        }).execute()
    except Exception as notif_err:
        logger.warning(f"[Notification] doc {action} failed (non-fatal): {notif_err}")

# RBAC mapping for Document Lens v2 actions (from original L5040-5048)
_DOC_V2_ALLOWED_ROLES = {
    "upload_document": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "update_document": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "add_document_tags": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "delete_document": ["captain", "manager"],
    "get_document_url": ["crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
                         "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "list_documents": ["crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
}


# ============================================================================
# view_related_documents  (was L4648-4700)
# ============================================================================
async def view_related_documents(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")

    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")

    try:
        docs = db_client.table("documents").select(
            "id, filename, doc_type, storage_path, created_at"
        ).eq("yacht_id", yacht_id).or_(
            f"metadata->>entity_id.eq.{entity_id},metadata->>related_entity_id.eq.{entity_id}"
        ).limit(20).execute()

        return {
            "status": "success",
            "success": True,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "documents": docs.data or [],
            "count": len(docs.data) if docs.data else 0,
        }
    except Exception:
        # Fallback to simple query
        try:
            docs = db_client.table("documents").select(
                "id, filename, doc_type, storage_path, created_at"
            ).eq("yacht_id", yacht_id).limit(10).execute()

            return {
                "status": "success",
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "documents": docs.data or [],
                "count": len(docs.data) if docs.data else 0,
                "note": "Showing recent documents for yacht",
            }
        except Exception:
            return {
                "status": "success",
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "documents": [],
                "count": 0,
            }


# ============================================================================
# view_document_section  (was L4702-4748)
# ============================================================================
async def view_document_section(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    document_id = payload.get("document_id")
    section_id = payload.get("section_id")

    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")
    if not section_id:
        raise HTTPException(status_code=400, detail="section_id is required")

    try:
        doc = db_client.table("documents").select(
            "id, filename, metadata"
        ).eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not doc.data:
            raise HTTPException(status_code=404, detail="Document not found")

        metadata = doc.data.get("metadata", {}) or {}
        sections = metadata.get("sections", {}) or {}
        section_content = sections.get(section_id, {})

        return {
            "status": "success",
            "success": True,
            "document_id": document_id,
            "document_title": doc.data.get("filename"),
            "section_id": section_id,
            "section": section_content if section_content else {
                "content": "Section not found",
                "note": f"Section '{section_id}' not available in document",
            },
        }
    except HTTPException:
        raise
    except Exception:
        return {
            "status": "success",
            "success": True,
            "document_id": document_id,
            "section_id": section_id,
            "section": {"content": "Section not available"},
        }


# ============================================================================
# Document Lens V2 actions (L5037-5078) — delegate to handlers.document_handlers
# ============================================================================

async def upload_document(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("upload_document", user_context)
    result = await _delegate_to_doc_handler("upload_document", db_client, yacht_id, user_id, payload)
    if isinstance(result, dict) and result.get("status") != "error":
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="create",
                entity_type="document",
                entity_id=result.get("document_id") or result.get("id") or yacht_id,
                action="upload_document",
                user_role=user_context.get("role"),
                change_summary=f"Document uploaded: {payload.get('file_name', '')}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record upload_document: {ledger_err}")
        _push_doc_notification(
            db_client, yacht_id, user_id, "uploaded",
            "Document uploaded",
            f"{payload.get('file_name', 'document')} uploaded to vessel documents",
            result.get("document_id") or result.get("id") or yacht_id,
            user_context.get("role"),
        )
        result["_ledger_written"] = True
    return result


async def update_document(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("update_document", user_context)
    document_id = payload.get("document_id")
    result = await _delegate_to_doc_handler("update_document", db_client, yacht_id, user_id, payload)
    if isinstance(result, dict) and result.get("status") != "error":
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="document",
                entity_id=document_id or yacht_id,
                action="update_document",
                user_role=user_context.get("role"),
                change_summary=f"Document metadata updated: {', '.join(result.get('updated_fields', []))}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record update_document: {ledger_err}")
        _push_doc_notification(
            db_client, yacht_id, user_id, "updated",
            "Document updated",
            f"Document metadata updated: {', '.join(result.get('updated_fields', []))}",
            document_id or yacht_id,
            user_context.get("role"),
        )
        result["_ledger_written"] = True
    return result


async def delete_document(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("delete_document", user_context)
    document_id = payload.get("document_id")
    result = await _delegate_to_doc_handler("delete_document", db_client, yacht_id, user_id, payload)
    if isinstance(result, dict) and result.get("status") != "error":
        try:
            # HMAC01 Option 1: SIGNED actions MUST propagate the signature payload
            # into ledger_events.metadata so the receipt layer can prove who
            # approved the destructive action. Without this, the ledger row
            # records the mutation but not the PIN/TOTP evidence.
            sig_metadata = payload.get("signature") or {}
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="delete",
                entity_type="document",
                entity_id=document_id or yacht_id,
                action="delete_document",
                user_role=user_context.get("role"),
                change_summary=f"Document deleted: reason={payload.get('reason', '')}",
                metadata={"signature": sig_metadata} if sig_metadata else None,
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record delete_document: {ledger_err}")
        _push_doc_notification(
            db_client, yacht_id, user_id, "deleted",
            "Document deleted",
            f"Document deleted: {payload.get('reason', 'no reason given')}",
            document_id or yacht_id,
            user_context.get("role"),
        )
        result["_ledger_written"] = True
    return result


async def add_document_tags(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("add_document_tags", user_context)
    document_id = payload.get("document_id")
    result = await _delegate_to_doc_handler("add_document_tags", db_client, yacht_id, user_id, payload)
    if isinstance(result, dict) and result.get("status") != "error":
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="update",
                entity_type="document",
                entity_id=document_id or yacht_id,
                action="add_document_tags",
                user_role=user_context.get("role"),
                change_summary=f"Tags updated: {payload.get('tags', [])}",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record add_document_tags: {ledger_err}")
        _push_doc_notification(
            db_client, yacht_id, user_id, "tags_updated",
            "Document tags updated",
            f"Tags updated: {payload.get('tags', [])}",
            document_id or yacht_id,
            user_context.get("role"),
        )
        result["_ledger_written"] = True
    return result


async def get_document_url(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("get_document_url", user_context)
    return await _delegate_to_doc_handler("get_document_url", db_client, yacht_id, user_id, payload)


async def list_documents(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    _enforce_doc_rbac("list_documents", user_context)
    return await _delegate_to_doc_handler("list_documents", db_client, yacht_id, user_id, payload)


# ============================================================================
# HELPERS
# ============================================================================

def _enforce_doc_rbac(action: str, user_context: dict) -> None:
    """Check RBAC for doc v2 actions. Raises HTTPException(403) if denied."""
    user_role = user_context.get("role", "")
    allowed_roles = _DOC_V2_ALLOWED_ROLES.get(action, [])
    if user_role not in allowed_roles:
        logger.warning(f"[RLS] Role '{user_role}' denied for action '{action}'. Allowed: {allowed_roles}")
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' is not authorized to perform action '{action}'"
        )


async def _delegate_to_doc_handler(
    action: str, db_client: Client, yacht_id: str, user_id: str, payload: dict,
) -> dict:
    """Load handlers.document_handlers lazily and call the named handler."""
    from handlers.document_handlers import get_document_handlers
    doc_handlers = get_document_handlers(db_client)
    handler_fn = doc_handlers.get(action)
    if not handler_fn:
        raise HTTPException(status_code=404, detail=f"Document handler '{action}' not found")
    return await handler_fn(yacht_id=yacht_id, user_id=user_id, **payload)


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Inline query actions
    "view_related_documents": view_related_documents,
    "view_document_section": view_document_section,
    # Document Lens v2 (delegate)
    "upload_document": upload_document,
    "update_document": update_document,
    "delete_document": delete_document,
    "add_document_tags": add_document_tags,
    "get_document_url": get_document_url,
    "list_documents": list_documents,
}
