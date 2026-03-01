# Phase 16: Prefill Integration - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build /v1/actions/prepare endpoint that accepts NLP outputs and returns prefilled form previews with entity resolution and confidence scoring. This is the server-side "mutation preview" layer that produces pre-filled action modals from natural language queries.

**NOT in scope:** Client-side filter chips (Phase 18), action listing changes, new UI components beyond ActionModal prefill wiring.

</domain>

<decisions>
## Implementation Decisions

### Request/Response Contract

**Endpoint:** `/v1/actions/prepare` (separate from `/v1/actions/list` — do NOT pollute listing semantics)

**Request shape:**
```json
{
  "q": "make work order for main engine for next week, critical",
  "domain": "work_orders",
  "candidate_action_ids": ["create_work_order", "add_note_to_work_order"],
  "context": {
    "yacht_id": "uuid",
    "user_role": "chief_engineer"
  },
  "hint_entities": {
    "equipment_id": null,
    "work_order_id": null
  },
  "client": {
    "timezone": "America/New_York",
    "now_iso": "2026-03-01T16:00:00-05:00"
  }
}
```

**Response shape:**
```json
{
  "action_id": "create_work_order",
  "match_score": 0.95,
  "ready_to_commit": false,
  "prefill": {
    "equipment_id": { "value": "uuid", "confidence": 0.92, "source": "entity_resolver" },
    "priority": { "value": "critical", "confidence": 0.95, "source": "keyword_map" },
    "scheduled_date": { "value": "2026-03-08", "confidence": 0.88, "source": "temporal" },
    "title": { "value": "Main Engine - [add symptom]", "confidence": 0.60, "source": "template" }
  },
  "missing_required_fields": ["description"],
  "ambiguities": [
    {
      "field": "equipment_id",
      "candidates": [
        { "id": "uuid1", "label": "Main Engine (Port)", "confidence": 0.55 },
        { "id": "uuid2", "label": "Main Engine (Stbd)", "confidence": 0.54 }
      ]
    }
  ],
  "errors": []
}
```

**Error format (non-negotiable):** Always return structured errors, never just "500"
```json
{
  "error_code": "RLS_DENIED",
  "message": "User cannot access equipment candidate(s)",
  "field": "equipment_id"
}
```

### Frontend Integration

**When to call /prepare:**
- On query settle (debounced 350-500ms)
- On action hover/focus
- Cancel in-flight requests on new keystroke
- Cache by `(q, domain, yacht_id, role)` for ~30s

**Where it plugs in:**
- `useCelesteSearch.ts` — add parallel call: `prepareAction(q, domain, candidate_action_ids)` alongside existing actions list + search
- `ActionModal.tsx` — initialize `formData` from `prefill` response

**UI state badges on suggested actions:**
- ✅ "Ready" — all required fields resolved
- ⚠️ "Needs input" — missing fields
- ❓ "Pick one" — ambiguity list present

### Entity Resolution Behavior

**Confidence gates (strict thresholds):**
- `>= 0.85` → auto-fill silently
- `0.65–0.84` → prefill but show "confirm" UI
- `< 0.65` → treat as ambiguous / missing

**Ambiguity handling:**
- Show picker in modal only for the ambiguous field
- Never block the entire action
- Multiple close candidates → dropdown with "Did you mean?"

**Security (non-negotiable):**
- RLS must be applied during candidate search
- If user can't see it, it cannot appear as a candidate
- This prevents data leakage in entity suggestions

### Temporal Parsing Rules

**Timezone handling:**
- Use client-provided timezone from `client.timezone`
- Resolve relative dates using `client.now_iso`

**"Next week" definition (pick one, never change):**
- Start of next week (Monday) unless user says a specific day

**Temporal response fields:**
- `value` — ISO date
- `source` — "temporal"
- `confidence` — float
- `assumption` — e.g., "interpreted next week as next Monday"

### Claude's Discretion

- Exact debounce timing within 350-500ms range
- Cache TTL tuning within ~30s guideline
- Specific loading skeleton designs
- Error retry logic (if any)

</decisions>

<specifics>
## Specific Ideas

**Two parallel assist layers above search results:**
1. **Deterministic Filter Chips** — fast, client-side, navigates to filtered fragmented URLs (Phase 18)
2. **Dynamic Action Buttons** — server-side, role-aware, produces mutation preview that pre-fills modal (THIS PHASE)

**The split:**
- "Show me…" → chips + filtered pages
- "Do this…" → action + prefill + execute

**Keep prefill separate from list:**
- Do NOT make `/v1/actions/list` magically do prefill
- Separate step keeps caching clean, debugging clean, tests honest

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. User explicitly confirmed the split between:
- Phase 16 (this): Server-side prefill/prepare
- Phase 18: Client-side filter chips + fragmented routes

</deferred>

---

*Phase: 16-prefill-integration*
*Context gathered: 2026-03-01*
