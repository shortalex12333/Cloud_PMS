"""
Attachment Upload Route — POST /v1/attachments/upload

Proxies file uploads from the browser through Render so storage writes
hit the TENANT Supabase project (vzsohavtuotocgrfkfyd).

The browser MUST NOT write to TENANT Supabase directly — that project is
owned by the Render backend. Vercel (frontend) only touches MASTER for auth.

Flow:
  Browser → POST multipart to Render → Render uploads to TENANT storage
          → Render inserts pms_attachments row → 200 OK to browser
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from supabase import create_client

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id
from utils.filenames import sanitize_storage_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/attachments", tags=["attachments"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — mirrors frontend constant

ACCEPTED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/png', 'image/heic', 'image/webp', 'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'application/zip',
    'application/octet-stream',
}


def _get_tenant_client(tenant_key_alias: str):
    """Return a Supabase client for the TENANT project using service key."""
    url = os.environ.get(f'{tenant_key_alias}_SUPABASE_URL')
    key = os.environ.get(f'{tenant_key_alias}_SUPABASE_SERVICE_KEY')
    if not url or not key:
        url = os.environ.get('TENANT_1_SUPABASE_URL')
        key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise ValueError(f'Missing TENANT credentials for {tenant_key_alias}')
    return create_client(url, key)


@router.post("/upload", include_in_schema=True)
async def upload_entity_attachment(
    file: UploadFile = File(..., description="File to attach (≤15 MB)"),
    entity_type: str = Form(..., description='Parent entity type e.g. "warranty"'),
    entity_id: str = Form(..., description="UUID of the parent entity"),
    bucket: str = Form(..., description="Supabase storage bucket name"),
    category: str = Form(..., description='File category e.g. "claim_document"'),
    yacht_id_override: Optional[str] = Form(None, alias="yacht_id"),
    auth: dict = Depends(get_authenticated_user),
):
    yacht_id = resolve_yacht_id(auth, yacht_id_override)
    user_id = auth["user_id"]

    # ── MIME gate ──────────────────────────────────────────────────────────
    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in ACCEPTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}",
        )

    # ── Read + size gate ───────────────────────────────────────────────────
    try:
        file_content = await file.read()
    except Exception as exc:
        logger.error(f"[attachments/upload] Failed to read stream: {exc}")
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(file_content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)} MB",
        )

    # ── Build storage path ─────────────────────────────────────────────────
    attachment_id = str(uuid.uuid4())
    raw_name = file.filename or "attachment"
    filename = sanitize_storage_filename(raw_name)
    storage_path = f"{entity_type}/{entity_id}/{attachment_id}/{filename}"

    supabase = _get_tenant_client(auth["tenant_key_alias"])

    # ── Step 1: upload blob ─────────────────────────────────────────────────
    try:
        supabase.storage.from_(bucket).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except Exception as exc:
        logger.error(f"[attachments/upload] Storage upload failed: bucket={bucket} path={storage_path} err={exc}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # ── Step 2: insert pms_attachments row ────────────────────────────────
    now = datetime.utcnow().isoformat()
    row = {
        "id": attachment_id,
        "yacht_id": yacht_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "storage_bucket": bucket,
        "storage_path": storage_path,
        "filename": filename,
        "mime_type": content_type,
        "file_size": len(file_content),
        "category": category,
        "uploaded_by": user_id,
        "created_at": now,
    }
    try:
        result = supabase.table("pms_attachments").insert(row).execute()
        if not result.data:
            raise Exception("Insert returned no data")
    except Exception as exc:
        logger.error(f"[attachments/upload] pms_attachments insert failed, rolling back blob: {exc}")
        try:
            supabase.storage.from_(bucket).remove([storage_path])
        except Exception as rb_exc:
            logger.error(f"[attachments/upload] ROLLBACK FAILED — orphan blob: {storage_path} err={rb_exc}")
        raise HTTPException(status_code=500, detail="Failed to save attachment record")

    logger.info(
        f"[attachments/upload] OK: id={attachment_id[:8]} entity={entity_type}/{entity_id[:8]} "
        f"bucket={bucket} size={len(file_content)} yacht={yacht_id[:8]}"
    )
    return {
        "id": attachment_id,
        "filename": filename,
        "storage_path": storage_path,
        "storage_bucket": bucket,
        "mime_type": content_type,
        "file_size": len(file_content),
        "entity_type": entity_type,
        "entity_id": entity_id,
    }
