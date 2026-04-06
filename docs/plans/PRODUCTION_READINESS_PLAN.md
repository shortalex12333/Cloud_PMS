# Production Readiness Plan — Import Pipeline

**Date**: 2026-04-01
**Deadline**: 2026-04-08 (boss returns)
**Status**: HONEST ASSESSMENT — defining what "done" means

---

## WHAT "PRODUCTION READY" MEANS

A real user on registration.celeste7.ai can:
1. Complete 2FA verification
2. Download their installer
3. Click "Import your data"
4. Upload a real PMS export (.csv, .xlsx, .sql, .zip)
5. See their columns detected and mapped
6. Confirm the mapping (human gate)
7. Preview what will be imported
8. Commit
9. Go to app.celeste7.ai and SEARCH for their imported data
10. Find it. Within minutes.

If any step fails, crashes, shows wrong data, or silently drops records — it's NOT production ready.

---

## HONEST GAP ANALYSIS

### WHAT'S BUILT (code exists, tested against mocks)
- [x] CSV parser (encoding, delimiter, header, date, domain detection)
- [x] XLSX parser (openpyxl, header row skip, date conversion)
- [x] SQL parser (INSERT + COPY blocks)
- [x] ZIP handler (extract, route data/documents)
- [x] Column matcher (rapidfuzz + known profiles for IDEA/Seahub/Sealogical)
- [x] Date normalizer (DD-MMM-YYYY, DD/MM, MM/DD, Excel serial → ISO)
- [x] Status mapper (ACTIVE→operational, closed→resolved, etc.)
- [x] Import service (transform, dry-run, commit, rollback, search_index wiring)
- [x] 6 API routes (upload, session, confirm-mapping, dry-run, commit, rollback)
- [x] Frontend: all screens (upload, mapping, preview, commit, rollback)
- [x] 151 tests (unit + integration + edge cases + Playwright)
- [x] Schema migration SQL written
- [x] Implementation plan documented

### WHAT'S NOT DONE (and must be before production)

| # | Gap | Risk if skipped | Effort |
|---|-----|-----------------|--------|
| 1 | **Schema migration not run on tenant DB** | Nothing works. No import_sessions table, no tracking columns | 10 min |
| 2 | **vessel-imports storage bucket doesn't exist** | Upload crashes with "bucket not found" | 5 min |
| 3 | **requirements.txt not updated** | Deploy to Render fails — missing openpyxl, rapidfuzz, sqlparse, xlrd, python-dateutil | 5 min |
| 4 | **Registration backend doesn't issue import_token** | Real users can't authenticate. UI shows blank/redirect | 2 hrs |
| 5 | **CORS not updated on Render env vars** | registration.celeste7.ai → pipeline-core blocked by browser | 5 min |
| 6 | **Never tested against real Supabase DB** | INSERT may fail on constraints, types, RLS we haven't hit | 2 hrs |
| 7 | **Never started the real backend and hit it with curl** | Route registration, import path resolution, env var loading may fail | 1 hr |
| 8 | **projection.yaml doesn't know about import tracking columns** | search_text won't include source/imported_at — search may not surface imports correctly | 30 min |
| 9 | **No error handling for Supabase Storage failures** | If storage is down/full, upload silently fails | 30 min |
| 10 | **No rate limiting on import endpoints** | Anyone with a token can spam uploads | 30 min |
| 11 | **pms_work_orders.created_by NOT NULL** — may not be droppable | Migration may fail if existing rows or code depends on NOT NULL | 30 min |
| 12 | **Frontend not deployed to Vercel** | Only works on localhost | 15 min |
| 13 | **Backend changes not committed/pushed to GitHub** | Render auto-deploy won't trigger | 15 min |
| 14 | **No real PMS export tested** | Parser may break on real data we haven't seen | Unknown |
| 15 | **search_index UNIQUE constraint on (object_type, object_id)** | Our UUID-based object_ids should be fine, but untested | 10 min |
| 16 | **Supabase service role key in import routes** | If key is wrong/expired, all DB operations fail silently | 10 min |
| 17 | **No health check for import endpoints** | Can't tell if import pipeline is alive on Render | 15 min |
| 18 | **Cleanup after failed imports** | If commit crashes mid-way, partial data left in DB with no rollback | 1 hr |

---

## EXECUTION PLAN — 7 DAYS

### Day 1 (Apr 2): Infrastructure & Real DB
**Goal**: Schema deployed, storage created, backend running against real DB

- [ ] Update requirements.txt with new dependencies
- [ ] Run schema migration on tenant DB via Supabase SQL editor
- [ ] Verify: existing pms_equipment, pms_work_orders etc. still queryable (no breakage)
- [ ] Create vessel-imports bucket on tenant Supabase Storage
- [ ] Set bucket RLS: authenticated users can upload to their yacht path
- [ ] Start real backend locally with real env vars
- [ ] Verify: import routes registered (check /health or startup logs)
- [ ] curl: upload IDEA fixture → verify import_sessions row in real DB
- [ ] curl: verify file in real Supabase Storage

### Day 2 (Apr 3): Real Pipeline E2E
**Goal**: Full pipeline works against real tenant DB

