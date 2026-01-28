# Shopping_List Feature Flags

**Purpose:** Gradual rollout and fail-closed behavior for Shopping_List lens features

**Philosophy:** All new features default to **OFF** on main branch. Features are enabled progressively:
1. **Local development:** Manual toggle for testing
2. **Staging canary:** Enable for one test yacht
3. **Staging full:** Enable for all staging yachts
4. **Production canary:** Enable for 10% of traffic
5. **Production rollout:** Gradually increase to 100%

**Fail-Closed Behavior:** When a feature flag is OFF, the system returns `503 FEATURE_DISABLED` instead of attempting the operation.

---

## Feature Flags


### 1. `SHOPPING_LIST_LENS_V1_ENABLED`

**Description:** Lens V1 Enabled

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Usage:**
```python
from integrations.feature_flags import SHOPPING_LIST_LENS_V1_ENABLED

if not SHOPPING_LIST_LENS_V1_ENABLED:
    raise HTTPException(
        status_code=503,
        detail={
            "status": "error",
            "error_code": "FEATURE_DISABLED",
            "message": "Shopping_List feature disabled (canary flag off)"
        }
    )
```

**Behavior:**
- `true`: Feature enabled
- `false`: Returns 503 FEATURE_DISABLED

---


## Environment Variables

Set these in Render dashboard (staging) or production environment:

```bash
# Shopping_List Flags
SHOPPING_LIST_LENS_V1_ENABLED=false  # Default OFF
```

**Staging Canary Configuration:**

```bash
# Enable for canary testing
SHOPPING_LIST_LENS_V1_ENABLED=true
```

---

## Toggle Procedures

### Enable Shopping_List (Canary)

1. **Render Dashboard → Environment**
   ```
   SHOPPING_LIST_LENS_V1_ENABLED=true
   ```

2. **Trigger Deployment**
   ```bash
   curl -X POST "https://api.render.com/deploy/srv-YOUR-SERVICE-ID?key=YOUR-KEY"
   ```

3. **Verify Deployment**
   ```bash
   curl -s https://pipeline-core.int.celeste7.ai/v1/actions/health | jq '.status'
   # Expected: "healthy"
   ```

4. **Test Feature Availability**
   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/suggestions \
     -H "Authorization: Bearer {JWT}" \
     -H "Content-Type: application/json" \
     -d '{"domain": "shopping_list"}'

   # Should return 200 with action suggestions (not 503)
   ```

---

### Disable Shopping_List (Rollback)

**Scenario:** Canary shows errors or performance issues.

1. **Render Dashboard → Environment**
   ```
   SHOPPING_LIST_LENS_V1_ENABLED=false
   ```

2. **Trigger Deployment** (same as above)

3. **Verify Rollback**
   ```bash
   # Expected: 503 FEATURE_DISABLED
   ```

---

## Monitoring

### Feature Flag Status (Startup Logs)

When the service starts, all feature flags are logged:

```
INFO:integrations.feature_flags:[FeatureFlags] SHOPPING_LIST_LENS_V1_ENABLED=True

```

**Check Logs:**
```bash
# Render dashboard → Logs tab
# Search for: [FeatureFlags]
```

---

## Current Status

**Shopping_List Flags (as of 2026-01-28):**

| Flag | Status | Ready for Canary |
|------|--------|------------------|
| `SHOPPING_LIST_LENS_V1_ENABLED` | OFF (main) | ⏳ Not tested |

**Recommended Canary Configuration:**
```bash
SHOPPING_LIST_LENS_V1_ENABLED=true
```

**Next Steps:**
1. Enable canary flags in staging
2. Monitor for 24h (0×500, P99 latency)
3. Expand to staging full
4. Enable production canary (10%)
5. Gradual rollout to 100%
