# Routing Gaps Report

**Generated:** 2026-01-12
**Test Suite:** P6 E2E Adversarial Testing
**NORMAL+EDGE Pass Rate:** 69.2% (83/120 scenarios)

---

## Summary

37 scenarios in NORMAL+EDGE categories failed because the routing pipeline (Module A + IntentParser + Keyword Fallback + Entity Inference) could not match them to any action.

These represent **routing coverage gaps** - legitimate user queries that should map to actions but currently don't have patterns.

---

## NORMAL Category Gaps (21 scenarios)

| ID | Query | Expected Action | Priority |
|----|-------|-----------------|----------|
| N005 | "generate purchase request" | create_purchase_request | HIGH |
| N021 | "view document" | view_document | HIGH |
| N022 | "find related documents" | view_related_documents | MEDIUM |
| N023 | "suggest parts for equipment" | suggest_parts | MEDIUM |
| N024 | "view equipment parts" | view_equipment_parts | MEDIUM |
| N026 | "view part usage" | view_part_usage | LOW |
| N027 | "scan barcode 12345" | scan_part_barcode | MEDIUM |
| N028 | "view linked equipment" | view_linked_equipment | LOW |
| N029 | "view linked faults" | view_linked_faults | LOW |
| N033 | "view checklist" | view_checklist | HIGH |
| N036 | "open vessel dashboard" | open_vessel | MEDIUM |
| N038 | "request predictive insight" | request_predictive_insight | LOW |
| N039 | "view document section overview" | view_document_section | MEDIUM |
| N043 | "assign work order to engineer" | assign_work_order | HIGH |
| N046 | "edit handover section" | edit_handover_section | MEDIUM |
| N049 | "upload invoice" | upload_invoice | HIGH |
| N054 | "tag for survey" | tag_for_survey | LOW |
| N055 | "upload photo" | upload_photo | MEDIUM |
| N056 | "record voice note" | record_voice_note | LOW |
| N058 | "log delivery received" | log_delivery_received | HIGH |
| N060 | "view work order checklist" | view_work_order_checklist | HIGH |

---

## EDGE Category Gaps (16 scenarios)

| ID | Query | Expected Outcome | Issue Type |
|----|-------|------------------|------------|
| E007 | (empty query) | error | Missing null-check |
| E011 | "overheating" | success | Symptom-only query |
| E021 | "tell me about the pump" | success | Conversational query |
| E026 | "thanks" | acknowledgment | Contextual response |
| E027 | "yes" | confirmation | Contextual response |
| E028 | "no" | rejection | Contextual response |
| E029 | "cancel" | cancel | Contextual response |
| E033 | "find something" | success | Vague query |
| E035 | "when was last maintenance" | success | Natural language |
| E036 | "who assigned work order" | success | Natural language |
| E039 | "\"exact phrase search\"" | success | Quoted search |
| E040 | "manual.pdf" | success | Filename search |
| E047 | "work order 工作单" | success | Multilingual |
| E054 | "diagnose_fault_E047" | success | Snake_case |
| E056 | "view document with empty content" | success | Edge description |
| E058 | "export all fleet data" | success | Bulk export |

---

## Recommended Fixes

### High Priority (7 patterns needed)
These are common user flows with missing patterns:

1. **create_purchase_request** - Add pattern: `["generate", "create"] + ["purchase", "pr", "requisition"] + ["request", "order"]`
2. **view_document** - Add pattern: `["view", "show", "open"] + ["document", "doc", "file"]`
3. **view_checklist** - Add pattern: `["view", "show"] + ["checklist", "check list"]`
4. **assign_work_order** - Add pattern: `["assign", "reassign"] + ["work order", "wo", "task"] + ["to"]`
5. **upload_invoice** - Add pattern: `["upload", "attach"] + ["invoice", "receipt", "bill"]`
6. **log_delivery_received** - Add pattern: `["log", "record", "mark"] + ["delivery", "received", "arrived"]`
7. **view_work_order_checklist** - Add pattern: `["view", "show"] + ["work order"] + ["checklist"]`

### Medium Priority (8 patterns)
Secondary flows that enhance UX:

- view_related_documents, suggest_parts, view_equipment_parts
- scan_part_barcode, open_vessel, view_document_section
- edit_handover_section, upload_photo

### Contextual Responses (4 patterns)
These need state-machine context handling:

- "yes" / "no" / "cancel" / "thanks" → requires pending action context

---

## Module A Pattern File Location

Add patterns to: `apps/api/actions.json` under the appropriate action entry

Example format:
```json
{
  "action": "create_purchase_request",
  "patterns": [
    "generate purchase request",
    "create pr",
    "new purchase requisition"
  ],
  "requires_confirmation": true
}
```

---

## Impact Analysis

| Metric | Before Gaps Fixed | After Gaps Fixed (Est.) |
|--------|-------------------|-------------------------|
| NORMAL Pass Rate | 65.0% | ~95% |
| EDGE Pass Rate | 73.3% | ~90% |
| NORMAL+EDGE | 69.2% | ~93% |
| Total Coverage | 55.0% | ~85% |

---

## Next Steps

1. Add HIGH priority patterns to `actions.json`
2. Re-run E2E test suite
3. Verify NORMAL+EDGE >= 95%
4. Implement contextual response handler for yes/no/cancel/thanks
