# Handover Workflow Implementation Summary
**Date**: 2026-02-05
**Status**: Schema Complete, Handlers Complete, Routes Pending

## What Was Implemented

### 1. Database Schema ✅ COMPLETE
Added dual-hash, dual-signature fields to support the full workflow:

**`handover_items` table:**
- `content_hash` - SHA256 of normalized draft content JSON
- `finalized_at` - When draft was locked
- `finalized_by` - User who finalized
- `version` - Draft version number
- `is_finalized` - Lock flag

**`handover_exports` table:**
- `content_hash` - Links to draft content hash
- `document_hash` - SHA256 of PDF/HTML artifact (already existed)
- `signatures` - JSONB envelope with outgoing/incoming signatures
- `previous_export_id` - Version chain for re-exports
- `status` - draft | pending_outgoing | pending_incoming | completed
- `outgoing_*` fields - outgoing_user_id, role, signed_at, comments (already existed)
- `incoming_*` fields - incoming_user_id, role, signed_at, comments, acknowledged_critical (already existed)
- `signoff_complete` - Boolean flag (already existed)

**Indexes:**
- `idx_handover_exports_status`
- `idx_handover_exports_outgoing_user`
- `idx_handover_exports_incoming_user`
- `idx_handover_exports_previous` (version chain)
- `idx_handover_items_finalized`

### 2. Backend Handlers ✅ COMPLETE
Created `/apps/api/handlers/handover_workflow_handlers.py` with `HandoverWorkflowHandlers` class:

**Stage 1: Draft Review & Finalization**
- `validate_draft(yacht_id, user_id, section?, category?)` - Checks for blocking errors
- `finalize_draft(yacht_id, user_id, section?, category?)` - Locks content, generates content_hash

**Stage 2: Export**
- `export_handover(yacht_id, user_id, export_type, section?, department?, shift_date?)` - Generates HTML/PDF with document_hash

**Stage 3: Dual Signature**
- `sign_outgoing(export_id, yacht_id, user_id, user_role, note?, method='typed')` - Outgoing signs
- `sign_incoming(export_id, yacht_id, user_id, user_role, acknowledge_critical, note?, method='typed')` - Incoming countersigns

**Stage 4: Verification**
- `get_pending_handovers(yacht_id, user_id, role_filter?)` - List handovers awaiting signature
- `verify_export(export_id, yacht_id)` - Returns hashes + signatures for QR verification

**Notifications:**
- `_notify_ledger_export_ready()` - Sends notification to ledger when export ready for signing

### 3. Action Registry ✅ COMPLETE
Added 7 new actions to `/apps/api/action_router/registry.py`:

1. `validate_handover_draft` - READ variant
2. `finalize_handover_draft` - MUTATE variant
3. `export_handover` - MUTATE variant
4. `sign_handover_outgoing` - SIGNED variant (requires officer+ role)
5. `sign_handover_incoming` - SIGNED variant (requires officer+ role + critical acknowledgment)
6. `get_pending_handovers` - READ variant
7. `verify_handover_export` - READ variant

All actions require officer+ roles: `chief_engineer`, `chief_officer`, `captain`, `manager`

---

## What Remains To Be Done

### 4. Route Wiring 🔴 PENDING
Need to wire the new handlers to actual FastAPI routes in `/apps/api/routes/p0_actions_routes.py`:

```python
from handlers.handover_workflow_handlers import HandoverWorkflowHandlers

# Initialize handler
handover_workflow = HandoverWorkflowHandlers(supabase_client)

# Wire endpoints
@router.post("/v1/handover/validate")
async def validate_handover_draft_route(...):
    return await handover_workflow.validate_draft(...)

@router.post("/v1/handover/finalize")
async def finalize_handover_draft_route(...):
    return await handover_workflow.finalize_draft(...)

@router.post("/v1/handover/export")
async def export_handover_route(...):
    return await handover_workflow.export_handover(...)

@router.post("/v1/handover/sign/outgoing")
async def sign_outgoing_route(...):
    return await handover_workflow.sign_outgoing(...)

@router.post("/v1/handover/sign/incoming")
async def sign_incoming_route(...):
    return await handover_workflow.sign_incoming(...)

@router.get("/v1/handover/pending")
async def get_pending_route(...):
    return await handover_workflow.get_pending_handovers(...)

@router.get("/v1/handover/verify")
async def verify_export_route(...):
    return await handover_workflow.verify_export(...)
```

### 5. Frontend UI 🔴 PENDING
Need to build the sign-off workflow UI:

**Draft Workspace** (`/handover/drafts/:id`):
- Section/item review table with diff highlights
- "Validate Draft" button → shows warnings/errors
- "Finalize Draft" button → locks and displays `content_hash`

