# EntityTableList — Shared Spec

**Date:** 2026-04-23
**Author:** DOCUMENTS04
**Co-signed:** CERT04 · RECEIVING05 · SHOPPING05 (PURCHASE05 to follow)
**Component:** `apps/web/src/features/entity-list/components/EntityTableList.tsx`

---

## Purpose

CEO directive 2026-04-23: every lens list view moves from card-style
(SpotlightResultRow / EntityRecordRow) to a **tabulated format with
click-to-sort headers**. Same component renders on every domain; each
lens drops in a **column spec**; nothing else forks.

Parallel to the `FilterPanel` + `FilterFieldConfig` rollout earlier tonight.

---

## The contract

```ts
interface EntityTableColumn<T> {
  key: string;                                       // sort id + React key
  label: string;                                     // header cell text
  accessor: (row: T) => string | number | null;      // cell display value
  sortAccessor?: (row: T) => string | number | null; // default = accessor
  render?: (row: T) => React.ReactNode;              // overrides display (pills, badges)
  align?: 'left' | 'right';                          // default left; right for numbers
  mono?: boolean;                                    // mono font for ids, dates, sizes
  minWidth?: number;
  maxWidth?: number;                                 // triggers ellipsis when !wrap
  wrap?: boolean;                                    // word-wrap instead of truncate
}

interface EntityTableListProps<T extends { id: string; yachtId?: string }> {
  rows: T[];
  columns: EntityTableColumn<T>[];
  onSelect: (id: string, yachtId?: string) => void;
  selectedId?: string | null;
  domain: string;              // sort-state namespace: celeste:<domain>:sort
  isLoading?: boolean;
  emptyMessage?: string;
  loadingMessage?: string;
}
```

---

## Behaviour the component guarantees

| Behaviour | Detail |
|---|---|
| Click cycle | `none → asc → desc → none` on the clicked header |
| aria-sort | `'none'` / `'ascending'` / `'descending'` reflects state |
| Null sort | Rows where `sortAccessor` returns `null`/`undefined` always sort to the **end** regardless of direction |
| Numeric sort | `sortAccessor` returning `number` → numeric compare; otherwise lexicographic string |
| Keyboard | Headers focusable; `Enter` / `Space` toggles sort. Rows focusable; `Enter` fires `onSelect` |
| Selection | `selectedId` match → `aria-selected=true` + `--teal-bg` background |
| Persistence | Sort state at `sessionStorage['celeste:<domain>:sort']`; restored on mount; removed when cycle returns to `none` |
| Em-dash | Empty / null accessor returns render as `—` in `--text-tertiary` |
| Hover | Non-selected rows highlight with `--surface-hover` |
| Sticky header | `position: sticky; top: 0` |

---

## Tokens used

All existing; **zero new tokens.**

```
Surfaces    var(--surface-base)  var(--surface)  var(--surface-hover)
Borders     var(--border-sub)    var(--border-faint)
Text        var(--text-primary)  var(--text-secondary)  var(--text-tertiary)
Selection   var(--teal-bg)       var(--brand-interactive)
Type        var(--font-sans)     var(--font-mono)
            var(--font-size-body) var(--font-size-caption)
            var(--font-weight-label) var(--letter-spacing-label)
Spacing     var(--space-3)  var(--space-4)  var(--space-6)
Motion      var(--duration-fast)  var(--ease-out)
```

---

## Per-lens column spec — one file per lens

Colocated with each lens's adapter / filter-config.

| Lens | File | Exported symbol | Status |
|---|---|---|---|
| documents | `components/documents/DocumentsTableList.tsx` | `DOCUMENT_COLUMNS` | ✅ In this PR |
| certificates | tbd | `CERTIFICATE_COLUMNS` | 🚧 CERT04 waiting |
| receiving | tbd | `RECEIVING_COLUMNS` | 🚧 RECEIVING05 waiting |
| shopping-list | tbd | `SHOPPING_LIST_COLUMNS` | 🚧 SHOPPING05 waiting |
| work-orders | tbd | `WORK_ORDER_COLUMNS` | 🟥 |
| purchase-orders | tbd | `PURCHASE_ORDER_COLUMNS` | 🟥 |
| warranty | tbd | `WARRANTY_COLUMNS` | 🟥 |
| hours-of-rest | tbd | `HOURS_OF_REST_COLUMNS` | 🟥 |
| handover | tbd | `HANDOVER_COLUMNS` | 🟥 |

---

## What the component deliberately does NOT do

- **No column visibility toggle** — columns defined by the spec; iterate per lens.
- **No virtualisation** — current per-yacht corpus fits. Add later if any lens exceeds ~2k.
- **No drag-to-reorder** — add when there's signal users want it.
- **No multi-column sort** — single column, cycle through direction. Keeps the mental model clean.
- **No server-side sort** — local sort on in-memory rows. Lenses that server-paginate need a different shared abstraction (future).
- **No export button** — per-lens toolbar can add one that reads the rows prop.

---

## Rollout pattern (matches FilterPanel rollout)

1. Component lands on `main` (this PR). Other lenses keep rendering cards unchanged until their owner migrates.
2. Each lens owner opens a follow-up PR that:
   - Adds `X_COLUMNS: EntityTableColumn<T>[]` in the lens's column-spec file
   - Replaces the list render with `<EntityTableList rows={items} columns={X_COLUMNS} ... />`
   - Adds unit tests for column formatters + any `render` callbacks
3. Lens-specific things (status pill palette, badges, days-to-expiry chips) live in `render` callbacks inside the column spec — the shared component stays dumb.

---

## Reference implementation

`DocumentsTableList` in this PR:

- `DOCUMENT_COLUMNS: EntityTableColumn<DocRichLike>[]` — 9 columns (Filename / Type / System / OEM / Model / Uploaded by / Size / Created / Updated)
- Mix of text columns (lowercased for sort), mono columns (size/dates/model), one right-aligned numeric column (size, using numeric sort via `sortAccessor` returning the raw `number`)
- Wrapper preserves the prior `<DocumentsTableList docs=… onSelect=… selectedDocId=… />` API so existing call sites keep working without migration

---

## Tests

- `apps/web/tests/components/entity-list/EntityTableList.test.tsx` — **23** tests covering every generic contract (empty/loading, cell rendering, sort cycle, numeric sort, null-to-end, keyboard nav, per-domain sessionStorage, selection, `render` slot, `compareValues`)
- `apps/web/tests/components/documents/DocumentsTableList.test.tsx` — **14** existing tests still green against the new wrapper (API preserved)

**Total: 37/37 green via vitest.**
