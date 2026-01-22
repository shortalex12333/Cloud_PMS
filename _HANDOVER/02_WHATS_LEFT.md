# 02 - WHAT'S LEFT TO DO

## Priority 1: Production Mutation Proofs (63 remaining)

**The main gap.** Each mutation action needs:

1. Execute the action via API
2. Query database to verify row was created/updated
3. Query audit_log to verify entry exists
4. (Optional) Screenshot UI showing result

### Actions Needing Mutation Proof

**Cluster: fix_something (4 mutations)**
- [ ] `add_fault_note`
- [ ] `add_fault_photo`
- [ ] `create_work_order_from_fault`
- [x] `acknowledge_fault` ← DONE (the 1 verified action)

**Cluster: do_maintenance (12 mutations)**
- [ ] `create_work_order`
- [ ] `mark_work_order_complete`
- [ ] `add_work_order_note`
- [ ] `add_work_order_photo`
- [ ] `add_parts_to_work_order`
- [ ] `assign_work_order`
- [ ] `mark_checklist_item_complete`
- [ ] `add_checklist_note`
- [ ] `add_checklist_photo`
- [ ] `add_worklist_task`
- [ ] `update_worklist_progress`
- [ ] `export_worklist`

**Cluster: manage_equipment (1 mutation)**
- [ ] `add_equipment_note`

**Cluster: control_inventory (2 mutations)**
- [ ] `order_part`
- [ ] `log_part_usage`

**Cluster: communicate_status (8 mutations)**
- [ ] `add_to_handover`
- [ ] `add_document_to_handover`
- [ ] `add_predictive_insight_to_handover`
- [ ] `edit_handover_section`
- [ ] `regenerate_handover_summary`
- [ ] `upload_photo`
- [ ] `record_voice_note`
- [ ] `export_fleet_summary`

**Cluster: comply_audit (2 mutations)**
- [ ] `update_hours_of_rest`
- [ ] `tag_for_survey`

**Cluster: procure_suppliers (6 mutations)**
- [ ] `create_purchase_request`
- [ ] `add_item_to_purchase`
- [ ] `approve_purchase`
- [ ] `upload_invoice`
- [ ] `log_delivery_received`
- [ ] `update_purchase_status`

**Estimated Time:** ~15 min per action × 63 = **~16 hours**

---

## Priority 2: Fix Test Payload Mismatches (10 fixes)

Tests use wrong field names. Quick fixes:

| Test File | Action | Change `photo` to `photo_url` |
|-----------|--------|-------------------------------|
| nl_to_action_mapping.spec.ts | add_fault_photo | Yes |
| nl_to_action_mapping.spec.ts | add_work_order_photo | Yes |
| nl_to_action_mapping.spec.ts | add_checklist_photo | Yes |
| nl_to_action_mapping.spec.ts | upload_photo | Yes |

| Test File | Action | Change `assignee_id` to `assigned_to` |
|-----------|--------|---------------------------------------|
| nl_to_action_mapping.spec.ts | assign_work_order | Yes |

| Test File | Action | Other Changes |
|-----------|--------|---------------|
| nl_to_action_mapping.spec.ts | open_vessel | `yacht_id` → `vessel_id` |
| nl_to_action_mapping.spec.ts | view_document_section | Add `section_id` |
| nl_to_action_mapping.spec.ts | mark_work_order_complete | Add `completion_notes`, `signature` |

**Estimated Time:** ~5 min per fix × 10 = **~1 hour**

---

## Priority 3: Security Pen Testing (13 patches)

Patches were applied but not tested:

| Patch | Description | Test Method |
|-------|-------------|-------------|
| P0-001 | SQL injection in search | Try `'; DROP TABLE--` |
| P0-002 | Auth bypass on /execute | Test without token |
| P0-003 | Missing tenant isolation | Query other tenant's data |
| P0-004 | Hardcoded credentials | Grep for secrets |
| P0-005 | Insecure file upload | Upload .exe, check execution |
| P0-006 | Missing rate limiting | Burst 1000 requests |
| P0-007 | XSS in error messages | Inject `<script>` |
| P0-008 | CSRF on mutations | Test cross-origin POST |

**Estimated Time:** ~30 min per patch × 13 = **~6.5 hours**

---

## Priority 4: Edge Case Tests

Many edge cases defined in `microaction_registry.ts` but not tested:

- Invalid UUIDs
- Null values
- Permission denied scenarios
- Concurrent modifications
- Very long strings
- Special characters

**Estimated Time:** ~10 hours

---

## Priority 5: Performance Baselines

No performance data exists:

- [ ] Response time per action
- [ ] Concurrent user handling
- [ ] Database query performance
- [ ] Memory usage under load

**Estimated Time:** ~5 hours

---

## TOTAL REMAINING WORK

| Task | Hours |
|------|-------|
| Mutation proofs | 16 |
| Payload fixes | 1 |
| Security testing | 6.5 |
| Edge cases | 10 |
| Performance | 5 |
| **TOTAL** | **~38 hours** |

---

## SUGGESTED ORDER

1. **First:** Fix payload mismatches (1 hour) - makes future tests accurate
2. **Second:** Mutation proofs for high-value actions (8 hours)
   - `create_work_order`
   - `add_fault_note`
   - `mark_work_order_complete`
   - `order_part`
3. **Third:** Remaining mutation proofs (8 hours)
4. **Fourth:** Security testing (6.5 hours)
5. **Fifth:** Edge cases and performance (15 hours)

---

*Updated: 2026-01-22*
