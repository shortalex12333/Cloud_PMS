# Production Pairing — Phase 1: Build lens-v2 in Parallel

> **Goal:** Build new React component library in `apps/web/src/components/lens-v2/` that visually matches the approved prototypes. Zero production files touched. Same data contracts (useEntityLens, EntityLensContext, available_actions).

> **Token Decisions (all 8 resolved — prototype wins):**
> 1. Warm surfaces (#0c0b0a / #181614 / #1e1b18)
> 2. Lighter teal (#5AABCC)
> 3. Muted status colours (#C0503A / #C4893B / #4A9468)
> 4. Asymmetric rgba borders (top 0.11, sides 0.06, bottom 0.03)
> 5. rgba text transparency
> 6. Inter font stack
> 7. Heavy prototype shadows
> 8. Create all prototype-only tokens (glass-bg, split-bg, mark-underline, etc.)

---

## Wave 1 — Foundation (sequential, blocks everything)

- [ ] **1.1** `lens.module.css` — tokens (dark + light) + all component styles from lens-base.css, scoped via CSS module
- [ ] **1.2** `LensShell.tsx` — outer panel (720px, asymmetric borders, scroll body) + EntityLensProvider wrapper
- [ ] **1.3** `LensGlassHeader.tsx` — glass nav bar (back, entity type, related, theme toggle, close)
- [ ] **1.4** `IdentityStrip.tsx` — overline ID, title, context line, pills, detail lines, description
- [ ] **1.5** `SplitButton.tsx` — primary action + dropdown (disabled state, tooltip, danger items)
- [ ] **1.6** `CollapsibleSection.tsx` — section wrapper (separator, heading, icon, count, action, chevron, collapse)
- [ ] **1.7** `LensPill.tsx` — status pill (green/amber/red/neutral)
- [ ] **1.8** `ScrollReveal.tsx` — IntersectionObserver wrapper

## Wave 2 — Shared Sections

- [ ] **2.1** `sections/NotesSection.tsx` — note timeline
- [ ] **2.2** `sections/AuditTrailSection.tsx` — dot timeline
- [ ] **2.3** `sections/AttachmentsSection.tsx` — file rows with thumbnails
- [ ] **2.4** `sections/PartsSection.tsx` — parts list with links
- [ ] **2.5** `sections/ChecklistSection.tsx` — checklist with progress bar
- [ ] **2.6** `sections/DocRowsSection.tsx` — document rows
- [ ] **2.7** `sections/KVSection.tsx` — key-value detail rows
- [ ] **2.8** `sections/index.ts` — barrel export

## Wave 3 — Canary Entity

- [ ] **3.1** `entity/WorkOrderContent.tsx` — first entity, matches lens-work-order.html exactly
- [ ] **3.2** Verify: render at localhost, visual diff against prototype, theme toggle, action buttons

## Wave 4 — Remaining 11 Entities (parallelizable)

- [ ] **4.1** `entity/EquipmentContent.tsx`
- [ ] **4.2** `entity/FaultContent.tsx`
- [ ] **4.3** `entity/CertificateContent.tsx`
- [ ] **4.4** `entity/PartsInventoryContent.tsx`
- [ ] **4.5** `entity/PurchaseOrderContent.tsx`
- [ ] **4.6** `entity/DocumentContent.tsx`
- [ ] **4.7** `entity/WarrantyContent.tsx`
- [ ] **4.8** `entity/HoursOfRestContent.tsx`
- [ ] **4.9** `entity/ShoppingListContent.tsx`
- [ ] **4.10** `entity/ReceivingContent.tsx`
- [ ] **4.11** `entity/HandoverContent.tsx`
- [ ] **4.12** `entity/index.ts` — barrel export

## Wave 5 — Verification

- [ ] **5.1** All 12 entities render without console errors
- [ ] **5.2** Dark + light mode toggle works on all
- [ ] **5.3** Action buttons render from available_actions
- [ ] **5.4** Sections collapse/expand
- [ ] **5.5** Visual diff against prototypes at localhost:3006

---

## Acceptance Criteria

1. Zero production files modified (nothing outside `lens-v2/`)
2. All 12 entity content components visually match approved prototypes
3. Same data contract: useEntityLensContext() for all data + actions
4. Dark + light mode via `[data-theme]` attribute
5. All sections collapsible, scroll reveal, split button dropdown
6. CSS module scoping — no style leaks to/from production components

## Rollback

Delete `apps/web/src/components/lens-v2/` directory. Zero impact on production.
