# Remaining Work — Entity Lenses

**Last Updated:** 2026-03-03

---

## v1.3 Milestone Status: ✅ 100% COMPLETE

All planned phases (15-20.2) have been executed. All CRITICAL and HIGH gaps resolved.

| Phase | Name | Status | Date |
|-------|------|--------|------|
| 15 | Intent Envelope | ✅ Complete | 2026-03-01 |
| 16 | Prefill Integration | ✅ Complete | 2026-03-01 |
| 16.1 | Mount /prepare Endpoint | ✅ Complete | 2026-03-02 |
| 16.2 | Unified Route Architecture | ✅ Complete | 2026-03-02 |
| 17 | Readiness States | ✅ Complete | 2026-03-02 |
| 18 | Route & Disambiguation | ✅ Complete | 2026-03-02 |
| 19 | Agent Deployment (4 waves) | ✅ Complete | 2026-03-02 |
| **20** | **Email Lens Conversion** | ✅ Complete | 2026-03-03 |
| **20.1** | **Document/Handover Gaps** | ✅ Complete | 2026-03-03 |
| **20.2** | **Test Verification** | ✅ Complete | 2026-03-03 |

**Deliverables:**
- IntentEnvelope abstraction (READ | MUTATE | MIXED)
- `/v1/actions/prepare` endpoint for prefill preview
- Readiness states (READY, NEEDS_INPUT, BLOCKED)
- Disambiguation UX for ambiguous entities
- RouteShell pattern (-4,262 LOC across 11 routes)
- PermissionService from lens_matrix.json
- EmailLensContent + button navigation to `/email`
- Document lens in lens_matrix.json (6 actions)
- Handover Add Note button
- **1184+ E2E Playwright tests verified**

---

## Gap Status: ALL CRITICAL/HIGH RESOLVED ✅

| Gap | Priority | Status | Resolution |
|-----|----------|--------|------------|
| GAP-027 | HIGH | ✅ RESOLVED | Email lens conversion complete |
| GAP-028 | HIGH | ✅ RESOLVED | Handover panel-only confirmed, Add button added |
| GAP-029 | HIGH | ✅ RESOLVED | Document lens added to lens_matrix.json |
| GAP-030 | CRITICAL | ✅ RESOLVED | Test infrastructure verified passing |

---

## Remaining Work (MEDIUM/LOW Only)

### MEDIUM Priority (6) — Non-Blocking

| ID | Description | Status |
|----|-------------|--------|
| GAP-006 | User edit protection in ActionModal | Workaround: debounce/cache |
| GAP-007 | Equipment notes RLS | ⚠️ Verify needed |
| GAP-008 | Equipment attachments RLS | ⚠️ Verify needed |
| GAP-009 | Storage write policies | Migration ready |
| GAP-010 | Doc metadata write policies | Migration ready |
| GAP-011 | Crew certificate RLS | Migration ready |

### LOW Priority (6) — Future Enhancement

| ID | Description | Status |
|----|-------------|--------|
| GAP-014 | Temporal parser edge cases | Track for user requests |
| GAP-015 | Priority synonym expansion | Track for usage data |
| GAP-016 | Entity resolution fuzzy match | Consider rapidfuzz |
| GAP-017 | Missing route registration log | Polish |
| GAP-018 | /prepare OpenAPI documentation | Auto-fix when deployed |
| GAP-026 | Duplicate registry key | Low impact |

---

## Future Milestones (Not v1.3)

### v1.4: Recall Improvement (SEARCH — Different Domain)

**Status:** PARKED — Blocked on migration deployment
**Blocker:** `50_enhance_search_text.sql` not deployed

See `.planning/STATE.md` for details.

### v2.0: Remaining Lenses v2 Documentation

Low priority — lenses work functionally, just need formal v2 docs:
- Fault lens v2 docs
- Inventory/Part lens v2 docs
- Crew lens v2 docs
- Receiving lens v2 docs
- Shopping List lens v2 docs

---

## Final Metrics

| Metric | Value |
|--------|-------|
| Lenses in matrix | 13 |
| LensContent components | 14 |
| Actions configured | 87 |
| E2E tests | 1184+ |
| CRITICAL gaps | 0 |
| HIGH gaps | 0 |
| MEDIUM gaps | 6 |
| LOW gaps | 6 |

---

## Quick Commands

```bash
# Check current gaps
cat docs/ON_GOING_WORK/BACKEND/LENSES/GAPS.md | grep "❌ OPEN"

# Run E2E tests
npx playwright test --project=chromium

# Check project status
/gsd:progress
```

---

*See also: OVERVIEW.md, GAPS.md, PHASES-COMPLETE.md*
