'use client';

/**
 * ConfidenceField Component
 *
 * Wrapper component that highlights low-confidence prefilled fields
 * with visual indicators and correction chips (alternative suggestions).
 *
 * Confidence thresholds:
 * - >= 0.8: Normal field (no indicator)
 * - 0.5 - 0.8: Yellow border + "Low confidence" badge
 * - < 0.5: Red border + "Review required" badge
 *
 * When alternatives are provided, clickable chips allow quick correction.
 *
 * BACKEND INTEGRATION NOTE:
 * The prefill response should include field-level metadata:
 * {
 *   "mutation_preview": { "equipment_id": "uuid", ... },
 *   "field_confidence": {
 *     "equipment_id": 0.65,
 *     "priority": 0.95
 *   },
 *   "field_alternatives": {
 *     "equipment_id": ["Main Engine Port", "Main Engine Starboard"]
 *   }
 * }
 *
 * If backend doesn't return field_confidence yet, the component will
 * render children without confidence indicators.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, AlertCircle, Check } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ConfidenceFieldProps {
  /** Field name for identification */
  fieldName: string;
  /** Current field value */
  value: any;
  /** Confidence score from prefill (0-1) */
  confidence?: number;
  /** Alternative suggestions for correction */
  alternatives?: string[];
  /** Callback when value changes (via chip selection) */
  onChange: (value: any) => void;
  /** The actual input element(s) to wrap */
  children: React.ReactNode;
  /** Additional class names for the wrapper */
  className?: string;
  /** Show confidence indicator even for high confidence */
  showHighConfidence?: boolean;
}

// ---------------------------------------------------------------------------
// Confidence Level Utilities
// ---------------------------------------------------------------------------

type ConfidenceLevel = 'high' | 'medium' | 'low';