**Export Pane**:
- "Generate Export" button
- Display `document_hash` and preview link (HTML/PDF)
- Display both hashes for visual verification

**Sign Panes**:
- **Outgoing sign pane**:
  - Render footer with hash
  - Capture typed signature (MVP)
  - Re-auth prompt (password/OTP) for step-up
  - Submit button

- **Incoming sign pane**:
  - Render critical items summary
  - Required checkbox: "I acknowledge all critical items"
  - Capture signature
  - Submit button

- **Completed state**:
  - Show "Signoff Complete" status
  - Offer "Email Export" and "Download PDF" buttons

**`/open` Handler Enhancement**:
- For `scope='view'` → focus entity (already done)
- For `scope='sign:outgoing'` → open outgoing sign pane
- For `scope='sign:incoming'` → open incoming sign pane

### 6. Token Scope Enhancement 🔴 PENDING
Update link token service to support sign scopes:

- Add `scope` options: `'view'` | `'sign:outgoing'` | `'sign:incoming'`
- Validate user_id/yacht_id match on resolve
- Enforce role requirements (officer+ only)

### 7. Step-Up Re-auth 🔴 PENDING
Implement step-up authentication for signature actions:

- Check if `last_login_at` > N hours (e.g., 4 hours)
- If stale, require re-auth via password/OTP
- Record re-auth timestamp
- Enforce for both `sign_outgoing` and `sign_incoming`

### 8. PDF Footer with Hashes 🔴 PENDING
Update HTML/PDF export template to include verification footer:

```html
<div class="verification-footer">
  <p>Content Hash: <code>sha256:{content_hash[:16]}...</code></p>
  <p>Document Hash: <code>sha256:{document_hash[:16]}...</code></p>
  <p>QR Code: [Link to /verify?export_id=...]</p>
</div>
```

### 9. Notifications Table 🔴 PENDING
Verify `notifications` table exists and has correct schema:

```sql
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  notification_type TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);
```

### 10. E2E Tests 🔴 PENDING
Test the full workflow:

1. Draft → Finalize (verify content_hash appears)
2. Finalize → Export (verify document_hash appears)
3. Export → Outgoing Sign (verify status=pending_incoming)
4. Outgoing Sign → Incoming Sign (verify signoff_complete=true)
5. Verify page shows both signatures and hashes
6. Test error paths: sign before export, sign without critical ack, etc.

---

## Workflow States

```
Items Created
    ↓
[Draft Review] ← Users edit, validate
    ↓
FINALIZE (content_hash generated, items locked)
    ↓
EXPORT (document_hash generated, status=pending_outgoing)
    ↓
OUTGOING SIGN (status=pending_incoming, notification sent)
    ↓
INCOMING SIGN (signoff_complete=true, status=completed)
    ↓
VERIFICATION (QR/verify page shows hashes + signatures)
```

---

## Security Model

**Roles Required**: `chief_engineer`, `chief_officer`, `captain`, `manager`

**Signature Methods (MVP)**:
- Typed signature + step-up re-auth (password/OTP)
- Server-side soft signature (HMAC-based JWS envelope)

**Signature Methods (Phase 2)**:
- WebAuthn device-bound signatures
- Email-delivered one-time sign tokens for incoming countersign

**Audit**:
- Every action writes to `pms_audit_log`
- Signature envelopes stored in `handover_exports.signatures` (JSONB)
- Full version chain via `previous_export_id`

---

## Next Steps

1. **Wire routes** - Connect handlers to FastAPI endpoints
2. **Test backend** - Use Postman/curl to test each endpoint
3. **Build frontend UI** - Draft workspace, export pane, sign panes
4. **Add token scopes** - Support `sign:outgoing` and `sign:incoming`
5. **Implement step-up re-auth** - Password/OTP prompt before signature
6. **Update export template** - Add hashes to PDF footer with QR code
7. **E2E testing** - Full workflow validation

---

## Files Modified

1. ✅ `/apps/api/handlers/handover_workflow_handlers.py` - NEW
2. ✅ `/apps/api/action_router/registry.py` - UPDATED (added 7 actions)
3. 🔴 `/apps/api/routes/p0_actions_routes.py` - PENDING (route wiring)
4. ✅ Tenant DB schema - UPDATED (content_hash, signatures, previous_export_id)

---

## Questions for Review

1. **Notifications Table**: Does `notifications` table exist in tenant DB? Need to verify schema.
2. **Step-Up Re-auth**: Should we use existing auth middleware or build custom?
3. **Export Template**: Which file contains the HTML export template for handovers?
4. **Frontend Framework**: React? Vue? Where is the handover UI code?
5. **Token Service**: Is link token service in pipeline-core or handover-export repo?

---

Ready to proceed with route wiring and deployment when you confirm the approach.
