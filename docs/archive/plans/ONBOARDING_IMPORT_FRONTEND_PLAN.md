# Onboarding Import Pipeline — Frontend Plan

**Date**: 2026-04-01
**Author**: onboard_frontend01
**Status**: DRAFT — awaiting boss approval
**Companion**: ONBOARDING_IMPORT_PIPELINE_PLAN.md (backend)

---

## 1. WHERE THIS LIVES

**Repository**: `/Users/celeste7/celesteos-portal/` (GitHub: shortalex12333/celesteos-portal)
**Deployed to**: registration.celeste7.ai via Vercel
**Tech stack**: Vite 6.3 + React 18.3 + TypeScript 5.5 + Tailwind 3.4 + Lucide icons
**Design tokens**: Already in `src/index.css` — warm blacks, teal affordance, signal colours

**NOT in**: Cloud_PMS/apps/web (the main app stays untouched)

---

## 2. NEW DEPENDENCIES

```json
{
  "react-router-dom": "^7.0.0",
  "react-dropzone": "^14.3.0"
}
```

No state management library. Fetch + useState is sufficient for a linear flow.
No tanstack-query — overkill for 6 API calls in sequence.

---

## 3. FILE STRUCTURE (new code in src/)

```
src/
├── App.tsx                          # Router: / = download flow, /import = import flow
├── main.tsx                         # Entry point (add BrowserRouter)
├── index.css                        # Design tokens (already exists, add import-specific classes)
├── lib/
│   ├── api.ts                       # Existing download API (untouched)
│   ├── config.ts                    # Add IMPORT_API_URL
│   └── importApi.ts                 # NEW: typed fetch for all 6 import endpoints
├── components/
│   ├── Logo.tsx                     # Existing (shared)
│   ├── PlatformStep.tsx             # Existing
│   ├── EmailStep.tsx                # Existing
│   ├── CodeStep.tsx                 # Existing
│   ├── DownloadStep.tsx             # MODIFIED: add "Import your data" CTA
│   └── import/                      # NEW: all import screens
│       ├── ImportLayout.tsx          # Shared layout: orb backdrop, card, step indicator
│       ├── UploadScreen.tsx          # Stage 1: source dropdown + file drop zone
│       ├── DetectingScreen.tsx       # Stage 2: "Analysing structure..." status
│       ├── MappingScreen.tsx         # Stage 3: column mapping table (HUMAN GATE)
│       ├── MappingRow.tsx            # Single row in mapping table
│       ├── PreviewScreen.tsx         # Stage 4: dry run preview
│       ├── DomainPreview.tsx         # Expandable domain section in preview
│       ├── CommitScreen.tsx          # Stage 5: commit progress + completion
│       ├── RollbackScreen.tsx        # Post-import: rollback within 48h
│       └── ImportProgress.tsx        # Step indicator (upload → map → preview → done)
└── types/
    └── import.ts                    # TypeScript types matching backend API contracts
```

---

## 4. ROUTE STRUCTURE

```tsx
// App.tsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<DownloadFlow />} />
    <Route path="/import" element={<ImportFlow />} />
    <Route path="/import/:sessionId" element={<ImportSession />} />
  </Routes>
</BrowserRouter>
```

- `/` — Existing 4-step download flow (PlatformStep → EmailStep → CodeStep → DownloadStep). Unchanged.
- `/import` — New. Upload screen. User arrives after download or via direct link.
- `/import/:sessionId` — Session detail. Renders the correct screen based on session status (detecting → mapping → preview → completed).

---

## 5. STATE MANAGEMENT

No global state. Each screen fetches what it needs.

```
UploadScreen
  └── POST /api/import/upload → receives session_id → navigate to /import/:sessionId

ImportSession (polls GET /api/import/session/:id)
  └── status === 'detecting'  → DetectingScreen (polling)
  └── status === 'mapping'    → MappingScreen (interactive)
  └── status === 'preview'    → PreviewScreen (interactive)
  └── status === 'importing'  → CommitScreen (polling)
  └── status === 'completed'  → CommitScreen (done state)
  └── status === 'rolled_back'→ RollbackScreen (done state)
  └── status === 'failed'     → Error state
```

