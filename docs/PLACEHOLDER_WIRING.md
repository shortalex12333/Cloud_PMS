# Placeholder Components — Wiring Guide

Three spotlight components use placeholder/naive data. This doc tracks what each needs wired to real data.

---

## 1. SmartPointers (`apps/web/src/components/spotlight/SmartPointers.tsx`)

**Current:** Queries `faults`, `work_orders`, `inventory` tables from Supabase directly.

**Desired:** Backend API endpoint that returns prioritized attention items.

| Field | Type | Source |
|-------|------|--------|
| `id` | `string` | UUID from source table |
| `severity` | `'critical' \| 'warning' \| 'info' \| 'ok'` | Backend logic (priority + age + threshold) |
| `icon` | `'fault' \| 'work_order' \| 'inventory' \| 'certificate' \| 'receiving' \| 'hours_of_rest'` | Source table type |
| `main` | `string` (HTML with `<strong>`) | Backend template: `<strong>{title}</strong> {suffix}` |
| `sub` | `string` | Mono subtitle: `TYPE · REF · STATUS` |
| `time` | `string` | Relative time delta: `2d open`, `14 days`, `Today` |
| `overflow` | `boolean` | Backend: true for items beyond top 5 |

**Ideal endpoint:** `GET /v1/pointers?yacht_id={id}` → `{ pointers: Pointer[] }`

**Data sources to aggregate:**
- `faults` — open/investigating, sorted by priority then age
- `work_orders` — overdue (due_date < now, status open)
- `inventory` — below min stock (`quantity_on_hand <= minimum_quantity`)
- `certificates` — expiring within 30 days
- `receiving` — expected today/tomorrow
- `hours_of_rest` — crew near MLC limit
- `work_orders` — recently completed, pending sign-off

---

## 2. LensPillStrip (`apps/web/src/components/spotlight/LensPillStrip.tsx`)

**Current:** Static pills with hardcoded labels and routes.

**Desired:** Dynamic pills with real counts and optional urgency badges.

| Field | Type | Source |
|-------|------|--------|
| `label` | `string` | Static (predefined set) |
| `route` | `string` | Static (lens route) |
| `count` | `number \| undefined` | Real-time count from DB |
| `countUrgency` | `'critical' \| 'warning' \| null` | Threshold-based |
| `action` | `boolean` | Static (for action pills like "Log HOR") |

**Counts to wire:**
- `Open Faults` → `SELECT count(*) FROM faults WHERE status IN ('open','investigating')`
- `Overdue W/O` → `SELECT count(*) FROM work_orders WHERE status='open' AND due_date < now()`
- `Upcoming Tasks` → `SELECT count(*) FROM work_orders WHERE status='open' AND due_date BETWEEN now() AND now() + interval '7 days'`
- `Shipment Arriving` → `SELECT count(*) FROM receiving WHERE status='expected' AND expected_date <= now() + interval '2 days'`

**Could share the same `/v1/pointers` endpoint** with a `counts` field.

---

## 3. QueryInterpretation (`apps/web/src/components/spotlight/QueryInterpretation.tsx`)

**Current:** Naive client-side term extraction (splits on spaces, removes noise words).

**Desired:** Backend entity extraction from the search pipeline.

| Field | Type | Source |
|-------|------|--------|
| `text` | `string` | Extracted entity term (e.g. "oil filter", "main engine") |
| `entityType` | `string \| undefined` | Matched type: `part`, `equipment`, `location`, `person` |

**Ideal source:** The search backend already does entity extraction for ranking. Expose it:
- `POST /v1/search` response could include `interpreted_terms: [{text, entity_type}]`
- Or `useCelesteSearch` hook could return `interpretedTerms` alongside results

**Fallback:** Current naive extraction is acceptable for MVP — it just splits the query.

---

## Priority

1. **SmartPointers** — highest value, replaces static data with real attention items
2. **QueryInterpretation** — medium, backend already does this extraction internally
3. **LensPillStrip counts** — low, pills work fine without counts
