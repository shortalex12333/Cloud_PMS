# Handover Dual-Signature Workflow - DEPLOYED
**Date**: 2026-02-05
**PR**: #105
**Deploy ID**: `dep-d62hpqp4tr6s73bnbv10`
**Status**: ✅ DEPLOYED TO RENDER

---

## Endpoints Now Live

### Draft Management
```bash
# Validate draft before finalization
POST /v1/actions/handover/{draft_id}/validate
Authorization: Bearer {jwt}

Response: {
  "valid": true|false,
  "errors": [],
  "warnings": [],
  "blocking_count": 0,
  "warning_count": 0
}

# Finalize draft (lock + content_hash)
POST /v1/actions/handover/{draft_id}/finalize
Authorization: Bearer {jwt}
Role: Officer+ (chief_engineer, chief_officer, captain, manager)

Response: {
  "status": "success",
  "content_hash": "abc123...",
  "finalized_at": "2026-02-05T...",
  "finalized_by": "user-uuid",
  "item_count": 15
}
```

### Export Generation
```bash
# Generate export with document_hash
POST /v1/actions/handover/{draft_id}/export
Authorization: Bearer {jwt}
Role: Officer+
Query: ?export_type=html&department=engineering&shift_date=2026-02-05

Response: {
  "status": "success",
  "export_id": "export-uuid",
  "document_hash": "def456...",
  "content_hash": "abc123...",
  "export_type": "html",
  "total_items": 15
}
```

### Dual Signature
```bash
# Outgoing user signs
POST /v1/actions/handover/{export_id}/sign/outgoing
Authorization: Bearer {jwt}
Role: Officer+
Body: {
  "note": "All critical items flagged",
  "method": "typed"  # MVP: soft signature
}

Response: {
  "status": "success",
  "export_id": "export-uuid",
  "signed_at": "2026-02-05T...",
  "signed_by": "user-uuid",
  "role": "chief_engineer",
  "signature_method": "typed"
}

# Incoming user countersigns
POST /v1/actions/handover/{export_id}/sign/incoming
Authorization: Bearer {jwt}
Role: Officer+
Body: {
  "acknowledge_critical": true,  # REQUIRED
  "note": "Critical items reviewed",
  "method": "typed"
}

Response: {
  "status": "success",
  "export_id": "export-uuid",
  "signed_at": "2026-02-05T...",
  "signed_by": "user-uuid",
  "role": "captain",
  "signoff_complete": true
}
```

### Verification & Pending
```bash
# Get pending handovers
GET /v1/actions/handover/pending?role_filter=outgoing|incoming
Authorization: Bearer {jwt}

Response: {
  "status": "success",
  "pending_count": 2,
  "exports": [...]
}

# Verify export (QR page)
GET /v1/actions/handover/{export_id}/verify
Authorization: Bearer {jwt}

Response: {
  "status": "success",
  "export_id": "export-uuid",
  "content_hash": "abc123...",
  "document_hash": "def456...",
  "signoff_complete": true,
  "outgoing": {
    "user_id": "user-uuid",
    "role": "chief_engineer",
    "signed_at": "2026-02-05T...",
    "signature": {...}
  },
  "incoming": {
    "user_id": "user-uuid",
    "role": "captain",
    "signed_at": "2026-02-05T...",
    "critical_acknowledged": true,
    "signature": {...}
  }
}
```

---

## Database Schema (Already Applied)

### `handover_items`
```sql
-- Finalization fields
content_hash TEXT                     -- SHA256 of normalized draft JSON
finalized_at TIMESTAMPTZ              -- When draft locked
finalized_by UUID → auth.users        -- Who locked it
version INTEGER DEFAULT 1             -- Draft version
is_finalized BOOLEAN DEFAULT FALSE    -- Lock flag
```

