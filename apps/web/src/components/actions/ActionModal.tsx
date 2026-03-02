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

import React, { useState, useCallback, useEffect } from 'react';
import { X, Loader2, FolderOpen, AlertTriangle, PenLine, Info, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  executeAction,
  fetchPrefill,
  type ActionSuggestion,
  type PrefillResponse,
  type DropdownOption,
  type PrefillWarning,
  type PrepareResponse,
  type PrefillField,
} from '@/lib/actionClient';
import { toast } from 'sonner';
import { DisambiguationSelector } from '@/components/ui/DisambiguationSelector';
import { ConfidenceField } from '@/components/ui/ConfidenceField';

interface ActionModalProps {
  action: ActionSuggestion;
  yachtId: string | null;
  entityId?: string;
  /** Original search query text for NLP prefill */
  queryText?: string;
  /** Already extracted entities from search context */
  extractedEntities?: Record<string, string>;
  /** v1.3: Prefill data from /prepare endpoint */
  prefillData?: PrepareResponse | null;
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

/**
 * AmbiguityDropdown Component
 *
 * Renders "Did you mean: X / Y?" dropdown for ambiguous entity resolution.
 * Used when NLP matches multiple candidates with similar confidence.
 *
 * Per DISAMB-01: Shows dropdown in ActionModal for ambiguous equipment entities.
 */
interface AmbiguityDropdownProps {
  fieldName: string;
  fieldLabel: string;
  candidates: Array<{
    id: string;
    label: string;
    confidence?: number;
    metadata?: Record<string, unknown>;
  }>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  required?: boolean;
}

function AmbiguityDropdown({
  fieldName,
  fieldLabel,
  candidates,
  selectedId,
  onSelect,
  required = false,
}: AmbiguityDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedCandidate = candidates.find(c => c.id === selectedId);

  return (
    <div className="space-y-1.5" data-testid={`ambiguity-${fieldName}`}>
      <label className="flex items-center gap-2 typo-meta font-medium text-txt-secondary">
        {fieldLabel}
        {required && <span className="text-red-400">*</span>}
      </label>

      {/* Did you mean prompt */}
      <div className="p-2 bg-amber-500/10 rounded border border-amber-500/30">
        <div className="flex items-center gap-2 typo-meta text-amber-400 mb-2">
          <AlertTriangle className="w-4 h-4" />
          Did you mean:
        </div>

        {/* Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className={cn(
              'w-full flex items-center justify-between px-3 py-2 rounded-md',
              'bg-surface-base border',
              selectedId ? 'border-amber-500/50' : 'border-red-500/50',
              'typo-body text-left',
              'focus:outline-none focus:ring-2 focus:ring-amber-500/30'
            )}
            aria-expanded={isOpen}
            aria-haspopup="listbox"
          >
            <span className={selectedCandidate ? 'text-celeste-text-title' : 'text-txt-tertiary'}>
              {selectedCandidate?.label || 'Select an option...'}
            </span>
            <ChevronDown className={cn(
              'w-4 h-4 text-txt-secondary transition-transform',
              isOpen && 'rotate-180'
            )} />
          </button>

          {/* Options */}
          {isOpen && (
            <div
              className={cn(
                'absolute z-10 w-full mt-1 py-1',
                'bg-surface-elevated rounded-md shadow-lg',
                'border border-surface-border',
                'max-h-48 overflow-y-auto'
              )}
              role="listbox"
            >
              {candidates.map((candidate) => (
                <button
                  key={candidate.id}
                  type="button"
                  onClick={() => {
                    onSelect(candidate.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    'w-full px-3 py-2 text-left typo-body',
                    'hover:bg-surface-hover transition-colors',
                    selectedId === candidate.id && 'bg-celeste-accent/10 text-celeste-accent'
                  )}
                  role="option"
                  aria-selected={selectedId === candidate.id}
                >
                  <div className="flex items-center justify-between">
                    <span>{candidate.label}</span>
                    {candidate.confidence != null && (
                      <span className="typo-meta text-txt-tertiary">
                        {Math.round(candidate.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  {candidate.metadata && (
                    <div className="typo-meta text-txt-tertiary mt-0.5">
                      {Object.entries(candidate.metadata)
                        .filter(([k]) => k !== 'id')
                        .slice(0, 2)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(' | ')}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ActionModal({
  action,
  yachtId,
  entityId,
  queryText,
  extractedEntities,
  prefillData,
  onClose,
  onSuccess,
}: ActionModalProps) {
  // Initialize formData from prefill if available
  const getInitialFormData = useCallback((): Record<string, string> => {
    if (!prefillData?.prefill) return {};

    const initial: Record<string, string> = {};
    for (const [field, data] of Object.entries(prefillData.prefill)) {
      // Only use values with confidence >= 0.65 (per CONTEXT.md)
      if (data.confidence >= 0.65 && data.value != null) {
        initial[field] = String(data.value);
      }
    }
    return initial;
  }, [prefillData]);

  const [formData, setFormData] = useState<Record<string, string>>(getInitialFormData);
  const [filename, setFilename] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prefill state
  const [isPrefilling, setIsPrefilling] = useState(false);
  const [dropdownOptions, setDropdownOptions] = useState<Record<string, DropdownOption[]>>({});
  const [warnings, setWarnings] = useState<PrefillWarning[]>([]);
  const [readyToCommit, setReadyToCommit] = useState(true);
  const [disambiguationPending, setDisambiguationPending] = useState<string[]>([]);

  // Field confidence state for low-confidence highlighting
  const [fieldConfidence, setFieldConfidence] = useState<Record<string, number>>({});
  const [fieldAlternatives, setFieldAlternatives] = useState<Record<string, string[]>>({});

  // Auto-generate idempotency key on mount (stable per modal instance)
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  // Update formData when prefillData changes (v1.3)
  useEffect(() => {
    if (prefillData?.prefill) {
      setFormData(getInitialFormData());
    }
  }, [prefillData, getInitialFormData]);

  // Fetch prefill data on modal open
  useEffect(() => {
    if (!queryText) return;

    const fetchPrefillData = async () => {
      setIsPrefilling(true);
      setError(null);

      try {
        const response = await fetchPrefill(
          action.action_id,
          queryText,
          extractedEntities
        );

        if (response.status === 'success') {
          // Apply prefilled values to form
          if (response.mutation_preview) {
            const newFormData: Record<string, string> = {};
            for (const [key, value] of Object.entries(response.mutation_preview)) {
              if (typeof value === 'string' || typeof value === 'number') {
                newFormData[key] = String(value);
              }
            }
            setFormData((prev) => ({ ...prev, ...newFormData }));
          }

          // Store dropdown options for disambiguation
          if (response.dropdown_options) {
            setDropdownOptions(response.dropdown_options);
            // Track fields that need disambiguation (multiple options)
            const pendingFields = Object.entries(response.dropdown_options)
              .filter(([_, opts]) => opts.length > 1)
              .map(([field]) => field);
            setDisambiguationPending(pendingFields);
          }

          // Store warnings
          if (response.warnings) {
            setWarnings(response.warnings);
          }

          // Track ready state
          setReadyToCommit(response.ready_to_commit);

          // Store field confidence scores for low-confidence highlighting
          if (response.field_confidence) {
            setFieldConfidence(response.field_confidence);
          }

          // Store field alternatives for correction chips
          if (response.field_alternatives) {
            setFieldAlternatives(response.field_alternatives);
          }

          console.log('[ActionModal] Prefill applied:', {
            action: action.action_id,
            prefilledFields: Object.keys(response.mutation_preview || {}),
            dropdownFields: Object.keys(response.dropdown_options || {}),
            warningsCount: response.warnings?.length || 0,
            readyToCommit: response.ready_to_commit,
            fieldConfidenceCount: Object.keys(response.field_confidence || {}).length,
            fieldAlternativesCount: Object.keys(response.field_alternatives || {}).length,
          });
        }
      } catch (err) {
        console.error('[ActionModal] Prefill failed:', err);
        // Don't block the modal on prefill failure - allow manual entry
        toast.info('Could not auto-fill form', {
          description: 'Please fill in the fields manually.',
        });
      } finally {
        setIsPrefilling(false);
      }
    };

    fetchPrefillData();
  }, [action.action_id, queryText, extractedEntities]);

  // Filter out yacht_id, signature, and idempotency_key from visible fields (handled automatically)
  const visibleFields = action.required_fields.filter(
    (f) => f !== 'yacht_id' && f !== 'signature' && f !== 'idempotency_key'
  );

  const handleFieldChange = useCallback((field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(null);

    // If this field was pending disambiguation, mark it as resolved
    if (disambiguationPending.includes(field) && value) {
      setDisambiguationPending((prev) => prev.filter((f) => f !== field));
    }
  }, [disambiguationPending]);

  // Check if a field has warnings
  const getFieldWarning = useCallback((field: string): PrefillWarning | undefined => {
    return warnings.find((w) => w.field === field);
  }, [warnings]);

  // Check if disambiguation is blocking submit
  const isDisambiguationBlocking = disambiguationPending.length > 0;

  // Helper: Get field confidence class for border styling (v1.3)
  const getFieldConfidenceClass = useCallback((field: string): string => {
    if (!prefillData?.prefill?.[field]) return '';

    const confidence = prefillData.prefill[field].confidence;
    if (confidence >= 0.85) return 'border-green-500/30';  // Auto-filled silently
    if (confidence >= 0.65) return 'border-amber-500/30';  // Confirm UI
    return 'border-red-500/30';  // Ambiguous
  }, [prefillData]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Block submit if disambiguation is pending
    if (isDisambiguationBlocking) {
      setError(`Please select an option for: ${disambiguationPending.map(getFieldLabel).join(', ')}`);
      return;
    }

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
  }, [action, formData, yachtId, entityId, visibleFields, idempotencyKey, onSuccess, isDisambiguationBlocking, disambiguationPending]);

  // Build storage path preview
  const storagePathPreview = action.storage_options?.path_preview
    ?.replace('{filename}', filename || '<filename>')
    || null;

  return (
    <div className="fixed inset-0 z-modal flex items-center justify-center">
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
          'bg-surface-elevated rounded-lg shadow-modal',
          'border border-surface-border',
          'animate-in fade-in-0 zoom-in-95 duration-normal'
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <h2
              id="action-modal-title"
              className="typo-title font-semibold text-celeste-text-title"
            >
              {action.label}
            </h2>
            {action.variant === 'SIGNED' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded typo-meta font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <PenLine className="w-3 h-3" />
                Requires Signature
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="btn-icon h-8 w-8"
            aria-label="Close"
          >
            <X className="w-[18px] h-[18px]" />
          </button>
        </div>

        {/* Loading State while prefilling */}
        {isPrefilling && (
          <div className="px-5 py-8 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-celeste-accent" />
            <p className="typo-meta text-txt-secondary">Loading form...</p>
          </div>
        )}

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          data-testid={`action-form-${action.action_id}`}
          className={cn(isPrefilling && 'hidden')}
        >
          <div className="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
            {/* Hidden idempotency key for testability */}
            <input
              type="hidden"
              data-testid="idempotency-key"
              value={idempotencyKey}
              readOnly
            />

            {/* Warnings banner */}
            {warnings.length > 0 && (
              <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30 space-y-2">
                <div className="flex items-center gap-2 typo-meta font-medium text-amber-400">
                  <AlertTriangle className="w-4 h-4" />
                  Attention Required
                </div>
                <ul className="typo-meta text-amber-300 space-y-1 pl-6 list-disc">
                  {warnings.map((warning, idx) => (
                    <li key={idx}>
                      {warning.field && <span className="font-medium">{getFieldLabel(warning.field)}: </span>}
                      {warning.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Disambiguation notice */}
            {isDisambiguationBlocking && (
              <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
                <div className="flex items-center gap-2 typo-meta text-blue-400">
                  <Info className="w-4 h-4" />
                  Please select options for highlighted fields to continue.
                </div>
              </div>
            )}

            {/* Ambiguous entity disambiguation - DISAMB-01 */}
            {prefillData?.ambiguities?.map((ambiguity) => (
              <AmbiguityDropdown
                key={ambiguity.field}
                fieldName={ambiguity.field}
                fieldLabel={getFieldLabel(ambiguity.field)}
                candidates={ambiguity.candidates}
                selectedId={formData[ambiguity.field] || null}
                onSelect={(id) => handleFieldChange(ambiguity.field, id)}
                required
              />
            ))}

            {/* Dynamic fields from required_fields */}
            {visibleFields.map((field) => {
              const fieldType = inferFieldType(field);
              const label = getFieldLabel(field);
              const confidence = fieldConfidence[field];
              const alternatives = fieldAlternatives[field];

              // Helper to render the actual input element
              const renderInput = () => {
                if (fieldType === 'date') {
                  return (
                    <input
                      type="date"
                      id={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-md',
                        'bg-surface-base border border-surface-border',
                        'typo-body text-celeste-text-title',
                        'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted focus:border-transparent',
                        'transition-colors duration-fast',
                        getFieldConfidenceClass(field)
                      )}
                      required
                    />
                  );
                }

                if (fieldType === 'textarea') {
                  return (
                    <textarea
                      id={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      rows={3}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-md resize-none',
                        'bg-surface-base border border-surface-border',
                        'typo-body text-celeste-text-title placeholder:text-txt-tertiary',
                        'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted focus:border-transparent',
                        'transition-colors duration-fast',
                        getFieldConfidenceClass(field)
                      )}
                      placeholder={`Enter ${label.toLowerCase()}...`}
                      required
                    />
                  );
                }

                if (fieldType === 'select' && field === 'certificate_type') {
                  return (
                    <select
                      id={field}
                      name={field}
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-md',
                        'bg-surface-base border border-surface-border',
                        'typo-body text-celeste-text-title',
                        'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted focus:border-transparent',
                        'transition-colors duration-fast',
                        getFieldConfidenceClass(field)
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
                  );
                }

                if (fieldType === 'select' && field === 'source_type') {
                  return (
                    <select
                      id={field}
                      name={field}
                      value={formData[field] || 'manual_add'}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      className={cn(
                        'w-full px-3 py-2.5 rounded-md',
                        'bg-surface-base border border-surface-border',
                        'typo-body text-celeste-text-title',
                        'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted focus:border-transparent',
                        'transition-colors duration-fast',
                        getFieldConfidenceClass(field)
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
                  );
                }

                // Default: text/number input
                return (
                  <input
                    type={field.includes('quantity') || field.includes('price') ? 'number' : 'text'}
                    id={field}
                    name={field}
                    value={formData[field] || ''}
                    onChange={(e) => handleFieldChange(field, e.target.value)}
                    className={cn(
                      'w-full px-3 py-2.5 rounded-md',
                      'bg-surface-base border border-surface-border',
                      'typo-body text-celeste-text-title placeholder:text-txt-tertiary',
                      'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted focus:border-transparent',
                      'transition-colors duration-fast',
                      getFieldConfidenceClass(field)
                    )}
                    placeholder={`Enter ${label.toLowerCase()}...`}
                    min={field.includes('quantity') ? '1' : undefined}
                    step={field.includes('quantity') ? '1' : field.includes('price') ? '0.01' : undefined}
                    required
                    data-testid={`${field}-input`}
                  />
                );
              };

              return (
                <div key={field} className="space-y-1.5">
                  <label
                    htmlFor={field}
                    className="flex items-center gap-2 typo-meta font-medium text-txt-secondary"
                  >
                    {label}
                    {/* v1.3: Confidence indicator badge */}
                    {prefillData?.prefill?.[field] && (
                      <span className={cn(
                        "text-xs",
                        prefillData.prefill[field].confidence >= 0.85 ? "text-green-400" : "text-amber-400"
                      )}>
                        {prefillData.prefill[field].confidence >= 0.85 ? "auto-filled" : "confirm"}
                      </span>
                    )}
                  </label>

                  {/* Wrap field with ConfidenceField for low-confidence highlighting and correction chips */}
                  <ConfidenceField
                    fieldName={field}
                    value={formData[field] || ''}
                    confidence={confidence}
                    alternatives={alternatives}
                    onChange={(value) => handleFieldChange(field, String(value))}
                  >
                    {renderInput()}
                  </ConfidenceField>

                </div>
              );
            })}

            {/* Storage Confirmation Section */}
            {action.storage_options && (
              <div className="p-3 rounded-md bg-surface-base border border-surface-border space-y-3">
                <div className="flex items-center gap-2 typo-meta font-medium text-txt-secondary">
                  <FolderOpen className="w-4 h-4" />
                  Storage Location
                </div>

                <div className="space-y-2 typo-meta">
                  <div className="flex justify-between">
                    <span className="text-txt-tertiary">Bucket:</span>
                    <span className="text-celeste-text-title font-mono">
                      {action.storage_options.bucket}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <span className="text-txt-tertiary">Path:</span>
                    <div className="font-mono typo-meta text-celeste-accent bg-celeste-accent/10 px-2 py-1.5 rounded break-all">
                      {storagePathPreview}
                    </div>
                  </div>

                  {/* Optional filename input */}
                  <div className="pt-2">
                    <label
                      htmlFor="filename"
                      className="block typo-meta text-txt-tertiary mb-1"
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
                        'bg-surface-elevated border border-surface-border',
                        'typo-meta text-celeste-text-title placeholder:text-txt-tertiary',
                        'focus:outline-none focus:ring-1 focus:ring-celeste-accent-muted'
                      )}
                    />
                  </div>
                </div>

                {action.storage_options.confirmation_required && (
                  <div className="flex items-start gap-2 pt-2 typo-meta text-amber-400">
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
              <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30 typo-meta text-red-400">
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-5 py-4 border-t border-surface-border">
            <button
              type="button"
              onClick={onClose}
              className="btn-ghost"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="action-submit"
              disabled={isSubmitting || isDisambiguationBlocking}
              className={cn(
                'btn-primary',
                isDisambiguationBlocking && 'opacity-50 cursor-not-allowed'
              )}
              aria-disabled={isSubmitting || isDisambiguationBlocking}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Executing...
                </>
              ) : isDisambiguationBlocking ? (
                'Select options above'
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
