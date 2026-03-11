# VERIFY AGENT — Work Order Lens

**Your role:** Test the work order entity endpoint end-to-end. Backend curl → Docker logs → frontend lens check.

---

## Environment

- API: `http://localhost:8000`
- Frontend: `http://localhost:3002`
- Docker service: `celeste-api`
- Project root: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local/`

---

## Step 1: Get a real work order ID

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh search "work order" 2>/dev/null | grep "work_order" | head -5
```

---

## Step 2: Mint JWT + test endpoint

```python
# Save as /tmp/test_wo.py and run: python3 /tmp/test_wo.py <WORK_ORDER_ID>
import urllib.request, json, time, jwt, sys

WO_ID = sys.argv[1]
secret = 'wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw=='
skey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q'

req = urllib.request.Request('https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/admin/users?page=1&per_page=1')
req.add_header('apikey', skey)
req.add_header('Authorization', f'Bearer {skey}')
users = json.loads(urllib.request.urlopen(req).read()).get('users', [])
uid = users[0]['id']

token = jwt.encode({'sub': uid, 'aud': 'authenticated', 'role': 'authenticated',
    'iss': 'supabase', 'iat': int(time.time()), 'exp': int(time.time()) + 3600},
    secret, algorithm='HS256')

req2 = urllib.request.Request(f'http://localhost:8000/v1/entity/work_order/{WO_ID}')
req2.add_header('Authorization', f'Bearer {token}')
data = json.loads(urllib.request.urlopen(req2).read())
print(json.dumps(data, indent=2))

# Verify required fields
for field in ['id', 'title', 'status', 'notes', 'parts', 'checklist']:
    assert field in data, f"MISSING FIELD: {field}"
assert isinstance(data['notes'], list), "notes must be array"
print("✅ ALL CHECKS PASSED")
```

---

## Step 3: Check Docker logs if 500

```bash
docker logs celeste-api --tail=50 2>&1 | grep -i "error\|500\|work_order"
```

---

## Step 4: Frontend verification

Open `http://localhost:3002`, search "work order", click a result.
Expected: `/work-orders/{id}` route loads with title, status badge, and sections visible.
Failure: "Failed to Load" error state with retry button.

---

## Rebuild command (if code changed)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
docker compose up --build -d api && docker logs -f celeste-api --tail=20
```
