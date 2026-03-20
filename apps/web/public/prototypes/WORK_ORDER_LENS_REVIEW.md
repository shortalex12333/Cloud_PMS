# Work Order Lens — Implementation Review & Findings

> **Date:** 2026-03-17
> **Scope:** Audit of Work Order lens implementation against design spec + prototype

## Component Inventory

| Layer | File | Status |
|-------|------|--------|
| **UI Component** | `apps/web/src/components/lens/WorkOrderLensContent.tsx` (480 lines) | Exists |
| **Action Hook** | `apps/web/src/hooks/useWorkOrderActions.ts` (~230 lines) | Exists |
| **Permissions Hook** | `apps/web/src/hooks/useWorkOrderActions.ts` (same file, exported) | Exists |
| **Sections** | `NotesSection`, `PartsSection`, `AttachmentsSection`, `HistorySection`, `RelatedEntitiesSection` | All exist |
| **Action Modals** | `AddNoteModal`, `AddPartModal`, `MarkCompleteModal`, `ReassignModal`, `ArchiveModal`, `AddHoursModal`, `EditWorkOrderModal` | All exist |
| **ChecklistSection** | — | **MISSING** |
| **Dropdown Menu UI** | `apps/web/src/components/ui/dropdown-menu.tsx` (Radix) | Exists, unused by WO |

## Finding 1: Checklist — Full Backend, Zero Frontend

The checklist subsystem has complete backend support but no frontend rendering:

| Layer | What Exists | Location |
|-------|------------|----------|
| **Database Table** | `pms_checklist_items` — columns: `id`, `work_order_id`, `description`, `is_completed`, `completed_at`, `completed_by`, `notes`, `sequence` | `database/migrations/` |
| **RLS Policies** | SELECT/INSERT/UPDATE on `authenticated` role | `database/migrations/050_work_order_actions_rls.sql` |
| **Microaction: View** | `viewWorkOrderChecklist()` — queries `pms_checklist_items` by `work_order_id`, returns items + progress `{ completed, total, percent }` | `apps/web/src/lib/microactions/handlers/workOrders.ts:835-906` |
| **Microaction: Complete** | `markChecklistItemComplete()` — updates `is_completed`, `completed_at`, `completed_by` | `workOrders.ts:911-967` |
| **Microaction: Note** | `addChecklistNote()` — inserts into `pms_notes` linked to checklist item | `workOrders.ts:972+` |
| **Hook Wrapper** | `viewChecklist()` — calls `execute('view_work_order_checklist', {})` | `useWorkOrderActions.ts:202-206` |
| **Storage Bucket** | `"checklist_item"` mapped to `"pms-work-order-photos"` | `apps/api/routes/entity_routes.py` |
| **Frontend Component** | **DOES NOT EXIST** | — |
| **Hook Call** | `viewChecklist` is **exported but never called** | — |

**Data flow (when wired):** `pms_checklist_items` table → `POST /v1/actions/execute { action: 'view_work_order_checklist' }` → microaction handler queries Supabase → returns `{ checklist: [...items], progress: { completed, total, percent } }` → frontend renders.

## Finding 2: Action Buttons — Should Be Dropdown

**Current:** 6 separate buttons in a `flex-wrap` row:
1. `Start Work` — PrimaryButton
2. `Mark Complete` — PrimaryButton
3. `Edit` — GhostButton
4. `Log Hours` — GhostButton
5. `Reassign` — GhostButton
6. `Archive` — GhostButton (red)

**Problem:** On mobile, wraps to 2-3 rows. Not scalable. Spec says split button + dropdown.

**Solution:** Primary CTA stays standalone. Secondary actions go into Radix `DropdownMenu` (already in codebase at `apps/web/src/components/ui/dropdown-menu.tsx`).

## Finding 3: Stale Header Comment

Lines 3-8 reference deprecated "1-URL philosophy" and ContextPanel. Architecture is now fragmented URLs (`/work-orders/{id}`).

## Finding 4: MarkCompleteModal Missing Signature

Per design spec, "Mark Complete" should require PIN+TOTP signature (same as Reassign/Archive). Currently has no signature requirement — only optional `completion_notes` textarea.

## Implementation Plan

See plan file for full task breakdown:
- Task 1: Create `ChecklistSection.tsx`
- Task 2: Replace action buttons with dropdown menu
- Task 3: Wire ChecklistSection + fix stale header comment
- Task 4: Verification

## Prototype QA Status (2026-03-17)

All 12 lens prototypes passed systemic QA:

| Check | 12/12 |
|-------|-------|
| 16 new CSS variables in `:root` | PASS |
| 16 new CSS variables in `[data-theme="light"]` | PASS |
| Zero raw `rgba()` in component CSS | PASS |
| Light mode block exists | PASS |
| Theme toggle button/JS exists | PASS |
| Header touch targets = 44px | PASS |
| Split button touch targets = 44px | PASS |
| `var(--border-top)` in `.panel` | PASS |
| `var(--shadow-panel)` in `.panel` | PASS |
| `var(--glass-bg)` in `.lens-hdr` | PASS |

### New CSS Tokens (16 universal + entity-specific)

**Universal (all 12 prototypes):**
`--border-top`, `--border-side`, `--border-bottom`, `--border-faint`, `--border-chrome`, `--shadow-panel`, `--shadow-drop`, `--shadow-tip`, `--glass-bg`, `--split-bg`, `--split-bg-hover`, `--mark-underline`, `--mark-thumb`, `--on-status`, `--neutral-bg`, `--mark-hover`

**Entity-specific:**
- Hours of Rest: `--green-bg-hover` (green-themed split button)
- Equipment: `--amber-bg-hover` (amber-themed split button)
- Parts: `--thumb-grad` (attachment thumbnail gradient)