function getConfidenceLevel(confidence: number | undefined): ConfidenceLevel {
  if (confidence === undefined || confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

function getConfidenceStyles(level: ConfidenceLevel) {
  switch (level) {
    case 'high':
      return {
        border: 'border-surface-border',
        badge: null,
        ring: 'focus-within:ring-celeste-accent-muted',
      };
    case 'medium':
      return {
        border: 'border-amber-500',
        badge: {
          text: 'Low confidence',
          className: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          icon: AlertTriangle,
        },
        ring: 'focus-within:ring-amber-500/50',
      };
    case 'low':
      return {
        border: 'border-red-500',
        badge: {
          text: 'Review required',
          className: 'bg-red-500/10 text-red-400 border-red-500/30',
          icon: AlertCircle,
        },
        ring: 'focus-within:ring-red-500/50',
      };
  }
}

// ---------------------------------------------------------------------------
// CorrectionChip Sub-component
// ---------------------------------------------------------------------------

interface CorrectionChipProps {
  label: string;
  onClick: () => void;
  isSelected?: boolean;
}

function CorrectionChip({ label, onClick, isSelected }: CorrectionChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 rounded-md',
        'text-xs font-medium',
        'transition-all duration-fast',
        'focus:outline-none focus:ring-2 focus:ring-celeste-accent-muted',
        isSelected
          ? 'bg-celeste-accent text-surface-elevated'
          : 'bg-surface-base border border-surface-border text-txt-secondary hover:border-celeste-accent hover:text-celeste-accent'
      )}
      aria-label={`Select alternative: ${label}`}
    >
      {isSelected && <Check className="w-3 h-3" />}
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ConfidenceField({
  fieldName,
  value,
  confidence,
  alternatives,
  onChange,
  children,
  className,
  showHighConfidence = false,
}: ConfidenceFieldProps) {
  const level = getConfidenceLevel(confidence);
  const styles = getConfidenceStyles(level);

  // If no confidence data provided, just render children without wrapper styling
  if (confidence === undefined) {
    return <div className={className}>{children}</div>;
  }

  // For high confidence, render without indicators unless explicitly requested
  if (level === 'high' && !showHighConfidence) {
    return <div className={className}>{children}</div>;
  }

  const BadgeIcon = styles.badge?.icon;
  const hasAlternatives = alternatives && alternatives.length > 0;

  // Check if current value matches any alternative
  const normalizedValue = String(value).toLowerCase().trim();
  const isValueInAlternatives = alternatives?.some(
    (alt) => alt.toLowerCase().trim() === normalizedValue
  );

  return (
    <div
      className={cn('space-y-2', className)}
      data-testid={`confidence-field-${fieldName}`}
      data-confidence={confidence}
      data-confidence-level={level}
    >
      {/* Field wrapper with confidence border */}
      <div
        className={cn(
          'relative rounded-md transition-colors duration-fast',
          styles.ring
        )}
      >
        {/* Confidence badge positioned above input */}
        {styles.badge && (
          <div className="flex items-center justify-between mb-1.5">
            <span
              className={cn(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border',
                styles.badge.className
              )}
              role="status"
              aria-live="polite"
            >
              {BadgeIcon && <BadgeIcon className="w-3 h-3" />}
              {styles.badge.text}
              {confidence !== undefined && (
                <span className="opacity-70">
                  ({Math.round(confidence * 100)}%)
                </span>
              )}
            </span>
          </div>
        )}

        {/* Wrap children with border styling */}
        <div
          className={cn(
            '[&>input]:border-2 [&>textarea]:border-2 [&>select]:border-2',
            level === 'medium' && '[&>input]:border-amber-500 [&>textarea]:border-amber-500 [&>select]:border-amber-500',
            level === 'low' && '[&>input]:border-red-500 [&>textarea]:border-red-500 [&>select]:border-red-500'
          )}
        >
          {children}
        </div>
      </div>

      {/* Correction chips for alternatives */}
      {hasAlternatives && (
        <div
          className="flex flex-wrap items-center gap-2"
          role="group"
          aria-label={`Suggestions for ${fieldName}`}
        >
          <span className="text-xs text-txt-tertiary">Suggestions:</span>
          {alternatives.map((alt) => (
            <CorrectionChip
              key={alt}
              label={alt}
              onClick={() => onChange(alt)}
              isSelected={alt.toLowerCase().trim() === normalizedValue}
            />
          ))}
          {/* "Other..." chip - keeps current value if not in suggestions */}
          {!isValueInAlternatives && value && (
            <span className="text-xs text-txt-tertiary italic">
              (custom value)
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hook for managing field confidence state
// ---------------------------------------------------------------------------

export interface FieldConfidenceData {
  confidence: Record<string, number>;
  alternatives: Record<string, string[]>;
}

/**
 * Hook to extract field confidence data from prefill response
 *
 * @param prefillResponse - Raw prefill response from backend
 * @returns Normalized confidence data for use with ConfidenceField
 *
 * @example
 * ```tsx
 * const { confidence, alternatives } = useFieldConfidence(prefillResponse);
 *
 * <ConfidenceField
 *   fieldName="equipment_id"
 *   value={formState.equipment_id}
 *   confidence={confidence.equipment_id}
 *   alternatives={alternatives.equipment_id}
 *   onChange={(v) => setFormState({ ...formState, equipment_id: v })}
 * >
 *   <input value={formState.equipment_id} ... />
 * </ConfidenceField>
 * ```
 */
export function useFieldConfidence(
  prefillResponse?: {
    field_confidence?: Record<string, number>;
    field_alternatives?: Record<string, string[]>;
    // Also support nested mutation_preview format
    mutation_preview?: {
      field_metadata?: Record<string, { confidence?: number }>;
    };
  } | null
): FieldConfidenceData {
  return React.useMemo(() => {
    const confidence: Record<string, number> = {};
    const alternatives: Record<string, string[]> = {};

    if (!prefillResponse) {
      return { confidence, alternatives };
    }

    // Extract from field_confidence (direct format)
    if (prefillResponse.field_confidence) {
      Object.assign(confidence, prefillResponse.field_confidence);
    }

    // Extract from mutation_preview.field_metadata (nested format)
    if (prefillResponse.mutation_preview?.field_metadata) {
      for (const [field, meta] of Object.entries(
        prefillResponse.mutation_preview.field_metadata
      )) {
        if (meta.confidence !== undefined && !(field in confidence)) {
          confidence[field] = meta.confidence;
        }
      }
    }

    // Extract alternatives
    if (prefillResponse.field_alternatives) {
      Object.assign(alternatives, prefillResponse.field_alternatives);
    }

    return { confidence, alternatives };
  }, [prefillResponse]);
}

export default ConfidenceField;
