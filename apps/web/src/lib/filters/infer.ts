/**
 * Quick Filters Inference Layer
 *
 * Deterministic, rule-based inference from user query to suggested filters.
 * Priority: Pattern matching > Keyword matching
 *
 * NO LLM inference. NO hallucinated filters.
 * Output MUST map to filter_ids from catalog.ts
 */

import { ALL_FILTERS, QuickFilter, getActiveFilters } from './catalog';

export interface InferredFilter {
  filter: QuickFilter;
  score: number; // 0-1, higher = better match
  matchType: 'pattern' | 'keyword' | 'domain';
}

/**
 * Domain detection patterns
 * Maps query prefixes/suffixes to domains
 */
const DOMAIN_PATTERNS: Record<string, RegExp[]> = {
  'work-orders': [
    /work\s*orders?/i,
    /\bwo\b/i,
    /\btasks?\b/i,
    /maintenance\s*(tasks?)?/i,
  ],
  faults: [/faults?/i, /defects?/i, /issues?/i, /problems?/i, /failures?/i],
  equipment: [/equipment/i, /assets?/i, /machinery/i, /systems?/i],
  inventory: [/inventory/i, /parts?/i, /stock/i, /supplies/i, /spares?/i],
  certificates: [/certificates?/i, /certs?/i, /certifications?/i, /compliance/i],
  email: [/emails?/i, /inbox/i, /messages?/i, /threads?/i],
  'shopping-list': [/shopping\s*list/i, /to\s*order/i, /procurement/i],
  receiving: [/receiving/i, /deliveries/i, /shipments?/i],
};

/**
 * High-confidence pattern matches
 * These are explicit feature requests
 */
const EXPLICIT_PATTERNS: Array<{ pattern: RegExp; filter_id: string; score: number }> = [
  // Work Orders
  { pattern: /overdue\s*(work\s*)?orders?/i, filter_id: 'wo_overdue', score: 1.0 },
  { pattern: /(work\s*)?orders?\s*overdue/i, filter_id: 'wo_overdue', score: 1.0 },
  { pattern: /late\s*(work\s*)?orders?/i, filter_id: 'wo_overdue', score: 0.95 },
  { pattern: /past\s*due\s*(work\s*)?orders?/i, filter_id: 'wo_overdue', score: 0.95 },
  { pattern: /due\s*(this\s*)?week/i, filter_id: 'wo_due_7d', score: 0.95 },
  { pattern: /(work\s*)?orders?\s*due\s*(soon|this\s*week)/i, filter_id: 'wo_due_7d', score: 1.0 },
  { pattern: /upcoming\s*(work\s*)?orders?/i, filter_id: 'wo_due_7d', score: 0.9 },
  { pattern: /open\s*(work\s*)?orders?/i, filter_id: 'wo_open', score: 1.0 },
  { pattern: /active\s*(work\s*)?orders?/i, filter_id: 'wo_open', score: 0.95 },
  { pattern: /emergency\s*(work\s*)?orders?/i, filter_id: 'wo_priority_emergency', score: 1.0 },
  { pattern: /critical\s*(priority\s*)?(work\s*)?orders?/i, filter_id: 'wo_priority_critical', score: 0.95 },

  // Faults
  { pattern: /open\s*faults?/i, filter_id: 'fault_open', score: 1.0 },
  { pattern: /active\s*faults?/i, filter_id: 'fault_open', score: 0.95 },
  { pattern: /unresolved\s*faults?/i, filter_id: 'fault_unresolved', score: 1.0 },
  { pattern: /critical\s*faults?/i, filter_id: 'fault_critical', score: 1.0 },
  { pattern: /safety\s*faults?/i, filter_id: 'fault_critical', score: 0.95 },
  { pattern: /severe\s*faults?/i, filter_id: 'fault_critical', score: 0.9 },

  // Equipment
  { pattern: /equipment\s*(needs?\s*)?attention/i, filter_id: 'eq_attention', score: 1.0 },
  { pattern: /flagged\s*equipment/i, filter_id: 'eq_attention', score: 0.95 },
  { pattern: /failed\s*equipment/i, filter_id: 'eq_failed', score: 1.0 },
  { pattern: /broken\s*equipment/i, filter_id: 'eq_failed', score: 0.95 },
  { pattern: /equipment\s*(in\s*)?maintenance/i, filter_id: 'eq_maintenance', score: 1.0 },
  { pattern: /critical\s*equipment/i, filter_id: 'eq_critical', score: 0.95 },

  // Inventory
  { pattern: /low\s*stock/i, filter_id: 'inv_low_stock', score: 1.0 },
  { pattern: /parts?\s*low/i, filter_id: 'inv_low_stock', score: 0.9 },
  { pattern: /running\s*low/i, filter_id: 'inv_low_stock', score: 0.9 },
  { pattern: /below\s*(min(imum)?|reorder)/i, filter_id: 'inv_low_stock', score: 0.95 },
  { pattern: /out\s*of\s*stock/i, filter_id: 'inv_out_of_stock', score: 1.0 },
  { pattern: /zero\s*stock/i, filter_id: 'inv_out_of_stock', score: 0.95 },
  { pattern: /no\s*stock/i, filter_id: 'inv_out_of_stock', score: 0.9 },

  // Certificates
  { pattern: /expir(ing|es?)\s*(soon\s*)?cert/i, filter_id: 'cert_expiring_30d', score: 1.0 },
  { pattern: /cert(ificate)?s?\s*expir/i, filter_id: 'cert_expiring_30d', score: 0.95 },
  { pattern: /expired\s*cert/i, filter_id: 'cert_expired', score: 1.0 },
  { pattern: /cert(ificate)?s?\s*expired/i, filter_id: 'cert_expired', score: 0.95 },

  // Email
  { pattern: /unlinked\s*emails?/i, filter_id: 'email_unlinked', score: 1.0 },
  { pattern: /emails?\s*(not\s*)?linked/i, filter_id: 'email_unlinked', score: 0.9 },
  { pattern: /orphan\s*emails?/i, filter_id: 'email_unlinked', score: 0.95 },
  { pattern: /linked\s*emails?/i, filter_id: 'email_linked', score: 1.0 },
  { pattern: /emails?\s*with\s*attachments?/i, filter_id: 'email_with_attachments', score: 1.0 },

  // Shopping List
  { pattern: /pending\s*(approval\s*)?(shopping|items?)/i, filter_id: 'shop_pending', score: 1.0 },
  { pattern: /awaiting\s*approval/i, filter_id: 'shop_pending', score: 0.95 },
  { pattern: /urgent\s*(shopping\s*)?(items?|orders?)/i, filter_id: 'shop_urgent', score: 1.0 },

  // Receiving
  { pattern: /pending\s*receiv/i, filter_id: 'recv_pending', score: 1.0 },
  { pattern: /receiv(ing|ed)?\s*pending/i, filter_id: 'recv_pending', score: 0.95 },
  { pattern: /discrepanc(y|ies)/i, filter_id: 'recv_discrepancy', score: 0.95 },
];

