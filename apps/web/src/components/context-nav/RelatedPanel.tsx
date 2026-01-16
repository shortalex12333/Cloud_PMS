/**
 * RelatedPanel Component
 *
 * Displays related artifacts grouped by domain.
 * Domain grouping order is FIXED (never dynamic or ranked).
 */

'use client';

import React from 'react';
// import type { RelatedGroup } from '@/lib/context-nav/types';

interface RelatedPanelProps {
  /** Current anchor artifact type */
  anchorType: string;
  /** Current anchor artifact ID */
  anchorId: string;
  /** Navigation context ID */
  contextId: string;
}

export function RelatedPanel({ anchorType, anchorId, contextId }: RelatedPanelProps) {
  // TODO: Implement in Phase 4
  // const { groups, loading, error } = useRelated(contextId, anchorType, anchorId);

  const groups: any[] = []; // Placeholder
  const loading = false;

  if (loading) {
    return <div className="related-panel-loading">Loading related artifacts...</div>;
  }

  if (groups.length === 0) {
    return (
      <div className="related-panel-empty p-8 text-center">
        <p className="text-gray-500">No related artifacts found.</p>
        <button className="btn-secondary mt-4">
          + Add Related
        </button>
      </div>
    );
  }

  return (
    <div className="related-panel">
      <h2 className="text-xl font-semibold mb-4">Related</h2>
      {groups.map((group) => (
        <section key={group.domain} className="domain-group mb-6">
          <h3 className="text-lg font-medium mb-2 capitalize">{group.domain}</h3>
          <ul className="space-y-2">
            {group.items.map((item: any) => (
              <li key={item.artefact_id} className="related-item p-3 border rounded hover:bg-gray-50">
                <div className="font-medium">{item.title}</div>
                {item.subtitle && <div className="text-sm text-gray-600">{item.subtitle}</div>}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

// TODO: Implement full functionality in Phase 4
// - Connect to useRelated hook
// - Handle item click → updateAnchor()
// - Add loading/error states
// - Add "Add Related" modal
