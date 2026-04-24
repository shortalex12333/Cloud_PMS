// apps/web/src/lib/__tests__/entityRoutes.test.ts

import { describe, it, expect } from 'vitest';
import { getEntityRoute, type EntityRouteType } from '../entityRoutes';

describe('getEntityRoute', () => {
  it.each<[EntityRouteType, string]>([
    ['work_order', '/work-orders'],
    ['fault', '/faults'],
    ['equipment', '/equipment'],
    ['part', '/inventory'],
    ['email', '/email'],
    ['shopping_list', '/shopping-list'],
    ['receiving', '/receiving'],
    ['document', '/documents'],
    ['certificate', '/certificates'],
    ['warranty', '/warranties'],
    ['purchase_order', '/purchasing'],
    ['hours_of_rest', '/hours-of-rest'],
    ['hours_of_rest_signoff', '/hours-of-rest/signoffs'],
    ['manual', '/documents'],
    ['shopping_item', '/shopping-list'],
    ['inventory', '/inventory'],
    ['handover_export', '/handover-export'],
  ])('resolves %s → %s (no id)', (type, expected) => {
    expect(getEntityRoute(type)).toBe(expected);
  });

  it('appends entityId when supplied', () => {
    expect(getEntityRoute('work_order', 'wo-uuid-1')).toBe('/work-orders/wo-uuid-1');
    expect(getEntityRoute('fault', 'f-uuid-1')).toBe('/faults/f-uuid-1');
    expect(getEntityRoute('hours_of_rest_signoff', 'sig-uuid-1'))
      .toBe('/hours-of-rest/signoffs/sig-uuid-1');
  });

  it('handover_item falls through to "/" — latent-bug guard (2026-04-24)', () => {
    // Previously mapped to /handover-export/{id}, which 404'd because a
    // handover_item.id is not a handover_export.id. Callers needing the real
    // URL should read handover_items.entity_url directly (populated from this
    // helper via the item's source entity_type/entity_id at export time).
    expect(getEntityRoute('handover_item')).toBe('/');
    expect(getEntityRoute('handover_item', 'any-uuid')).toBe('/');
  });

  it('unknown string type falls through to "/"', () => {
    // Runtime-cast because TS type union excludes bogus values.
    expect(getEntityRoute('not_a_real_type' as EntityRouteType)).toBe('/');
  });
});
