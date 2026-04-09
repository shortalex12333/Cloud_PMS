# VERIFY AGENT — Part / Inventory Lens

## Test

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "oil filter" 2>/dev/null | grep "part\|inventory" | head -3

PART_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/part/$PART_ID | python3 -m json.tool
```

## Expected fields

`id`, `part_name`, `stock_quantity`, `min_stock_level`, `location`

## Also test inventory route (same endpoint)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/part/$PART_ID | python3 -c "
import json,sys; d=json.load(sys.stdin)
for f in ['id','part_name','stock_quantity']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ part endpoint OK')
"
```

## Frontend check

Search "oil filter" → click → verify `/inventory/{id}` loads with part name + stock level visible.
