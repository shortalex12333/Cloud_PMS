# CelesteOS Feature Flags

**Purpose:** Gradual rollout and fail-closed behavior for new features.

**Philosophy:** All new features default to **OFF** on main branch. Features are enabled progressively:
1. **Local development:** Manual toggle for testing
2. **Staging canary:** Enable for one test yacht
3. **Staging full:** Enable for all staging yachts
4. **Production canary:** Enable for 10% of traffic
5. **Production rollout:** Gradually increase to 100%

**Fail-Closed Behavior:** When a feature flag is OFF, the system returns `503 FEATURE_DISABLED` instead of attempting the operation. This prevents partial failures and makes flag state visible in monitoring.

---

## Fault Lens v1 Feature Flags

### Master Flag

#### `FAULT_LENS_V1_ENABLED`

**Description:** Master gate for all Fault Lens v1 features. When OFF, all fault-related endpoints return 503.

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Usage:**
```python
from integrations.feature_flags import FAULT_LENS_V1_ENABLED, check_fault_lens_feature

# Check master flag
if not FAULT_LENS_V1_ENABLED:
    raise HTTPException(
        status_code=503,
        detail={
            "status": "error",
            "error_code": "FEATURE_DISABLED",
            "message": "Fault Lens v1 is disabled (canary flag off)"
        }
    )
```

**Behavior:**
- `true`: All Fault Lens v1 features available (subject to individual flags)
- `false`: All fault endpoints return 503 FEATURE_DISABLED

**Rollout Plan:**
- **Main:** `false` (default)
- **Staging Canary:** `true` (one test yacht)
- **Staging Full:** `true` (after canary verification)
- **Production Canary:** `true` (10% traffic)
- **Production Full:** `true` (after 48h green metrics)

---

### Individual Feature Flags

These flags provide **granular control** within Fault Lens v1. They only apply when `FAULT_LENS_V1_ENABLED=true`.

#### `FAULT_LENS_SUGGESTIONS_ENABLED`

**Description:** POST /v1/actions/suggestions endpoint for action discovery.

**Default:** `false`

**Enables:**
- Action suggestions based on query text
- Role-based action filtering
- Context gating (entity_type/entity_id requirements)
- Storage path preview for upload actions

**503 Response When Disabled:**
```json
{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "Fault Lens feature 'suggestions' is disabled"
}
```

**Rollout:** Enable alongside `FAULT_LENS_V1_ENABLED` (no separate canary needed)

---

#### `FAULT_LENS_SIGNED_ACTIONS_ENABLED`

**Description:** SIGNED actions requiring PIN+TOTP signature payload.

**Default:** `false`

**Enables:**
- `create_work_order_from_fault` (captain/manager signature required)
- `reassign_work_order` (manager signature required)
- `archive_work_order` (captain signature required)

**Validation When Enabled:**
- Missing signature → 400 signature_required
- Invalid signature structure → 400 invalid_signature
- Invalid signer role → 403 invalid_signer_role
- Valid signature → 200 + audit log entry

**503 Response When Disabled:**
```json
{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "Fault Lens feature 'signed_actions' is disabled"
}
```

**Rollout:** Enable after signatures tested in staging (requires mobile app PIN flow)

---

#### `FAULT_LENS_RELATED_ENABLED`

**Description:** Related entities endpoint (faults → work orders, equipment, parts).

**Default:** `false`

**Enables:**
- GET /v1/faults/{fault_id}/related
- Cross-entity relationship queries
- Fault → Work Order linkage
- Fault → Equipment history

**503 Response When Disabled:**
```json
{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "Fault Lens feature 'related' is disabled"
}
```

**Rollout:** Enable after Show Related testing complete (deferred to post-v1)

---

#### `FAULT_LENS_WARRANTY_ENABLED`

**Description:** Warranty status checks for fault-equipment relationships.

**Default:** `false`

**Enables:**
- Warranty expiration warnings
- Warranty claim suggestions
- Equipment warranty lookups

**503 Response When Disabled:**
```json
{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "Fault Lens feature 'warranty' is disabled"
}
```

**Rollout:** Enable after warranty data migration (deferred to post-v1)

---

## Environment Variables

Set these in Render dashboard (staging) or production environment:

```bash
# Fault Lens v1 Flags
FAULT_LENS_V1_ENABLED=false                  # Master gate (default OFF)
FAULT_LENS_SUGGESTIONS_ENABLED=false         # Suggestions API (default OFF)
FAULT_LENS_SIGNED_ACTIONS_ENABLED=false      # Signed actions (default OFF)
FAULT_LENS_RELATED_ENABLED=false             # Related entities (default OFF)
FAULT_LENS_WARRANTY_ENABLED=false            # Warranty checks (default OFF)
```

**Staging Canary Configuration:**

