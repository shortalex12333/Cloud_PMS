# VERIFY AGENT — Certificate Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('certificate' in p for p in paths)
print('✅ certificate endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real certificate ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "SOLAS certificate" 2>/dev/null | grep "certificate" | head -3
./celeste.sh search "STCW" 2>/dev/null | grep "certificate" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
CERT_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/certificate/$CERT_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','name','certificate_type','expiry_date']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ certificate OK, type:', d['certificate_type'], 'domain:', d.get('domain'))
"
```

---

## Frontend check

Search "certificate" → click → `/certificates/{id}` loads.
Verify: certificate name, type, issuing authority, expiry date visible.
If 404 in search results for certificate type → the vessel/crew fallback may need checking.

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "certif\|500\|error"
```

Common issues:
- `maybe_single()` vs `.single()` → use `maybe_single()` to avoid 204 errors
- `properties` is stored as string not dict → `json.loads()` needed
- Column `certificate_name` vs `name` — vessel table uses `certificate_name`, not `name`
