# VERIFY AGENT — Receiving Lens

## Test

```bash
TOKEN=$(python3 /tmp/mint_jwt.py)
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "receiving" 2>/dev/null | grep "receiving" | head -3

RECV_ID=<paste-id>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/receiving/$RECV_ID | python3 -c "
import json,sys; d=json.load(sys.stdin)
assert d.get('status') is not None, 'CRITICAL: status missing — actions will not render'
for f in ['id','vendor_name','status']:
    assert d.get(f) is not None, f'MISSING: {f}'
print('✅ receiving OK, status:', d['status'])
"
```

## Frontend check

Search "receiving" → click → verify `/receiving/{id}` loads with vendor name + status + action buttons.