### `handover_exports`
```sql
-- Dual-hash fields
content_hash TEXT                     -- Links to finalized draft
document_hash TEXT                    -- SHA256 of PDF/HTML artifact
signatures JSONB                      -- {outgoing: {...}, incoming: {...}}
previous_export_id UUID → handover_exports  -- Version chain

-- Workflow fields (already existed)
status TEXT DEFAULT 'draft'           -- draft | pending_outgoing | pending_incoming | completed
outgoing_user_id UUID
outgoing_role TEXT
outgoing_signed_at TIMESTAMPTZ
outgoing_comments TEXT
incoming_user_id UUID
incoming_role TEXT
incoming_signed_at TIMESTAMPTZ
incoming_comments TEXT
incoming_acknowledged_critical BOOLEAN
signoff_complete BOOLEAN DEFAULT FALSE
```

### `notifications` (New Table)
```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  notification_type TEXT NOT NULL,     -- 'handover_ready_outgoing' | 'handover_ready_incoming'
  entity_type TEXT,
  entity_id UUID,
  created_by UUID → auth.users,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB,
  read_at TIMESTAMPTZ,
  read_by UUID → auth.users
);

-- RLS Policies
notifications_select_yacht: yacht_id = get_user_yacht_id()
notifications_insert_service: service_role can insert
notifications_update_read: users can mark as read
```

---

## Workflow States

```
Items Created (handover_items)
    ↓
[Draft Review] ← Users edit, validate
    ↓
FINALIZE
  ├─ content_hash = sha256(normalized_items_json)
  ├─ is_finalized = true
  └─ items become read-only
    ↓
EXPORT
  ├─ document_hash = sha256(html_bytes)
  ├─ content_hash linked
  ├─ status = 'pending_outgoing'
  └─ notification sent to outgoing signer
    ↓
SIGN OUTGOING
  ├─ outgoing_* fields filled
  ├─ status = 'pending_incoming'
  ├─ signature stored in JSONB
  └─ notification sent to incoming signer
    ↓
SIGN INCOMING
  ├─ incoming_* fields filled
  ├─ critical_acknowledged required
  ├─ status = 'completed'
  ├─ signoff_complete = true
  └─ signature stored in JSONB
    ↓
VERIFICATION
  └─ QR page shows both hashes + signatures
```

---

## Export Template Updates

### Footer Now Includes:
```html
<div class="footer">
    <div>Generated 2026-02-05 14:32 UTC • CelesteOS Handover Export</div>
    <div class="verification-hashes">
        <div style="font-size: 11px; color: #6c757d; margin-top: 8px;">
            <div><strong>Content Hash:</strong> <code>sha256:abc123...</code></div>
            <div style="margin-top: 4px;">
                <strong>Verify:</strong>
                <a href="/handover/{export_id}/verify">View Verification Details</a>
            </div>
        </div>
    </div>
</div>
```

---

## Security Model

### Role Requirements
- **All workflow endpoints**: Officer+ only
  - `chief_engineer`
  - `chief_officer`
  - `captain`
  - `manager`

### Signature Methods (MVP)
- **Soft Signature**: Server-side HMAC-based JWS envelope
  - Payload: `{ document_hash, export_id, signer_user_id, role, timestamp, method }`
  - Stored in `handover_exports.signatures` JSONB
  - No step-up re-auth required (as requested)

### Future Enhancements (Phase 2)
- WebAuthn device-bound signatures
- Email-delivered one-time sign tokens
- Step-up re-auth with password/OTP

### RLS & Isolation
- All endpoints filter by `yacht_id = get_user_yacht_id()`
- Notifications table has yacht-scoped RLS
- Service role can insert notifications (for automated triggers)

---

## Action Registry

### 7 New Actions Added
1. `validate_handover_draft` - READ variant
2. `finalize_handover_draft` - MUTATE variant, Officer+
3. `export_handover` - MUTATE variant, Officer+
4. `sign_handover_outgoing` - **SIGNED variant**, Officer+
5. `sign_handover_incoming` - **SIGNED variant**, Officer+ + critical ack
6. `get_pending_handovers` - READ variant
7. `verify_handover_export` - READ variant

---

## Testing Checklist

