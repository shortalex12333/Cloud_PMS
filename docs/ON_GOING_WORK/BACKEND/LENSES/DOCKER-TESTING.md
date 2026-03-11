# Docker Local-First Testing — Entity Lenses

**Last Updated:** 2026-03-02

---

## Philosophy

**Remote platforms hide information. Local Docker reveals everything.**

| Approach | Cost | Debug Visibility | Iteration Speed |
|----------|------|------------------|-----------------|
| Remote (Render/Vercel) | $7+/month | 10% (logs only) | 5-10 min |
| **Local Docker (Mac Studio)** | **$0** | **100%** | **10-30 sec** |

**WHY Local First:**
- Claude can inspect container logs in real-time
- No deployment delays between iterations
- Full filesystem access for debugging
- Zero cost for unlimited testing

---

## Quick Start

### Start API Locally

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Build and start API
docker compose -f docker-compose.local.yml build api --no-cache
docker compose -f docker-compose.local.yml up api -d

# Check health
curl http://localhost:8000/health
```

### Expected Output

```json
{"status":"healthy","version":"1.0.0","pipeline_ready":false}
```

---

## Available Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Development with volume mounts |
| `docker-compose.local.yml` | Local testing (code baked in) |
| `docker-compose.f1-workers.yml` | F1 search workers |

---

## Testing Action Endpoints

### Test /execute Endpoint

```bash
# Create work order (requires JWT)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "action": "create_work_order",
    "context": {"yacht_id": "uuid"},
    "payload": {
      "title": "Test Work Order",
      "type": "corrective",
      "priority": "routine"
    }
  }'
```

### Test /prepare Endpoint (After GAP-001 Fix)

```bash
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{
    "q": "create urgent work order for main engine next week",
    "domain": "work_orders",
    "context": {"yacht_id": "uuid"},
    "client": {"timezone": "America/New_York", "now_iso": "2026-03-02T10:00:00-05:00"}
  }'
```

### Expected /prepare Response

```json
{
  "action_id": "create_work_order",
  "match_score": 0.95,
  "ready_to_commit": false,
  "prefill": {
    "equipment_id": {"value": "uuid", "confidence": 0.92, "source": "entity_resolver"},
    "priority": {"value": "HIGH", "confidence": 0.95, "source": "keyword_map"},
    "scheduled_date": {"value": "2026-03-09", "confidence": 0.85, "source": "temporal"}
  },
  "missing_required_fields": ["description"],
  "ambiguities": [],
  "errors": [],
  "role_blocked": false,
  "blocked_reason": null
}
```

---

## Lens-Specific Tests

### Work Order Lens

```bash
# Create work order
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <HOD_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_work_order",
    "context": {"yacht_id": "uuid"},
    "payload": {"title": "Test", "type": "corrective", "priority": "routine"}
  }'
# Expected: 200, returns work_order_id

# Add note (crew can do this)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <CREW_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_work_order_note",
    "context": {"yacht_id": "uuid", "work_order_id": "uuid"},
    "payload": {"text": "Test note"}
  }'
# Expected: 200
```

### Equipment Lens

```bash
# Update status (engineer+)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <ENGINEER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_equipment_status",
    "context": {"yacht_id": "uuid", "equipment_id": "uuid"},
    "payload": {"status": "maintenance", "attention_reason": "Scheduled service"}
  }'
# Expected: 200

# Add note (all crew)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <CREW_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_equipment_note",
    "context": {"yacht_id": "uuid", "equipment_id": "uuid"},
    "payload": {"text": "Observation"}
  }'
# Expected: 200

# Decommission (signed, captain/manager only)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <CAPTAIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "decommission_equipment",
    "context": {"yacht_id": "uuid", "equipment_id": "uuid"},
    "payload": {
      "reason": "Beyond repair",
      "signature": {
        "user_id": "uuid",
        "role_at_signing": "captain",
        "signature_type": "decommission_equipment",
        "reason": "Beyond repair",
        "signature_hash": "sha256:...",
        "signed_at": "2026-03-02T10:30:00Z"
      }
    }
  }'
# Expected: 200
```

### Certificate Lens

```bash
# Create vessel certificate (HOD)
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <HOD_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_vessel_certificate",
    "context": {"yacht_id": "uuid"},
    "payload": {
      "certificate_type": "class",
      "certificate_name": "Lloyd Register Class Certificate",
      "issuing_authority": "Lloyd Register",
      "expiry_date": "2027-01-15"
    }
  }'
# Expected: 200 (HOD), 403 (Crew)
```

---

## Role Gating Tests

### Test Role Blocked

```bash
# Crew cannot update equipment status
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <CREW_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_equipment_status",
    "context": {"yacht_id": "uuid", "equipment_id": "uuid"},
    "payload": {"status": "operational"}
  }'
# Expected: 403 Forbidden

