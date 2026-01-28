# Fault Lens — Scope Plan (Entity Extraction & Prefill)

Lens: Faults
Branch: fault/entity-extraction-prefill_v1 (based on main)
Owner: Backend authority; UI renders returned actions only

---

Objectives
- Surface explicit, backend-owned action buttons (no guesswork)
- Prefill `report_fault` from query: title, equipment_id, severity
- Two‑phase signed flow for `create_work_order_from_fault` (prepare → preview → commit)
- Symptom→severity mapping with DB‑truth alignment (medium → minor)
- Yacht‑scoped equipment resolution (text → UUID)

Feature Summary
- Explicit Action Buttons: "Report Fault" renders in SuggestedActions when intent detected
- Auto‑Population: "main engine overheating" → title="main engine overheating", equipment_id=UUID, severity=major
- Two‑Phase Mutation: `create_work_order_from_fault` exposes preview before commit; signature required at commit
- Symptom→Severity Mapping: "overheating"→major, "scratch"→cosmetic, unknown→minor
- Equipment Resolution: fuzzy match within yacht to resolve equipment_id

Field Classification (pms_faults)
- REQUIRED: equipment_id, description
- OPTIONAL: title, severity
- BACKEND_AUTO: id, yacht_id, fault_code, status (default open), detected_at, metadata, timestamps
- CONTEXT: equipment_id resolved from extraction (backend validates)

Response Structure (Suggestions)
```
{
  "query": "main engine overheating",
  "entities": {
    "equipment": "main engine",
    "symptom": "overheating"
  },
  "renderable_actions": [{
    "action_id": "report_fault",
    "label": "Report Fault",
    "is_primary": true,
    "prefill": {
      "title": "main engine overheating",
      "equipment_id": "<uuid>",
      "severity": "major",
      "description": "main engine overheating"
    },
    "unresolved": []
  }]
}
```

Extraction & Prefill Rules
- Equipment resolution: tokenize query; match against pms_equipment(name, model, location) WHERE yacht_id=current; top‑1 cosine or trigram
- Severity rules (first hit wins):
  - critical: "fire", "smoke", "loss of steering", "flood", "mayday"
  - major: "overheating", "leak", "shutdown", "alarm"
  - cosmetic: "scratch", "paint", "cosmetic"
  - default: minor
- Title: use original query; Description: same as title unless provided
- Fallbacks: if equipment unresolved → keep `unresolved` with { field: "equipment_id", reason: "ambiguous" }

DB‑Truth Alignment
- Required fields enforced at execute; missing → 400 with explicit field list
- Severity mapped to DB allowed set: {cosmetic, minor, major, critical, safety}
- RLS deny‑by‑default for writes (INSERT/UPDATE) via `is_hod()`
- Storage for photos: bucket `pms-discrepancy-photos`, path `{yacht_id}/faults/{fault_id}/{filename}`

Implementation Phases (4 PRs)
- PR #1 Registry schema: apps/api/action_router/registry.py (roles, domain, search_keywords, storage_options)
- PR #2 Transforms & lookups: apps/api/handlers/fault_transforms.py, fault_handlers.py (extraction→prefill; severity map)
- PR #3 Two‑phase endpoints: apps/api/routes/p0_actions_routes.py (prepare/preview/commit for signed WO)
- PR #4 Orchestration integration: search orchestrator wires `GET /v1/actions/list` with domain=faults

Acceptance
- Suggestions: HOD sees `report_fault` for valid queries; crew sees no MUTATE/SIGNED actions
- Execute: `report_fault` with prefill → 200 and valid audit row
- Signed: `create_work_order_from_fault` missing signature → 400; with signature by captain/manager → 200

