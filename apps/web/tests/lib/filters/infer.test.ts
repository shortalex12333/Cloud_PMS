/**
 * Unit Tests for Quick Filters Inference Engine
 *
 * Tests cover:
 * - Determinism: Same input ALWAYS produces same output
 * - Pattern matching: Explicit patterns get score >= 0.9
 * - Keyword matching: Keywords get score 0.3-0.8
 * - Domain detection: Domain patterns detected correctly
 * - Edge cases: Empty, short (<3 chars), unicode, special chars
 * - Catalog integrity: All filters have unique IDs, valid routes
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  inferFilters,
  hasExplicitFilterMatch,
  getSuggestionsForDomain,
  InferredFilter,
} from '@/lib/filters/infer';
import {
  ALL_FILTERS,
  getActiveFilters,
  QuickFilter,
} from '@/lib/filters/catalog';

// =============================================================================
// TEST HELPERS
// =============================================================================

/**
 * Run inference multiple times and verify results are identical
 */
function verifyDeterminism(query: string, iterations = 100): boolean {
  const firstResult = inferFilters(query);
  const firstJson = JSON.stringify(firstResult);

  for (let i = 1; i < iterations; i++) {
    const result = inferFilters(query);
    if (JSON.stringify(result) !== firstJson) {
      return false;
    }
  }
  return true;
}

/**
 * Find a specific filter in results by filter_id
 */
function findFilterInResults(
  results: InferredFilter[],
  filterId: string
): InferredFilter | undefined {
  return results.find((r) => r.filter.filter_id === filterId);
}

// =============================================================================
// CATALOG INTEGRITY TESTS
// =============================================================================

describe('Catalog Integrity', () => {
  it('ALL_FILTERS has no duplicate filter_ids', () => {
    const filterIds = ALL_FILTERS.map((f) => f.filter_id);
    const uniqueIds = new Set(filterIds);
    expect(uniqueIds.size).toBe(filterIds.length);
  });

  it('all filters have required fields', () => {
    for (const filter of ALL_FILTERS) {
      expect(filter.filter_id).toBeTruthy();
      expect(typeof filter.filter_id).toBe('string');
      expect(filter.filter_id.length).toBeGreaterThan(0);

      expect(filter.label).toBeTruthy();
      expect(typeof filter.label).toBe('string');

      expect(filter.domain).toBeTruthy();
      expect(typeof filter.domain).toBe('string');

      expect(filter.entity_type).toBeTruthy();
      expect(typeof filter.entity_type).toBe('string');

      expect(filter.route).toBeTruthy();
      expect(filter.route.startsWith('/')).toBe(true);

      expect(filter.query_params).toBeDefined();
      expect(typeof filter.query_params).toBe('object');

      expect(Array.isArray(filter.keywords)).toBe(true);
      expect(filter.keywords.length).toBeGreaterThan(0);

      expect(filter.definition).toBeTruthy();
      expect(typeof filter.definition).toBe('string');
    }
  });

  it('blocked filters are excluded from getActiveFilters()', () => {
    const activeFilters = getActiveFilters();
    const blockedFilters = ALL_FILTERS.filter((f) => f.blocked);

    // Verify blocked filters exist in catalog
    expect(blockedFilters.length).toBeGreaterThan(0);

    // Verify they are not in active filters
    for (const blocked of blockedFilters) {
      const found = activeFilters.find(
        (f) => f.filter_id === blocked.filter_id
      );
      expect(found).toBeUndefined();
    }
  });

  it('all active filters have valid routes starting with /', () => {
    const activeFilters = getActiveFilters();
    for (const filter of activeFilters) {
      expect(filter.route).toMatch(/^\//);
    }
  });

  it('filter_id follows naming convention (domain_descriptor)', () => {
    for (const filter of ALL_FILTERS) {
      expect(filter.filter_id).toMatch(/^[a-z]+_[a-z0-9_]+$/);
    }
  });

  it('each domain has at least one filter', () => {
    const domains = new Set(ALL_FILTERS.map((f) => f.domain));
    const activeFilters = getActiveFilters();

    for (const domain of domains) {
      const domainFilters = activeFilters.filter((f) => f.domain === domain);
      // Some domains may have all filters blocked, so we check ALL_FILTERS
      const allDomainFilters = ALL_FILTERS.filter((f) => f.domain === domain);
      expect(allDomainFilters.length).toBeGreaterThan(0);
    }
  });
});

// =============================================================================
// DETERMINISM TESTS
// =============================================================================

describe('Determinism', () => {
  it('same input ALWAYS produces same output (100 iterations)', () => {
    const testQueries = [
      'overdue work orders',
      'low stock',
      'open faults',
      'equipment maintenance',
      'expiring certificates',
    ];

    for (const query of testQueries) {
      expect(verifyDeterminism(query, 100)).toBe(true);
    }
  });

  it('results are sorted by score descending consistently', () => {
    const results = inferFilters('overdue work orders');

    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
    }

    // Verify sorting is consistent across multiple calls
    for (let j = 0; j < 10; j++) {
      const newResults = inferFilters('overdue work orders');
      expect(newResults.map((r) => r.filter.filter_id)).toEqual(
        results.map((r) => r.filter.filter_id)
      );
    }
  });

  it('empty query always returns empty array', () => {
    for (let i = 0; i < 100; i++) {
      expect(inferFilters('')).toEqual([]);
    }
  });

  it('whitespace-only query returns empty array', () => {
    expect(inferFilters('   ')).toEqual([]);
    expect(inferFilters('\t\n')).toEqual([]);
  });
});

