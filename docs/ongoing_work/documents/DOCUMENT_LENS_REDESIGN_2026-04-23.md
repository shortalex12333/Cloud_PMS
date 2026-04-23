# Documents Lens Redesign — Session 2026-04-23

**Engineer:** Claude Sonnet 4.6 (DOCUMENTS04)
**Spec:** `/Users/celeste7/Desktop/celeste-screenshots/doc_cert_ux_change.md`
**Coordinated with:** CERT04 (`peer a4rjnwoe`) — parallel certificate lens redesign; shared section components.
**Branch:** `feat/documents-lens-redesign`
**Base:** `origin/main` at `afd70a18` (after CERT04's PR #663 landed)

---

## Scope (my side)

Per the spec, the file rendered from storage is the primary focus of the
Document lens. Metadata is subsidiary. All UUIDs must resolve to human-readable
labels before they reach the UI. The list view becomes a sortable table.

**In scope:**

1. **Shared section components** (used by both cert + doc lens)
   - `LensFileViewer` — hero PDF / image viewer with loading / error / fallback
   - `RelatedEquipmentSection` — collapsible list + "+ Link equipment" button
   - `EquipmentPickerModal` — alphabetical `pms_equipment` picker with search
   - `RenewalHistorySection` + `SupersededBanner` — prior versions + old-version banner
   - `AuditTrailSection` — enhanced with `actor_role` + `deleted` fields
2. **Design tokens** — `--lens-max-width-wide: 1120px`, `--lens-doc-viewer-h: clamp(480px, 70vh, 760px)`
3. **Backend entity enrichment** — `/v1/entity/document/{id}` resolves all UUIDs:
   - `yacht_name` (from `yacht_registry.name`)
   - `uploaded_by_name` + `uploaded_by_role`
   - `deleted_by_name` + `deleted_by_role`
   - `related_equipment[]` (hydrated from `doc_metadata.equipment_ids`)
   - `audit_trail[]` (from `pms_audit_log`; actor_name + actor_role + deleted flag)
4. **Equipment-array link handlers** — `link_equipment_to_document` +
   `unlink_equipment_from_document` actions that mutate the
   `doc_metadata.equipment_ids` array. Idempotent, yacht-scoped.
5. **DocumentContent.tsx rebuild** — file viewer hero + collapsible sections per spec
6. **Documents list view** — new `DocumentsTableList` with sortable columns

**Out of scope (this PR):**

- `mapActionFields.ts` warning copy for upload attachment (CERT04's scope at
  the moment; will follow in a cross-lens polish PR)
- Documents onboarding bulk-import audit (tracked on `PLAN.md` as gap #2)

---

## Architecture decisions

### UUIDs out, names in
Every UUID the old endpoint used to return as a flat display value now
travels as a paired `{uuid, resolved_label}` set. The frontend renders only
the label; UUIDs remain for internal routing. Resolver: `apps/api/lib/user_resolver.py`
(batch IN-queries, yacht-scoped, null-safe). One resolver both cert and
doc lenses share; we do NOT duplicate logic.

### Storage of equipment ↔ document links
The existing `doc_metadata.equipment_ids uuid[]` column already exists, so
no junction table. Idempotent array mutation via the two new action handlers.
Cross-yacht UUIDs rejected by a validating query before insert, belt-and-
braces on top of RLS.

### Audit trail source
`pms_audit_log` filtered by `entity_type='document'` + `entity_id=<doc_id>`.
Each row's `user_id` / `actor_id` is resolved to name + role via the same
resolver batch. `metadata.deleted` drives the line-through presentation — we
keep every row visible, even deletion events (soft-delete for audit).

### Width handling
`WIDE_LENS_TYPES` set on `EntityLensPage.tsx` applies `.panelWide` when the
entity type is `certificate` or `document`. CSS-class approach (not `:has()`)
so jsdom tests exercise it directly. Token: `--lens-max-width-wide: 1120px`.
Viewer height: `--lens-doc-viewer-h: clamp(480px, 70vh, 760px)` — adapts.

### View mode on the list page
Default view is the existing **Tree** (folder hierarchy). The new **List**
mode with sortable columns is opt-in via a toggle at the top of the page.
Choice persisted to sessionStorage so refresh keeps the user's mode. Sort
state also persisted. Search-active mode pre-empts both.

### Coordination with CERT04
Shared components live in `apps/web/src/components/lens-v2/sections/`; both
lenses import them. `user_resolver.py` shared under `apps/api/lib/`.
`.panelWide` + `WIDE_LENS_TYPES` wiring is CERT04's (they landed first);
this branch rebased onto their commit cleanly. No cert/doc branching inside
any shared component.

---

## Files changed

| File | Change |
|------|--------|
| `apps/web/src/styles/tokens.css` | Added `--lens-max-width-wide`, `--lens-doc-viewer-h` |
| `apps/web/src/components/lens-v2/sections/AuditTrailSection.tsx` | Added `actor_role` + `deleted` fields; line-through rendering |
| `apps/web/src/components/lens-v2/sections/LensFileViewer.tsx` | **NEW** — PDF/image/fallback viewer |
| `apps/web/src/components/lens-v2/sections/RelatedEquipmentSection.tsx` | **NEW** — collapsible list + picker trigger |
| `apps/web/src/components/lens-v2/sections/EquipmentPickerModal.tsx` | **NEW** — alphabetical picker |
| `apps/web/src/components/lens-v2/sections/RenewalHistorySection.tsx` | **NEW** — prior versions + SupersededBanner |
| `apps/web/src/components/lens-v2/sections/index.ts` | Exported new components |
| `apps/web/src/components/lens-v2/entity/DocumentContent.tsx` | Rebuilt around file-viewer hero |
| `apps/web/src/components/documents/DocumentsTableList.tsx` | **NEW** — tabulated list view |
| `apps/web/src/app/documents/page.tsx` | Tree / List view toggle + `DocumentsTableList` wiring |
| `apps/api/lib/user_resolver.py` | **NEW** — shared UUID→label resolver (CERT04's version taken on rebase; API matches mine) |
| `apps/api/routes/entity_routes.py` | `get_document_entity` enriched with resolved labels, related equipment, audit trail |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Added `_doc_link_equipment_to_document`, `_doc_unlink_equipment_from_document` |
| `apps/api/action_router/registry.py` | Registered `link_equipment_to_document` + `unlink_equipment_from_document` actions |
| `apps/api/tests/test_user_resolver.py` | **NEW** — 14 pytest covering resolver contracts (in-memory FakeClient) |
| `apps/web/tests/components/documents/DocumentsTableList.test.tsx` | **NEW** — 14 vitest covering sort / selection / a11y / persistence |

## Verification

| Step | Result |
|------|--------|
| Backend Python AST parse of all four modified files | ✓ pass |
| `pytest apps/api/tests/test_user_resolver.py -v` | 14/14 pass |
| `npx tsc --noEmit` on `apps/web` | exit 0 |
| `npx vitest run tests/components/documents/DocumentsTableList.test.tsx` | 14/14 pass |
| `npx eslint` on all changed frontend files | 0 errors (1 `next/image` warning on blob-URL `<img>`, acceptable) |
| Rebase onto origin/main after CERT04's PR #663 merged | Clean after two conflict resolutions: `user_resolver.py` (took CERT04's — API-equivalent to mine), `AttachmentsSection.tsx` (took CERT04's — has both `title` + `sectionId` to mine's `title`-only) |
| Live DB probes against TENANT `vzsohavtuotocgrfkfyd` | Confirmed `yacht_registry.name`, `auth_users_profiles.id`/`name`, `auth_users_roles.user_id`/`role` schema. `pms_audit_log` has 642 document events for test yacht. |

## Follow-up (not blocking this PR)

| Item | Owner | Notes |
|------|-------|-------|
| Attachment upload popup copy: "DOES NOT OVERWRITE THE DOCUMENT — to replace, use Update Document" | CERT04 / cross-lens | Lives in `mapActionFields.ts`; CERT04 owns that file this cycle |
| Live browser e2e (Playwright) walking the new lens with signed URL | HANDOVER tester (or fresh session) | Needs a doc with real stored file + linked equipment on TEST_YACHT |
| Link document → handover flow for the new related-equipment context | HANDOVER04 | Out of scope |
| `--lens-max-width-wide` adopted by any future doc-embedding lens | n/a | Pattern documented for handover-export viewer if it lands later |

## References

- Spec: `/Users/celeste7/Desktop/celeste-screenshots/doc_cert_ux_change.md`
- Brand: `/Users/celeste7/Documents/CelesteOS-Branding/Brand/colour-system.md`, `frontend_ux.md`
- Sibling PR (cert): GitHub PR #663 (merged `afd70a18`)
- Memory anchors updated: `project_documents_final_status.md` will receive a new change log line when this PR merges.
