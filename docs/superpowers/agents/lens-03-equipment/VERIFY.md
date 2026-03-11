# VERIFY AGENT — Equipment Lens

**Your role:** Test equipment endpoint + frontend.

## JWT mint

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)  # See lens-02-fault/VERIFY.md for script
```

## Test

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "main engine" 2>/dev/null | grep "equipment" | head -3

EQUIP_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/equipment/$EQUIP_ID | python3 -m json.tool
```

## Expected fields

`id`, `name`, `status`, `manufacturer`, `model`, `location`

## Frontend check

Search "equipment" → click → verify `/equipment/{id}` loads with name + status + running hours visible.

## Debug

```bash
docker logs celeste-api --tail=30 | grep -i "equipment\|error"
```
