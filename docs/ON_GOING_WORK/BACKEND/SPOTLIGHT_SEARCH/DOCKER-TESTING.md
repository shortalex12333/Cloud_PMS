# Docker Local-First Testing — Spotlight Search

**Last Updated:** 2026-03-02

---

## Philosophy

**Remote platforms hide information. Local Docker reveals everything.**

| Approach | Cost | Debug Visibility | Iteration Speed |
|----------|------|------------------|-----------------|
| Remote (Render/Vercel) | $7+/month | 10% (logs only) | 5-10 min |
| **Local Docker (Mac Studio)** | **$0** | **100%** | **10-30 sec** |

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

## Testing /prepare Endpoint (After GAP-001 Fix)

### Basic Test

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

### Expected Response

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

## Observability Commands

### Real-Time Monitoring

```bash
# Watch ALL container stats
docker stats

# Follow API logs
docker logs -f back_button_cloud_pms-api-1

# Watch for errors only
docker logs -f back_button_cloud_pms-api-1 2>&1 | grep -i error
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

## Test Scenarios

### Scenario 1: Temporal Parsing

```bash
# Test "tomorrow"
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order for tomorrow", "domain": "work_orders"}'
# Expected: scheduled_date = +1 day, confidence = 0.95

# Test "next week"
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create work order next week", "domain": "work_orders"}'
# Expected: scheduled_date = Monday of NEXT week, confidence = 0.85
```

### Scenario 2: Priority Mapping

```bash
# Test "urgent"
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create urgent work order", "domain": "work_orders"}'
# Expected: priority.value = "HIGH", confidence = 0.95

# Test "critical"
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -d '{"q": "create critical fault", "domain": "faults"}'
# Expected: severity.value = "EMERGENCY", confidence = 0.95
```

### Scenario 3: Role Gating

```bash
# Test with crew role (blocked action)
curl -X POST http://localhost:8000/v1/actions/prepare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <CREW_JWT>" \
  -d '{"q": "delete work order", "domain": "work_orders"}'
# Expected: role_blocked = true, blocked_reason = "Requires Captain role"
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
```

---

## Troubleshooting

### API Not Starting

```bash
# Check logs
docker logs back_button_cloud_pms-api-1 --tail 100

# Common issues:
# 1. Missing env vars (SUPABASE_URL, etc.)
# 2. Port already in use (lsof -i :8000)
# 3. Build failed (docker compose build api 2>&1 | tail -50)
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

### Health Check Failing

```bash
# Check health endpoint directly
curl -v http://localhost:8000/health

# Check container logs for errors
docker logs back_button_cloud_pms-api-1 2>&1 | grep -i "error\|failed\|exception"
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

# Only then push to remote
git push
```

---

*See also: OVERVIEW.md, GAPS.md, QUICK-REFERENCE.md*
