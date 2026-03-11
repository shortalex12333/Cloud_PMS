# VERIFY AGENT — Hours of Rest Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('hours_of_rest' in p for p in paths)
print('✅ hours_of_rest endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real hours-of-rest record ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "hours of rest" 2>/dev/null | grep "hours_of_rest\|rest" | head -3
./celeste.sh search "rest record" 2>/dev/null | grep "hours" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
HOR_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/hours_of_rest/$HOR_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','date','total_rest_hours','is_compliant']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ hours_of_rest OK, date:', d['date'], 'compliant:', d['is_compliant'], 'status:', d.get('status'))
"
```

---

## Verify rest_periods parsing

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/hours_of_rest/$HOR_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
rp = d.get('rest_periods', [])
assert isinstance(rp, list), f'rest_periods must be a list, got {type(rp)}'
print('✅ rest_periods OK, count:', len(rp))
if rp:
    assert 'start' in rp[0] or 'hours' in rp[0], 'rest_periods items missing start/hours keys'
    print('   first period:', rp[0])
"
```

---

## Frontend check

Search "hours of rest" → click → `/hours-of-rest/{id}` loads.
Verify: date visible, total rest hours, compliance status badge (green/red), rest periods timeline.

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "hours_of_rest\|500\|error"
```

Common issues:
- `rest_periods` stored as JSON string in DB → use `json.loads()` if `isinstance(str)` check fails
- `total_rest_hours` may be Decimal type from PostgreSQL → Python will serialise as float, OK
- `is_daily_compliant` may be null if record is incomplete — `status` should return `"unknown"` not crash
