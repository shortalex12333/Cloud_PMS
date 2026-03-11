# VERIFY AGENT — Document Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('document' in p for p in paths)
print('✅ document endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real document ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "manual" 2>/dev/null | grep "document" | head -3
./celeste.sh search "certificate pdf" 2>/dev/null | grep "document" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
DOC_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/document/$DOC_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','filename','mime_type']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ document OK, filename:', d['filename'], 'mime_type:', d['mime_type'])
"
```

---

## Verify soft-delete filter works

A deleted document must return 404, not 200.
If you have a `deleted_at` value to test with, run:

```bash
# If you have the ID of a deleted doc, it must 404
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/document/$DELETED_DOC_ID | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d.get('detail') == 'Document not found', 'FAIL: deleted doc should 404'
print('✅ soft-delete filter works')
"
```

---

## Frontend check

Search "manual" or "pdf" → click → `/documents/{id}` loads.
Verify: filename visible, MIME type badge, download button present (uses `url` field).

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "document\|500\|error"
```

Common issues:
- `deleted_at IS NULL` filter syntax — use `.is_("deleted_at", "null")` not `.eq("deleted_at", None)`
- `tags` column may be a PostgreSQL array `text[]` — Supabase returns as Python list, safe to return directly
- `storage_path` null → `url` field will be null — that is OK for v1