### Backend Unit Tests 🔴 TODO
- [ ] `finalize_draft` sets content_hash and locks items
- [ ] `export_handover` sets document_hash and storage fields
- [ ] `sign_outgoing` transitions status to pending_incoming
- [ ] `sign_incoming` requires acknowledge_critical=true
- [ ] `sign_incoming` sets signoff_complete=true
- [ ] `verify_export` returns both hashes and signatures
- [ ] Pending lists reflect state transitions correctly

### E2E Tests 🔴 TODO
- [ ] Draft → Finalize → Export → Outgoing → Incoming → Verify
- [ ] Critical acknowledgment enforced for incoming sign
- [ ] Role gating: Crew denied, Officer+ allowed
- [ ] Yacht isolation: Cross-yacht access denied
- [ ] Hashes match between finalize/export/verify

### Manual Smoke Test 🟡 READY
```bash
# 1. Finalize draft
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/handover/draft-123/finalize" \
  -H "Authorization: Bearer {jwt}"

# 2. Export
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/handover/draft-123/export" \
  -H "Authorization: Bearer {jwt}"

# 3. Sign outgoing
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/handover/{export_id}/sign/outgoing" \
  -H "Authorization: Bearer {jwt}" \
  -d '{"note": "All good", "method": "typed"}'

# 4. Sign incoming
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/handover/{export_id}/sign/incoming" \
  -H "Authorization: Bearer {jwt}" \
  -d '{"acknowledge_critical": true, "note": "Reviewed", "method": "typed"}'

# 5. Verify
curl "https://pipeline-core.int.celeste7.ai/v1/actions/handover/{export_id}/verify" \
  -H "Authorization: Bearer {jwt}"
```

---

## What's Still TODO

### Frontend UI 🔴 CRITICAL
1. **Draft workspace** (`/handover/drafts/:id`)
   - "Validate Draft" button → show warnings/errors
   - "Finalize Draft" button → lock and display content_hash

2. **Export pane**
   - "Generate Export" button
   - Display document_hash and content_hash
   - Preview link (HTML/PDF)

3. **Sign panes**
   - Outgoing sign pane: render PDF preview, hash footer, submit signature
   - Incoming sign pane: critical items summary + required checkbox, submit signature
   - Completed state: "Signoff Complete" + download/email buttons

4. **`/open` handler enhancement**
   - Support `scope='sign:outgoing'` and `scope='sign:incoming'` (opens sign pane)
   - Currently only supports `scope='view'`

### Token Scopes 🔴 CRITICAL
- Update `handover-export` service link token validation
- Add `sign:outgoing` and `sign:incoming` to `SUPPORTED_SCOPES`
- Validate user_id/yacht_id match + role requirements on resolve

### PDF Generation 🟡 NICE-TO-HAVE
- Currently generates HTML only
- PDF conversion via wkhtmltopdf or Puppeteer
- Store in Supabase Storage bucket `handover-exports`

---

## Deployment Evidence

**PR**: https://github.com/shortalex12333/Cloud_PMS/pull/105
**Commit**: `8a79c29`
**Deploy**: `dep-d62hpqp4tr6s73bnbv10`
**Service**: pipeline-core (Render)
**Branch**: `main`

**Files Changed**:
- `apps/api/handlers/handover_workflow_handlers.py` (NEW)
- `apps/api/action_router/registry.py` (7 new actions)
- `apps/api/routes/p0_actions_routes.py` (7 new endpoints)
- `apps/api/services/handover_export_service.py` (hash footer)

**Database Migrations Applied**:
- `handover_items`: content_hash, finalized_at, finalized_by, version, is_finalized
- `handover_exports`: signatures, previous_export_id, content_hash
- `notifications` table created with RLS

---

## Next Steps

1. **Frontend UI** - Build draft workspace, export pane, and sign panes
2. **Token Scopes** - Add `sign:*` support to handover-export service
3. **E2E Tests** - Write Playwright tests for full workflow
4. **PDF Generation** - Implement HTML→PDF conversion
5. **Notifications UI** - Display pending handovers in user notifications

Ready for frontend integration and E2E testing.
