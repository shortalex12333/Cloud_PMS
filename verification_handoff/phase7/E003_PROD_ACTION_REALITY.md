# E003: PRODUCTION API ACTION REALITY

**Date:** 2026-01-21
**Phase:** 7 - System Reality Extraction
**Status:** COMPLETE

---

## Summary

Probed all 46 registered actions against production API to determine deployment status.

**Critical Finding:** 16 actions (35%) registered in code are NOT deployed to production.

---

## API Endpoint

```
POST https://pipeline-core.int.celeste7.ai/v1/actions/execute
```

---

## Classification Rules

| HTTP Status | Classification | Meaning |
|-------------|----------------|---------|
| 200, 201 | EXISTS | Action deployed and functional |
| 400, 422 | EXISTS_SCHEMA | Action deployed, payload validation failed |
| 401, 403 | EXISTS_GATED | Action deployed, auth check failed |
| 404 | NOT_FOUND | Action NOT deployed (FAIL) |
| 500, 502 | EXISTS_ERROR | Action deployed, handler error |

---

## Results Summary

| Classification | Count | Percentage |
|----------------|-------|------------|
| EXISTS (200/201) | 23 | 50% |
| EXISTS_SCHEMA (400/422) | 6 | 13% |
| EXISTS_ERROR (500) | 1 | 2% |
| NOT_FOUND (404) | **16** | **35%** |
| **Total** | **46** | 100% |

---

## Actions That EXIST (29 total)

### Fully Functional (200/201) - 23 actions

| Action | Status | Notes |
|--------|--------|-------|
| acknowledge_fault | 200 | Works |
| add_fault_photo | 200 | Works |
| add_note_to_work_order | 200 | Works |
| add_parts_to_work_order | 200 | Works |
| add_wo_hours | 200 | Works |
| add_wo_note | 200 | Works |
| add_work_order_photo | 200 | Works |
| add_worklist_task | 200 | Works |
| cancel_work_order | 200 | Works |
| close_fault | 200 | Works |
| close_work_order | 200 | Works |
| create_work_order | 200 | Works |
| diagnose_fault | 200 | Works |
| export_worklist | 200 | Works |
| mark_fault_false_alarm | 200 | Works |
| reopen_fault | 200 | Works |
| start_work_order | 200 | Works |
| update_fault | 200 | Works |
| update_work_order | 200 | Works |
| view_fault_detail | 200 | Works |
| view_work_order_checklist | 200 | Works |
| view_work_order_detail | 200 | Works |
| view_worklist | 200 | Works |

### Schema Validation Failed (400) - 6 actions

| Action | Status | Error |
|--------|--------|-------|
| add_to_handover | 400 | Missing required field(s): title |
| assign_work_order | 400 | Schema mismatch |
| create_work_order_from_fault | 400 | Already has work order |
| report_fault | 400 | equipment_id mismatch |
| show_manual_section | 400 | Missing required field |
| update_equipment_status | 400 | Missing required field(s): new_status |

### Handler Error (500) - 1 action

| Action | Status | Error |
|--------|--------|-------|
| add_wo_part | 500 | Internal error |

---

## Actions NOT DEPLOYED (16 actions) - FAIL

| Action | HTTP Status | Error Message |
|--------|-------------|---------------|
| add_document_to_handover | 404 | Action not found or not implemented |
| add_fault_note | 404 | Action not found or not implemented |
| add_note | 404 | Action not found or not implemented |
| add_part_to_handover | 404 | Action not found or not implemented |
| add_predictive_to_handover | 404 | Action not found or not implemented |
| classify_fault | 404 | Action not found or not implemented |
| create_work_order_fault | 404 | Action not found or not implemented |
| delete_document | 404 | Document not found (misleading - action doesn't exist) |
| delete_shopping_item | 404 | Shopping list item not found (misleading) |
| edit_handover_section | 404 | Action not found or not implemented |
| export_handover | 404 | Action not found or not implemented |
| open_document | 404 | Action not found or not implemented |
| order_part | 404 | Action not found or not implemented |
| suggest_parts | 404 | Action not found or not implemented |
| update_worklist_progress | 404 | Action not found or not implemented |
| view_fault_history | 404 | Action not found or not implemented |

---

## Deployment Gap Analysis

### By Category

**Fully Missing from Production:**
- Document actions: `open_document`, `delete_document`, `add_document_to_handover`
- Handover actions: `add_part_to_handover`, `add_predictive_to_handover`, `edit_handover_section`, `export_handover`
- Fault advanced: `add_fault_note`, `classify_fault`, `suggest_parts`, `view_fault_history`
- Parts/Shopping: `order_part`, `delete_shopping_item`
- Worklist: `update_worklist_progress`
- Work order: `create_work_order_fault`
- Equipment: `add_note`

### Impact Assessment

| Category | Impact |
|----------|--------|
| Document handling | Users cannot open/delete documents via actions |
| Handover management | Limited handover functionality |
| Fault diagnostics | Advanced fault features unavailable |
| Parts ordering | No parts ordering via actions |

---

## Sample API Requests & Responses

### EXISTS (200)
```
Request:
POST /v1/actions/execute
{
  "action": "view_fault_detail",
  "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
  "payload": {"fault_id": "1f41d11f-1f0a-4735-8a12-e7a094f832a6"}
}

Response:
HTTP 200
{"status": "success", "action": "view_fault_detail", ...}
```

### NOT_FOUND (404)
```
Request:
POST /v1/actions/execute
{
  "action": "open_document",
  "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
  "payload": {"storage_path": "85fe1119-b04c-41ac-80f1-829d23322598/test.pdf"}
}

Response:
HTTP 404
{"detail": {"message": "Action 'open_document' not found or not implemented"}}
```

---

## Evidence Files

| File | Description |
|------|-------------|
| `phase7_step3_output.json` | Full probe results for all 46 actions |

---

## Conclusion

**35% of registered actions are not deployed to production.**

This represents a significant deployment drift between the codebase and production environment. Any feature that relies on these actions will fail at runtime.

**Recommended Actions:**
1. Decide: Deploy missing actions OR remove from registry
2. Update code registry to match production reality
3. Add deployment validation to CI/CD

---

**Document:** E003_PROD_ACTION_REALITY.md
**Completed:** 2026-01-21