/**
 * Normalize query for matching
 */
function normalizeQuery(query: string): string {
  return query
    .toLowerCase()
    .trim()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ');
}

/**
 * Detect domain from query
 */
function detectDomain(query: string): string | null {
  const normalized = normalizeQuery(query);
  for (const [domain, patterns] of Object.entries(DOMAIN_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(normalized)) {
        return domain;
      }
    }
  }
  return null;
}

/**
 * Infer filters from user query
 *
 * @param query - User's search query
 * @param maxResults - Maximum number of filters to return (default: 5)
 * @returns Array of inferred filters, sorted by score descending
 */
export function inferFilters(query: string, maxResults = 5): InferredFilter[] {
  if (!query || query.length < 3) {
    return [];
  }

  const normalized = normalizeQuery(query);
  const results: InferredFilter[] = [];
  const seenFilterIds = new Set<string>();
  const activeFilters = getActiveFilters();

  // Phase 1: Explicit pattern matching (highest confidence)
  for (const { pattern, filter_id, score } of EXPLICIT_PATTERNS) {
    if (pattern.test(query) && !seenFilterIds.has(filter_id)) {
      const filter = activeFilters.find((f) => f.filter_id === filter_id);
      if (filter) {
        results.push({ filter, score, matchType: 'pattern' });
        seenFilterIds.add(filter_id);
      }
    }
  }

  // Phase 2: Keyword matching (medium confidence)
  for (const filter of activeFilters) {
    if (seenFilterIds.has(filter.filter_id)) continue;

    let keywordScore = 0;
    let matchedKeywords = 0;

    for (const keyword of filter.keywords) {
      const keywordNorm = keyword.toLowerCase();
      if (normalized.includes(keywordNorm)) {
        matchedKeywords++;
        // Longer keyword matches = higher confidence
        keywordScore += keyword.length / 20;
      }
    }

    if (matchedKeywords > 0) {
      // Cap keyword score at 0.8 (pattern matches are always higher)
      const finalScore = Math.min(0.8, keywordScore / matchedKeywords + 0.3 * matchedKeywords);
      results.push({ filter, score: finalScore, matchType: 'keyword' });
      seenFilterIds.add(filter.filter_id);
    }
  }

  // Phase 3: Domain-based suggestions (lower confidence)
  const domain = detectDomain(query);
  if (domain) {
    const domainFilters = activeFilters.filter(
      (f) => f.domain === domain && !seenFilterIds.has(f.filter_id)
    );
    // Add top 2 domain filters with low score
    for (const filter of domainFilters.slice(0, 2)) {
      results.push({ filter, score: 0.3, matchType: 'domain' });
      seenFilterIds.add(filter.filter_id);
    }
  }

  // Sort by score descending, return top N
  return results.sort((a, b) => b.score - a.score).slice(0, maxResults);
}

/**
 * Check if query explicitly requests a feature (high-confidence match)
 * Use this to decide whether to show chips prominently
 */
export function hasExplicitFilterMatch(query: string): boolean {
  if (!query || query.length < 3) return false;

  for (const { pattern } of EXPLICIT_PATTERNS) {
    if (pattern.test(query)) {
      return true;
    }
  }
  return false;
}

/**
 * Get suggested filters for a specific domain
 * Useful when user is on a list page and we want to suggest relevant filters
 */
export function getSuggestionsForDomain(domain: string, limit = 4): QuickFilter[] {
  return getActiveFilters()
    .filter((f) => f.domain === domain)
    .slice(0, limit);
}
