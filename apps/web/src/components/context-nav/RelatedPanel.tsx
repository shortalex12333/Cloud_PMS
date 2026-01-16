/**
 * RelatedPanel Component
 *
 * Displays related artifacts grouped by domain.
 * Domain grouping order is FIXED (never dynamic or ranked).
 */

'use client';

import React, { useState } from 'react';
import { useNavigationContext } from '@/contexts/NavigationContext';
import { AddRelatedModal } from './AddRelatedModal';

interface RelatedPanelProps {
  /** Current anchor artifact type */
  anchorType: string;
  /** Current anchor artifact ID */
  anchorId: string;
  /** Navigation context ID */
  contextId: string;
}

export function RelatedPanel({ anchorType, anchorId, contextId }: RelatedPanelProps) {
  const { relatedGroups, relatedLoading, relatedError, pushViewer } = useNavigationContext();
  const [showAddModal, setShowAddModal] = useState(false);

  if (relatedLoading) {
    return (
      <div className="related-panel-loading p-8 text-center">
        <p className="text-gray-500">Loading related artifacts...</p>
      </div>
    );
  }

  if (relatedError) {
    return (
      <div className="related-panel-error p-8 text-center">
        <p className="text-red-600">Error loading related: {relatedError}</p>
      </div>
    );
  }

  if (!relatedGroups || relatedGroups.length === 0) {
    return (
      <div className="related-panel-empty p-8 text-center">
        <p className="text-gray-500 mb-4">No related artifacts found.</p>
        <button className="btn-secondary" onClick={() => setShowAddModal(true)}>
          + Add Related
        </button>
        {showAddModal && (
          <AddRelatedModal
            anchorType={anchorType}
            anchorId={anchorId}
            onClose={() => setShowAddModal(false)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="related-panel p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Related Artifacts</h2>
        <button className="btn-secondary text-sm" onClick={() => setShowAddModal(true)}>
          + Add Related
        </button>
      </div>

      {relatedGroups.map((group) => (
        <section key={group.domain} className="domain-group mb-6">
          <h3 className="text-lg font-medium mb-3 capitalize text-gray-700">
            {group.domain.replace('_', ' ')}
          </h3>
          <ul className="space-y-2">
            {group.items.map((item) => (
              <li
                key={item.artefact_id}
                className="related-item p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => pushViewer(item.artefact_type, item.artefact_id)}
              >
                <div className="font-medium">{item.title}</div>
                {item.subtitle && <div className="text-sm text-gray-600">{item.subtitle}</div>}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {showAddModal && (
        <AddRelatedModal
          anchorType={anchorType}
          anchorId={anchorId}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
