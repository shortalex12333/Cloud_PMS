'use client';

/**
 * ActionModal Component
 *
 * Generic modal for executing actions with dynamic form fields.
 * - Renders form fields from required_fields
 * - Shows storage confirmation for file-related actions
 * - Executes via backend action router
 * - All field definitions come from backend - no UI authority
 */

import React, { useState, useCallback } from 'react';
import { X, Loader2, FolderOpen, AlertTriangle, PenLine } from 'lucide-react';
import { cn } from '@/lib/utils';
import { executeAction, type ActionSuggestion } from '@/lib/actionClient';
import { toast } from 'sonner';

interface ActionModalProps {
  action: ActionSuggestion;
  yachtId: string | null;
  entityId?: string;
  onClose: () => void;
  onSuccess: () => void;
}

// Field type inference from field name
function inferFieldType(fieldName: string): 'text' | 'date' | 'select' | 'textarea' {
  if (fieldName.includes('date') || fieldName.includes('expiry') || fieldName.includes('issue')) {
    return 'date';
  }
  if (fieldName.includes('reason') || fieldName.includes('note') || fieldName.includes('description')) {
    return 'textarea';
  }
  if (fieldName.includes('type') || fieldName.includes('priority')) {
    return 'select';
  }
  return 'text';
}

// Get field label from field name
function getFieldLabel(fieldName: string): string {
  return fieldName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Certificate type options for select fields
const CERTIFICATE_TYPE_OPTIONS = [
  { value: 'FLAG', label: 'Flag State Certificate' },
  { value: 'CLASS', label: 'Classification Certificate' },
  { value: 'SAFETY', label: 'Safety Certificate' },
  { value: 'CREW', label: 'Crew Certificate' },
  { value: 'OTHER', label: 'Other' },
];

// Shopping list source_type options
const SOURCE_TYPE_OPTIONS = [
  { value: 'manual_add', label: 'Manual Add' },
  { value: 'inventory_low', label: 'Inventory Low' },
  { value: 'inventory_oos', label: 'Inventory Out of Stock' },
  { value: 'work_order_usage', label: 'Work Order Usage' },
  { value: 'receiving_missing', label: 'Receiving Missing' },
  { value: 'receiving_damaged', label: 'Receiving Damaged' },
];

export default function ActionModal({
  action,
  yachtId,
  entityId,
  onClose,
  onSuccess,
}: ActionModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [filename, setFilename] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-generate idempotency key on mount (stable per modal instance)
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  // Filter out yacht_id, signature, and idempotency_key from visible fields (handled automatically)
  const visibleFields = action.required_fields.filter(
    (f) => f !== 'yacht_id' && f !== 'signature' && f !== 'idempotency_key'
  );

  const handleFieldChange = useCallback((field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate required fields
    const missingFields = visibleFields.filter(
      (f) => !formData[f]?.trim()
    );
    if (missingFields.length > 0) {
      setError(`Please fill in: ${missingFields.map(getFieldLabel).join(', ')}`);
      return;
    }

    if (!yachtId) {
      setError('No yacht context available');
      return;
    }

    setIsSubmitting(true);

    try {
      // Build context
      const context: Record<string, string> = {
        yacht_id: yachtId,
      };

      // Add entity_id for update/link actions
      if (entityId) {
        context.certificate_id = entityId;
      }

      // Build payload from form data
      const payload: Record<string, any> = { ...formData };

      // Add auto-generated idempotency key (if action requires it)
      if (action.required_fields.includes('idempotency_key')) {
        payload.idempotency_key = idempotencyKey;
      }

      // For SIGNED actions, add signature placeholder (real signature would come from auth flow)
      if (action.variant === 'SIGNED') {
        payload.signature = {
          signed_by: 'current_user',
          signed_at: new Date().toISOString(),
          reason: formData.reason || 'User initiated action',
        };
      }

      console.log('[ActionModal] Executing action:', {
        action: action.action_id,
        context,
        payload,
      });

      const result = await executeAction(action.action_id, context, payload);

      if (result.status === 'success') {
        toast.success('Action completed', {
          description: action.label,
        });
        onSuccess();
      } else {
        throw new Error(result.message || 'Action failed');
      }
    } catch (err) {
      console.error('[ActionModal] Action failed:', err);
      const message = err instanceof Error ? err.message : 'Action failed';
      setError(message);
      toast.error('Action failed', { description: message });
    } finally {
      setIsSubmitting(false);
    }
  }, [action, formData, yachtId, entityId, visibleFields, idempotencyKey, onSuccess]);

  // Build storage path preview
  const storagePathPreview = action.storage_options?.path_preview
    ?.replace('{filename}', filename || '<filename>')
    || null;

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className={cn(
          'relative z-10 w-full max-w-md mx-4',
          'bg-[#2c2c2e] rounded-2xl shadow-2xl',
          'border border-[#3d3d3f]',
          'animate-in fade-in-0 zoom-in-95 duration-200'
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#3d3d3f]">
          <div className="flex items-center gap-2">
            <h2
              id="action-modal-title"
              className="text-[17px] font-semibold text-white"
            >
              {action.label}
            </h2>
            {action.variant === 'SIGNED' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <PenLine className="w-3 h-3" />
                Requires Signature
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} data-testid={`action-form-${action.action_id}`}>
          <div className="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
            {/* Hidden idempotency key for testability */}
            <input
              type="hidden"
              data-testid="idempotency-key"
              value={idempotencyKey}
              readOnly
            />

            {/* Dynamic fields from required_fields */}
            {visibleFields.map((field) => {
              const fieldType = inferFieldType(field);
              const label = getFieldLabel(field);

              return (
                <div key={field} className="space-y-1.5">
                  <label
                    htmlFor={field}
                    className="block text-[13px] font-medium text-[#98989f]"
                  >
                    {label}
                  </label>

                  {fieldType === 'date' ? (
                    <input
                      type="date"
                      id={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-lg',
                        'bg-[#1c1c1e] border border-[#3d3d3f]',
                        'text-[15px] text-white',
                        'focus:outline-none focus:ring-2 focus:ring-[#0a84ff] focus:border-transparent',
                        'transition-colors'
                      )}
                      required
                    />
                  ) : fieldType === 'textarea' ? (
                    <textarea
                      id={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      rows={3}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-lg resize-none',
                        'bg-[#1c1c1e] border border-[#3d3d3f]',
                        'text-[15px] text-white placeholder:text-[#636366]',
                        'focus:outline-none focus:ring-2 focus:ring-[#0a84ff] focus:border-transparent',
                        'transition-colors'
                      )}
                      placeholder={`Enter ${label.toLowerCase()}...`}
                      required
                    />
                  ) : fieldType === 'select' && field === 'certificate_type' ? (
                    <select
                      id={field}
                      name={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-lg',
                        'bg-[#1c1c1e] border border-[#3d3d3f]',
                        'text-[15px] text-white',
                        'focus:outline-none focus:ring-2 focus:ring-[#0a84ff] focus:border-transparent',
                        'transition-colors'
                      )}
                      required
                    >
                      <option value="">Select type...</option>
                      {CERTIFICATE_TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : fieldType === 'select' && field === 'source_type' ? (
                    <select
                      id={field}
                      name={field}
                      value={formData[field] || 'manual_add'}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-lg',
                        'bg-[#1c1c1e] border border-[#3d3d3f]',
                        'text-[15px] text-white',
                        'focus:outline-none focus:ring-2 focus:ring-[#0a84ff] focus:border-transparent',
                        'transition-colors'
                      )}
                      required
                      data-testid="source_type-select"
                    >
                      {SOURCE_TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.includes('quantity') || field.includes('price') ? 'number' : 'text'}
                      id={field}
                      name={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-lg',
                        'bg-[#1c1c1e] border border-[#3d3d3f]',
                        'text-[15px] text-white placeholder:text-[#636366]',
                        'focus:outline-none focus:ring-2 focus:ring-[#0a84ff] focus:border-transparent',
                        'transition-colors'
                      )}
                      placeholder={`Enter ${label.toLowerCase()}...`}
                      min={field.includes('quantity') ? '1' : undefined}
                      step={field.includes('quantity') ? '1' : field.includes('price') ? '0.01' : undefined}
                      required
                      data-testid={`${field}-input`}
                    />
                  )}
                </div>
              );
            })}

            {/* Storage Confirmation Section */}
            {action.storage_options && (
              <div className="p-3 rounded-lg bg-[#1c1c1e] border border-[#3d3d3f] space-y-3">
                <div className="flex items-center gap-2 text-[13px] font-medium text-[#98989f]">
                  <FolderOpen className="w-4 h-4" />
                  Storage Location
                </div>

                <div className="space-y-2 text-[13px]">
                  <div className="flex justify-between">
                    <span className="text-[#636366]">Bucket:</span>
                    <span className="text-white font-mono">
                      {action.storage_options.bucket}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[#636366]">Path:</span>
                    <div className="font-mono text-[12px] text-[#0a84ff] bg-[#0a84ff]/10 px-2 py-1.5 rounded break-all">
                      {storagePathPreview}
                    </div>
                  </div>

                  {/* Optional filename input */}
                  <div className="pt-2">
                    <label
                      htmlFor="filename"
                      className="block text-[12px] text-[#636366] mb-1"
                    >
                      Filename (optional):
                    </label>
                    <input
                      type="text"
                      id="filename"
                      value={filename}
                      onChange={(e) => setFilename(e.target.value)}
                      placeholder="document.pdf"
                      className={cn(
                        'w-full px-2 py-1.5 rounded',
                        'bg-[#2c2c2e] border border-[#3d3d3f]',
                        'text-[13px] text-white placeholder:text-[#636366]',
                        'focus:outline-none focus:ring-1 focus:ring-[#0a84ff]'
                      )}
                    />
                  </div>
                </div>

                {action.storage_options.confirmation_required && (
                  <div className="flex items-start gap-2 pt-2 text-[12px] text-amber-400">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>
                      This action will store files in the specified location.
                      Please confirm the path is correct.
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Error message */}
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-[13px] text-red-400">
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-5 py-4 border-t border-[#3d3d3f]">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'px-4 py-2 rounded-lg',
                'text-[14px] font-medium text-[#98989f]',
                'hover:text-white hover:bg-white/10',
                'transition-colors'
              )}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="action-submit"
              disabled={isSubmitting}
              className={cn(
                'px-4 py-2 rounded-lg',
                'text-[14px] font-medium text-white',
                'bg-[#0a84ff] hover:bg-[#0a84ff]/80',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors',
                'inline-flex items-center gap-2'
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Executing...
                </>
              ) : action.variant === 'SIGNED' ? (
                <>
                  <PenLine className="w-4 h-4" />
                  Sign & Execute
                </>
              ) : (
                'Execute'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
