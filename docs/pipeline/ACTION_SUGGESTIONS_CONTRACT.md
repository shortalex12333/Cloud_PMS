# Action Suggestions API Contract

Backend-authoritative contract for listing micro‑actions by query. Frontend renders what backend returns — never invents actions.

---

## Endpoint

```
GET /v1/actions/list
Authorization: Bearer <JWT>
```

### Query Parameters
- `q` (optional): Search text (e.g., `add certificate`)
- `domain` (optional): Domain filter (e.g., `certificates`)
- `entity_id` (optional): Entity UUID to resolve `{certificate_id}` in storage path previews

### Security
- JWT required; role gating applied during listing
- Yacht isolation enforced on execution; listing never bypasses RLS

---

## Response

```json
{
  "query": "add certificate",
  "actions": [
    {
      "action_id": "create_vessel_certificate",
      "label": "Add Vessel Certificate",
      "variant": "MUTATE",               // READ | MUTATE | SIGNED
      "allowed_roles": ["chief_engineer","captain","manager"],
      "required_fields": ["yacht_id","certificate_type","certificate_name","issuing_authority"],
      "domain": "certificates",
      "match_score": 0.85,
      "storage_options": {
        "bucket": "documents",
        "path_preview": "{yacht_id}/certificates/<new_id>/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
        "confirmation_required": true
      }
    }
  ],
  "total_count": 2,
  "role": "chief_engineer"
}
```

### Fields
- `variant`: SIGNED actions require signature during execute
- `required_fields`: Render minimal form; omit `yacht_id` in UI (backend infers)
- `storage_options` (optional): Show path preview; do not allow arbitrary path edits; presigned URLs only in execute flow

---

## Examples

List actions (HOD):
```
curl -H "Authorization: Bearer $HOD_JWT" \
  "$API_BASE/v1/actions/list?q=add+certificate&domain=certificates"
```

List actions (CREW): should return no MUTATE/SIGNED actions
```
curl -H "Authorization: Bearer $CREW_JWT" \
  "$API_BASE/v1/actions/list?domain=certificates"
```

---

## Non‑negotiables
- Backend owns action availability, roles, and storage semantics
- UI renders returned labels/fields; never fabricates actions
- Execution goes through `/v1/actions/execute`; DB RLS is the final authority

