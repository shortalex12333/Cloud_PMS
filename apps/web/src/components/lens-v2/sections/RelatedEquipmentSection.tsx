'use client';

/**
 * RelatedEquipmentSection — collapsible section showing equipment linked to
 * this entity (document or certificate).
 *
 * Per doc_cert_ux_change.md:
 *   Row layout (matches equipment list pattern):
 *     @ {code} — {name}                                 [Visit]
 *       {manufacturer}        {description truncated}
 *
 *   Visit button routes to the equipment lens for the given equipment_id.
 *
 * Shared between Certificate lens and Document lens. Empty-state prompts the
 * user to open the picker (link flow owned by the parent lens).
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface RelatedEquipmentItem {
  /** Equipment UUID (internal). Never rendered. */
  id: string;
  /** pms_equipment.code — e.g. "FA037". */
  code?: string | null;
  /** pms_equipment.name — e.g. "AC Cooling unit Master Cabin". */
  name: string;
  /** pms_equipment.manufacturer — e.g. "ABB". */
  manufacturer?: string | null;
  /** pms_equipment.description — free text; rendered truncated. */
  description?: string | null;
}

export interface RelatedEquipmentSectionProps {
  items: RelatedEquipmentItem[];
  /** Fires when user clicks "Link equipment". Parent opens the picker. */
  onOpenPicker?: () => void;
  /** Fires when user clicks "Visit" on a row. Parent routes to equipment lens. */
  onVisitEquipment?: (equipment_id: string) => void;
  /** Fires when user clicks the unlink icon on a row. Parent confirms + unlinks. */
  onUnlink?: (equipment_id: string) => void;
  /**
   * When false, hides the "Link equipment" button (role gate). Visit remains
   * available to everyone who can see the entity.
   */
  canLink?: boolean;
  defaultCollapsed?: boolean;
  title?: string;
  /** Max description length before ellipsis (matches spec: "first x characters"). */
  descTruncateAt?: number;
}

/**
 * Truncate a string to `max` chars with an ellipsis. Preserves word boundary
 * when possible. Pure function; no-op for short strings.
 */
function truncate(text: string | null | undefined, max: number): string {
  if (!text) return '';
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  const base = lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut;
  return `${base.trimEnd()}…`;
}

export function RelatedEquipmentSection({
  items,
  onOpenPicker,
  onVisitEquipment,
  onUnlink,
  canLink = false,
  defaultCollapsed = true,
  title = 'Related Equipment',
  descTruncateAt = 60,
}: RelatedEquipmentSectionProps) {
  return (
    <CollapsibleSection
      id={`sec-${title.toLowerCase().replace(/\s+/g, '-')}`}
      title={title}
      count={items.length}
      defaultCollapsed={defaultCollapsed}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="2.5" y="4" width="11" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
          <path d="M6 4V2.5h4V4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      }
      action={
        canLink && onOpenPicker
          ? { label: '+ Link equipment', onClick: onOpenPicker, testid: 'related-equipment-link' }
          : undefined
      }
    >
      {items.length === 0 ? (
        <div className={styles.emptyState} style={{ padding: 'var(--space-4) var(--space-4)' }}>
          No equipment linked yet
          {canLink && (
            <>
              {' — '}
              <button
                type="button"
                onClick={onOpenPicker}
                className="text-action"
                style={{
                  background: 'transparent',
                  border: 0,
                  padding: 0,
                  cursor: 'pointer',
                  color: 'var(--brand-interactive)',
                  textDecoration: 'underline',
                }}
              >
                link one
              </button>
            </>
          )}
        </div>
      ) : (
        <div role="list">
          {items.map((eq) => (
            <div
              key={eq.id}
              role="listitem"
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                gap: 'var(--space-3)',
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--border-faint)',
                alignItems: 'center',
              }}
            >
              {/* Left: two-line row per spec */}
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'baseline' }}>
                  {eq.code && (
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--text-tertiary)',
                      }}
                    >
                      @ {eq.code}
                    </span>
                  )}
                  <span
                    style={{
                      fontSize: 'var(--font-size-body)',
                      fontWeight: 'var(--font-weight-body-strong)',
                      color: 'var(--text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {eq.code && <span aria-hidden> — </span>}
                    {eq.name}
                  </span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: 'var(--space-4)',
                    marginTop: 2,
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {eq.manufacturer && <span style={{ minWidth: 90 }}>{eq.manufacturer}</span>}
                  {eq.description && (
                    <span
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={eq.description}
                    >
                      {truncate(eq.description, descTruncateAt)}
                    </span>
                  )}
                </div>
              </div>

              {/* Right: actions */}
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <button
                  type="button"
                  onClick={() => onVisitEquipment?.(eq.id)}
                  className="btn-secondary"
                  style={{ height: 28, fontSize: 'var(--font-size-action)' }}
                  disabled={!onVisitEquipment}
                  aria-label={`Open equipment ${eq.code ?? eq.name}`}
                >
                  Visit
                </button>
                {canLink && onUnlink && (
                  <button
                    type="button"
                    onClick={() => onUnlink(eq.id)}
                    className="btn-ghost"
                    style={{
                      height: 28,
                      width: 28,
                      padding: 0,
                      color: 'var(--text-tertiary)',
                    }}
                    aria-label={`Unlink ${eq.name}`}
                    title="Unlink"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </CollapsibleSection>
  );
}
