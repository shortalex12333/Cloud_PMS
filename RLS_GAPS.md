# RLS GAPS REPORT

**Generated:** 2026-01-18
**Method:** Migration file analysis + API behavior observation

---

## RLS ARCHITECTURE

### Helper Functions (From Migrations)

| Function | Purpose | Status |
|----------|---------|--------|
| `jwt_yacht_id()` | Extract yacht_id from JWT claims | EXISTS but returns NULL (JWT hook not configured) |
| `get_user_yacht_id()` | Fallback: query auth_users_profiles | EXISTS |
| `is_manager()` | Check if user has manager role | EXISTS |
| `get_user_role()` | Get user role from DB | EXISTS |

### RLS Policy Pattern
```sql
CREATE POLICY "policy_name" ON table_name
  FOR SELECT
  TO public
  USING (
    yacht_id = COALESCE(
      jwt_yacht_id(),           -- Try JWT first (fast, no DB query)
      get_user_yacht_id()       -- Fallback to DB query
    )
  );
```

---

## TABLES WITH RLS POLICIES (From Migrations)

| Table | Policy Exists | yacht_id Check |
|-------|---------------|----------------|
| `doc_metadata` | ✅ | `yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id())` |
| `search_document_chunks` | ✅ | `yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id())` |
| `action_executions` | ✅ | `yacht_id = get_user_yacht_id()` |
| `action_confirmations` | ✅ | `yacht_id = get_user_yacht_id()` |
| `ledger_events` | ✅ | `yacht_id = get_user_yacht_id()` |
| `navigation_contexts` | ✅ | `yacht_id = get_user_yacht_id()` |
| `situation_detections` | ✅ | `yacht_id = get_user_yacht_id()` |
| `handovers` | ✅ | `yacht_id = get_user_yacht_id()` |
| `handover_items` | ✅ | `yacht_id = get_user_yacht_id()` |

---

## TABLES REFERENCED IN CODE WITHOUT RLS VERIFICATION

| Table | yacht_id Column | RLS Status |
|-------|-----------------|------------|
| `attachments` | Unknown | **TABLE DOES NOT EXIST** |
| `audit_log` | Unknown | **TABLE DOES NOT EXIST** |
| `auth_users` | Unknown | **TABLE DOES NOT EXIST** |
| `checklist_items` | Unknown | **TABLE DOES NOT EXIST** |
| `crew_members` | Unknown | **TABLE DOES NOT EXIST** |
| `hours_of_rest` | Unknown | **TABLE DOES NOT EXIST** |
| `notes` | Unknown | **TABLE DOES NOT EXIST** |
| `purchase_requests` | Unknown | **TABLE DOES NOT EXIST** |
| `work_order_parts` | Unknown | **TABLE DOES NOT EXIST** |

---

## RLS BYPASS RISKS

### Risk 1: Service Role Key Usage
- E2E tests use service role key (bypasses RLS)
- Cannot verify RLS enforcement through tests

### Risk 2: yacht_id NULL in Requests
- If yacht_id is NULL, COALESCE falls back to `get_user_yacht_id()`
- `get_user_yacht_id()` queries `auth_users_profiles`
- If that lookup fails, NO rows are returned (silent failure)

### Risk 3: JWT Hook Not Configured
- `jwt_yacht_id()` always returns NULL
- Forces DB query on every RLS check (performance impact)
- Not a security issue, but indicates incomplete setup

---

## MISSING RLS POLICIES

### Tables That SHOULD Have RLS But Status Unknown

| Table | Has yacht_id | RLS Needed |
|-------|--------------|------------|
| `pms_work_orders` | ✅ | ✅ REQUIRED |
| `pms_equipment` | ✅ | ✅ REQUIRED |
| `pms_faults` | ✅ | ✅ REQUIRED |
| `pms_parts` | ✅ | ✅ REQUIRED |
| `email_threads` | ✅ | ✅ REQUIRED |
| `email_messages` | ✅ | ✅ REQUIRED |

**Cannot verify RLS on these tables without direct Supabase dashboard access or pg_policies query.**

---

## RLS VERIFICATION NEEDED

### Test Case 1: Cross-Tenant Read (Should Fail)
```sql
-- As user from Yacht A, try to read Yacht B data
SELECT * FROM pms_work_orders WHERE yacht_id = 'yacht-b-id';
-- Expected: 0 rows (RLS blocks)
-- Actual: UNKNOWN (cannot test without proper user session)
```

### Test Case 2: Cross-Tenant Write (Should Fail)
```sql
-- As user from Yacht A, try to insert into Yacht B
INSERT INTO handover_items (yacht_id, ...) VALUES ('yacht-b-id', ...);
-- Expected: INSERT 0 0 (RLS blocks)
-- Actual: UNKNOWN
```

### Test Case 3: Same-Tenant Read (Should Pass)
```sql
-- As user from Yacht A, read Yacht A data
SELECT * FROM pms_work_orders WHERE yacht_id = 'yacht-a-id';
-- Expected: Rows returned
-- Actual: UNKNOWN
```

---

## STORAGE RLS

### From Migration 08_add_storage_rls_policy.sql

```sql
-- Storage bucket RLS for document access
CREATE POLICY "Users can view documents" ON storage.objects
  FOR SELECT
  TO public
  USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = get_user_yacht_id()::text
  );
```

**Pattern:** Documents stored as `documents/{yacht_id}/filename.pdf`

### Gap: No Write Policy Verified
- Can users upload documents to their yacht? Unknown.
- Can users upload to other yachts? Unknown.

---

## RECOMMENDATIONS

1. **Verify RLS on all PMS tables** via Supabase dashboard
2. **Add RLS test suite** using real user tokens (not service key)
3. **Enable JWT hook** to populate yacht_id in JWT claims
4. **Document all storage access patterns** and verify bucket policies
