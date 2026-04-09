# VERIFY AGENT — Shopping List Lens

**Your role:** After DATA agent creates the endpoint and Docker is rebuilt — test it.

---

## Pre-check: Endpoint registered?

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import json,sys; paths=json.load(sys.stdin).get('paths',{})
found = any('shopping_list' in p for p in paths)
print('✅ shopping_list endpoint registered' if found else '❌ NOT registered')
"
```

---

## Get real shopping list item ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "oil filter" 2>/dev/null | grep "shopping_list" | head -3
./celeste.sh search "spare part" 2>/dev/null | grep "shopping_list" | head -3
```

---

## Test endpoint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
ITEM_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/shopping_list/$ITEM_ID | python3 -c "
import json,sys
d = json.load(sys.stdin)
for f in ['id','title','status']:
    assert d.get(f) is not None, f'MISSING: {f}'
items = d.get('items', [])
assert len(items) == 1, f'items must have exactly 1 element, got {len(items)}'
print('✅ shopping_list OK, title:', d['title'], 'status:', d['status'])
print('   item:', items[0].get('part_name'), 'qty:', items[0].get('quantity_requested'))
"
```

---

## Frontend check

Search a part name that appears in shopping list → click result with type `shopping_list` → `/shopping-list/{id}` loads.
Verify: part name visible, quantity, urgency badge, status badge, action buttons (approve/reject for HOD).

---

## Debug 500s

```bash
docker logs celeste-api --tail=30 | grep -i "shopping\|500\|error"
```

Common issues:
- The `id` in search results is a `pms_shopping_list_items.id`, NOT a list header ID — confirm by checking the search result `entity_type` = `shopping_list`
- `quantity_requested` may be Decimal → serialises to float, OK
- `urgency` column may not exist in older schema → use `.get("urgency")` with None default
