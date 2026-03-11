# DATA AGENT — Handover Export Lens

**Your role:** IMPLEMENT `GET /v1/entity/handover_export/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/handover_export/{export_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Table (EXACT column names from handler code)

```
handover_exports (columns):
  id                   uuid        NOT NULL
  yacht_id             uuid        NOT NULL
  original_storage_url text        nullable
  edited_content       jsonb       nullable   JSON with {sections: [...]} or array of sections
  review_status        text        NOT NULL   "pending","under_review","approved","rejected"
  created_at           timestamptz NOT NULL
  user_signature       jsonb       nullable   {data: "base64...", signed_at: "..."}
  user_signed_at       timestamptz nullable
  hod_signature        jsonb       nullable
  hod_signed_at        timestamptz nullable
  draft_id             uuid        nullable
  export_type          text        nullable   "handover","monthly","voyage"
  exported_at          timestamptz nullable
  exported_by_user_id  uuid        nullable
  document_hash        text        nullable
  export_status        text        nullable   "draft","exported","archived"
  file_name            text        nullable
```

**sections note:** `edited_content` is stored as JSON. It may be:
- `{sections: [...]}` → return `edited_content.sections`
- `[...]` (direct array) → return as-is
- string → `json.loads()` it first

**Signature note:** The frontend component expects BOTH `user_signature` AND `userSignature` (camelCase). Return both.

---

## Required Response Shape

```json
{
  "id": "uuid",
  "yacht_id": "uuid",
  "review_status": "pending",
  "export_type": "handover",
  "export_status": "draft",
  "file_name": "handover_2026_03.pdf",
  "sections": [
    {"title": "Work Orders", "content": "..."},
    {"title": "Open Faults", "content": "..."}
  ],
  "user_signature": null,
  "userSignature": null,
  "hod_signature": null,
  "submitted_at": null,
  "created_at": "...",
  "draft_id": null
}
```

---

## Implementation Template

```python
@router.get("/v1/entity/handover_export/{export_id}")
async def get_handover_export_entity(export_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("handover_exports").select("*") \
            .eq("id", export_id) \
            .eq("yacht_id", yacht_id) \
            .maybe_single().execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="Handover export not found")

        data = r.data

        # Parse edited_content → sections
        edited_content = data.get("edited_content") or {}
        if isinstance(edited_content, str):
            import json as _j
            edited_content = _j.loads(edited_content) if edited_content else {}
        if isinstance(edited_content, list):
            sections = edited_content
        elif isinstance(edited_content, dict):
            sections = edited_content.get("sections", [])
        else:
            sections = []

        user_sig = data.get("user_signature")
        return {
            "id": data.get("id"),
            "yacht_id": data.get("yacht_id"),
            "review_status": data.get("review_status"),
            "export_type": data.get("export_type"),
            "export_status": data.get("export_status"),
            "file_name": data.get("file_name"),
            "sections": sections,
            "user_signature": user_sig,
            "userSignature": user_sig,    # camelCase alias for frontend component
            "hod_signature": data.get("hod_signature"),
            "submitted_at": data.get("exported_at"),
            "created_at": data.get("created_at"),
            "draft_id": data.get("draft_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch handover_export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

ALL roles: edit_handover_section, regenerate_handover_summary, export_handover (requires confirmation), add_to_handover, edit_handover_item, attach_document_to_handover

---

## Success Criteria

200 + `id`, `yacht_id`, `review_status` non-null. `sections` array present (may be empty).
