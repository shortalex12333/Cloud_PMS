# DATA AGENT — Certificate Lens

**Your role:** IMPLEMENT `GET /v1/entity/certificate/{id}` in `apps/api/routes/entity_routes.py`.
This endpoint does NOT exist yet. You must create it.

---

## Endpoint to create

`GET /v1/entity/certificate/{certificate_id}`
**File to modify:** `apps/api/routes/entity_routes.py` (create if not exists)
**Mount in:** `apps/api/pipeline_service.py` (add import + `app.include_router(entity_routes_router)`)

---

## DB Tables (EXACT column names from FINAL doc)

```
pms_vessel_certificates (14 columns):
  id              uuid        NOT NULL
  yacht_id        uuid        NOT NULL
  certificate_type text       NOT NULL   e.g. "CLASS", "ISM", "SOLAS"
  certificate_name text       NOT NULL   the human name
  certificate_number text     nullable
  issuing_authority text      NOT NULL
  issue_date      date        nullable
  expiry_date     date        nullable
  last_survey_date date       nullable
  next_survey_due date        nullable
  status          text        NOT NULL   "active","expired","superseded","draft"
  document_id     uuid        nullable
  properties      jsonb       nullable   may contain { notes: "..." }
  created_at      timestamptz NOT NULL

pms_crew_certificates (12 columns):
  id              uuid        NOT NULL
  yacht_id        uuid        NOT NULL
  person_name     text        NOT NULL   crew member name
  person_node_id  uuid        nullable   links to auth_users_profiles
  certificate_type text       NOT NULL   e.g. "STCW", "GMDSS", "ENG1"
  certificate_number text     nullable
  issuing_authority text      nullable
  issue_date      date        nullable
  expiry_date     date        nullable
  document_id     uuid        nullable
  properties      jsonb       nullable
  created_at      timestamptz NOT NULL
```

---

## Lookup Strategy

1. Query `pms_vessel_certificates` WHERE `id = {id}` AND `yacht_id = {yacht_id}`
2. If no result → query `pms_crew_certificates` WHERE `id = {id}` AND `yacht_id = {yacht_id}`
3. If still no result → 404

---

## Required Response Shape

```json
{
  "id": "uuid",
  "name": "Lloyd's Classification",
  "certificate_type": "CLASS",
  "issuing_authority": "Lloyd's Register",
  "issue_date": "2024-01-15",
  "expiry_date": "2025-01-15",
  "status": "active",
  "certificate_number": "CERT-001",
  "notes": null,
  "crew_member_id": null,
  "domain": "vessel",
  "yacht_id": "uuid",
  "created_at": "..."
}
```

**Mapping:**
- Vessel: `name` ← `certificate_name`, `crew_member_id` = null
- Crew: `name` ← `certificate_type` (no separate name column), `crew_member_id` ← `person_node_id`, `domain` = "crew"
- `notes` ← `properties.get('notes')` if properties is dict

---

## Implementation Template

```python
@router.get("/v1/entity/certificate/{certificate_id}")
async def get_certificate_entity(certificate_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        data, domain = None, "vessel"
        r = supabase.table("pms_vessel_certificates").select("*").eq("id", certificate_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if r.data:
            data = r.data
        else:
            r2 = supabase.table("pms_crew_certificates").select("*").eq("id", certificate_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if r2.data:
                data, domain = r2.data, "crew"

        if not data:
            raise HTTPException(status_code=404, detail="Certificate not found")

        props = data.get("properties") or {}
        if isinstance(props, str):
            import json as _j; props = _j.loads(props) if props else {}

        return {
            "id": data.get("id"),
            "name": data.get("certificate_name") if domain == "vessel" else data.get("certificate_type", "Certificate"),
            "certificate_type": data.get("certificate_type"),
            "issuing_authority": data.get("issuing_authority"),
            "issue_date": data.get("issue_date"),
            "expiry_date": data.get("expiry_date"),
            "status": data.get("status", "active"),
            "certificate_number": data.get("certificate_number"),
            "notes": props.get("notes") if isinstance(props, dict) else None,
            "crew_member_id": data.get("person_node_id") if domain == "crew" else None,
            "domain": domain,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Role-Gated Actions

ALL roles: view only (no mutations for crew)
HOD (chief_engineer/captain/manager): create_vessel_certificate, create_crew_certificate, update_certificate, link_document_to_certificate, upload_certificate_document, update_certificate_metadata
HOD + signed: supersede_certificate
Manager only: delete_certificate

---

## Success Criteria

200 + `id`, `name`, `certificate_type`, `expiry_date` non-null.
