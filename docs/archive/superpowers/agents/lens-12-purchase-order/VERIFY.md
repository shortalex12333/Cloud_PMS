# VERIFY AGENT — Purchase Order Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('purchase_order' in p for p in paths)
print('✅ purchase_order endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real purchase order ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "purchase order" 2>/dev/null | grep "purchase_order" | head -3
./celeste.sh search "PO-" 2>/dev/null | grep "purchase" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
PO_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/purchase_order/$PO_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','po_number','status']:
    assert d.get(f) is not None, f'MISSING: {f}'
items = d.get('items', [])
assert isinstance(items, list), 'items must be a list'
print('✅ purchase_order OK, po_number:', d['po_number'], 'status:', d['status'], 'items:', len(items))
"
```

---

## Check line items

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/purchase_order/$PO_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
items = d.get('items', [])
if items:
    i = items[0]
    assert i.get('quantity_ordered') is not None, 'MISSING: quantity_ordered on item'
    print('✅ items OK, first item:', i.get('name'), 'qty:', i.get('quantity_ordered'))
else:
    print('⚠️  no items on this PO (may be valid)')
"
```

---

## Frontend check

Search "purchase order" or "PO-" → click → `/purchasing/{id}` loads.
Note: `/purchasing/[id]` is a CUSTOM page, NOT RouteShell. It has its own data fetch.
Verify: PO number, supplier, status badge, line items table, total amount.

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "purchase_order\|500\|error"
```

Common issues:
- `pms_purchase_order_items` join: query uses `purchase_order_id` = po_id (NOT `id`)
- `supplier_name` vs `vendor_name` → fallback handles this
- `total_amount` Decimal from PostgreSQL → serialises to float, OK
- The `/purchasing/[id]` page may have its OWN data fetcher separate from RouteShell — if endpoint works but page still 404s, check the page component's fetch URL
