# PHASE 4: Microactions (71) Reality Check

**Date:** 2026-01-20T16:15:00Z
**User:** x@alex-short.com (captain role)
**Yacht:** 85fe1119-b04c-41ac-80f1-829d23322598 (M/Y Test Vessel)

## Summary

| Metric | Count |
|--------|-------|
| Total Actions | 71 |
| READ Actions | 34 |
| MUTATE Actions | 37 |
| Domains | 13 |

## BLOCKER: B001-AR (Action Router JWT Bug)

**CRITICAL**: The action router has the **same B001 bug** that was fixed in `auth.py`.

**File:** `apps/api/action_router/validators/jwt_validator.py`
**Lines:** 37-42

```python
jwt_secret = (
    os.getenv("TENANT_SUPABASE_JWT_SECRET") or   # ❌ TENANT first
    os.getenv("TENNANT_SUPABASE_JWT_SECRET") or
    os.getenv("MASTER_SUPABASE_JWT_SECRET") or   # ❌ MASTER should be first
    os.getenv("SUPABASE_JWT_SECRET")
)
```

**Error when calling `/v1/actions/execute`:**
```json
{"detail": "Invalid token: Signature verification failed"}
```

**Fix Required:** Apply same fix as `auth.py` - check MASTER secret first, then TENANT.

## Action Registry by Domain

### inventory (9 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_inventory_item | READ | ✅ |
| 2 | view_stock_levels | READ | |
| 3 | edit_inventory_quantity | MUTATE | |
| 4 | create_reorder | MUTATE | |
| 5 | view_part_location | READ | |
| 6 | view_part_usage | READ | |
| 7 | log_part_usage | MUTATE | |
| 8 | add_part | MUTATE | |
| 9 | scan_part_barcode | READ | |

### work_orders (11 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_work_order | READ | ✅ |
| 2 | create_work_order | MUTATE | |
| 3 | update_work_order_status | MUTATE | |
| 4 | view_work_order_history | READ | |
| 5 | mark_work_order_complete | MUTATE | |
| 6 | add_work_order_note | MUTATE | |
| 7 | add_work_order_photo | MUTATE | |
| 8 | add_parts_to_work_order | MUTATE | |
| 9 | view_work_order_checklist | READ | |
| 10 | assign_work_order | MUTATE | |
| 11 | edit_work_order_details | MUTATE | |

### fault (9 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_fault | READ | ✅ |
| 2 | run_diagnostic | READ | |
| 3 | log_symptom | MUTATE | |
| 4 | diagnose_fault | READ | |
| 5 | report_fault | MUTATE | |
| 6 | view_fault_history | READ | |
| 7 | suggest_parts | READ | |
| 8 | add_fault_note | MUTATE | |
| 9 | add_fault_photo | MUTATE | |

### equipment (6 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_equipment | READ | ✅ |
| 2 | view_maintenance_history | READ | |
| 3 | view_equipment_parts | READ | |
| 4 | view_linked_faults | READ | |
| 5 | view_equipment_manual | READ | |
| 6 | add_equipment_note | MUTATE | |

### handover (6 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | add_to_handover | MUTATE | |
| 2 | add_document_to_handover | MUTATE | |
| 3 | add_predictive_insight_to_handover | MUTATE | |
| 4 | edit_handover_section | MUTATE | |
| 5 | export_handover | READ | ✅ |
| 6 | regenerate_handover_summary | MUTATE | |

### purchasing (7 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | create_purchase_request | MUTATE | |
| 2 | add_item_to_purchase | MUTATE | |
| 3 | approve_purchase | MUTATE | |
| 4 | upload_invoice | MUTATE | |
| 5 | track_delivery | READ | ✅ |
| 6 | log_delivery_received | MUTATE | |
| 7 | update_purchase_status | MUTATE | |

### shipyard (5 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_worklist | READ | ✅ |
| 2 | add_worklist_task | MUTATE | |
| 3 | update_worklist_progress | MUTATE | |
| 4 | export_worklist | READ | |
| 5 | tag_for_survey | MUTATE | |

### checklists (4 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_checklist | READ | ✅ |
| 2 | mark_checklist_item_complete | MUTATE | |
| 3 | add_checklist_note | MUTATE | |
| 4 | add_checklist_photo | MUTATE | |

### hours_of_rest (4 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_hours_of_rest | READ | ✅ |
| 2 | update_hours_of_rest | MUTATE | |
| 3 | export_hours_of_rest | READ | |
| 4 | view_compliance_status | READ | |

### fleet (3 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_fleet_summary | READ | ✅ |
| 2 | open_vessel | READ | |
| 3 | export_fleet_summary | READ | |

### mobile (3 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_attachments | READ | ✅ |
| 2 | upload_photo | MUTATE | |
| 3 | record_voice_note | MUTATE | |

### manual (2 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | view_manual_section | READ | ✅ |
| 2 | view_related_docs | READ | |

### predictive (2 actions)
| # | action_id | Variant | Primary |
|---|-----------|---------|---------|
| 1 | request_predictive_insight | READ | ✅ |
| 2 | view_smart_summary | READ | |

## Action Rules Verification

| Rule | Status |
|------|--------|
| Every action has canonical action_id | ✅ |
| Every action is READ or MUTATE | ✅ |
| MUTATE actions are dropdown_only | ✅ Auto-enforced |
| Primary actions are READ only | ✅ Enforced in __post_init__ |
| MUTATE actions have audit level | ✅ Auto-set to FULL |

## MUTATE Actions Requiring Signature (17)

| action_id | Domain |
|-----------|--------|
| edit_inventory_quantity | inventory |
| create_reorder | inventory |
| add_part | inventory |
| create_work_order | work_orders |
| update_work_order_status | work_orders |
| mark_work_order_complete | work_orders |
| edit_work_order_details | work_orders |
| report_fault | fault |
| update_hours_of_rest | hours_of_rest |
| create_purchase_request | purchasing |
| approve_purchase | purchasing |
| log_delivery_received | purchasing |
| add_worklist_task | shipyard |

## Verdict

**PHASE 4: BLOCKED**

### Verified
- 71 microactions defined in registry
- Correct READ/MUTATE classification
- Primary action rules enforced
- MUTATE signature requirements in place
- Audit logging configured

### Blocked By
- **B001-AR**: Action router JWT validator uses TENANT secret first
- Cannot execute any actions via `/v1/actions/execute` until fixed

### Fix Required
Apply B001 fix pattern to `apps/api/action_router/validators/jwt_validator.py`:
- Try MASTER_SUPABASE_JWT_SECRET first
- Fall back to TENANT_SUPABASE_JWT_SECRET

## Evidence Files
- This report: `evidence/MICROACTIONS_matrix.md`
- Action registry: `apps/api/actions/action_registry.py`
- JWT validator (needs fix): `apps/api/action_router/validators/jwt_validator.py`
