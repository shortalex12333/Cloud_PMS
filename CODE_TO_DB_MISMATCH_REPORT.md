# CODE TO DATABASE MISMATCH REPORT

**Generated:** 2026-01-18
**Method:** grep + REST API introspection

---

## SUMMARY

| Category | Count |
|----------|-------|
| Tables referenced in code | 35 |
| Tables that exist | 18 |
| Tables that DO NOT exist | 17 |
| Placeholder IDs in code | 5 locations |
| Broken code paths | 40+ |

---

## CROSS-CHECK MATRIX

### MISSING TABLES (BROKEN)

| Code Reference | Expected Table | Exists | Verdict |
|---------------|----------------|--------|---------|
| `useEmailData.ts:476` | `crew_members` | NO | **BROKEN (MISSING TABLE)** |
| `lib/auth.ts:74` | `auth_users` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/faults.ts:570` | `attachments` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/faults.ts:209` | `maintenance_templates` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/faults.ts:483` | `notes` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:620` | `attachments` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:209` | `audit_log` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:121` | `checklist_items` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:472` | `notes` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:141` | `work_order_parts` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/workOrders.ts:1119` | `worklist_items` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/compliance.ts:24` | `hours_of_rest` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/compliance.ts:379` | `survey_tags` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/procurement.ts:37` | `purchase_requests` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/procurement.ts:138` | `purchase_request_items` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/procurement.ts:299` | `invoices` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/procurement.ts:470` | `deliveries` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/inventory.ts:190` | `purchase_requests` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/inventory.ts:266` | `work_order_parts` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/equipment.ts:487` | `sensor_readings` | NO | **BROKEN (MISSING TABLE)** |
| `handlers/equipment.ts:626` | `notes` | NO | **BROKEN (MISSING TABLE)** |
| `dispatchers.ts:21` | `pms_equipment_notes` | NO | **BROKEN (MISSING TABLE)** |

### EXISTING TABLES (VALID)

| Code Reference | Expected Table | Exists | Verdict |
|---------------|----------------|--------|---------|
| Various | `pms_equipment` | YES | **VALID** |
| Various | `pms_faults` | YES | **VALID** |
| Various | `pms_parts` | YES | **VALID** |
| Various | `pms_work_orders` | YES | **VALID** |
| Various | `pms_work_order_notes` | YES | **VALID** |
| Various | `pms_work_order_parts` | YES | **VALID** |
| Various | `handovers` | YES | **VALID** |
| Various | `handover_items` | YES | **VALID** |
| Various | `email_threads` | YES | **VALID** |
| Various | `email_watchers` | YES | **VALID** |
| Various | `documents` | YES | **VALID** |
| Various | `document_chunks` | YES | **VALID** |
| Various | `search_document_chunks` | YES | **VALID** |
| Various | `action_executions` | YES | **VALID** |
| Various | `graph_edges` | YES | **VALID** |
| Various | `auth_microsoft_tokens` | YES | **VALID** |
| Various | `auth_signatures` | YES | **VALID** |
| Various | `auth_users_profiles` | YES | **VALID** |

---

## PLACEHOLDER IDs IN CODE

| File | Line | Placeholder |
|------|------|-------------|
| `AddRelatedModal.tsx` | 34 | `placeholder-yacht-id` |
| `AddRelatedModal.tsx` | 35 | `placeholder-user-id` |
| `NavigationContext.tsx` | 123 | `placeholder-yacht-id` |
| `NavigationContext.tsx` | 124 | `placeholder-user-id` |
| `supabaseClient.ts` | 15 | `placeholder.supabase.co`, `placeholder-key` |

**Impact:** Any code path that uses these placeholders will fail with UUID parsing errors.

---

## yacht_id RESOLUTION PATHS

### Path 1: AuthContext → Bootstrap API
```
Login → Supabase Auth → AuthContext.handleSession()
  → POST /v1/bootstrap (Render API)
  → Returns: { yacht_id, role, tenant_key_alias }
  → Stored in: AuthContext.user.yachtId
```
**Status:** ✅ WORKS (yacht_id is returned and stored)

### Path 2: useCelesteSearch → getYachtId()
```
useCelesteSearch → buildSearchPayload()
  → getYachtId() from authHelpers.ts
  → Reads: session.user.user_metadata.yacht_id
  → Returns: NULL
```
**Status:** ❌ BROKEN

**Root Cause:** `getYachtId()` reads from `user_metadata.yacht_id` which is NEVER SET. The yacht_id from bootstrap is stored in `AuthContext.user.yachtId`, not in Supabase session metadata.

### Path 3: NavigationContext → Placeholder Fallback
```
NavigationContext.pushViewer()
  → state.yachtId || 'placeholder-yacht-id'
  → state.yachtId is NULL (never initialized from AuthContext)
  → Uses placeholder
```
**Status:** ❌ BROKEN

### Path 4: Microaction Handlers → Direct Table Access
```
Handler → supabase.from('table_name')
  → Table does not exist
  → RPC error or silent failure
```
**Status:** ❌ BROKEN (17 tables missing)

---

## NAMING INCONSISTENCIES

| Context | Name Used | Expected |
|---------|-----------|----------|
| AuthContext | `yachtId` (camelCase) | `yacht_id` |
| user_metadata | `yacht_id` | `yacht_id` |
| API payloads | `yacht_id` | `yacht_id` |
| NavigationContext | `yachtId` | (should match AuthContext) |

---

## TYPE MISMATCHES

| Column | Code Expects | DB Type | Match |
|--------|--------------|---------|-------|
| `yacht_id` | `string` | `uuid` | ✅ Compatible |
| `user_id` | `string` | `uuid` | ✅ Compatible |
| `id` (various) | `string` | `uuid` | ✅ Compatible |

---

## DEAD CODE

| File | Line | Reason |
|------|------|--------|
| All microaction handlers in `/handlers/compliance.ts` | * | References non-existent `hours_of_rest` table |
| All microaction handlers in `/handlers/procurement.ts` | * | References non-existent `purchase_requests`, `invoices`, `deliveries` tables |
| `useEmailData.ts:476` | 476 | References non-existent `crew_members` table |
| `lib/auth.ts:74` | 74 | References non-existent `auth_users` table |
