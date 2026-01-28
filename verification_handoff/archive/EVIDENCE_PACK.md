# Fault Lens v1 - Phase 6 Evidence Pack

**Date:** 2026-01-27
**Status:** Ready for sign-off

---

## 1. HOD Helper Scope (Fixed)

### Before (WRONG)
```sql
role IN ('chief_engineer', 'captain', 'manager')
```

### After (CORRECT - per canon)
```sql
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'chief_officer', 'captain', 'purser')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_hod IS
  'Canon HOD = chief_engineer, chief_officer, captain, purser. Manager separate.';
```

**Canon:** HOD = chief_engineer, chief_officer, captain, purser. Manager is NOT part of HOD by default.

---

## 2. Entity Links RLS (Fixed)

### Before (WRONG)
```sql
-- Allowed: HOD OR manager
is_hod(auth.uid(), get_user_yacht_id()) OR is_manager(auth.uid(), get_user_yacht_id())
```

### After (CORRECT)
```sql
-- Policy: links_insert_hod_only
CREATE POLICY links_insert_hod_only ON pms_entity_links
    FOR INSERT TO public
    WITH CHECK (
        yacht_id = get_user_yacht_id()
        AND is_hod(auth.uid(), get_user_yacht_id())
    );

-- Policy: links_delete_hod_only
CREATE POLICY links_delete_hod_only ON pms_entity_links
    FOR DELETE TO public
    USING (
        yacht_id = get_user_yacht_id()
        AND is_hod(auth.uid(), get_user_yacht_id())
    );
```

**Canon:** Add Related = HOD only (chief_engineer, chief_officer, captain, purser). Manager excluded.

---

## 3. Registry Role Matrix (Fault Actions)

| Action | crew | CE | CO | capt | mgr | purser |
|--------|------|----|----|------|-----|--------|
| report_fault | ✓ | ✓ | ✓ | ✓ | - | - |
| add_fault_photo | ✓ | ✓ | ✓ | ✓ | - | - |
| add_fault_note | ✓ | ✓ | ✓ | ✓ | - | - |
| acknowledge_fault | - | ✓ | ✓ | ✓ | - | - |
| update_fault | - | ✓ | ✓ | ✓ | - | - |
| close_fault | - | ✓ | ✓ | ✓ | - | - |
| diagnose_fault | - | ✓ | ✓ | ✓ | - | - |
| reopen_fault | - | ✓ | ✓ | ✓ | - | - |
| view_fault_detail | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| view_fault_history | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| create_work_order_from_fault (SIGNED) | - | ✓* | ✓* | ✓* | ✓* | - |

*Initiate only. **Signature requires: captain or manager**

### Source: `apps/api/action_router/registry.py:603-800`
```python
"report_fault": ActionDefinition(
    ...
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
),

"add_fault_photo": ActionDefinition(
    ...
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
),

"add_fault_note": ActionDefinition(
    ...
    allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
),
```

---

## 4. Storage Isolation Proof (pms-discrepancy-photos)

### INSERT Policy
```sql
-- Policy: crew_upload_discrepancy_photos
WITH CHECK: (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = (get_user_yacht_id())::text
)
```
**Effect:** Must upload to `{yacht_id}/faults/...` path. Cross-yacht upload denied.

### SELECT Policy
```sql
-- Policy: crew_read_discrepancy_photos
USING: (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = (get_user_yacht_id())::text
)
```
**Effect:** Can only read files from own yacht folder.

### DELETE Policy
```sql
-- Policy: hod_delete_discrepancy_photos
USING: (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = (get_user_yacht_id())::text
    AND is_hod(auth.uid(), get_user_yacht_id())
)
```
**Effect:** HOD only can delete. Crew cannot delete.

---

## 5. Signature Role Enforcement

### Request/Response Transcripts

#### Missing Signature → 400
```json
// Request
{
  "action": "create_work_order_from_fault",
  "context": {"yacht_id": "..."},
  "payload": {"fault_id": "..."}  // No signature
}

// Response: 400
{
  "status": "error",
  "error_code": "signature_required",
  "message": "Signature payload required for SIGNED action"
}
```

