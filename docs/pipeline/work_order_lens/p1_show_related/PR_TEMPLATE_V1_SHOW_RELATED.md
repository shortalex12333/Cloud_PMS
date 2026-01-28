# PR: P1 Show Related (Work Order Lens) - V1 Implementation

## Summary

V1 "Show Related" delivers **FK-only retrieval** for work order context surfacing:

- **Deterministic ordering** via foreign key joins (no embeddings in V1)
- **`related_text`** column for explainability (seeds future V2 embedding input)
- **Zero 500s contract** - all error paths return proper 4xx codes
- **Role-gated mutations** - only HOD/captain/manager can add explicit links

### Endpoints
- `GET /v1/related?entity_type=&entity_id=&limit=` - View related entities
- `POST /v1/related/add` - Add explicit entity link (HOD/captain/manager only)

---

## Ground Truth

### Tables & Soft-Delete Filters

| Table | Has `deleted_at` | Filter Applied |
|-------|------------------|----------------|
| `pms_work_orders` | YES | `.is_("deleted_at", "null")` |
| `pms_equipment` | YES | `.is_("deleted_at", "null")` |
| `pms_faults` | YES | `.is_("deleted_at", "null")` |
| `pms_parts` | YES | `.is_("deleted_at", "null")` |
| `pms_work_order_parts` | YES | `.is_("deleted_at", "null")` |
| `pms_attachments` | YES | `.is_("deleted_at", "null")` |
| `pms_work_order_notes` | NO | No filter (no column) |
| `doc_metadata` | NO | No filter (FK-only) |
| `pms_entity_links` | NO | No filter (hard delete; unique constraint) |

### Document Paths

| Group | Source Table | Join Path |
|-------|--------------|-----------|
| Parts | `pms_work_order_parts` → `pms_parts` | FK: `work_order_id` |
| Manuals | `doc_metadata` | `equipment_ids @> ARRAY[equipment_id]` |
| Previous Work | `pms_work_orders` | `equipment_id` match, exclude self |
| Attachments | `pms_attachments` | `entity_type='work_order'`, `entity_id` match |
| Explicit Links | `pms_entity_links` | `source_entity_type`, `source_entity_id` |

---

## Evidence Checklist

### Docker Tests (14 tests)

- [ ] All 14 tests PASS
- [ ] Zero 500 errors (exit code 0, not 2)
- [ ] Output attached below

```
# Docker Test Results (2026-01-28)
# NOTE: Tests require seeded test data. Infrastructure validated.
================================================================================
P1 SHOW RELATED - DOCKER TEST SUITE
================================================================================
API URL: http://api:8000
Yacht A: 85fe1119-b04c-41ac-80f1-829d23322598

Infrastructure Validation:
- API container: ✅ Running (healthcheck passed)
- Routes registered: ✅ /v1/related accessible
- JWT auth: ✅ Working (401/403 tests pass)
- 404 handling: ✅ Correct (not-found tests pass)

Test Data Required:
- TEST_WO_A_ID needs seeding in tenant DB
- TEST_PART_A_ID needs seeding in tenant DB

Full green requires: Seed test data before running tests.
================================================================================
```

### Staging CI Tests (7 tests)

- [ ] All 7 tests PASS
- [ ] Zero 500 errors
- [ ] Sample response attached

```
# Paste Staging CI output here
================================================================================
P1 Show Related - Staging CI Tests
================================================================================
...
================================================================================
STAGING CI TEST RESULTS
================================================================================
Passed: 7
Failed: 0
500 Errors: NO
```

### Sample GET Response

```json
{
  "status": "success",
  "groups": [
    {
      "group_key": "parts",
      "label": "Parts",
      "count": 2,
      "items": [
        {
          "entity_id": "...",
          "entity_type": "part",
          "title": "Filter Element",
          "subtitle": "Part #: FE-123",
          "related_text": "...",
          "match_reasons": ["FK:wo_part"],
          "weight": 100,
          "open_action": "focus"
        }
      ],
      "limit": 10,
      "has_more": false
    }
  ],
  "add_related_enabled": true,
  "group_counts": {"parts": 2, "manuals": 1, "previous_work": 3},
  "missing_signals": ["handover_group_omitted_v1"],
  "metadata": {"limit_per_group": 10, "total_items": 6}
}
```

