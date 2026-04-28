"""
Shared helpers for entity lens endpoints.

Extracted from routes/entity_routes.py (Phase C thinning) so that
entity_lens_handlers.py and HandoverWorkflowHandlers can import them
without circular dependencies.
"""

import logging
from typing import Dict, List, Optional

from lib.user_resolver import resolve_users

logger = logging.getLogger(__name__)

# Fallback bucket map for pre-migration rows without storage_bucket column.
# New rows store storage_bucket directly on pms_attachments.
ATTACHMENT_BUCKET = {
    "fault": "pms-discrepancy-photos",
    "work_order": "pms-work-order-photos",
    "checklist_item": "pms-work-order-photos",
    "equipment": "pms-work-order-photos",
    "purchase_order": "pms-finance-documents",
    "warranty": "pms-warranty-documents",
    "receiving": "pms-receiving-images",
    "certificate": "pms-certificate-documents",
    "shopping_list": "pms-shopping-list-photos",
}


def _sign_url(supabase, bucket: str, path: str, expires_in: int = 3600):
    """Sign a storage path. Returns URL string or None. Never raises."""
    if not path:
        return None
    try:
        result = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signed_url")
    except Exception as e:
        logger.warning(f"Failed to sign {bucket}/{path}: {e}")
        return None


def _get_attachments(supabase, entity_type: str, entity_id: str, yacht_id: str) -> list:
    """Query pms_attachments, sign each, return list matching frontend Attachment shape."""
    try:
        result = supabase.table("pms_attachments").select(
            "id, filename, mime_type, storage_path, file_size, category, storage_bucket, "
            "description, uploaded_by, created_at"
        ).eq("entity_type", entity_type).eq("entity_id", entity_id).eq(
            "yacht_id", yacht_id
        ).is_("deleted_at", "null").execute()

        rows = result.data or []

        user_ids = list({r.get("uploaded_by") for r in rows if r.get("uploaded_by")})
        user_map: Dict[str, Dict[str, Optional[str]]] = {}
        if user_ids:
            try:
                user_map = resolve_users(supabase, yacht_id, user_ids)
            except Exception as exc:
                logger.warning(
                    f"_get_attachments: uploader resolve failed for {entity_type}/{entity_id}: {exc}"
                )

        attachments = []
        fallback_bucket = ATTACHMENT_BUCKET.get(entity_type, "attachments")
        for att in rows:
            path = att.get("storage_path")
            if not path:
                continue
            bucket = att.get("storage_bucket") or fallback_bucket
            url = _sign_url(supabase, bucket, path)
            if not url:
                continue
            uploader_uid = att.get("uploaded_by")
            uploader_name = None
            if uploader_uid:
                uploader_name = (user_map.get(uploader_uid) or {}).get("name")
            attachments.append({
                "id": att["id"],
                "filename": att.get("filename", "file"),
                "url": url,
                "signed_url": url,
                "mime_type": att.get("mime_type", "application/octet-stream"),
                "size_bytes": att.get("file_size") or 0,
                "category": att.get("category"),
                "description": att.get("description"),
                "uploaded_at": att.get("created_at"),
                "uploaded_by": uploader_uid,
                "uploaded_by_name": uploader_name,
                "thumbnail_path": None,
            })
        return attachments
    except Exception as e:
        logger.warning(f"Failed to get attachments for {entity_type}/{entity_id}: {e}")
        return []


def _nav(entity_type: str, entity_id, label: str):
    """Return nav link dict or None if entity_id is falsy."""
    if not entity_id:
        return None
    return {"entity_type": entity_type, "entity_id": str(entity_id), "label": label}