Polling interval for status transitions: 2 seconds. Stop polling once status is interactive (mapping, preview) or terminal (completed, failed, rolled_back).

---

## 6. API CLIENT (lib/importApi.ts)

```typescript
const IMPORT_API_URL = import.meta.env.VITE_IMPORT_API_URL || 'http://localhost:8000';

interface ImportApiOptions {
  token: string;  // JWT from 2FA completion
}

export function createImportApi({ token }: ImportApiOptions) {
  const headers = {
    'Authorization': `Bearer ${token}`,
  };

  return {
    upload: async (source: string, files: File[]): Promise<UploadResponse> => {
      const form = new FormData();
      form.append('source', source);
      files.forEach(f => form.append('files', f));
      const resp = await fetch(`${IMPORT_API_URL}/api/import/upload`, {
        method: 'POST', headers, body: form,
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },

    getSession: async (id: string): Promise<ImportSession> => {
      const resp = await fetch(`${IMPORT_API_URL}/api/import/session/${id}`, {
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },

    confirmMapping: async (id: string, mappings: MappingPayload): Promise<ConfirmResponse> => {
      const resp = await fetch(`${IMPORT_API_URL}/api/import/session/${id}/confirm-mapping`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mappings }),
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },

    dryRun: async (id: string): Promise<DryRunResponse> => {
      const resp = await fetch(`${IMPORT_API_URL}/api/import/session/${id}/dry-run`, {
        method: 'POST', headers,
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },

    commit: async (id: string): Promise<CommitResponse> => {
      const resp = await fetch(`${IMPORT_API_URL}/api/import/session/${id}/commit`, {
        method: 'POST', headers,
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },

    rollback: async (id: string): Promise<RollbackResponse> => {
      const resp = await fetch(`${IMPORT_API_URL}/api/import/session/${id}/rollback`, {
        method: 'POST', headers,
      });
      if (!resp.ok) throw new ImportError(resp);
      return resp.json();
    },
  };
}
```

---

## 7. SCREEN DESIGNS (per design philosophy spec)

### 7a. UploadScreen (Stage 1)

