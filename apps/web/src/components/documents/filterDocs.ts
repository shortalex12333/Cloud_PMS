/**
 * filterDocs — pure function that applies an ActiveFilters map to a Doc[].
 *
 * Per CEO directive 2026-04-23 the MVP is intentionally simple: client-side
 * ILIKE-style matching on the already-fetched document list. No backend
 * round-trip, no SQL, no injection surface. When the corpus grows past a
 * few thousand rows and in-memory filter becomes a perf concern we'll
 * migrate to server-side params on `/api/vessel/{id}/domain/documents/records`.
 *
 * Filter semantics (one entry per key in DOCUMENT_FILTERS):
 *   text           — case-insensitive substring match (like SQL ILIKE '%v%')
 *   select         — exact match on a derived bucket (see content_type_group)
 *   date-range     — ISO yyyy-mm-dd comparison against the field value
 *                    (field < from → filtered out; field > to → filtered out)
 *
 * tags_text is a special case: the underlying column is text[]; we match if
 * ANY element of the array contains the user input (case-insensitive).
 *
 * All semantics stay null-safe — an empty/missing field fails a non-empty
 * filter (you cannot match "alice" against a doc whose uploaded_by_name is
 * null); an empty filter value is treated as "no filter".
 */

import type { ActiveFilters, DateRange } from '@/features/entity-list/types/filter-config';
import { isDateRange } from '@/features/entity-list/types/filter-config';
import type { Doc } from './docTreeBuilder';

// Extra Doc fields the filter reads that aren't on the base Doc type.
// Defined as an interface so callers who pass richer records work too.
export interface DocRich extends Doc {
  system_type?: string | null;
  oem?: string | null;
  model?: string | null;
  tags?: string[] | null;
}

// ── Helpers ────────────────────────────────────────────────────────────────

/** ILIKE-style substring check. Empty needle ⇒ matches everything. */
function ilike(haystack: string | null | undefined, needle: string): boolean {
  const n = needle.trim().toLowerCase();
  if (!n) return true;
  if (!haystack) return false;
  return haystack.toLowerCase().includes(n);
}

/** Check a value against a date-range. ISO strings compared lexicographically. */
function inDateRange(value: string | null | undefined, range: DateRange): boolean {
  if (!value) return false;
  // Normalise both sides to yyyy-mm-dd for string comparison
  const v = value.slice(0, 10);
  const { from, to } = range;
  if (from && v < from) return false;
  if (to && v > to) return false;
  return true;
}

/** Collapse a raw MIME string to the filter bucket the user selects. */
export function contentTypeGroup(mime: string | null | undefined): string {
  const m = (mime ?? '').toLowerCase();
  if (!m) return 'other';
  if (m === 'application/pdf') return 'pdf';
  if (m.startsWith('image/')) return 'image';
  if (
    m.includes('spreadsheet') ||
    m.includes('excel') ||
    m === 'text/csv' ||
    m === 'application/vnd.ms-excel'
  ) {
    return 'spreadsheet';
  }
  if (
    m.includes('wordprocessingml') ||
    m.includes('msword') ||
    m === 'text/plain' ||
    m === 'text/markdown'
  ) {
    return 'word';
  }
  return 'other';
}

/** Match tags_text against any element of doc.tags (case-insensitive). */
function tagsContains(tags: string[] | null | undefined, needle: string): boolean {
  const n = needle.trim().toLowerCase();
  if (!n) return true;
  if (!tags || tags.length === 0) return false;
  return tags.some((t) => (t ?? '').toLowerCase().includes(n));
}

// ── Main entry ─────────────────────────────────────────────────────────────

/**
 * Apply an ActiveFilters map to a list of docs and return the matching rows.
 *
 * A doc is kept iff it satisfies EVERY active filter (AND across keys).
 * Unknown filter keys are ignored so the function is forward-compatible with
 * filter-config.ts additions that might land before the matching branch here.
 */
export function filterDocs<T extends DocRich>(docs: T[], filters: ActiveFilters): T[] {
  // Fast-path: no filters → return the input unchanged (same array ref is
  // not guaranteed; callers should memoise if that matters)
  if (!filters || Object.keys(filters).length === 0) return docs;

  return docs.filter((doc) => {
    for (const [key, raw] of Object.entries(filters)) {
      if (raw == null) continue;

      switch (key) {
        case 'doc_type':
          if (typeof raw === 'string' && !ilike(doc.doc_type, raw)) return false;
          break;

        case 'system_type':
          if (typeof raw === 'string' && !ilike(doc.system_type, raw)) return false;
          break;

        case 'oem':
          if (typeof raw === 'string' && !ilike(doc.oem, raw)) return false;
          break;

        case 'model':
          if (typeof raw === 'string' && !ilike(doc.model, raw)) return false;
          break;

        case 'uploaded_by_name':
          if (typeof raw === 'string' && !ilike(doc.uploaded_by_name, raw)) return false;
          break;

        case 'tags_text':
          if (typeof raw === 'string' && !tagsContains(doc.tags, raw)) return false;
          break;

        case 'content_type_group': {
          // raw may be a single string or array (multi-select). We treat
          // as set membership.
          const wanted = Array.isArray(raw) ? raw : [raw];
          if (wanted.length > 0 && !wanted.includes(contentTypeGroup(doc.content_type))) {
            return false;
          }
          break;
        }

        case 'created_at':
          if (isDateRange(raw) && !inDateRange(doc.created_at, raw)) return false;
          break;

        case 'updated_at':
          if (isDateRange(raw) && !inDateRange(doc.updated_at, raw)) return false;
          break;

        default:
          // Forward-compat: ignore keys the filter function doesn't yet know.
          break;
      }
    }
    return true;
  });
}