### Sample POST /v1/related/add (HOD)

```bash
# Request
curl -X POST -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"...","source_entity_type":"work_order","source_entity_id":"...","target_entity_type":"part","target_entity_id":"...","link_type":"related","note":"Linked during inspection"}' \
  "$API_URL/v1/related/add"

# Response (200)
{"status": "success", "link_id": "...", "created_at": "2026-01-28T..."}
```

### Explicit Links Roundtrip

- [ ] POST add link → 200
- [ ] GET related → explicit_links group contains new link
- [ ] Duplicate POST → 409

---

## Risk & Mitigations

| Risk | Mitigation |
|------|------------|
| Handover group empty | `missing_signals: ["handover_group_omitted_v1"]` informs UI |
| Doc re-ranking noise | Deferred until `description` field curated |
| Stale embeddings (V2) | Will add `embedding_updated_at` + nightly batch refresh |
| Cross-yacht leakage | All queries filter by `yacht_id`; 404 (not 403) for isolation |

---

## Runbook

### Required Environment Variables (Staging CI)

```bash
export STAGING_API_URL=https://api-staging.backbuttoncloud.com
export STAGING_YACHT_ID=<yacht-uuid>
export STAGING_JWT_CREW=<crew-jwt>
export STAGING_JWT_HOD=<hod-jwt>
export STAGING_WORK_ORDER_ID=<work-order-uuid>
export STAGING_PART_ID=<part-uuid>
```

### Commands

```bash
# Docker tests (local)
docker-compose -f docker-compose.test.yml up --build

# Staging CI
python tests/ci/staging_work_orders_show_related.py

# Curl: GET related (any role)
curl -H "Authorization: Bearer $JWT" \
  "$API_URL/v1/related?entity_type=work_order&entity_id=$WO_ID&limit=10"

# Curl: POST add link (HOD/captain/manager only)
curl -X POST -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"$YACHT_ID","source_entity_type":"work_order","source_entity_id":"$WO_ID","target_entity_type":"part","target_entity_id":"$PART_ID","link_type":"related","note":"Test"}' \
  "$API_URL/v1/related/add"
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Test failures |
| 2 | 500 errors detected (HARD FAIL) |

### Zero-500s Policy

Any 500 error triggers exit code 2 and blocks merge. All error conditions must return proper 4xx:
- 400: Invalid entity_type, link_type, limit, note length, self-link
- 403: CREW attempting to add link
- 404: Entity not found (including cross-yacht)
- 409: Duplicate link

---

## Files Changed

### Implementation
- `apps/api/handlers/related_handlers.py` - V1 handler implementation
- `apps/api/routes/related_routes.py` - Route definitions

### Tests
- `tests/docker/run_work_orders_show_related_tests.py` - Docker test suite (14 tests)
- `tests/ci/staging_work_orders_show_related.py` - Staging CI tests (7 tests)

### Documentation (8-Phase Pipeline)
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_0_EXTRACTION_GATE.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_1_SCOPE.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_2_DB_TRUTH.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_3_ENTITY_GRAPH.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_4_ACTIONS.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_5_SCENARIOS.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_6_SQL_BACKEND.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_7_RLS_MATRIX.md`
- `docs/pipeline/work_order_lens/p1_show_related/p1_show_related_PHASE_8_GAPS_MIGRATIONS.md`

### Migrations
- `supabase/migrations/20260128_1600_v1_related_text_columns.sql`

---

## Post-Merge Smoke Test

1. Deploy to Render
2. GET /v1/related for a real WO → verify groups, match_reasons, add_related_enabled
3. HOD/Captain add link → 200
4. CREW add link → 403
5. Verify explicit_links roundtrip

---

## V2/V3 Roadmap (Deferred)

- **V2**: Add `search_embedding` + `embedding_updated_at`; nightly batch refresh; re-rank formula
- **V3**: Optional Edge/watchdog for tighter freshness if needed
