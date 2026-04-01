# Handover Export System — Engineer Onboarding

## What This System Does

Yacht crew rotate every 2 months. When an engineer leaves, they must formally hand over everything the incoming engineer needs to know. Maritime law requires a signed document proving this happened.

CelesteOS digitises this. Crew tag items throughout their rotation ("Add to Handover" on faults, work orders, equipment, parts). At rotation end, they click Export. An AI microservice produces a professional document. The crew member reviews, edits, signs. The HOD countersigns. It becomes a tamper-evident compliance record.

## Two Repos

| Repo | URL | Purpose |
|------|-----|---------|
| **handover_export** | `github.com/shortalex12333/handover_export` | Stateless LLM microservice — items in, HTML out |
| **Cloud_PMS** | `github.com/shortalex12333/Cloud_PMS` | Main app — owns DB, storage, auth, frontend |

## Setup (5 minutes)

```bash
# 1. Microservice (only needs OpenAI key)
cd ~/Documents/handover_export
cp .env.example .env          # Fill in OPENAI_API_KEY
docker compose up --build     # Runs on :10000

# 2. Main app
cd ~/Documents/Cloud_PMS
docker compose --profile full up --build   # API :8000, all workers

# 3. Frontend
cd apps/web && npm run dev    # Runs on :3000

# 4. Login
# http://localhost:3000 → x@alex-short.com / Password2!
```

## Data Flow

```
User tags items throughout rotation
  → INSERT handover_items (entity_type, entity_id, summary, entity_url)

User clicks "Export Handover" (HandoverDraftPanel.tsx)
  → POST /v1/handover/export (Cloud_PMS backend)
    → Lookup yacht name from yacht_registry
    → Lookup user role from auth_users_roles
    → Fetch handover_items, filter by department
    → POST /api/v1/handover/transform (microservice :10000)
      → GPT-4o-mini classify (assign department category)
      → Group by entity_id (merge only true duplicates)
      → GPT-4o-mini summarise (preserve ALL detail)
      → Jinja2 render → HTML
    ← Returns { html, sections, document_hash }
    → Write handover_entries (immutable truth seeds)
    → Write handover_drafts + sections + items
    → Upload HTML to Supabase Storage
    → Write handover_exports record
    → Write ledger_events notification
  ← Return export_id to frontend
  → Frontend marks items as exported
  → User sees toast → clicks "View" → lens page

User reviews document (HandoverContent.tsx)
  → Entity endpoint returns sections from edited_content JSONB
  → Lens renders as light-mode professional document
  → contenteditable fields when review_status = pending_review

User signs (wet signature canvas)
  → POST /v1/handover/export/{id}/submit
  → user_signature stored as base64 PNG
  → review_status → pending_hod_signature

HOD countersigns
  → POST /v1/handover/export/{id}/countersign
  → review_status → complete
  → Projection worker indexes in search_index
```

## 9 Database Tables

```
handover_items           ← Raw tagged items (input)
handover_entries         ← LLM-processed truth seeds (immutable)
handover_drafts          ← Document container (state machine)
handover_draft_sections  ← Department groups within draft
handover_draft_items     ← Individual items with LLM summaries
handover_draft_edits     ← Audit trail of user edits
handover_exports         ← Final export record (signatures, storage URLs)
handover_signoffs        ← Dual signature record
handover_sources         ← External material (future: email integration)
```

Full schema details: `docs/Explanations/handover_backend.md`

## Key Files

### Microservice (handover_export)

| File | What to know |
|------|-------------|
| `src/routers/handover_generate.py` | The `/transform` endpoint. Orchestrates the entire pipeline. |
| `src/pipeline/stages/classify_pms.py` | Maps items to `classify_email()` — reuses the email classification prompt |
| `src/pipeline/stages/group_pms.py` | Groups by `entity_id`. Only merges true duplicates. |
| `src/pipeline/stages/merge_summaries.py` | Calls `merge_handover_notes()` — prompt preserves ALL detail |
| `src/ai/openai_client.py` | Two LLM methods: `classify_email()` and `merge_handover_notes()` |
| `templates/handover_report.html` | Jinja2 A4 template — for storage/print, NOT for in-app viewing |

