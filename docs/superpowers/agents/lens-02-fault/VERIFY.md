# VERIFY AGENT — Fault Lens

**Your role:** Test fault endpoint + verify frontend lens loads.

---

## Environment

- API: `http://localhost:8000`
- Frontend: `http://localhost:3002`

## JWT Script (reuse across all verify agents)

```python
# /tmp/mint_jwt.py
import urllib.request, json, time, jwt

secret = 'wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw=='
skey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q'
req = urllib.request.Request('https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/admin/users?page=1&per_page=1')
req.add_header('apikey', skey); req.add_header('Authorization', f'Bearer {skey}')
uid = json.loads(urllib.request.urlopen(req).read())['users'][0]['id']
token = jwt.encode({'sub': uid, 'aud': 'authenticated', 'role': 'authenticated',
    'iss': 'supabase', 'iat': int(time.time()), 'exp': int(time.time()) + 3600},
    secret, algorithm='HS256')
print(token)
```

## Test Fault Endpoint

```bash
# 1. Get fault ID from search
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "fault" 2>/dev/null | grep "fault" | head -3

# 2. Test endpoint
TOKEN=$(python3 /tmp/mint_jwt.py)
FAULT_ID=<paste-id-from-step-1>
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/entity/fault/$FAULT_ID | python3 -m json.tool
```

## Expected response fields

Must contain: `id`, `title`, `severity`, `status`, `equipment_name`, `reporter`

## Frontend check

Search "fault" or "main engine fault" → click result → verify `/faults/{id}` loads with title + severity badge.

## Debug

```bash
docker logs celeste-api --tail=30 | grep -i "fault\|error"
```
