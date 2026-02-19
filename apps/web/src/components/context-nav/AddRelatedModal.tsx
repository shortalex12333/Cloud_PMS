/**
 * AddRelatedModal Component
 *
 * Modal for adding explicit user relations between artifacts.
 * Only shown when related panel is empty or user clicks "+ Add Related".
 */

'use client';

import React, { useState } from 'react';
import { addUserRelation } from '@/lib/context-nav/api-client';
import { useNavigationContext } from '@/contexts/NavigationContext';

interface AddRelatedModalProps {
  anchorType: string;
  anchorId: string;
  onClose: () => void;
}

export function AddRelatedModal({ anchorType, anchorId, onClose }: AddRelatedModalProps) {
  const { pushRelated, yachtId, userId } = useNavigationContext();
  const [toArtifactType, setToArtifactType] = useState('');
  const [toArtifactId, setToArtifactId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // CRITICAL: Do NOT use placeholders - fail visibly if auth not ready
    if (!yachtId || !userId) {
      setError('Authentication required. Please log in.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Use yacht_id and user_id from NavigationContext (synced from AuthContext)

      await addUserRelation({
        yacht_id: yachtId,
        user_id: userId,
        from_artefact_type: anchorType,
        from_artefact_id: anchorId,
        to_artefact_type: toArtifactType,
        to_artefact_id: toArtifactId,
      });

      // Refresh related results after add
      await pushRelated();

      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add relation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-[16px] p-6 max-w-md w-full">
        <h3 className="typo-title font-semibold mb-4">Add Related Artifact</h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block typo-body font-medium mb-2">Artifact Type</label>
            <select
              value={toArtifactType}
              onChange={(e) => setToArtifactType(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            >
              <option value="">Select type...</option>
              <option value="inventory_item">Inventory Item</option>
              <option value="work_order">Work Order</option>
              <option value="fault">Fault</option>
              <option value="shopping_item">Shopping Item</option>
              <option value="document">Document</option>
              <option value="manual_section">Manual Section</option>
              <option value="email_message">Email Message</option>
              <option value="certificate">Certificate</option>
            </select>
          </div>

          <div className="mb-4">
            <label className="block typo-body font-medium mb-2">Artifact ID</label>
            <input
              type="text"
              value={toArtifactId}
              onChange={(e) => setToArtifactId(e.target.value)}
              className="w-full border rounded px-3 py-2"
              placeholder="Enter artifact ID"
              required
            />
          </div>

          {error && <div className="mb-4 text-red-600 typo-body">{error}</div>}

          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={loading}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Adding...' : 'Add Relation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