```bash
# Enable for canary testing
FAULT_LENS_V1_ENABLED=true
FAULT_LENS_SUGGESTIONS_ENABLED=true
FAULT_LENS_SIGNED_ACTIONS_ENABLED=true
FAULT_LENS_RELATED_ENABLED=false  # Not yet tested
FAULT_LENS_WARRANTY_ENABLED=false # Not yet tested
```

---

## Toggle Procedures

### Enable Fault Lens v1 (Canary)

1. **Render Dashboard → Environment**
   ```
   FAULT_LENS_V1_ENABLED=true
   FAULT_LENS_SUGGESTIONS_ENABLED=true
   FAULT_LENS_SIGNED_ACTIONS_ENABLED=true
   ```

2. **Trigger Deployment**
   ```bash
   curl -X POST "https://api.render.com/deploy/srv-d5fr5hre5dus73d3gdn0?key=Dcmb-n4O_M0"
   ```

3. **Verify Deployment**
   ```bash
   curl -s https://pipeline-core.int.celeste7.ai/v1/actions/health | jq '.status'
   # Expected: "healthy"
   ```

4. **Test Feature Availability**
   ```bash
   # Test suggestions endpoint
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/suggestions \
     -H "Authorization: Bearer {JWT}" \
     -H "Content-Type: application/json" \
     -d '{"domain": "faults"}'

   # Should return 200 with action suggestions (not 503)
   ```

---

### Disable Fault Lens v1 (Rollback)

**Scenario:** Canary shows errors or performance issues.

1. **Render Dashboard → Environment**
   ```
   FAULT_LENS_V1_ENABLED=false
   ```

2. **Trigger Deployment**
   ```bash
   curl -X POST "https://api.render.com/deploy/srv-d5fr5hre5dus73d3gdn0?key=Dcmb-n4O_M0"
   ```

3. **Verify Rollback**
   ```bash
   # Test fault endpoints
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/suggestions \
     -H "Authorization: Bearer {JWT}" \
     -H "Content-Type: application/json" \
     -d '{"domain": "faults"}'

   # Expected: 503 FEATURE_DISABLED
   ```

4. **Monitor Logs**
   ```bash
   # Verify logs show feature disabled
   # Expected: [FeatureFlags] FAULT_LENS_V1_ENABLED=False
   ```

---

## Monitoring

### Feature Flag Status (Startup Logs)

When the service starts, all feature flags are logged:

```
INFO:integrations.feature_flags:[FeatureFlags] FAULT_LENS_V1_ENABLED=True
INFO:integrations.feature_flags:[FeatureFlags] FAULT_LENS_SUGGESTIONS_ENABLED=True
INFO:integrations.feature_flags:[FeatureFlags] FAULT_LENS_RELATED_ENABLED=False
INFO:integrations.feature_flags:[FeatureFlags] FAULT_LENS_WARRANTY_ENABLED=False
INFO:integrations.feature_flags:[FeatureFlags] FAULT_LENS_SIGNED_ACTIONS_ENABLED=True
```

**Check Logs:**
```bash
# Render dashboard → Logs tab
# Search for: [FeatureFlags]
```

### Feature Disabled Errors (Runtime)

When a feature is disabled, the API returns structured 503 errors:

```json
{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "Fault Lens v1 is disabled (canary flag off)"
}
```

**Monitor 503 Rate:**
- **Expected:** 0% when feature is enabled
- **Alert:** If 503 rate > 0% after enabling flag → deployment failed

**Metrics to Track:**
- `http_requests_total{status_code="503", error_code="FEATURE_DISABLED"}`
- `feature_flag_status{flag="FAULT_LENS_V1_ENABLED"}`

---

## Code Implementation

**File:** `apps/api/integrations/feature_flags.py`