- [ ] curl: confirm-mapping → verify column_map stored
- [ ] curl: dry-run → verify preview with real transformed rows
- [ ] curl: commit → verify real rows in pms_equipment
- [ ] SQL: SELECT * FROM pms_equipment WHERE import_session_id = :id — verify content
- [ ] SQL: SELECT * FROM search_index WHERE object_id IN (imported IDs) — verify pending
- [ ] Check projection_worker — does it pick up and process?
- [ ] Wait 3 min, then search on app.celeste7.ai for "MTU-2019-7834"
- [ ] curl: rollback → verify rows deleted
- [ ] Test with Seahub fixture (different domain: defects, tasks, inventory)
- [ ] Test with all 6 domains: equipment, work_orders, faults, parts, certificates, crew_certificates
- [ ] Fix every failure found

### Day 3 (Apr 4): Auth & Registration Backend
**Goal**: Real users can authenticate for import

- [ ] Clone celesteos-registration-windows repo
- [ ] Add import_token to verify-download-code response
- [ ] Generate JWT: { sub: email, yacht_id, scope: "import", exp: +24h }
- [ ] Sign with MASTER_SUPABASE_JWT_SECRET
- [ ] Test locally: complete 2FA → receive import_token
- [ ] Test: frontend stores token → import API accepts it
- [ ] Test: expired token → 401
- [ ] Test: wrong yacht_id token → session not found
- [ ] Push registration backend changes
- [ ] Deploy to Render

### Day 4 (Apr 5): Frontend Integration & Deploy
**Goal**: Portal works end-to-end against real backend

- [ ] Frontend01: run Playwright against real backend (not mock)
- [ ] Frontend01: verify mapping screen with real detection results
- [ ] Frontend01: override a dropdown, confirm, verify persistence
- [ ] Frontend01: commit, verify real counts match DB
- [ ] Frontend01: search on app.celeste7.ai for imported data
- [ ] Commit all frontend changes
- [ ] Push celesteos-portal to GitHub
- [ ] Deploy to Vercel
- [ ] Update CORS on Render: add registration.celeste7.ai
- [ ] Test: full flow from deployed portal → deployed backend

### Day 5 (Apr 6): Hardening & Edge Cases
**Goal**: Pipeline doesn't break on bad input or failures

- [ ] Test with intentionally corrupted CSV (null bytes, wrong encoding, broken quotes)
- [ ] Test with oversized file (>50MB) — does it timeout or handle gracefully?
- [ ] Test commit failure mid-way — verify partial rollback or clean error
- [ ] Test concurrent imports to same yacht — verify no conflict
- [ ] Test rollback after 48h — verify rejection
- [ ] Add transaction wrapping to commit (BEGIN/COMMIT/ROLLBACK on failure)
- [ ] Add request size limit to upload endpoint
- [ ] Add import session expiry (abandon sessions older than 24h)
- [ ] Test with duplicate equipment names (UNIQUE constraint)
- [ ] Test with empty required fields (certificate_type NOT NULL)

### Day 6 (Apr 7): Real PMS Data & Polish
**Goal**: Works with real-world data

- [ ] If real PMS export available: run through full pipeline
- [ ] Fix whatever breaks (there WILL be things)
- [ ] If no real export: create comprehensive test fixtures that cover every known quirk
- [ ] Test ZIP with embedded PDFs — verify stored in vessel-documents, doc_metadata created
- [ ] Verify projection_worker indexes documents (PyMuPDF text extraction)
- [ ] Review all error messages — they must be clear, not stack traces
- [ ] Review all API responses — they must be complete, not partial
- [ ] Add /api/import/health endpoint for monitoring

### Day 7 (Apr 8): Final Verification & Handover
**Goal**: Boss returns to a working product

- [ ] Full end-to-end: registration.celeste7.ai → 2FA → download → import → app.celeste7.ai search
- [ ] Record the full flow (screenshots or screen recording)
- [ ] Run all 151+ tests one final time
- [ ] Run Playwright against deployed (not localhost)
- [ ] Write deployment runbook: what's deployed where, env vars, how to monitor
- [ ] Write troubleshooting guide: common failures and fixes
- [ ] Update MEMORY.md with project state

---

## DEFINITION OF DONE

All of these must be TRUE:

1. Schema migration deployed on tenant DB
2. vessel-imports bucket exists with correct RLS
3. Backend deployed on Render with new deps
4. Frontend deployed on Vercel
5. Registration backend issues import_token
6. CORS allows registration.celeste7.ai → pipeline-core
7. Full flow works: upload → detect → map → preview → commit → searchable
8. Rollback works within 48h
9. All 6 domains tested (equipment, work_orders, faults, parts, vessel_certs, crew_certs)
10. projection_worker picks up imported records → search works
11. Auth flow works (real JWT, expired token rejected, wrong yacht rejected)
12. Error states show clear messages, not crashes
13. 150+ tests passing
14. Playwright passes against real backend (not mock)

If I can't check ALL 14 boxes, it's not production ready. No excuses.

---

## WHAT I CANNOT GUARANTEE

- Real PMS exports from IDEA Yacht/Seahub/Sealogical may have formats we haven't seen. The parser is built defensively but real data always surprises. The human gate (column mapping) is the safety net — if the parser guesses wrong, the user corrects it.
- Search latency depends on projection_worker and embedding_worker timing. MVP: 2-3 minutes after commit. Not instant.
- The registration backend update requires access to a separate repo. If I can't push there, auth is blocked.

---

**Starting Day 1 now.**
