# BROKEN_TO_FIXED_LOG.md
## CelesteOS System Hardening - Error Tracking by Phase

Generated: 2026-01-19
Last Updated: 2026-01-19

---

## PHASE GROUP 1 — FOUNDATIONAL TRUTH (1–10)

### Phase 1-4: Environment Setup
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| FIXED | yacht_id NULL in pms_faults | Default yacht not assigned during seed | Added yacht_id to seed data | Critical - breaks all yacht isolation |

### Phase 5-6: Database Schema
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| BLOCKED | `pms_maintenance_schedules` missing | Table never created | Needs migration | Blocks 5 PM schedule actions |
| BLOCKED | `pms_certificates` missing | Table never created | Needs migration | Blocks 3 certificate actions |
| BLOCKED | `pms_service_contracts` missing | Table never created | Needs migration | Blocks 2 contract actions |
| BLOCKED | `dash_handover_items.handover_id` NOT NULL | Schema constraint prevents inserts | Needs schema fix | Blocks 5 handover actions |

### Phase 7: RPCs
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| FIXED | `get_unlinked_email_threads` RPC missing | RPC never created in Supabase | Added fallback in email.py | Returns manual filter instead |

### Phase 8-10: Truth Map
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| DONE | Truth map produced | - | ACTION_COVERAGE_REPORT | 20/75 actions working |

---

## PHASE GROUP 2 — AUTH & CONTEXT PROPAGATION (11–20)

### Phase 11-14: Auth Flow
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | Auth works | - | - | JWT validated correctly |

### Phase 15-16: yacht_id Propagation
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| FIXED | yacht_id not in search | Missing context injection | Added to search handlers | - |
| FIXED | yacht_id not in actions | Missing context injection | Added to action handlers | - |
| FIXED | yacht_id not in viewer | Placeholder ID used | Replaced with real ID | - |

### Phase 17-20: RLS & Isolation
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | RLS policies exist | - | - | Verified in tests |
| OK | Cross-yacht blocked | - | - | 403 returned correctly |

---

## PHASE GROUP 3 — SEARCH CORE (21–35)

### Phase 21-25: Search Paths
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | Global search works | - | - | SQL + vector hybrid |
| OK | Empty state handled | - | - | Shows "no results" |

### Phase 26-35: Edge Cases
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| TODO | High-volume stress test | Not yet run | - | Need load testing |

---

## PHASE GROUP 4 — EMAIL SYSTEM (36–55)

### Phase 36-40: Email Tables & Sync
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | Email tables exist | - | - | email_threads, email_messages |
| FIXED | /email/inbox 500 error | RPC missing + feature flags false | Enabled flags + added fallback | - |

### Phase 41-45: Email UI
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| FIXED | Placeholder in email UI | Hardcoded placeholder-* IDs | Replaced with real IDs | - |

### Phase 46-55: Email Features
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| TODO | Email search | Not fully tested | - | Hybrid path needs verification |
| TODO | Link to work | Not fully tested | - | Entity linking UI |
| TODO | Attachment viewer | Not fully tested | - | Opens in document viewer |

---

## PHASE GROUP 5 — DOCUMENT VIEWER (56–65)

### Phase 56-60: Viewer Core
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| FIXED | Placeholder document IDs | Hardcoded IDs in frontend | Replaced with real UUIDs | - |
| TODO | Storage access | Not verified | - | Need to test bucket permissions |

### Phase 61-65: Viewer Features
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| TODO | Viewer → microactions | Not tested | - | Action panel in viewer |
| TODO | Viewer → handover | Blocked by handover | - | Depends on handover fix |

---

## PHASE GROUP 6 — MICROACTIONS (66–85)

### Phase 66-70: Action Enumeration
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| DONE | 75 actions enumerated | - | - | See coverage report |
| FIXED | view_equipment_detail 404 | Handler missing | Added handler | Now returns 200 |
| FIXED | upload_document 404 | Handler missing | Added handler | Now returns 200 |
| FIXED | view_document 404 | Handler missing | Added handler | Now returns 200 |
| FIXED | view_equipment 404 | Handler missing | Added handler | Now returns 200 |

### Phase 71-75: Action Execution
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | READ actions | 20 working | - | All return 200 |
| BLOCKED | PM actions (5) | Missing table | Needs migration | pms_maintenance_schedules |
| BLOCKED | Handover actions (5) | Schema issue | Needs fix | handover_id NOT NULL |
| BLOCKED | Certificate actions (3) | Missing table | Needs migration | pms_certificates |
| BLOCKED | Contract actions (2) | Missing table | Needs migration | pms_service_contracts |
| TODO | 40 not implemented | Code not written | - | Future phases |

### Phase 76-80: Guards & Audit
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | G0 guards verified | - | - | JWT + yacht_id on all |
| TODO | Audit logs | Not fully verified | - | Need to check pms_audit_log |

### Phase 81-85: Edge Cases
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| OK | Invalid input → 400 | - | - | Validation working |
| OK | Auth missing → 401 | - | - | JWT check working |
| OK | Wrong yacht → 403/404 | - | - | Isolation working |

---

## PHASE GROUP 7 — SITUATIONS & HANDOVER (86–95)

### Phase 86-90: Situations
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| TODO | Situation triggers | Not tested | - | Need to verify detection |
| TODO | Situation visibility | Not tested | - | UI component |

### Phase 91-95: Handover
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| BLOCKED | All handover actions | dash_handover_items.handover_id NOT NULL | Needs schema fix | 5 actions blocked |

---

## PHASE GROUP 8 — HARDENING & PROOF (96–100)

### Phase 96-98: E2E & Cleanup
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| DONE | Microaction tests | 1119 passed | - | Full matrix |
| DONE | User flow tests | 43 passed, 2 skipped | - | E2E verified |

### Phase 99-100: Reports
| Status | Error | Why | How Fixed | Comments |
|--------|-------|-----|-----------|----------|
| DONE | ACTION_COVERAGE_REPORT | Generated | - | 20/75 (26.7%) |
| TODO | LAUNCH_READINESS_REPORT | Not yet | - | After all fixes |

---

## SUMMARY: BLOCKING ISSUES

| Issue | Blocks | Priority | Fix Required |
|-------|--------|----------|--------------|
| `pms_maintenance_schedules` missing | 5 PM actions | HIGH | CREATE TABLE migration |
| `pms_certificates` missing | 3 cert actions | MEDIUM | CREATE TABLE migration |
| `pms_service_contracts` missing | 2 contract actions | MEDIUM | CREATE TABLE migration |
| `dash_handover_items.handover_id` NOT NULL | 5 handover actions | HIGH | ALTER TABLE or schema redesign |
| 40 actions not implemented | 40 actions | LOW | Future development |

---

## COMMITS THIS SESSION

| Hash | Description |
|------|-------------|
| f9e873d | Enable email features and add missing action handlers |
| 23db24f | Add /v1/query endpoint to production service |
| 6584efa | Fix email inbox fallback when RPC doesn't exist |
| f7351f2 | Update test expectations for newly implemented actions |

---

## NEXT ACTIONS

1. Create migration for `pms_maintenance_schedules`
2. Create migration for `pms_certificates`
3. Create migration for `pms_service_contracts`
4. Fix `dash_handover_items` schema (make handover_id nullable or redesign)
5. Implement remaining 40 actions
6. Run full E2E recorded session
7. Produce LAUNCH_READINESS_REPORT
