'use client';

/**
 * WorkOrderCreateModal — Two-Phase Mutation Modal
 *
 * Implements the generic prefill engine pattern:
 * - Phase 1: /prepare returns mutation_preview with pre-filled fields
 * - Phase 2: /commit creates the work order after user review
 *
 * LAW 12: Deep UI Verification - Form fields are pre-filled based on
 * NLP entity extraction from the search query context.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { Toast } from '@/components/ui/Toast';
import {
  prepareWorkOrderCreate,
  commitWorkOrderCreate,
  type MutationPreview,
  type FieldMetadata,
} from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorkOrderCreateModalProps {
  open: boolean;
  onClose: () => void;
  /** Called after successful creation with the new work order ID */
  onSuccess?: (workOrderId: string, woNumber: string) => void;
  /** Yacht ID for context */
  yachtId: string;
  /** Original search query text (for NLP prefill) */
  queryText?: string;
  /** Extracted entities from search results */
  extractedEntities?: string[];
}

interface FormState {
  title: string;
  description: string;
  equipment_id: string;
  priority: string;
  assigned_to: string;
  scheduled_date: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WorkOrderCreateModal({
  open,
  onClose,
  onSuccess,
  yachtId,
  queryText,
  extractedEntities,
}: WorkOrderCreateModalProps) {
  // State
  const [phase, setPhase] = React.useState<'loading' | 'form' | 'submitting'>('loading');
  const [preview, setPreview] = React.useState<MutationPreview | null>(null);
  const [formState, setFormState] = React.useState<FormState>({
    title: '',
    description: '',
    equipment_id: '',
    priority: 'medium',
    assigned_to: '',
    scheduled_date: '',
  });
  const [error, setError] = React.useState<string | null>(null);
  const [toast, setToast] = React.useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const titleRef = React.useRef<HTMLInputElement>(null);

  // Phase 1: Fetch mutation preview on open
  React.useEffect(() => {
    if (!open) return;

    setPhase('loading');
    setError(null);

    const fetchPreview = async () => {
      try {
        const response = await prepareWorkOrderCreate({
          yacht_id: yachtId,
          query_text: queryText,
          extracted_entities: extractedEntities,
        });

        if (!response.success || !response.mutation_preview) {
          throw new Error(response.error || 'Failed to prepare work order');
        }

        const mp = response.mutation_preview;
        setPreview(mp);

        // Initialize form with pre-filled values
        setFormState({
          title: mp.title || '',
          description: mp.description || '',
          equipment_id: mp.equipment_id || '',
          priority: mp.priority || 'medium',
          assigned_to: mp.assigned_to || '',
          scheduled_date: mp.scheduled_date || '',
        });

        setPhase('form');
        setTimeout(() => titleRef.current?.focus(), 50);
      } catch (err) {
        console.error('[WorkOrderCreateModal] Prepare failed:', err);
        setError(err instanceof Error ? err.message : 'Failed to load form');
        setPhase('form');
      }
    };

    fetchPreview();
  }, [open, yachtId, queryText, extractedEntities]);

  // Escape key handler
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && phase !== 'submitting') {
        onClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose, phase]);

  if (!open) return null;

  // Phase 2: Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formState.title.trim()) {
      setError('Title is required');
      return;
    }

    setPhase('submitting');
    setError(null);

    try {
      const response = await commitWorkOrderCreate(
        { yacht_id: yachtId },
        {
          title: formState.title.trim(),
          description: formState.description.trim() || undefined,
          equipment_id: formState.equipment_id || undefined,
          priority: formState.priority,
          assigned_to: formState.assigned_to || undefined,
          scheduled_date: formState.scheduled_date || undefined,
        }
      );

      if (!response.success) {
        throw new Error(response.error || 'Failed to create work order');
      }

      setToast({
        type: 'success',
        message: `Created ${response.wo_number || 'work order'}`,
      });

      if (onSuccess && response.work_order_id) {
        onSuccess(response.work_order_id, response.wo_number || '');
      }

      setTimeout(onClose, 800);
    } catch (err) {
      console.error('[WorkOrderCreateModal] Commit failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to create work order');
      setPhase('form');
    }
  };

  const handleFieldChange = (field: keyof FormState, value: string) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  // Get field metadata helper
  const getFieldMeta = (field: string): FieldMetadata | undefined => {
    return preview?.field_metadata?.[field];
  };

  // Render field source badge
  const renderSourceBadge = (field: string) => {
    const meta = getFieldMeta(field);
    if (!meta || meta.source === 'user_input') return null;

    const sourceLabels: Record<string, { label: string; className: string }> = {
      nlp_entity: { label: 'AI', className: 'bg-brand-interactive/20 text-brand-interactive' },
      derived: { label: 'Auto', className: 'bg-status-info/20 text-status-info' },
      database: { label: 'DB', className: 'bg-status-success/20 text-status-success' },
    };

    const source = sourceLabels[meta.source];
    if (!source) return null;

    return (
      <span className={cn('ml-2 px-1.5 py-0.5 text-xs rounded', source.className)}>
        {source.label}
      </span>
    );
  };

  const canSubmit = formState.title.trim().length > 0 && phase === 'form';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-sidebar bg-black/60"
        onClick={phase !== 'submitting' ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="wo-create-title"
        className={cn(
          'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
          'z-modal',
          'bg-surface-elevated border border-surface-border',
          'rounded-lg shadow-modal',
          'w-full max-w-lg mx-4',
          'max-h-[90vh] overflow-hidden flex flex-col'
        )}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-surface-border">
          <h2 id="wo-create-title" className="text-heading text-txt-primary">
            Create Work Order
          </h2>
          {queryText && (
            <p className="mt-1 text-label text-txt-secondary truncate">
              From: "{queryText}"
            </p>
          )}
        </div>

        {/* Loading State */}
        {phase === 'loading' && (
          <div className="px-6 py-12 flex flex-col items-center justify-center gap-4">
            <div className="w-8 h-8 border-2 border-brand-interactive border-t-transparent rounded-full animate-spin" />
            <p className="text-label text-txt-secondary">Preparing form...</p>
          </div>
        )}

        {/* Form */}
        {phase !== 'loading' && (
          <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
            <div className="px-6 py-4 space-y-4 overflow-y-auto flex-1">
              {/* Error banner */}
              {error && (
                <div className="flex items-start gap-3 px-4 py-3 bg-status-critical/10 border border-status-critical/30 rounded-md">
                  <svg
                    className="w-5 h-5 text-status-critical flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <p className="text-label text-status-critical">{error}</p>
                </div>
              )}

              {/* Title - Required */}
              <div>
                <label htmlFor="wo-title" className="block text-label text-txt-primary mb-2">
                  Title <span className="text-status-critical">*</span>
                  {renderSourceBadge('title')}
                </label>
                <input
                  ref={titleRef}
                  type="text"
                  id="wo-title"
                  value={formState.title}
                  onChange={(e) => handleFieldChange('title', e.target.value)}
                  placeholder="e.g., Replace coolant pump seals"
                  className={cn(
                    'w-full',
                    'bg-surface-primary border border-surface-border rounded-md',
                    'px-3 py-2',
                    'text-body text-txt-primary placeholder:text-txt-tertiary',
                    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                    'transition-colors duration-fast'
                  )}
                  disabled={phase === 'submitting'}
                />
              </div>

              {/* Description */}
              <div>
                <label htmlFor="wo-description" className="block text-label text-txt-primary mb-2">
                  Description
                  {renderSourceBadge('description')}
                </label>
                <textarea
                  id="wo-description"
                  value={formState.description}
                  onChange={(e) => handleFieldChange('description', e.target.value)}
                  rows={3}
                  placeholder="Additional details about the work required..."
                  className={cn(
                    'w-full',
                    'bg-surface-primary border border-surface-border rounded-md',
                    'px-3 py-2',
                    'text-body text-txt-primary placeholder:text-txt-tertiary',
                    'resize-y',
                    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                    'transition-colors duration-fast'
                  )}
                  disabled={phase === 'submitting'}
                />
              </div>

              {/* Equipment Dropdown */}
              {preview?.equipment_id_options && preview.equipment_id_options.length > 0 && (
                <div>
                  <label htmlFor="wo-equipment" className="block text-label text-txt-primary mb-2">
                    Equipment
                    {renderSourceBadge('equipment_id')}
                  </label>
                  <select
                    id="wo-equipment"
                    value={formState.equipment_id}
                    onChange={(e) => handleFieldChange('equipment_id', e.target.value)}
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast'
                    )}
                    disabled={phase === 'submitting'}
                  >
                    <option value="">Select equipment...</option>
                    {preview.equipment_id_options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Priority */}
              <div>
                <label htmlFor="wo-priority" className="block text-label text-txt-primary mb-2">
                  Priority
                  {renderSourceBadge('priority')}
                </label>
                <select
                  id="wo-priority"
                  value={formState.priority}
                  onChange={(e) => handleFieldChange('priority', e.target.value)}
                  className={cn(
                    'w-full',
                    'bg-surface-primary border border-surface-border rounded-md',
                    'px-3 py-2',
                    'text-body text-txt-primary',
                    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                    'transition-colors duration-fast'
                  )}
                  disabled={phase === 'submitting'}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              {/* Assigned To Dropdown */}
              {preview?.assigned_to_options && preview.assigned_to_options.length > 0 && (
                <div>
                  <label htmlFor="wo-assigned" className="block text-label text-txt-primary mb-2">
                    Assign To
                    {renderSourceBadge('assigned_to')}
                  </label>
                  <select
                    id="wo-assigned"
                    value={formState.assigned_to}
                    onChange={(e) => handleFieldChange('assigned_to', e.target.value)}
                    className={cn(
                      'w-full',
                      'bg-surface-primary border border-surface-border rounded-md',
                      'px-3 py-2',
                      'text-body text-txt-primary',
                      'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                      'transition-colors duration-fast'
                    )}
                    disabled={phase === 'submitting'}
                  >
                    <option value="">Unassigned</option>
                    {preview.assigned_to_options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Scheduled Date */}
              <div>
                <label htmlFor="wo-scheduled" className="block text-label text-txt-primary mb-2">
                  Scheduled Date
                  {renderSourceBadge('scheduled_date')}
                </label>
                <input
                  type="date"
                  id="wo-scheduled"
                  value={formState.scheduled_date}
                  onChange={(e) => handleFieldChange('scheduled_date', e.target.value)}
                  className={cn(
                    'w-full',
                    'bg-surface-primary border border-surface-border rounded-md',
                    'px-3 py-2',
                    'text-body text-txt-primary',
                    'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                    'transition-colors duration-fast'
                  )}
                  disabled={phase === 'submitting'}
                />
              </div>
            </div>

            {/* Footer buttons */}
            <div className="px-6 py-4 border-t border-surface-border flex justify-end gap-3">
              <GhostButton
                type="button"
                onClick={onClose}
                disabled={phase === 'submitting'}
              >
                Cancel
              </GhostButton>
              <PrimaryButton
                type="submit"
                disabled={!canSubmit}
                aria-busy={phase === 'submitting'}
              >
                {phase === 'submitting' ? 'Creating...' : 'Create Work Order'}
              </PrimaryButton>
            </div>
          </form>
        )}
      </div>

      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onDismiss={() => setToast(null)}
        />
      )}
    </>
  );
}
