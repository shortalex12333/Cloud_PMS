'use client';

import * as React from 'react';
import { useAddRelated, SUPPORTED_ENTITY_TYPES } from '@/hooks/useRelated';

const LINK_TYPES = [
  { value: 'related',   label: 'Related' },
  { value: 'reference', label: 'Reference' },
  { value: 'evidence',  label: 'Evidence' },
  { value: 'manual',    label: 'Manual Link' },
  // NOTE: "explicit" is intentionally NOT in this list — it's a schema bug (GAP-01).
  // The backend VALID_LINK_TYPES does not include "explicit" despite it being the
  // schema default. Using it will return 400. Track fix in SHOW_RELATED_BACKEND.md.
] as const;

interface AddRelatedItemModalProps {
  fromEntityType: string;
  fromEntityId: string;
  onClose: () => void;
}

export function AddRelatedItemModal({
  fromEntityType,
  fromEntityId,
  onClose,
}: AddRelatedItemModalProps) {
  const [toEntityType, setToEntityType] = React.useState('');
  const [toEntityId, setToEntityId] = React.useState('');
  const [linkType, setLinkType] = React.useState<'related' | 'reference' | 'evidence' | 'manual'>('related');

  const { mutate, isPending, error } = useAddRelated(fromEntityType, fromEntityId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(
      {
        source_entity_type: fromEntityType,
        source_entity_id: fromEntityId,
        target_entity_type: toEntityType,
        target_entity_id: toEntityId,
        link_type: linkType,
      },
      { onSuccess: onClose }
    );
  };

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: 'rgba(0,0,0,0.60)' }}
      onClick={onClose}
    >
      <div
        className="bg-surface-elevated rounded-xl p-6 max-w-md w-full mx-4 border border-border-subtle"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-txt-primary mb-4">Add Explicit Link</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Link to Entity Type
            </label>
            <select
              value={toEntityType}
              onChange={(e) => setToEntityType(e.target.value)}
              required
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary"
            >
              <option value="">Select type…</option>
              {SUPPORTED_ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Entity ID (UUID)
            </label>
            <input
              type="text"
              value={toEntityId}
              onChange={(e) => setToEntityId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              required
              pattern="[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary font-mono"
            />
          </div>

          <div>
            <label className="block text-xs text-txt-tertiary mb-1 uppercase tracking-wider">
              Link Type
            </label>
            <select
              value={linkType}
              onChange={(e) => setLinkType(e.target.value as typeof linkType)}
              className="w-full bg-surface-base border border-border-subtle rounded-lg px-3 py-2 text-sm text-txt-primary"
            >
              {LINK_TYPES.map((lt) => (
                <option key={lt.value} value={lt.value}>{lt.label}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-status-critical">{(error as Error).message}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="flex-1 px-4 py-2 bg-surface-base hover:bg-surface-hover border border-border-subtle rounded-lg text-sm text-txt-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !toEntityType || !toEntityId}
              className="flex-1 px-4 py-2 bg-accent-primary hover:bg-accent-primary-hover rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              style={{ color: 'var(--txt)' }}
            >
              {isPending ? 'Adding…' : 'Add Link'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