# Crew cannot create certificate
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <CREW_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_vessel_certificate",
    "context": {"yacht_id": "uuid"},
    "payload": {"certificate_type": "class", "certificate_name": "Test", "issuing_authority": "Test"}
  }'
# Expected: 403 Forbidden
```

### Test Yacht Isolation

```bash
# User from Yacht A cannot access Yacht B's equipment
curl -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer <YACHT_A_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_equipment_status",
    "context": {"yacht_id": "YACHT_B_ID", "equipment_id": "uuid"},
    "payload": {"status": "operational"}
  }'
# Expected: 404 Not Found (RLS blocks access)
```

---

## Observability Commands

### Real-Time Monitoring

```bash
# Watch ALL container stats
docker stats

# Follow API logs
docker logs -f back_button_cloud_pms-api-1

# Watch for errors only
docker logs -f back_button_cloud_pms-api-1 2>&1 | grep -i error

# Watch for SQL queries
docker logs -f back_button_cloud_pms-api-1 2>&1 | grep -i "select\|insert\|update"
```

### Debugging

```bash
# Exec into container
docker exec -it back_button_cloud_pms-api-1 /bin/bash

# Check environment
docker exec back_button_cloud_pms-api-1 env

# Check processes
docker exec back_button_cloud_pms-api-1 ps aux

# Check file system
docker exec back_button_cloud_pms-api-1 ls -la /app

# Check action registry
docker exec back_button_cloud_pms-api-1 python3 -c "
from action_router.registry import ACTION_REGISTRY
for k in sorted(ACTION_REGISTRY.keys()): print(k)
"
```

### Health & Status

```bash
# Container health
docker inspect --format='{{json .State.Health}}' back_button_cloud_pms-api-1 | jq

# Exit code (why did it crash?)
docker inspect --format='{{.State.ExitCode}}' back_button_cloud_pms-api-1

# Resource usage
docker system df -v
```

---

## RLS Verification Tests

### Check RLS Enabled

```bash
# Connect to Supabase and run:
docker exec back_button_cloud_pms-api-1 python3 -c "
import asyncio
from supabase import create_client
# ... verify RLS enabled on tables
"

# Or via psql
psql -c "
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN (
    'pms_work_orders', 'pms_work_order_notes', 'pms_equipment',
    'pms_vessel_certificates', 'pms_crew_certificates', 'pms_faults'
);
"
# All should show relrowsecurity = true
```

### Check Policy Count

```bash
psql -c "
SELECT tablename, COUNT(*) AS policy_count
FROM pg_policies
WHERE tablename LIKE 'pms_%'
GROUP BY tablename
ORDER BY tablename;
"
# Should show 3+ policies per critical table
```

---

## Cleanup

```bash
# Stop containers
docker compose -f docker-compose.local.yml down

# Stop and remove volumes
docker compose -f docker-compose.local.yml down -v

# Remove images
docker rmi back_button_cloud_pms-api:latest

# Full cleanup (all Docker resources)
docker system prune -af
```

---

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker logs back_button_cloud_pms-api-1 --tail 100

# Common issues:
# 1. Missing env vars (SUPABASE_URL, etc.)
# 2. Port already in use: lsof -i :8000
# 3. Build failed: docker compose build api 2>&1 | tail -50
```

### /prepare Returns 404

```bash
# Check if route registered
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
print([p for p in d.get('paths',{}).keys() if 'prepare' in p.lower()])
"

# If empty: GAP-001 not fixed
# If shows route: check JWT/auth
```

### 403 Forbidden

```bash
# Check JWT claims
echo $JWT | cut -d'.' -f2 | base64 -d 2>/dev/null | jq

# Verify:
# - user_metadata.role is correct
# - yacht_id matches context
```

### 500 Internal Server Error

```bash
# NEVER acceptable - investigate immediately
docker logs back_button_cloud_pms-api-1 2>&1 | grep -A 10 "500\|error\|traceback"

# Check handler code for bugs
```

---

## Integration with GSD

```bash
# Before executing any phase
docker compose -f docker-compose.local.yml up api -d
sleep 10
curl http://localhost:8000/health  # Verify healthy

# Execute phase
/gsd:execute-phase 16.1

# Verify locally
curl -X POST http://localhost:8000/v1/actions/prepare ...

# Run E2E tests locally (optional)
E2E_BASE_URL=http://localhost:3000 npx playwright test --project=shard-8-workorders

# Only then push to remote
git push
```

---

## Common Test JWTs

Store these in environment for repeated testing:

```bash
# Create test tokens (replace with actual values)
export HOD_JWT="..."
export CREW_JWT="..."
export CAPTAIN_JWT="..."
export ENGINEER_JWT="..."

# Use in tests
curl -H "Authorization: Bearer $HOD_JWT" ...
```

---

*See also: OVERVIEW.md, GAPS.md, AGENT-ONBOARDING.md*