```python
"""
CelesteOS Backend - Feature Flags

Feature flags for gradual rollout and fail-closed behavior.
All features default to OFF.
"""

import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FAULT LENS V1 FLAGS (default: OFF - fail-closed)
# ============================================================================

# Master canary flag for Fault Lens v1
# Set to 'true' ONLY for canary yacht during initial rollout
FAULT_LENS_V1_ENABLED = os.getenv('FAULT_LENS_V1_ENABLED', 'false').lower() == 'true'

# Individual feature flags for granular control
FAULT_LENS_SUGGESTIONS_ENABLED = os.getenv('FAULT_LENS_SUGGESTIONS_ENABLED', 'false').lower() == 'true'
FAULT_LENS_RELATED_ENABLED = os.getenv('FAULT_LENS_RELATED_ENABLED', 'false').lower() == 'true'
FAULT_LENS_WARRANTY_ENABLED = os.getenv('FAULT_LENS_WARRANTY_ENABLED', 'false').lower() == 'true'
FAULT_LENS_SIGNED_ACTIONS_ENABLED = os.getenv('FAULT_LENS_SIGNED_ACTIONS_ENABLED', 'false').lower() == 'true'

logger.info(f"[FeatureFlags] FAULT_LENS_V1_ENABLED={FAULT_LENS_V1_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_SUGGESTIONS_ENABLED={FAULT_LENS_SUGGESTIONS_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_RELATED_ENABLED={FAULT_LENS_RELATED_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_WARRANTY_ENABLED={FAULT_LENS_WARRANTY_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_SIGNED_ACTIONS_ENABLED={FAULT_LENS_SIGNED_ACTIONS_ENABLED}")


def check_fault_lens_feature(feature_name: str) -> tuple[bool, str]:
    """
    Check if a Fault Lens feature is enabled.
    Returns (enabled, error_message).

    Fail-closed: if master switch is off, all features are disabled.
    """
    if not FAULT_LENS_V1_ENABLED:
        return False, "Fault Lens v1 is disabled (canary flag off)"

    flags = {
        'suggestions': FAULT_LENS_SUGGESTIONS_ENABLED,
        'related': FAULT_LENS_RELATED_ENABLED,
        'warranty': FAULT_LENS_WARRANTY_ENABLED,
        'signed_actions': FAULT_LENS_SIGNED_ACTIONS_ENABLED,
    }

    enabled = flags.get(feature_name, False)
    if not enabled:
        return False, f"Fault Lens feature '{feature_name}' is disabled"

    return True, ""
```

**Usage in Router:**

```python
from integrations.feature_flags import check_fault_lens_feature

@router.post("/suggestions")
async def get_suggestions(request_data: SuggestionsRequest, ...):
    # Feature flag check for faults domain
    if request_data.domain == "faults":
        enabled, message = check_fault_lens_feature("suggestions")
        if not enabled:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "error",
                    "error_code": "FEATURE_DISABLED",
                    "message": message,
                },
            )
    # ... rest of endpoint logic
```

---

## Best Practices

### 1. Fail-Closed by Default

All new features start with flags OFF. This prevents:
- Accidental production rollouts
- Partial feature deployments
- Untested code in production

### 2. Granular Control

Use individual flags within master gates:
- Master flag: Broad enable/disable (e.g., entire lens)
- Individual flags: Fine-grained control (e.g., specific endpoints)

### 3. Structured Error Responses

Always return 503 with `error_code: "FEATURE_DISABLED"`:
- Distinguishes from other 5xx errors
- Makes monitoring easier
- Clear signal for rollback

### 4. Logging

Log flag status on startup:
- Confirms deployment state
- Aids debugging
- Verifies environment variables loaded

### 5. Monitoring

Track 503 FEATURE_DISABLED separately:
- Not an error when flag is intentionally off
- IS an error when flag should be on

---

## Rollback Decision Tree

```
Is feature showing errors?
├─ Yes → Disable master flag immediately
│         Wait for deployment
│         Verify 503 responses
│         Investigate errors offline
│
└─ No → Is performance degraded?
    ├─ Yes → Check if specific feature is causing it
    │         Disable individual flag
    │         Monitor metrics
    │
    └─ No → Continue canary
            Monitor for 24-48h
            Expand rollout
```

---

## Feature Flag Lifecycle

1. **Development:** Feature flag added (default OFF)
2. **Testing:** Manually enabled in local/staging
3. **Canary:** Master flag enabled for 10% traffic
4. **Rollout:** Gradual increase (10% → 50% → 100%)
5. **Stabilization:** Monitor for 48h at 100%
6. **Flag Removal:** After 30 days at 100%, remove flag from code

**Flag Retention:** Keep flags for 30 days after 100% rollout to allow quick rollback if issues emerge.

---

## Current Status

**Fault Lens v1 Flags (as of 2026-01-28):**

| Flag | Status | Ready for Canary |
|------|--------|------------------|
| `FAULT_LENS_V1_ENABLED` | OFF (main) | ✅ Yes |
| `FAULT_LENS_SUGGESTIONS_ENABLED` | OFF (main) | ✅ Yes |
| `FAULT_LENS_SIGNED_ACTIONS_ENABLED` | OFF (main) | ✅ Yes |
| `FAULT_LENS_RELATED_ENABLED` | OFF (main) | ⏳ Not tested |
| `FAULT_LENS_WARRANTY_ENABLED` | OFF (main) | ⏳ Not tested |

**Recommended Canary Configuration:**
```bash
FAULT_LENS_V1_ENABLED=true
FAULT_LENS_SUGGESTIONS_ENABLED=true
FAULT_LENS_SIGNED_ACTIONS_ENABLED=true
FAULT_LENS_RELATED_ENABLED=false
FAULT_LENS_WARRANTY_ENABLED=false
```

**Next Steps:**
1. Enable canary flags in staging
2. Monitor for 24h (0×500, P99 latency)
3. Expand to staging full
4. Enable production canary (10%)
5. Gradual rollout to 100%
