/**
 * NotificationBell — route-mapping unit test.
 *
 * Covers the new `handover_export` entity_type wired in by the handover
 * acknowledgement notification cascade: clicking the bell row must go to
 * `/handover-export/{entity_id}` — NOT the legacy `/handover?id=...` query route.
 * Preserves the existing query-string routing for all other entity types.
 */

import { describe, it, expect } from 'vitest';
import { getNotificationRoute } from '../NotificationBell';

describe('getNotificationRoute', () => {
  it('routes handover_export to /handover-export/{id} (path param)', () => {
    expect(getNotificationRoute('handover_export', 'abc-123')).toBe(
      '/handover-export/abc-123',
    );
  });

  it('routes known lens entities to /{lens}?id=', () => {
    expect(getNotificationRoute('certificate', 'c1')).toBe('/certificates?id=c1');
    expect(getNotificationRoute('warranty', 'w1')).toBe('/warranties?id=w1');
    expect(getNotificationRoute('work_order', 'wo1')).toBe('/work-orders?id=wo1');
    expect(getNotificationRoute('fault', 'f1')).toBe('/faults?id=f1');
    expect(getNotificationRoute('equipment', 'e1')).toBe('/equipment?id=e1');
    expect(getNotificationRoute('document', 'd1')).toBe('/documents?id=d1');
    expect(getNotificationRoute('handover', 'h1')).toBe('/handover?id=h1');
    expect(getNotificationRoute('hours_of_rest', 'hr1')).toBe(
      '/hours-of-rest?id=hr1',
    );
  });

  it('falls back to /{entityType}?id= for unknown types', () => {
    expect(getNotificationRoute('unknown', 'x1')).toBe('/unknown?id=x1');
  });
});
