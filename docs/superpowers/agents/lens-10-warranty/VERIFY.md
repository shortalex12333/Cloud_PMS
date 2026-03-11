# VERIFY AGENT — Warranty Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('warranty' in p for p in paths)
print('✅ warranty endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real warranty ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "warranty" 2>/dev/null | grep "warranty" | head -3
./celeste.sh search "engine warranty" 2>/dev/null | grep "warranty" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
WRN_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/warranty/$WRN_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','title','status']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ warranty OK, title:', d['title'], 'status:', d['status'], 'expiry:', d.get('expiry_date'))
"
```

---

## Check column name fallbacks

```bash
# Inspect raw response to confirm supplier/expiry_date resolved correctly
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/warranty/$WRN_ID | python3 -m json.tool
```

If `supplier` is null but there is data in the DB, the column is named differently.
Check in Supabase: `SELECT column_name FROM information_schema.columns WHERE table_name = 'pms_warranties';`

---

## Frontend check

Search "warranty" → click → `/warranty/{id}` loads.
Verify: warranty number, equipment name, supplier, expiry date, status badge, action buttons (HOD only).

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "warranty\|500\|error"
```

Common issues:
- Column name mismatch (`supplier` vs `supplier_name`) — check DB schema with `SELECT *` to see actual columns
- `expiry_date` vs `end_date` — use fallback in code: `data.get("expiry_date") or data.get("end_date")`
- `void_warranty` action in frontend requires `manager` role — verify role gate in lens_matrix.json
