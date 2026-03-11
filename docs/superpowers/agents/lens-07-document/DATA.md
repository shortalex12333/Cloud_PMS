# DATA AGENT — Document Lens

**Your role:** IMPLEMENT `GET /v1/entity/document/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/document/{document_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Table (EXACT column names)

```
doc_metadata (14 columns):
  id              uuid        NOT NULL
  yacht_id        uuid        NOT NULL
  filename        text        NOT NULL
  storage_path    text        NOT NULL   bucket path, NOT a signed URL
  content_type    text        NOT NULL   MIME type e.g. "application/pdf"
  deleted_at      timestamptz nullable   filter: WHERE deleted_at IS NULL
  title           text        nullable   human title, fallback to filename
  description     text        nullable
  classification  text        nullable   "technical", "safety", "certificate" etc.
  equipment_id    uuid        nullable
  equipment_name  text        nullable
  tags            text[]      nullable   array of tag strings
  created_at      timestamptz NOT NULL
  created_by      uuid        nullable
```

**IMPORTANT:** Always filter `WHERE deleted_at IS NULL`. Soft-deleted docs must not be returned.
**URL note:** `storage_path` is a bucket key, NOT a signed URL. For v1, return it as `url`. Signing is a future task.

---

## Required Response Shape

```json
{
  "id": "uuid",
  "filename": "SOLAS_Certificate_2024.pdf",
  "title": "SOLAS Safety Certificate",
  "description": null,
  "mime_type": "application/pdf",
  "url": "documents/yacht-uuid/SOLAS_Certificate_2024.pdf",
  "classification": "certificate",
  "equipment_id": null,
  "equipment_name": null,
  "tags": ["safety", "vessel"],
  "created_at": "...",
  "created_by": "uuid",
  "yacht_id": "uuid"
}
```

**Mapping:**
- `mime_type` ← `content_type`
- `title` ← `title` if not null, else `filename`
- `url` ← `storage_path` (v1: return as-is, no signing)

---

## Implementation Template

```python
@router.get("/v1/entity/document/{document_id}")
async def get_document_entity(document_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("doc_metadata").select("*") \
            .eq("id", document_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Document not found")

        data = r.data
        return {
            "id": data.get("id"),
            "filename": data.get("filename"),
            "title": data.get("title") or data.get("filename"),
            "description": data.get("description"),
            "mime_type": data.get("content_type"),
            "url": data.get("storage_path"),
            "classification": data.get("classification"),
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "tags": data.get("tags") or [],
            "created_at": data.get("created_at"),
            "created_by": data.get("created_by"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

ALL roles: upload_document, update_document, add_document_tags, get_document_url
HOD (chief_engineer/captain/manager): reclassify_document, delete_document (requires signature)

---

## Success Criteria

200 + `id`, `filename`, `mime_type` non-null.
