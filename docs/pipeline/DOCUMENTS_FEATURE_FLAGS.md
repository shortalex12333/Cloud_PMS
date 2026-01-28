# Documents Feature Flags

**Purpose:** Gradual rollout and fail-closed behavior for Document Lens v2 features

**Philosophy:** All new features default to **OFF** on main branch. Features are enabled progressively:
1. **Local development:** Manual toggle for testing
2. **Staging canary:** Enable for one test yacht
3. **Staging full:** Enable for all staging yachts
4. **Production canary:** Enable for 10% of traffic
5. **Production rollout:** Gradually increase to 100%

**Fail-Closed Behavior:** When a feature flag is OFF, the system returns `503 FEATURE_DISABLED` instead of attempting the operation.

---

## Feature Flags

### 1. `DOCUMENT_LENS_V2_ENABLED`

**Description:** Document Lens V2 Enabled

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Usage:**
```python
from integrations.feature_flags import DOCUMENT_LENS_V2_ENABLED

if not DOCUMENT_LENS_V2_ENABLED:
    raise HTTPException(
        status_code=503,
        detail={
            "status": "error",
            "error_code": "FEATURE_DISABLED",
            "message": "Documents feature disabled (canary flag off)"
        }
    )
```

**Behavior:**
- `true`: Feature enabled
- `false`: Returns 503 FEATURE_DISABLED

---

### 2. `DOCUMENT_LENS_SUGGESTIONS_ENABLED`

**Description:** Document Lens Suggestions Enabled

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Behavior:**
- `true`: Suggestions endpoint returns document actions
- `false`: Returns 503 FEATURE_DISABLED

---

### 3. `DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED`

**Description:** Document Lens Signed Actions Enabled

**Default:** `false` (OFF on main branch)

**Type:** Boolean (environment variable)

**Behavior:**
- `true`: delete_document (SIGNED) action available
- `false`: Returns 503 FEATURE_DISABLED

---

## Environment Variables

Set these in Render dashboard (staging) or production environment:

```bash
# Documents Flags
DOCUMENT_LENS_V2_ENABLED=false  # Default OFF
DOCUMENT_LENS_SUGGESTIONS_ENABLED=false  # Default OFF
DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED=false  # Default OFF
```

**Staging Canary Configuration:**

```bash
# Enable for canary testing
DOCUMENT_LENS_V2_ENABLED=true
DOCUMENT_LENS_SUGGESTIONS_ENABLED=true
DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED=true
```

---

## Toggle Procedures

### Enable Documents (Canary)

1. **Render Dashboard → Environment**
   ```
   DOCUMENT_LENS_V2_ENABLED=true
   DOCUMENT_LENS_SUGGESTIONS_ENABLED=true
   DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED=true
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
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
     -H "Authorization: Bearer {JWT}" \
     -H "Content-Type: application/json" \
     -d '{"action": "list_documents", "context": {"yacht_id": "..."}, "payload": {}}'

   # Should return 200 with documents (not 503)
   ```

---

### Disable Documents (Rollback)

**Scenario:** Canary shows errors or performance issues.

1. **Render Dashboard → Environment**
   ```
   DOCUMENT_LENS_V2_ENABLED=false
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
INFO:integrations.feature_flags:[FeatureFlags] DOCUMENT_LENS_V2_ENABLED=True
INFO:integrations.feature_flags:[FeatureFlags] DOCUMENT_LENS_SUGGESTIONS_ENABLED=True
INFO:integrations.feature_flags:[FeatureFlags] DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED=True
```

**Check Logs:**
```bash
# Render dashboard → Logs tab
# Search for: [FeatureFlags]
```

---

## Current Status

**Document Lens Flags (as of 2026-01-28):**

| Flag | Status | Ready for Canary |
|------|--------|------------------|
| `DOCUMENT_LENS_V2_ENABLED` | ON (staging) | ✅ Tested |
| `DOCUMENT_LENS_SUGGESTIONS_ENABLED` | OFF (main) | ⏳ Not tested |
| `DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED` | ON (staging) | ✅ Tested |

**Note:** Document Lens v2 is already deployed and tested (tag: document-lens-gold). These flags are optional for additional control.

**Recommended Canary Configuration:**
```bash
DOCUMENT_LENS_V2_ENABLED=true
DOCUMENT_LENS_SUGGESTIONS_ENABLED=true
DOCUMENT_LENS_SIGNED_ACTIONS_ENABLED=true
```

**Next Steps:**
1. Enable canary flags in staging (optional)
2. Monitor for 24h (0×500, P99 latency)
3. Expand to staging full
4. Enable production canary (10%)
5. Gradual rollout to 100%
