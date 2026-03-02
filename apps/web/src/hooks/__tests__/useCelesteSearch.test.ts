/**
 * Tests for useCelesteSearch route generation
 *
 * Verifies:
 * - Canonical route generation for READ intents
 * - Segment-based URL patterns
 * - Query param fallback for non-segment filters
 * - Route parsing back to filters
 */

import {
  generateCanonicalRoute,
  parseRouteToFilters,
  type IntentEnvelope,
  type IntentFilter,
} from '../useCelesteSearch';

describe('generateCanonicalRoute', () => {
  const baseEnvelope: IntentEnvelope = {
    query: 'test query',
    query_hash: 'abc123',
    timestamp: Date.now(),
    mode: 'READ',
    lens: 'work_order',
    filters: [],
    action: null,
    entities: [],
    readiness_state: 'READY',
    confidence: 0.9,
    deterministic: true,
  };

  it('generates base route for lens with no filters', () => {
    const route = generateCanonicalRoute(baseEnvelope);
    expect(route).toBe('/work-orders');
  });

  it('generates segment route for status filter', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      filters: [{ field: 'status', value: 'open', operator: 'eq' }],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/work-orders/status/open');
  });

  it('generates segment route for priority filter', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      lens: 'fault',
      filters: [{ field: 'priority', value: 'critical', operator: 'eq' }],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/faults/priority/critical');
  });

  it('generates segment route for location filter', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      lens: 'part',
      filters: [{ field: 'location', value: 'box-3d', operator: 'eq' }],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/inventory/location/box-3d');
  });

  it('combines multiple segment filters', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      filters: [
        { field: 'status', value: 'open', operator: 'eq' },
        { field: 'priority', value: 'high', operator: 'eq' },
      ],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/work-orders/status/open/priority/high');
  });

  it('uses query params for non-segment filters', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      filters: [
        { field: 'status', value: 'open', operator: 'eq' },
        { field: 'equipment_id', value: 'me-001', operator: 'eq' },
      ],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/work-orders/status/open?equipment_id=me-001');
  });

  it('returns empty string for MUTATE mode', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      mode: 'MUTATE',
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('');
  });

  it('normalizes filter values for URL safety', () => {
    const envelope: IntentEnvelope = {
      ...baseEnvelope,
      filters: [{ field: 'status', value: 'In Progress', operator: 'eq' }],
    };
    const route = generateCanonicalRoute(envelope);
    expect(route).toBe('/work-orders/status/in-progress');
  });
});

describe('parseRouteToFilters', () => {
  it('parses single segment filter', () => {
    const filters = parseRouteToFilters('/work-orders/status/open');
    expect(filters).toEqual([
      { field: 'status', value: 'open', operator: 'eq' },
    ]);
  });

  it('parses multiple segment filters', () => {
    const filters = parseRouteToFilters('/work-orders/status/open/priority/high');
    expect(filters).toEqual([
      { field: 'status', value: 'open', operator: 'eq' },
      { field: 'priority', value: 'high', operator: 'eq' },
    ]);
  });

  it('restores underscores from hyphens', () => {
    const filters = parseRouteToFilters('/work-orders/status/in-progress');
    expect(filters).toEqual([
      { field: 'status', value: 'in_progress', operator: 'eq' },
    ]);
  });

  it('returns empty array for base path only', () => {
    const filters = parseRouteToFilters('/work-orders');
    expect(filters).toEqual([]);
  });

  it('ignores non-segment fields', () => {
    const filters = parseRouteToFilters('/work-orders/equipment_id/me-001');
    expect(filters).toEqual([]);
  });
});