### Cloud_PMS Backend

| File | What to know |
|------|-------------|
| `apps/api/routes/handover_export_routes.py` | The orchestrator. Lines 84-280 = microservice delegation path. Feature-flagged via `HANDOVER_USE_MICROSERVICE` env var. |
| `apps/api/services/handover_microservice_client.py` | HTTP client for the microservice. 120s timeout. |
| `apps/api/routes/entity_routes.py` | Entity endpoint `/v1/entity/handover_export/{id}` — returns sections for the lens page |
| `apps/api/services/handover_export_service.py` | Old basic HTML export (fallback when microservice unavailable) |

### Cloud_PMS Frontend

| File | What to know |
|------|-------------|
| `apps/web/src/components/handover/HandoverDraftPanel.tsx` | The Export button. Calls backend API, marks items exported. |
| `apps/web/src/components/lens-v2/entity/HandoverContent.tsx` | The lens page. Renders sections as light-mode professional document. Wet signature modal. |
| `apps/web/src/lib/microactions/handlers/handover.ts` | Microaction handler for `export_handover` |
| `apps/web/src/lib/featureFlags.ts` | Route mapping: `handover_export → /handover-export` |
| `apps/web/src/app/handover-export/[id]/page.tsx` | Page wrapper using `useParams()` (Next.js 14) |

## Architecture Decisions

| Decision | Why |
|----------|-----|
| Microservice is stateless | No DB credentials needed. Cloud_PMS owns all persistence. Blast radius isolation. |
| Two renderers (Jinja2 + React) | Jinja2 template = storage/print/compliance archive. React component = in-app viewing/editing. Same data, two contexts. |
| Group by entity_id, not category | Every tagged item must appear in output. Merge only true duplicates. |
| LLM preserves all detail | Prompt says "completeness over brevity." Equipment names, part numbers, dates, vendor names — never stripped. |
| Feature-flagged | `HANDOVER_USE_MICROSERVICE=true` enables. Falls back to basic HTML if microservice down. |
| Light-mode document always | The document container renders white bg regardless of app theme. Professional documents are always light. |
| No PIN for signing | Wet signature canvas only. User draws, confirms. No PIN codes. |

## Test Commands

```bash
# Build check
cd apps/web && npm run build

# Unit tests (109 tests)
cd apps/web && npm run test:unit

# Microservice health
curl http://localhost:10000/health

# Full chain test (generate JWT, call export, check DB)
# See: docs/Explanations/handover_backend.md for manual test steps

# E2E tests
cd apps/web && SUPABASE_JWT_SECRET='ep2o/...' npx playwright test --project=shard-49
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "No handover content available" | Entity endpoint not returning sections | Check `edited_content` JSONB has `{"sections": [...]}` structure |
| Export returns fallback (basic HTML) | Microservice not running or env var not set | Check `docker ps` for handover_export, check `HANDOVER_USE_MICROSERVICE=true` |
| LLM summaries are generic | Old classification summary being used instead of original text | Verify `group_pms.py` passes `item.summary` not `cls.summary` |
| 400 on handover_items PATCH | `status = 'exported'` violates check constraint | Use `status = 'completed'` |
| Wrong route (goes to /work-orders) | `featureFlags.ts` mapping wrong | Should be `handover_export: '/handover-export'` |

## Credentials

See: `/Users/celeste7/Documents/Cloud_PMS/env/env vars.md`

- Tenant DB: `db.vzsohavtuotocgrfkfyd.supabase.co` / password in env file
- Test user: `x@alex-short.com` / `Password2!`
- Test yacht: `85fe1119-b04c-41ac-80f1-829d23322598` (M/Y Test Vessel)
