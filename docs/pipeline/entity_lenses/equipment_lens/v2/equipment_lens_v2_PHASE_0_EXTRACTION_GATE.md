# Equipment Lens v2 - PHASE 0: EXTRACTION GATE

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 0 is the extraction gate. Before any design work begins, we must answer:
1. Is equipment a distinct entity that warrants its own lens?
2. What is the canonical data source?
3. What are the hard boundaries?

---

## EXTRACTION CRITERIA

### 1. Entity Independence

| Question | Answer | Evidence |
|----------|--------|----------|
| Does equipment have its own primary table? | **YES** | `pms_equipment` (24 columns, 560 rows) |
| Does equipment have unique identifiers? | **YES** | `id` (uuid), `code` (human-readable) |
| Can equipment exist without parent entities? | **YES** | Root equipment has `parent_id = NULL` |
| Does equipment have its own lifecycle? | **YES** | Status: operational → degraded → failed → maintenance → decommissioned |

### 2. Action Distinctness

| Question | Answer | Evidence |
|----------|--------|----------|
| Are there mutations specific to equipment? | **YES** | Status updates, decommission, attention flags |
| Can actions be performed without other lenses? | **YES** | Status change is equipment-only |
| Does equipment require its own role gating? | **YES** | Engineers manage, crew view |

### 3. Query Patterns

| Question | Answer | Evidence |
|----------|--------|----------|
| Do users search for equipment directly? | **YES** | "Generator #1", "watermaker", "engine room equipment" |
| Is equipment a focus target? | **YES** | Users focus on equipment to see detail + actions |
| Does equipment have distinct read patterns? | **YES** | Hierarchy, attention flags, status filtering |

---

## CANONICAL DATA SOURCE

**Primary Table**: `pms_equipment`

**Source of Truth**: Production Supabase Database

**Verification Method**:
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'pms_equipment'
ORDER BY ordinal_position;
```

**Row Count Verification**:
```sql
SELECT COUNT(*) FROM pms_equipment WHERE deleted_at IS NULL;
-- Expected: ~560 rows
```

---

## HARD BOUNDARIES

### What Equipment Lens OWNS

| Aspect | Scope |
|--------|-------|
| Equipment CRUD | Create, Read, Update (status/attention), Soft-delete |
| Equipment hierarchy | Parent-child relationships |
| Equipment status lifecycle | operational ↔ degraded ↔ failed ↔ maintenance → decommissioned |
| Attention flag management | Set, clear, reason tracking |
| Equipment notes | Notes specifically attached to equipment |
| Equipment attachments | Photos/docs attached to equipment |
| Equipment parts BOM | Link parts to equipment |

### What Equipment Lens DOES NOT OWN

| Aspect | Owned By | Escape Hatch |
|--------|----------|--------------|
| Fault creation/management | Fault Lens | `view_equipment_faults` → focus fault |
| Work order creation/management | Work Order Lens | `create_work_order_for_equipment` → creates WO, escapes |
| Part inventory/purchasing | Part Lens / Shopping Lens | `view_equipment_parts` → focus part |
| Document storage/metadata | Document Lens | Attachment click → focus document |
| Crew assignment/management | Crew Lens | Note author click → focus crew |

### Cross-Lens Interactions

```
Equipment Lens
    │
    ├──► Fault Lens (equipment_id FK)
    │        - Equipment failures create faults
    │        - Faults reference equipment
    │
    ├──► Work Order Lens (equipment_id FK)
    │        - Equipment maintenance creates WOs
    │        - WOs execute against equipment
    │
    ├──► Part Lens (via pms_equipment_parts_bom)
    │        - Equipment has BOM
    │        - Parts consumed for equipment
    │
    └──► Document Lens (via pms_attachments)
             - Equipment has photos/docs
             - Documents linked to equipment
```

---

## EXTRACTION DECISION

| Criterion | Status |
|-----------|--------|
| Entity independence | ✅ PASS |
| Action distinctness | ✅ PASS |
| Query patterns | ✅ PASS |
| Clear boundaries | ✅ PASS |

**DECISION**: Equipment is a valid, independent lens. Proceed to Phase 1.

---

## DEPENDENCIES

### Required Before Equipment Lens

| Dependency | Status | Notes |
|------------|--------|-------|
| `pms_equipment` table | ✅ Exists | 24 columns deployed |
| `pms_equipment_parts_bom` table | ✅ Exists | BOM linkage |
| `pms_notes` table | ✅ Exists | Note storage |
| `pms_attachments` table | ✅ Exists | File metadata |
| `public.get_user_yacht_id()` | ✅ Deployed | Yacht isolation |
| `public.get_user_role()` | ✅ Deployed | Role detection |
| `public.is_hod()` | ⚠️ VERIFY | Boolean helper |
| `public.is_manager()` | ⚠️ VERIFY | Boolean helper |
| Equipment RLS policies | ✅ Deployed | Canonical pattern |

### Required For Full Functionality

| Dependency | Status | Notes |
|------------|--------|-------|
| `pms_notifications` table | ❌ NEW | For attention/failure alerts |
| Storage bucket policies | ⚠️ VERIFY | For file uploads |
| Notes RLS | ⚠️ VERIFY | For note creation |
| Attachments RLS | ⚠️ VERIFY | For file uploads |

---

## NEXT PHASE

Proceed to **PHASE 1: SCOPE** to define:
- Complete action inventory
- Role permission matrix
- Scenario categories
- Acceptance criteria outline

---

**END OF PHASE 0**
