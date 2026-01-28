# Work Order Lens P1: Show Related — PHASE 0: EXTRACTION GATE

**Feature:** Show Related Entities for Work Orders
**Priority:** P1 (High)
**Status:** Planning
**Date:** 2026-01-28

---

## Purpose

Define the **entry criteria** and **scope boundaries** for P1 Show Related implementation. This phase ensures we have DB truth, clear contracts, and no UI-invented data before writing code.

---

## Extraction Gate Checklist

### ✅ Prerequisites Met

- [x] **P0 Complete:** Work Order Lens P0 deployed and validated (12/12 staging tests)
- [x] **DB Schema Ready:** `pms_entity_links` table exists with RLS policies
- [x] **RLS Helpers Deployed:** `is_hod()`, `is_manager()` zero-arg wrappers
- [x] **Contract Defined:** `SHOW_RELATED.md` specifies deterministic groups and match reasons
- [x] **Role Strings Canonical:** crew, chief_engineer, chief_officer, captain, manager

### ✅ Scope Definition

**IN SCOPE:**
- View related entities for a given work order (FK joins + explicit links)
- Add explicit entity links (HOD/manager only)
- Deterministic match reasons (FK, same_equipment, explicit_link, mentions)
- Five entity groups: parts, manuals, previous_work, handovers, attachments
- Metadata-only returns for restricted storage (no presigned URLs)

**OUT OF SCOPE:**
- UI-invented suggestions or "smart recommendations"
- Full-text search across all work order descriptions
- File content analysis or OCR
- Cross-yacht entity discovery
- Automatic link creation (all links explicit)

### ✅ Quality Gates

- **No 500 errors:** All client errors mapped to 4xx (400, 403, 404, 409)
- **RLS Deny-by-Default:** All queries scoped to `yacht_id = get_user_yacht_id()`
- **Deterministic Results:** Same input → same output (no randomness, no ML)
- **Role Gating Strict:** Only documented roles can execute actions
- **Audit Trail:** All mutations logged to `pms_audit_log`

### ✅ Success Criteria

- [ ] 8 phase documents complete
- [ ] 2 actions registered: `view_related_entities` (READ), `add_entity_link` (MUTATE)
- [ ] 2 endpoints: GET `/v1/related`, POST `/v1/related/add`
- [ ] Docker tests: 6+ scenarios (role gating, isolation, edge cases)
- [ ] Staging CI: Real JWT validation, zero 500s
- [ ] Frontend integration: Side panel renders backend payload only

---

## Risk Assessment

### Technical Risks

1. **FK Join Performance:** Multiple FK joins for related entities
   - **Mitigation:** Use indexed columns, limit result sets (top 10 per group)
   - **Fallback:** Add materialized view if queries >500ms

2. **Storage Metadata Leaks:** Returning metadata for restricted files
   - **Mitigation:** Only return metadata if user has read permission to entity (not file)
   - **Contract:** Frontend must not show download button if `file_access: false`

3. **Link Duplicates:** User adds same link twice
   - **Mitigation:** Add unique constraint on (source, target, link_type) or handle 409

### Security Risks

1. **Cross-Yacht Leakage:** Related entities from other yachts
   - **Mitigation:** All queries filter `yacht_id = get_user_yacht_id()`
   - **Testing:** Explicit cross-yacht test in Docker suite

2. **Role Escalation:** Crew adds entity links
   - **Mitigation:** Action registry enforces allowed_roles, RLS policy on INSERT
   - **Testing:** Crew POST → 403 test

---

## Dependencies

### Database
- ✅ `pms_entity_links` table (exists from P0)
- ✅ `pms_work_orders`, `pms_parts`, `pms_equipment` (FK sources)
- ✅ `pms_work_order_parts` (join table)
- ⏳ Optional: `v_related_parts_for_wo`, `v_related_docs_for_wo` views

### Backend
- ✅ Action router registry pattern
- ✅ RLS helper functions (`is_hod`, `is_manager`)
- ⏳ New: `RelatedHandlers` module
- ⏳ New: Routes for `/v1/related` endpoints

### Frontend
- ✅ "Show Related" UI toggle (exists in work order detail)
- ⏳ Integration: Call GET `/v1/related` on toggle
- ⏳ Render: Display groups with match_reason chips
- ⏳ Add Mode: POST to `/v1/related/add` on selection

---

## Acceptance Criteria

### Functional
- Work order detail shows "Related" section with 5 groups
- Each related item shows: entity_type, title, match_reasons[]
- HOD can add explicit links via "Add Related" button
- Crew can view related but cannot add links

### Non-Functional
- P95 latency <500ms for GET `/v1/related`
- Zero 500 errors (4xx for all client errors)
- Results deterministic (same WO → same results every time)
- RLS enforced (cross-yacht → 404/403, not data leak)

---

## Next Phase

**PHASE 1: SCOPE** - Define exact entity types, FK relationships, and match reason taxonomy.

---

**GATE STATUS:** ✅ READY TO PROCEED
