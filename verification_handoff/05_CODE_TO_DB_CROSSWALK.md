# 05_CODE_TO_DB_CROSSWALK.md — Code vs Database Reality

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Purpose:** Cross-examine code table/RPC references against actual DB

---

## METHODOLOGY

For each domain:
1. Identify code files that reference tables/RPCs
2. List expected tables, columns, types
3. Verify existence via API query
4. Mark as VALID, BROKEN, or DEAD CODE

---

## DOMAIN 1: AUTH / BOOTSTRAP / TENANT RESOLUTION

### Code Files
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/lib/authHelpers.ts`
- `apps/api/routes/bootstrap_routes.py` (presumed)

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `auth.users` | Supabase internal | id, email, user_metadata | ✅ YES | VALID |
| `auth_users_profiles` | RLS policies | user_id, yacht_id | ✅ YES (E003) | VALID |

### RPCs Referenced

| RPC | Code Location | Parameters | Exists? | Verdict |
|-----|---------------|------------|---------|---------|
| `get_my_bootstrap` | AuthContext.tsx:117 | (none) | NOT TESTED | UNKNOWN |

### Notes
- Frontend calls Render `/v1/bootstrap`, not Supabase RPC directly
- Bootstrap relies on Render having MASTER DB access
- Currently blocked by B001 (JWT mismatch)

---

## DOMAIN 2: SEARCH REQUESTS + HANDLER EXECUTION

### Code Files
- `apps/web/src/hooks/useCelesteSearch.ts`
- `apps/web/src/lib/apiClient.ts`
- `apps/api/pipeline_service.py`

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `work_orders` | graphrag_query.py | id, yacht_id, title, status | ✅ YES | VALID |
| `equipment` | graphrag_query.py | id, yacht_id, name | ✅ YES | VALID |
| `documents` | graphrag_query.py | id, yacht_id, filename | ✅ YES | VALID |
| `pms_work_orders` | graphrag_query.py | Same as work_orders | ✅ YES | VALID |
| `pms_equipment` | graphrag_query.py | Same as equipment | ✅ YES | VALID |
| `pms_parts` | graphrag_query.py | id, yacht_id, name | ✅ YES | VALID |

### RPCs Referenced

| RPC | Code Location | Parameters | Exists? | Verdict |
|-----|---------------|------------|---------|---------|
| `unified_search_v2` | useCelesteSearch.ts | search_query | ❌ NO (E019) | BROKEN |
| `vector_search` | Not found | - | NOT TESTED | UNKNOWN |

### Notes
- Primary search goes through Render pipeline, not Supabase RPC
- Fallback Supabase search RPCs are broken (B003)
- Table references are correct, RPC signatures are wrong

---

## DOMAIN 3: EMAIL WATCHER + EMAIL TABLES

### Code Files
- `apps/web/src/hooks/useEmailData.ts`
- `apps/web/src/lib/email/oauth-utils.ts`
- `apps/api/routes/email_routes.py` (presumed)

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `email_threads` | useEmailData.ts | id, yacht_id, subject | ✅ YES (E007) | VALID |
| `email_messages` | useEmailData.ts | id, thread_id, body | ✅ YES | VALID |
| `email_watchers` | useEmailData.ts | id, yacht_id, sync_status | ✅ YES (E013) | VALID |
| `email_links` | useEmailData.ts | id, email_id, entity_id | ✅ YES | VALID |
| `email_attachments` | useEmailData.ts | id, message_id, filename | ✅ YES | VALID |
| `api_tokens` | oauth-utils.ts | id, user_id, provider | ✅ YES | VALID |

### RPCs Referenced

| RPC | Code Location | Parameters | Exists? | Verdict |
|-----|---------------|------------|---------|---------|
| None directly | - | - | - | - |

### Notes
- Email tables verified with data
- OAuth flow not runtime tested (U009)
- RLS verified working (E007)

---

## DOMAIN 4: DOCUMENT VIEWER + STORAGE PATHS

### Code Files
- `apps/web/src/lib/documentLoader.ts`
- `apps/web/src/components/DocumentViewer.tsx`
- `apps/web/src/lib/apiClient.ts` (documentsApi)

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `documents` | documentLoader.ts | id, yacht_id, storage_path, filename | ✅ YES (E012) | VALID |

### Storage Buckets Referenced

| Bucket | Code Location | Exists? | Verdict |
|--------|---------------|---------|---------|
| `documents` | documentLoader.ts | ✅ YES (E014) | VALID |

### Notes
- Path validation code exists: `storagePath.startsWith(\`${yachtId}/\`)`
- Not runtime tested (U013)
- 2760 documents in database

---

## DOMAIN 5: HANDOVER WRITE PATH

### Code Files
- `apps/api/handlers/handover_handlers.py` (presumed)
- `apps/api/action_router/dispatchers/internal_dispatcher.py`

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `handovers` | handlers/*.py | id, yacht_id, title, status | ✅ YES (E010) | VALID |
| `handover_items` | handlers/*.py | id, yacht_id, handover_id, summary | ✅ YES (E011) | VALID |
| `pms_handover` | e2e_sandbox.py | id, yacht_id | ✅ YES | VALID |
| `handover_drafts` | handlers/*.py | id, yacht_id | NOT TESTED | UNKNOWN |
| `handover_signoffs` | handlers/*.py | id, handover_id | NOT TESTED | UNKNOWN |

### RPCs Referenced

| RPC | Code Location | Parameters | Exists? | Verdict |
|-----|---------------|------------|---------|---------|
| `create_handover_draft` | - | - | ✅ YES | VALID |
| `sign_handover_incoming` | - | - | ✅ YES | VALID |
| `sign_handover_outgoing` | - | - | ✅ YES | VALID |

### Notes
- Core handover tables verified with data
- add_to_handover action has reported error (B005)
- Needs runtime verification

---

## DOMAIN 6: AUDIT LOG WRITE PATH

### Code Files
- `apps/api/handlers/*.py` (MUTATE actions)
- `apps/api/action_router/dispatchers/internal_dispatcher.py`

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `audit_logs` | handlers/*.py | id, yacht_id, action, user_id, timestamp | NOT TESTED | UNKNOWN |
| `activity_log` | - | - | NOT TESTED | UNKNOWN |

### Notes
- MUTATE actions should write audit logs per ActionVariant spec
- **NOT VERIFIED** — Claude A did not check audit table population
- Critical for compliance, must be verified by Claude B

---

## DOMAIN 7: WORK ORDER MUTATIONS

### Code Files
- `apps/api/handlers/work_order_mutation_handlers.py`

### Tables Referenced

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `pms_work_orders` | work_order_mutation_handlers.py:333 | id, yacht_id, title, status, equipment_id | ✅ YES | VALID |
| `pms_work_order_notes` | work_order_mutation_handlers.py:488 | id, work_order_id, note, created_by | ✅ YES | VALID |
| `pms_work_order_parts` | work_order_mutation_handlers.py:778 | id, work_order_id, part_id, quantity | ✅ YES | VALID |
| `pms_faults` | work_order_mutation_handlers.py:72 | id, fault_number | ✅ YES | VALID |
| `pms_equipment` | work_order_mutation_handlers.py:192 | id, name | ✅ YES | VALID |
| `pms_parts` | work_order_mutation_handlers.py:570 | id, name, quantity_on_hand | ✅ YES | VALID |

### Notes
- All core PMS tables exist and are valid
- Missing tables are in separate domain (B002)

---

## DOMAIN 8: MISSING PMS TABLES (BROKEN REFERENCES)

### Tables Referenced But Missing

| Table | Code Location | Columns Expected | Exists? | Verdict |
|-------|---------------|------------------|---------|---------|
| `pms_maintenance_schedules` | handlers/*.py | id, yacht_id, equipment_id | ❌ NO | BROKEN |
| `pms_certificates` | handlers/*.py | id, yacht_id, equipment_id | ❌ NO | BROKEN |
| `pms_service_contracts` | handlers/*.py | id, yacht_id | ❌ NO | BROKEN |
| `pms_schedule_templates` | handlers/*.py | id, yacht_id | ❌ NO | BROKEN |
| `pms_compliance_items` | handlers/*.py | id, yacht_id | ❌ NO | BROKEN |

### Notes
- These tables are referenced in code but don't exist in DB
- ~15 microactions blocked (B002)
- Migrations may be pending

---

## SUMMARY

| Domain | Tables | Valid | Broken | Unknown |
|--------|--------|-------|--------|---------|
| Auth/Bootstrap | 2 | 2 | 0 | 0 |
| Search | 6 | 6 | 0 | 0 |
| Email | 6 | 6 | 0 | 0 |
| Documents | 1 | 1 | 0 | 0 |
| Handover | 5 | 3 | 0 | 2 |
| Audit | 2 | 0 | 0 | 2 |
| Work Order | 6 | 6 | 0 | 0 |
| Missing PMS | 5 | 0 | 5 | 0 |
| **Total** | **33** | **24** | **5** | **4** |

| Domain | RPCs | Valid | Broken | Unknown |
|--------|------|-------|--------|---------|
| Auth | 1 | 0 | 0 | 1 |
| Search | 2 | 0 | 1 | 1 |
| Handover | 3 | 3 | 0 | 0 |
| **Total** | **6** | **3** | **1** | **2** |

---

## ACTION ITEMS FOR CLAUDE B

1. **Verify Unknown Tables:** Query `handover_drafts`, `handover_signoffs`, `audit_logs`
2. **Verify Unknown RPCs:** Test `get_my_bootstrap`, `vector_search`
3. **Fix Broken Tables:** Run migrations for missing PMS tables or mark microactions as NOT_IMPLEMENTED
4. **Fix Broken RPCs:** Align `unified_search_v2` signature or remove dead code