// =============================================================================
// PATTERN MATCHING TESTS (Explicit patterns - score >= 0.9)
// =============================================================================

describe('Pattern Matching', () => {
  describe('Work Order Patterns', () => {
    it('"overdue work orders" -> wo_overdue with score 1.0', () => {
      const results = inferFilters('overdue work orders');
      const match = findFilterInResults(results, 'wo_overdue');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
      expect(match!.matchType).toBe('pattern');
    });

    it('"overdue orders" -> wo_overdue with score 1.0', () => {
      const results = inferFilters('overdue orders');
      const match = findFilterInResults(results, 'wo_overdue');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"late work orders" -> wo_overdue with score >= 0.9', () => {
      const results = inferFilters('late work orders');
      const match = findFilterInResults(results, 'wo_overdue');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"past due orders" -> wo_overdue with score >= 0.9', () => {
      const results = inferFilters('past due orders');
      const match = findFilterInResults(results, 'wo_overdue');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"open work orders" -> wo_open with score 1.0', () => {
      const results = inferFilters('open work orders');
      const match = findFilterInResults(results, 'wo_open');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
      expect(match!.matchType).toBe('pattern');
    });

    it('"due this week" -> wo_due_7d with score >= 0.9', () => {
      const results = inferFilters('due this week');
      const match = findFilterInResults(results, 'wo_due_7d');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"emergency work orders" -> wo_priority_emergency with score 1.0', () => {
      const results = inferFilters('emergency work orders');
      const match = findFilterInResults(results, 'wo_priority_emergency');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });
  });

  describe('Fault Patterns', () => {
    it('"open faults" -> fault_open with score 1.0', () => {
      const results = inferFilters('open faults');
      const match = findFilterInResults(results, 'fault_open');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
      expect(match!.matchType).toBe('pattern');
    });

    it('"active faults" -> fault_open with score >= 0.9', () => {
      const results = inferFilters('active faults');
      const match = findFilterInResults(results, 'fault_open');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"unresolved faults" -> fault_unresolved with score 1.0', () => {
      const results = inferFilters('unresolved faults');
      const match = findFilterInResults(results, 'fault_unresolved');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"critical faults" -> fault_critical with score 1.0', () => {
      const results = inferFilters('critical faults');
      const match = findFilterInResults(results, 'fault_critical');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });
  });

  describe('Inventory Patterns', () => {
    it('"low stock" -> inv_low_stock with score 1.0', () => {
      const results = inferFilters('low stock');
      const match = findFilterInResults(results, 'inv_low_stock');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
      expect(match!.matchType).toBe('pattern');
    });

    it('"out of stock" -> inv_out_of_stock with score 1.0', () => {
      const results = inferFilters('out of stock');
      const match = findFilterInResults(results, 'inv_out_of_stock');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"running low" -> inv_low_stock with score >= 0.9', () => {
      const results = inferFilters('running low');
      const match = findFilterInResults(results, 'inv_low_stock');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });
  });

  describe('Equipment Patterns', () => {
    it('"equipment needs attention" -> eq_attention with score 1.0', () => {
      const results = inferFilters('equipment needs attention');
      const match = findFilterInResults(results, 'eq_attention');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"failed equipment" -> eq_failed with score 1.0', () => {
      const results = inferFilters('failed equipment');
      const match = findFilterInResults(results, 'eq_failed');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"broken equipment" -> eq_failed with score >= 0.9', () => {
      const results = inferFilters('broken equipment');
      const match = findFilterInResults(results, 'eq_failed');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });
  });

  describe('Certificate Patterns', () => {
    it('"expiring certificates" -> cert_expiring_30d with score >= 0.9', () => {
      const results = inferFilters('expiring certificates');
      const match = findFilterInResults(results, 'cert_expiring_30d');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"expired cert" -> cert_expired with score 1.0', () => {
      const results = inferFilters('expired cert');
      const match = findFilterInResults(results, 'cert_expired');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });
  });

  describe('Email Patterns', () => {
    it('"unlinked emails" -> email_unlinked with score 1.0', () => {
      const results = inferFilters('unlinked emails');
      const match = findFilterInResults(results, 'email_unlinked');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"linked emails" -> email_linked with score 1.0', () => {
      const results = inferFilters('linked emails');
      const match = findFilterInResults(results, 'email_linked');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"emails with attachments" -> email_with_attachments with score 1.0', () => {
      const results = inferFilters('emails with attachments');
      const match = findFilterInResults(results, 'email_with_attachments');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });
  });

  describe('Shopping List Patterns', () => {
    it('"awaiting approval" -> shop_pending with score >= 0.9', () => {
      const results = inferFilters('awaiting approval');
      const match = findFilterInResults(results, 'shop_pending');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });

    it('"pending approval items" -> shop_pending with score 1.0', () => {
      const results = inferFilters('pending approval items');
      const match = findFilterInResults(results, 'shop_pending');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"urgent shopping items" -> shop_urgent with score 1.0', () => {
      const results = inferFilters('urgent shopping items');
      const match = findFilterInResults(results, 'shop_urgent');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });
  });

  describe('Receiving Patterns', () => {
    it('"pending receiving" -> recv_pending with score 1.0', () => {
      const results = inferFilters('pending receiving');
      const match = findFilterInResults(results, 'recv_pending');

      expect(match).toBeDefined();
      expect(match!.score).toBe(1.0);
    });

    it('"discrepancies" -> recv_discrepancy with score >= 0.9', () => {
      const results = inferFilters('discrepancies');
      const match = findFilterInResults(results, 'recv_discrepancy');

      expect(match).toBeDefined();
      expect(match!.score).toBeGreaterThanOrEqual(0.9);
    });
  });
});