```
┌─────────────────────────────────────────┐
│  Import vessel data                     │  card-brand container
│                                         │
│  SOURCE SYSTEM                          │  label-brand
│  ┌─────────────────────────────────┐    │
│  │ IDEA Yacht                    ▾ │    │  select dropdown, 44px
│  └─────────────────────────────────┘    │
│                                         │
│  EXPORT FILES                           │  label-brand
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│  │                                 │   │  Drop zone, dashed border
│  │   Drop files here or browse     │   │  --border-sub dashed
│  │   .csv  .xlsx  .sql  .zip       │   │  --txt-ghost text
│  │                                 │   │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                                         │
│  Selected: equipment.csv  (245 KB)      │  file list, mono for filename
│            work_orders.csv (89 KB)      │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │      Upload and analyse         │    │  btn-brand
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Design rules applied:**
- Source dropdown: 44px height (touch target), `input-brand` style
- File drop zone: dashed `--border-sub` border, `--txt-ghost` instruction text
- File list: filename in monospace (machine-generated), size in `--txt3`
- Button: `btn-brand` (teal). Disabled until source selected AND file(s) added
- No drag animation or confetti on drop. File appears in list. Quiet.
- Accepted formats: `.csv`, `.xlsx`, `.xls`, `.sql`, `.zip`

### 7b. DetectingScreen (Stage 2)

```
┌─────────────────────────────────────────┐
│  Analysing file structure...            │  --txt, 14px/500
│                                         │
│  ○ Detecting encoding                   │  status steps
│  ○ Reading column headers               │  ○ = pending (--txt-ghost)
│  ● Matching columns                     │  ● = active (--mark)
│  ○ Complete                             │  ✓ = done (--green)
│                                         │
│  equipment.csv — 15 rows detected       │  --txt3, mono for filename
└─────────────────────────────────────────┘
```

**Design rules:**
- Status text: "Analysing file structure..." — NOT "Working on it..." or "Hang tight..."
- Polling every 2s. Transitions to mapping screen when status='mapping'.
- No spinner animation. Status steps show progress via symbol change (○ → ● → ✓).
- Quiet, calm. The system is working.

### 7c. MappingScreen (Stage 3 — HUMAN GATE)

This is the most critical screen. The core value proposition.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Column mapping review                                               │
│  equipment.csv — 15 rows                                             │  --txt3
│                                                                      │
│  SOURCE COLUMN     CELESTE FIELD        CONFIDENCE   SAMPLE VALUES   │  section headers
│  ────────────────────────────────────────────────────────────────────│
│  EQUIP_NAME        name              ▾   95%  ●      Main Engine...  │  GREEN row
│  SERIAL_NO         serial_number     ▾   95%  ●      MTU-2019-78... │  GREEN row
│  MAKER             manufacturer      ▾   92%  ●      MTU, Caterp... │  GREEN row
│  RUNNING_HOURS     running_hours     ▾   78%  ●      12450, 8920... │  AMBER row
│  PARENT_EQUIP_ID   — skip —          ▾   35%  ●      1, 1, 3, 5,... │  RED row
│  UNKNOWN_COL       — select —        ▾   22%  ●      abc, def, g... │  RED row
│                                                                      │
│  DATE FORMAT DETECTED: DD-MMM-YYYY                                   │  --txt3
│  ENCODING: Latin-1 (converted to UTF-8)                              │  mono, --txt3
│                                                                      │
│  ⚠ 2 columns require manual review                                   │  --amber
│                                                                      │
│  ┌──────────────────────────────────┐                                │
│  │       Confirm mapping            │                                │  btn-brand
│  └──────────────────────────────────┘                                │
│  Confirm button disabled if any red columns not assigned or skipped  │
└──────────────────────────────────────────────────────────────────────┘
```

**Design rules applied:**
- **Table, not cards.** Structured multi-column data where comparing across columns matters (spec §11).
- **44px row height.** Touch-safe operational content.
- **Source column names in monospace.** Machine-generated identifiers.
- **CelesteOS field dropdown.** Populated from `celeste_vocabulary[domain].mappable`. Teal border on focus.
- **Confidence score.** Percentage in mono. Coloured dot: green (≥90%), amber (60-89%), red (<60%).
- **Sample values.** First 5 from file. Monospace. Truncated with ellipsis. Helps user verify mapping.
- **Row backgrounds:**
  - Green: `--green-bg` with `--green-border` left accent
  - Amber: `--amber-bg` with `--amber-border` left accent
  - Red: `--red-bg` with `--red-border` left accent
- **Confirm button:** `btn-brand`. DISABLED until every column is either mapped or explicitly skipped.
- **This screen NEVER auto-proceeds.** The human must click Confirm. This is a brand principle.
- **Date format line:** Shows detected format. If ambiguous, shows a dropdown to override.
- **Encoding line:** Shows detected encoding in mono.