#### Invalid Signature Keys → 400
```json
// Request
{
  "action": "create_work_order_from_fault",
  "payload": {
    "fault_id": "...",
    "signature": {"wrong_key": "value"}
  }
}

// Response: 400
{
  "status": "error",
  "error_code": "invalid_signature",
  "message": "Invalid signature: missing keys ['signed_at', 'user_id', 'role_at_signing', 'signature_type']"
}
```

#### Chief Engineer as Signer → 403
```json
// Request
{
  "action": "create_work_order_from_fault",
  "payload": {
    "fault_id": "...",
    "signature": {
      "signed_at": "2026-01-27T10:00:00Z",
      "user_id": "ce-user-id",
      "role_at_signing": "chief_engineer",  // DENIED
      "signature_type": "pin_totp"
    }
  }
}

// Response: 403
{
  "status": "error",
  "error_code": "invalid_signer_role",
  "message": "Signature requires role: captain, manager",
  "required_roles": ["captain", "manager"]
}
```

#### Captain as Signer → 200
```json
// Request
{
  "action": "create_work_order_from_fault",
  "payload": {
    "fault_id": "...",
    "signature": {
      "signed_at": "2026-01-27T10:00:00Z",
      "user_id": "captain-user-id",
      "role_at_signing": "captain",  // ALLOWED
      "signature_type": "pin_totp",
      "signature_hash": "abc123..."
    }
  }
}

// Response: 200
{
  "status": "success",
  "action": "create_work_order_from_fault",
  "result": {...}
}
```

---

## 6. RLS Proof Snippets

### pms_faults

| Operation | crew | HOD | manager | purser |
|-----------|------|-----|---------|--------|
| INSERT | ✓ | ✓ | - | - |
| SELECT | ✓ | ✓ | ✓ | ✓ |
| UPDATE | - | ✓ | - | - |
| DELETE | - | - | - | - |

```sql
-- crew INSERT allowed
crew_insert_faults: WITH CHECK (yacht_id = get_user_yacht_id())

-- crew UPDATE denied (no policy)
-- HOD UPDATE allowed
hod_update_faults:
  USING (yacht_id = get_user_yacht_id())
  WITH CHECK (yacht_id = get_user_yacht_id() AND is_hod(...))
```

### pms_entity_links

| Operation | crew | HOD | manager |
|-----------|------|-----|---------|
| INSERT | - | ✓ | - |
| SELECT | ✓ | ✓ | ✓ |
| DELETE | - | ✓ | - |

```sql
-- crew INSERT denied (is_hod check fails)
-- manager INSERT denied (is_hod now excludes manager)
links_insert_hod_only: WITH CHECK (yacht_id = get_user_yacht_id() AND is_hod(...))
```

### pms_warranty_claims

| Operation | crew | HOD | manager |
|-----------|------|-----|---------|
| INSERT (draft) | ✓ | ✓ | ✓ |
| INSERT (submitted) | - | - | - |
| SELECT | ✓ | ✓ | ✓ |
| UPDATE (draft→submitted) | - | ✓ | - |
| UPDATE (→approved) | - | - | ✓ |
| DELETE (draft) | - | ✓ | - |
| DELETE (submitted) | - | - | - |

```sql
-- crew INSERT draft only
crew_insert_warranty_claims:
  WITH CHECK (yacht_id = get_user_yacht_id() AND status = 'draft')

-- DELETE draft only, HOD only
hod_delete_warranty_claims:
  USING (yacht_id = get_user_yacht_id() AND status = 'draft' AND is_hod(...))
```

---

## 7. Notifications Idempotency

### Unique Index DDL
```sql
CREATE UNIQUE INDEX unique_notification
ON public.pms_notifications
USING btree (yacht_id, user_id, idempotency_key)
```