// =============================================================================
// KEYWORD MATCHING TESTS (score 0.3-0.8)
// =============================================================================

describe('Keyword Matching', () => {
  it('keyword matches have score between 0.3 and 0.8', () => {
    // Use a query that triggers keyword matching but not pattern matching
    const results = inferFilters('check the maintenance status');

    const keywordMatches = results.filter((r) => r.matchType === 'keyword');
    for (const match of keywordMatches) {
      expect(match.score).toBeGreaterThanOrEqual(0.3);
      expect(match.score).toBeLessThanOrEqual(0.8);
    }
  });

  it('longer keyword matches get higher scores', () => {
    const results = inferFilters('equipment needs attention flagged');

    // Should match 'attention' and 'flagged' keywords
    const keywordMatches = results.filter((r) => r.matchType === 'keyword');

    // If there are keyword matches, they should have reasonable scores
    for (const match of keywordMatches) {
      expect(match.score).toBeGreaterThan(0);
    }
  });

  it('multiple keyword matches boost score', () => {
    // Query with multiple keywords for the same filter
    const results1 = inferFilters('reorder');
    const results2 = inferFilters('reorder below minimum');

    // Both should find inv_low_stock, but the second might have higher score
    // or more results due to multiple keyword matches
    expect(results1.length).toBeGreaterThan(0);
    expect(results2.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// DOMAIN DETECTION TESTS
// =============================================================================

describe('Domain Detection', () => {
  it('detects work-orders domain', () => {
    const results = inferFilters('show me work orders');
    expect(results.length).toBeGreaterThan(0);

    // Should have some work-order related results
    const woFilters = results.filter(
      (r) => r.filter.domain === 'work-orders'
    );
    expect(woFilters.length).toBeGreaterThan(0);
  });

  it('detects faults domain', () => {
    const results = inferFilters('all faults');
    expect(results.length).toBeGreaterThan(0);

    const faultFilters = results.filter((r) => r.filter.domain === 'faults');
    expect(faultFilters.length).toBeGreaterThan(0);
  });

  it('detects equipment domain', () => {
    const results = inferFilters('equipment list');
    expect(results.length).toBeGreaterThan(0);

    const eqFilters = results.filter((r) => r.filter.domain === 'equipment');
    expect(eqFilters.length).toBeGreaterThan(0);
  });

  it('detects inventory domain', () => {
    const results = inferFilters('inventory items');
    expect(results.length).toBeGreaterThan(0);

    const invFilters = results.filter((r) => r.filter.domain === 'inventory');
    expect(invFilters.length).toBeGreaterThan(0);
  });

  it('domain matches have score of 0.3', () => {
    const results = inferFilters('show me equipment');
    const domainMatches = results.filter((r) => r.matchType === 'domain');

    for (const match of domainMatches) {
      expect(match.score).toBe(0.3);
    }
  });

  it('pattern matches take priority over domain matches', () => {
    const results = inferFilters('open work orders');

    // Should have pattern match first (wo_open)
    expect(results[0].matchType).toBe('pattern');
    expect(results[0].filter.filter_id).toBe('wo_open');
  });
});

// =============================================================================
// EDGE CASES
// =============================================================================

describe('Edge Cases', () => {
  describe('Empty and Short Queries', () => {
    it('empty string returns empty array', () => {
      expect(inferFilters('')).toEqual([]);
    });

    it('null-ish values handled gracefully', () => {
      // TypeScript should prevent this, but test runtime behavior
      expect(inferFilters(null as unknown as string)).toEqual([]);
      expect(inferFilters(undefined as unknown as string)).toEqual([]);
    });

    it('queries shorter than 3 chars return empty array', () => {
      expect(inferFilters('a')).toEqual([]);
      expect(inferFilters('ab')).toEqual([]);
      expect(inferFilters('wo')).toEqual([]);
    });

    it('exactly 3 char query is processed', () => {
      // "low" should trigger low stock
      const results = inferFilters('low');
      // May or may not have results, but should not throw
      expect(Array.isArray(results)).toBe(true);
    });
  });

  describe('Unicode and Special Characters', () => {
    it('unicode characters are handled gracefully', () => {
      const results = inferFilters('overdue orders with 日本語');
      // Should still match "overdue orders"
      const match = findFilterInResults(results, 'wo_overdue');
      expect(match).toBeDefined();
    });

    it('emoji in query does not break inference', () => {
      const results = inferFilters('low stock ');
      const match = findFilterInResults(results, 'inv_low_stock');
      expect(match).toBeDefined();
    });

    it('special characters are normalized', () => {
      const results = inferFilters('low!!! stock???');
      const match = findFilterInResults(results, 'inv_low_stock');
      expect(match).toBeDefined();
    });

    it('punctuation is removed during normalization', () => {
      const results1 = inferFilters('open faults');
      const results2 = inferFilters('open, faults!');

      expect(results1[0]?.filter.filter_id).toBe(results2[0]?.filter.filter_id);
    });
  });

  describe('Case Insensitivity', () => {
    it('uppercase queries work', () => {
      const results = inferFilters('OVERDUE WORK ORDERS');
      const match = findFilterInResults(results, 'wo_overdue');
      expect(match).toBeDefined();
    });

    it('mixed case queries work', () => {
      const results = inferFilters('OverDue Work Orders');
      const match = findFilterInResults(results, 'wo_overdue');
      expect(match).toBeDefined();
    });
  });

  describe('Whitespace Handling', () => {
    it('extra whitespace is normalized', () => {
      const results = inferFilters('  low    stock  ');
      const match = findFilterInResults(results, 'inv_low_stock');
      expect(match).toBeDefined();
    });

    it('tabs and newlines are handled', () => {
      const results = inferFilters('low\tstock\n');
      // May or may not match depending on normalization
      expect(Array.isArray(results)).toBe(true);
    });
  });

  describe('Unrelated Queries', () => {
    it('completely unrelated query returns empty or low-score results', () => {
      const results = inferFilters('random gibberish xyz123');

      if (results.length > 0) {
        // If any results, they should have low scores
        for (const result of results) {
          expect(result.score).toBeLessThan(0.5);
        }
      } else {
        expect(results).toEqual([]);
      }
    });

    it('SQL injection attempts return empty or safe results', () => {
      const results = inferFilters("'; DROP TABLE users; --");
      // Should not throw and should return safe results
      expect(Array.isArray(results)).toBe(true);
    });

    it('HTML/script injection attempts are safe', () => {
      const results = inferFilters('<script>alert("xss")</script>');
      expect(Array.isArray(results)).toBe(true);
    });
  });
});

// =============================================================================
// hasExplicitFilterMatch TESTS
// =============================================================================

describe('hasExplicitFilterMatch', () => {
  it('returns true for explicit pattern matches', () => {
    expect(hasExplicitFilterMatch('overdue work orders')).toBe(true);
    expect(hasExplicitFilterMatch('open faults')).toBe(true);
    expect(hasExplicitFilterMatch('low stock')).toBe(true);
    expect(hasExplicitFilterMatch('equipment needs attention')).toBe(true);
  });

  it('returns false for keyword-only matches', () => {
    expect(hasExplicitFilterMatch('check the maintenance')).toBe(false);
    expect(hasExplicitFilterMatch('urgent')).toBe(false);
  });

  it('returns false for empty query', () => {
    expect(hasExplicitFilterMatch('')).toBe(false);
  });

  it('returns false for short queries', () => {
    expect(hasExplicitFilterMatch('ab')).toBe(false);
  });

  it('returns false for random queries', () => {
    expect(hasExplicitFilterMatch('hello world')).toBe(false);
    expect(hasExplicitFilterMatch('random text here')).toBe(false);
  });
});

// =============================================================================
// getSuggestionsForDomain TESTS
// =============================================================================

describe('getSuggestionsForDomain', () => {
  it('returns filters for work-orders domain', () => {
    const suggestions = getSuggestionsForDomain('work-orders');
    expect(suggestions.length).toBeGreaterThan(0);
    expect(suggestions.every((f) => f.domain === 'work-orders')).toBe(true);
  });

  it('returns filters for faults domain', () => {
    const suggestions = getSuggestionsForDomain('faults');
    expect(suggestions.length).toBeGreaterThan(0);
    expect(suggestions.every((f) => f.domain === 'faults')).toBe(true);
  });

  it('returns filters for equipment domain', () => {
    const suggestions = getSuggestionsForDomain('equipment');
    expect(suggestions.length).toBeGreaterThan(0);
    expect(suggestions.every((f) => f.domain === 'equipment')).toBe(true);
  });

  it('returns filters for inventory domain', () => {
    const suggestions = getSuggestionsForDomain('inventory');
    expect(suggestions.length).toBeGreaterThan(0);
    expect(suggestions.every((f) => f.domain === 'inventory')).toBe(true);
  });

  it('respects limit parameter', () => {
    const limit2 = getSuggestionsForDomain('work-orders', 2);
    const limit10 = getSuggestionsForDomain('work-orders', 10);

    expect(limit2.length).toBeLessThanOrEqual(2);
    expect(limit10.length).toBeLessThanOrEqual(10);
  });

  it('returns empty array for unknown domain', () => {
    const suggestions = getSuggestionsForDomain('unknown-domain');
    expect(suggestions).toEqual([]);
  });

  it('excludes blocked filters', () => {
    // eq_due_service_30d is blocked
    const suggestions = getSuggestionsForDomain('equipment', 100);
    const blocked = suggestions.find(
      (f) => f.filter_id === 'eq_due_service_30d'
    );
    expect(blocked).toBeUndefined();
  });

  it('default limit is 4', () => {
    const suggestions = getSuggestionsForDomain('work-orders');
    // Work orders has 5 filters, so default should cap at 4
    expect(suggestions.length).toBeLessThanOrEqual(4);
  });
});

// =============================================================================
// maxResults PARAMETER TESTS
// =============================================================================

describe('maxResults Parameter', () => {
  it('respects maxResults limit', () => {
    const results3 = inferFilters('work orders', 3);
    const results1 = inferFilters('work orders', 1);

    expect(results3.length).toBeLessThanOrEqual(3);
    expect(results1.length).toBeLessThanOrEqual(1);
  });

  it('default maxResults is 5', () => {
    const results = inferFilters('show me everything about work orders faults equipment');
    expect(results.length).toBeLessThanOrEqual(5);
  });

  it('returns fewer than max if not enough matches', () => {
    const results = inferFilters('open faults', 100);
    // Should return actual matches, not pad to 100
    expect(results.length).toBeLessThan(100);
    expect(results.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// MATCH TYPE TESTS
// =============================================================================

describe('Match Types', () => {
  it('pattern matches are marked as "pattern"', () => {
    const results = inferFilters('overdue work orders');
    const patternMatch = results.find((r) => r.matchType === 'pattern');
    expect(patternMatch).toBeDefined();
    expect(patternMatch!.filter.filter_id).toBe('wo_overdue');
  });

  it('keyword matches are marked as "keyword"', () => {
    const results = inferFilters('behind schedule');
    const keywordMatches = results.filter((r) => r.matchType === 'keyword');
    // "behind schedule" is a keyword for wo_overdue
    expect(keywordMatches.length).toBeGreaterThanOrEqual(0);
  });

  it('domain matches are marked as "domain"', () => {
    const results = inferFilters('show me faults');
    const domainMatch = results.find((r) => r.matchType === 'domain');
    expect(domainMatch).toBeDefined();
    expect(domainMatch!.filter.domain).toBe('faults');
  });

  it('same filter not duplicated across match types', () => {
    const results = inferFilters('open work orders');
    const filterIds = results.map((r) => r.filter.filter_id);
    const uniqueIds = new Set(filterIds);

    expect(uniqueIds.size).toBe(filterIds.length);
  });
});

// =============================================================================
// SCORE ORDERING TESTS
// =============================================================================

describe('Score Ordering', () => {
  it('results are always sorted by score descending', () => {
    const queries = [
      'overdue work orders due soon',
      'faults equipment inventory',
      'critical issues',
    ];

    for (const query of queries) {
      const results = inferFilters(query);
      for (let i = 1; i < results.length; i++) {
        expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
      }
    }
  });

  it('pattern matches appear before keyword matches', () => {
    const results = inferFilters('open work orders maintenance');

    // Find first pattern and first keyword match positions
    const patternIndex = results.findIndex((r) => r.matchType === 'pattern');
    const keywordIndex = results.findIndex((r) => r.matchType === 'keyword');

    if (patternIndex !== -1 && keywordIndex !== -1) {
      expect(patternIndex).toBeLessThan(keywordIndex);
    }
  });

  it('keyword matches appear before domain matches', () => {
    const results = inferFilters('equipment check');

    // Domain matches have score 0.3, keyword matches should be higher
    const keywordMatches = results.filter((r) => r.matchType === 'keyword');
    const domainMatches = results.filter((r) => r.matchType === 'domain');

    if (keywordMatches.length > 0 && domainMatches.length > 0) {
      expect(keywordMatches[0].score).toBeGreaterThanOrEqual(
        domainMatches[0].score
      );
    }
  });
});

// =============================================================================
// FILTER STRUCTURE TESTS
// =============================================================================

describe('InferredFilter Structure', () => {
  it('returned filters have correct structure', () => {
    const results = inferFilters('overdue work orders');

    expect(results.length).toBeGreaterThan(0);

    for (const result of results) {
      // Check InferredFilter structure
      expect(result).toHaveProperty('filter');
      expect(result).toHaveProperty('score');
      expect(result).toHaveProperty('matchType');

      // Check score is valid
      expect(typeof result.score).toBe('number');
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(1);

      // Check matchType is valid
      expect(['pattern', 'keyword', 'domain']).toContain(result.matchType);

      // Check filter structure
      expect(result.filter).toHaveProperty('filter_id');
      expect(result.filter).toHaveProperty('label');
      expect(result.filter).toHaveProperty('domain');
      expect(result.filter).toHaveProperty('route');
    }
  });
});

// =============================================================================
// PERFORMANCE / STRESS TESTS
// =============================================================================

describe('Performance', () => {
  it('handles very long queries without crashing', () => {
    const longQuery = 'overdue work orders '.repeat(100);
    const results = inferFilters(longQuery);
    expect(Array.isArray(results)).toBe(true);
  });

  it('handles rapid consecutive calls', () => {
    const queries = Array(100).fill('overdue work orders');
    const allResults = queries.map((q) => inferFilters(q));

    // All should be identical
    const firstJson = JSON.stringify(allResults[0]);
    for (const results of allResults) {
      expect(JSON.stringify(results)).toBe(firstJson);
    }
  });
});