### 7d. PreviewScreen (Stage 4)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Import preview                                                      │
│                                                                      │
│  This import will create:                                            │
│                                                                      │
│  EQUIPMENT            15 records    0 duplicates    1 warning    ▾   │  expandable
│  ├ Main Engine Port        MTU        16V4000 M93L     Engine Room   │  first 10 rows
│  ├ Generator 1             Caterpillar C18              Engine Room   │
│  ├ Watermaker              Aquagiv    AQ-250            Technical     │
│  └ ... (12 more)                                                     │
│                                                                      │
│  WORK ORDERS          12 records    0 duplicates    0 warnings   ▸   │  collapsed
│                                                                      │
│  ⚠ WARNINGS                                                         │
│  ├ Row 8, RUNNING_HOURS: Empty value — will import as NULL           │
│                                                                      │
│  ┌──────────────────┬──────────────────────┐                         │
│  │     Cancel       │   Commit import      │                         │
│  └──────────────────┴──────────────────────┘                         │
│                     ghost btn      btn-brand (or disabled if !can_commit)
└──────────────────────────────────────────────────────────────────────┘
```

**Design rules:**
- **Domain sections** use the entity view section pattern (spec §18): ruled line, 14px/600 heading, count, chevron.
- **First 10 rows** shown as table rows (44px). Expandable per domain.
- **Warnings** in amber: `--amber` text, `--amber-bg` background.
- **Commit button** disabled when `can_commit=false`. Grey, no hover, `cursor: default`.
- **Cancel button** is ghost (no fill, `--txt3` text). Left of commit. Not red — cancelling is safe, not destructive.
- **Row data in mixed font:** equipment name in Inter, serial numbers in mono, dates in mono.

### 7e. CommitScreen (Stage 5)

```
┌─────────────────────────────────────────┐
│  Importing...                           │  status text, --txt
│                                         │
│  ● Writing equipment records            │  active step
│  ○ Writing work orders                  │
│  ○ Updating search index                │
│  ○ Complete                             │
└─────────────────────────────────────────┘

→ After completion:

┌─────────────────────────────────────────┐
│  Import complete                        │  --txt, 16px/600
│                                         │
│  50 records imported across 2 domains.  │  --txt2
│                                         │
│  EQUIPMENT            15                │  mono counts
│  WORK ORDERS          12                │
│  FAULTS                5                │
│  PARTS                10                │
│  CERTIFICATES          8                │
│                                         │
│  Records are being indexed.             │  --txt-ghost
│  Searchable within a few minutes.       │
│                                         │
│  Rollback available until 3 Apr 2026.   │  --txt3, date in mono
│                                         │
│  ┌─────────────────────────────────┐    │
│  │      Open CelesteOS             │    │  btn-brand → app.celeste7.ai
│  └─────────────────────────────────┘    │
│                                         │
│  Rollback this import                   │  teal text link, no button chrome
└─────────────────────────────────────────┘
```

**Design rules:**
- No celebration. No confetti. No "Great job!" Quiet state update (spec principle 9: Boring Is Correct).
- "Records are being indexed. Searchable within a few minutes." — honest about async.
- Rollback link: teal inline action (spec §19). Not a button — low visual weight.
- "Open CelesteOS" button links to `app.celeste7.ai`.

### 7f. RollbackScreen

```
┌─────────────────────────────────────────┐
│  Rollback import                        │
│                                         │
│  This will remove all 50 records        │  --txt
│  imported on 1 Apr 2026 at 14:32.       │  date/time in mono
│                                         │
│  This action cannot be undone.          │  --red
│                                         │
│  ┌─────────────────────────────────┐    │
│  │    Confirm rollback              │    │  red bg, white text
│  └─────────────────────────────────┘    │
│                                         │
│  Cancel                                 │  teal text link
└─────────────────────────────────────────┘
```

**Design rules:**
- Rollback is destructive → red button (spec: `--red` for danger).
- "This action cannot be undone." in `--red` text. Factual, not dramatic.
- Cancel is teal inline action.

---

## 8. ACCESSIBILITY

- All form controls have `aria-label` or associated `<label>`.
- Dropdown uses native `<select>` (accessible by default).
- Confidence indicators have `aria-label="95 percent confidence"` (not colour-only).
- Confirm mapping button has `aria-disabled="true"` with tooltip explaining why when disabled.
- Focus management: auto-focus first interactive element on each screen.
- Keyboard navigation: Tab through mapping rows, Enter to confirm.
- Status polling uses `aria-live="polite"` region for screen readers.

---

## 9. FRONTEND VERIFICATION CRITERIA

Per verification-integrity skill: "200 OK" is not "pass". Every test verifies CONTENT.

### Upload Screen

| Check | How to verify | FALSE SUCCESS if... |
|-------|---------------|---------------------|
| File stored | Response contains `import_session_id` (UUID format) | Response is 200 but session_id is null |
| Source sent correctly | Re-fetch session, verify source matches dropdown | Source is always "generic" regardless of selection |
| File list rendered | DOM contains filename + size | Files accepted but not shown to user |
| Button disabled | Cannot click without source + file | Button enabled with no files |

### Mapping Screen

| Check | How to verify | FALSE SUCCESS if... |
|-------|---------------|---------------------|
| Columns rendered | Count DOM rows === detection_result columns count | Table renders but is empty |
| Confidence colours | Green row has green background | All rows same colour |
| Dropdowns populated | `<select>` options match celeste_vocabulary[domain].mappable | Dropdown has options but they're wrong |
| Sample values shown | 5 values visible per row, monospace | Values shown but from wrong column |
| Confirm disabled | Button has `disabled` attribute when red columns unresolved | Button clickable with unmapped columns |
| Never auto-proceeds | After fetch, screen waits for human click | Screen transitions without user action |

### Preview Screen

| Check | How to verify | FALSE SUCCESS if... |
|-------|---------------|---------------------|
| Counts match | DOM counts === preview_summary.domains[x].total | Shows counts but they don't match API |
| Warnings rendered | Warning count in DOM === warnings array length | "0 warnings" when API returned warnings |
| First 10 rows | Table rows === min(total, 10) | Shows rows but data is placeholder |
| Commit disabled | When can_commit=false, button is disabled | Button enabled despite red errors |
| Cancel works | Clicking cancel navigates back, no data written | Cancel sends commit |

### Commit Screen

| Check | How to verify | FALSE SUCCESS if... |
|-------|---------------|---------------------|
| Records created | Response records_created matches per-domain counts | Shows "50 records" but response says 0 |
| Rollback link visible | DOM contains rollback action within 48h | No rollback option shown |
| Searchable messaging | "Searchable within a few minutes" shown | Claims "instantly searchable" |

### Rollback Screen

| Check | How to verify | FALSE SUCCESS if... |
|-------|---------------|---------------------|
| Records deleted | Response records_deleted has correct counts | "Rolled back" but records still in DB |
| 48h enforcement | After 48h, rollback button is disabled/hidden | Rollback available after expiry |
| Confirmation required | Cannot rollback with single click | One-click rollback without confirmation |

---

## 10. IMPLEMENTATION ORDER (FRONTEND)

| Step | What | Depends on (backend) | Days |
|------|------|---------------------|------|
| F1 | Install react-router, restructure App.tsx | None | 0.5 |
| F2 | Create importApi.ts with types | API contracts locked | 0.5 |
| F3 | UploadScreen + file drop zone | Upload endpoint (B3) | 1 |
| F4 | DetectingScreen (polling) | Detection logic (B2-B4) | 0.5 |
| F5 | MappingScreen + MappingRow (HUMAN GATE) | Confirm-mapping endpoint (B6) | 2 |
| F6 | PreviewScreen + DomainPreview | Dry-run endpoint (B8) | 1 |
| F7 | CommitScreen (progress + completion) | Commit endpoint (B10) | 0.5 |
| F8 | RollbackScreen | Rollback endpoint (B12) | 0.5 |
| F9 | Integration testing against fixtures | All endpoints | 1 |
| **Total frontend** | | | **~7 days** |

F1 + F2 can start immediately (no backend dependency).
F3 starts when backend upload endpoint is ready.
F5 (mapping UI) is the critical path — most complex, 2 days.

---

## 11. OPEN QUESTION FOR BOSS

The DownloadStep currently ends the flow. I'll add a CTA:

> **Have existing maintenance data?**
> Import equipment, work orders, and faults from your current system.
> [Import data →]

This links to `/import`. The question: should this CTA appear for ALL users, or only when the registration backend knows the yacht has no imported data yet?

---

**END OF FRONTEND PLAN — AWAITING BOSS APPROVAL**