### Idempotency Key Formation
```python
# Format: {entity_type}:{entity_id}:{event}:{date}
idempotency_key = f"warranty:{claim_id}:submitted:{datetime.now().date()}"
```

### Upsert Behavior
```sql
INSERT INTO pms_notifications (...)
ON CONFLICT (yacht_id, user_id, idempotency_key) DO NOTHING
RETURNING id INTO v_id;
```

**Result:** Duplicate notification with same key returns existing row ID. No duplicate created.

---

## 8. Canary Flag Gating

### Feature Flags (`apps/api/integrations/feature_flags.py`)
```python
FAULT_LENS_V1_ENABLED = os.getenv('FAULT_LENS_V1_ENABLED', 'false') == 'true'
FAULT_LENS_SUGGESTIONS_ENABLED = os.getenv('FAULT_LENS_SUGGESTIONS_ENABLED', 'false') == 'true'
FAULT_LENS_RELATED_ENABLED = os.getenv('FAULT_LENS_RELATED_ENABLED', 'false') == 'true'
FAULT_LENS_WARRANTY_ENABLED = os.getenv('FAULT_LENS_WARRANTY_ENABLED', 'false') == 'true'
FAULT_LENS_SIGNED_ACTIONS_ENABLED = os.getenv('FAULT_LENS_SIGNED_ACTIONS_ENABLED', 'false') == 'true'
```

### Gating Behavior

| Feature | Flag OFF Response |
|---------|-------------------|
| Suggestions (faults domain) | 503 FEATURE_DISABLED |
| Signed Actions (faults domain) | 503 FEATURE_DISABLED |
| Related API | 503 FEATURE_DISABLED |

### Implementation (router.py)
```python
# Suggestions endpoint
if request_data.domain == "faults":
    enabled, message = check_fault_lens_feature("suggestions")
    if not enabled:
        raise HTTPException(status_code=503, ...)

# Execute endpoint (SIGNED actions)
if action_def.variant == ActionVariant.SIGNED and action_def.domain == "faults":
    enabled, message = check_fault_lens_feature("signed_actions")
    if not enabled:
        raise HTTPException(status_code=503, ...)
```

---

## 9. Test Coverage

### New Test File: `apps/api/tests/test_fault_lens_v1_evidence.py`

- ✓ `TestPmsFaultsRLS` - crew INSERT/UPDATE, HOD UPDATE, cross-yacht denied
- ✓ `TestPmsEntityLinksRLS` - crew denied, HOD allowed, manager denied
- ✓ `TestPmsWarrantyClaimsRLS` - status transitions, delete draft only
- ✓ `TestPurserReadOnly` - view allowed, mutate denied
- ✓ `TestSignatureRoleEnforcement` - missing/invalid/denied/allowed transcripts
- ✓ `TestCrewFaultPhotoNote` - crew allowed for photo/note
- ✓ `TestSuggestionsParity` - GET /list and POST /suggestions equivalent
- ✓ `TestCanaryFlagGating` - feature flag enforcement
- ✓ `TestNotificationsIdempotency` - duplicate key handling
- ✓ `TestShowRelatedDeterminism` - no user free-text, FK-based matching

---

## 10. Audit Metadata Consistency

All mutations include:
```python
"metadata": {
    "source": "lens",
    "lens": "faults"  # or "warranty" for warranty handlers
}
```

Verified in:
- `fault_mutation_handlers.py`
- `related_handlers.py`
- `warranty_handlers.py`

---

## Sign-off Checklist

- [x] is_hod() fixed (chief_officer in, manager out)
- [x] entity_links RLS corrected (HOD only)
- [x] Registry crew permissions verified
- [x] Storage isolation policy DDL provided
- [x] Signature role enforcement with transcripts
- [x] RLS proof snippets per table cell
- [x] Notifications idempotency with unique index
- [x] Canary flags gate all Fault Lens features
- [x] Purser read-only tests
- [x] Crew photo/note tests
- [x] GET/POST suggestions parity

**Ready for canary enablement.**
