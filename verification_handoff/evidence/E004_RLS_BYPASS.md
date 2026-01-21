# E004: RLS BYPASS VULNERABILITIES

**Date:** 2026-01-20
**Phase:** 3 - Tenant Isolation (RLS + Code)
**Status:** CRITICAL VULNERABILITIES FOUND

---

## Summary

| Severity | Count | Impact |
|----------|-------|--------|
| 🔴 CRITICAL | 6 | Cross-yacht data modification |
| 🟠 HIGH | 1 | Cross-yacht information disclosure |

---

## 🔴 CRITICAL: Missing yacht_id Filters

### RLS-001: Work Order Status Update
**File:** `apps/api/actions/action_executor.py`
**Line:** 1355

```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).execute()
# MISSING: .eq("yacht_id", yacht_id)
```

**Impact:** Update ANY work order across ANY yacht by providing its ID.

---

### RLS-002: Work Order Metadata Update
**File:** `apps/api/actions/action_executor.py`
**Line:** 1497

```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).execute()
# MISSING: .eq("yacht_id", yacht_id)
```

**Impact:** Modify metadata of work orders on other yachts.

---

### RLS-003: Purchase Status Read
**File:** `apps/api/actions/action_executor.py`
**Line:** 1922

```python
current = self.db.table("purchases").select("status").eq("id", entity_id).single().execute()
# MISSING: .eq("yacht_id", yacht_id)
```

**Impact:** Read purchase data from other yachts.

---

### RLS-004: Checklist Item Access
**File:** `apps/api/actions/action_executor.py`
**Line:** 1982

```python
current = self.db.table("checklist_items").select("notes").eq("id", entity_id).single().execute()
# MISSING: .eq("yacht_id", yacht_id)
```

**Impact:** Read/modify checklist items on other yachts.

---

### RLS-005: Handover Update
**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Line:** 255

```python
result = supabase.table("handovers").update({
    "content": content,
    "updated_at": datetime.utcnow().isoformat(),
    "updated_by": params["user_id"],
}).eq("id", params["handover_id"]).execute()
# MISSING: .eq("yacht_id", params["yacht_id"])
```

**Impact:** Modify handover documents on other yachts.

---

### RLS-006: Document Soft-Delete
**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Line:** 449

```python
result = supabase.table("documents").update({
    "deleted_at": datetime.utcnow().isoformat(),
    ...
}).eq("id", params["document_id"]).execute()
# MISSING: .eq("yacht_id", params["yacht_id"])
```

**Impact:** Delete documents on other yachts.

---

## 🟠 HIGH: Information Disclosure

### RLS-007: Parts Query
**File:** `apps/api/handlers/work_order_mutation_handlers.py`
**Line:** 914

```python
part_res = self.db.table("pms_parts").select("id, name, part_number, quantity_on_hand").eq("id", wp["part_id"]).limit(1).execute()
# MISSING: .eq("yacht_id", yacht_id)
```

**Impact:** View parts inventory from other yachts.

---

## Attack Vector

### Cross-Tenant Data Access

1. Attacker authenticates to their yacht (yacht_id = A)
2. Attacker discovers entity ID from another yacht (yacht_id = B)
   - Via URL sharing, logs, or enumeration
3. Attacker calls update endpoint with cross-yacht entity_id
4. Query runs: `.eq("id", entity_id).execute()`
5. Since yacht_id is not filtered, entity from yacht B is modified

### Proof of Concept

```bash
# Authenticated as user on yacht A
# Attempt to update work order from yacht B
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $YACHT_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_work_order_status",
    "context": {"yacht_id": "YACHT_A_ID"},
    "payload": {"work_order_id": "YACHT_B_WORK_ORDER_ID", "status": "cancelled"}
  }'

# With bug: Work order from yacht B gets cancelled
# With fix: 404 Not Found (yacht_id filter prevents access)
```

---

## Required Fix Pattern

### Before (INSECURE):
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).execute()
```

### After (SECURE):
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).eq("yacht_id", yacht_id).execute()
```

---

## Why Service Role Key Bypasses RLS

The backend uses `SUPABASE_SERVICE_ROLE_KEY` which:
- Bypasses ALL Row Level Security policies
- Has full database access
- Makes RLS policies ineffective at the DB level

**This means code-level filtering is MANDATORY.**

---

## Affected Files

1. `apps/api/actions/action_executor.py` - Lines 1355, 1497, 1922, 1982
2. `apps/api/action_router/dispatchers/internal_dispatcher.py` - Lines 255, 449
3. `apps/api/handlers/work_order_mutation_handlers.py` - Line 914

---

**Evidence File:** E004_RLS_BYPASS.md
**Created:** 2026-01-20
**Auditor:** Claude B
