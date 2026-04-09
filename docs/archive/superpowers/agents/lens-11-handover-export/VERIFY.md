# VERIFY AGENT — Handover Export Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('handover_export' in p for p in paths)
print('✅ handover_export endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real handover export ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "handover" 2>/dev/null | grep "handover_export" | head -3
./celeste.sh search "crew handover" 2>/dev/null | grep "handover" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
EXPORT_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/handover_export/$EXPORT_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','yacht_id','review_status']:
    assert d.get(f) is not None, f'MISSING: {f}'
sections = d.get('sections', [])
assert isinstance(sections, list), 'sections must be a list'
print('✅ handover_export OK, review_status:', d['review_status'], 'sections:', len(sections))
"
```

---

## Verify camelCase alias present

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/handover_export/$EXPORT_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
assert 'userSignature' in d, 'MISSING: userSignature (camelCase alias required by frontend)'
print('✅ userSignature key present:', d.get('userSignature'))
"
```

---

## Frontend check

Search "handover" → click result with type `handover_export` → `/handover-export/{id}` loads.
Verify: sections list rendered, review status badge, signature fields, export button.

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "handover\|500\|error"
```

Common issues:
- `edited_content` may be `null` → `sections` defaults to `[]`, that is OK
- `edited_content` stored as jsonb string → use `json.loads()` if `isinstance(str)`
- Frontend expects `userSignature` (camelCase) — must return both `user_signature` and `userSignature`
- Route collision: `handover` vs `handover_export` — confirm search results use type `handover_export` not `handover`
