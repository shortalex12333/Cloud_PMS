'use client';

import * as React from 'react';
import { GROUP_DISPLAY_ORDER, GROUP_LABELS } from '@/hooks/useRelated';
import type { RelatedGroup as RelatedGroupType, RelatedItem as RelatedItemType } from '@/hooks/useRelated';
import type { SignalRelatedItem } from '@/hooks/useSignalRelated';

interface RelatedDrawerProps {
  groups: RelatedGroupType[];
  isLoading: boolean;
  error?: Error | null;
  onNavigate: (entityType: string, entityId: string) => void;
  /** Render add-related button (HOD/manager only — caller decides visibility) */
  onAddRelated?: () => void;
  /** Signal-discovered items — rendered in "Also Related" section after FK groups */
  signalItems?: SignalRelatedItem[];
  /** True while the signal fetch is in-flight */
  signalLoading?: boolean;
}

export function RelatedDrawer({
  groups,
  isLoading,
  error,
  onNavigate,
  onAddRelated,
  signalItems,
  signalLoading,
}: RelatedDrawerProps) {
  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '48px 16px', flex: 1 }}>
        <div style={{ width: '24px', height: '24px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <span style={{ fontSize: '12px', color: 'var(--txt3)' }}>Discovering related...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <p style={{ fontSize: '13px', color: 'var(--red)', marginBottom: '8px' }}>Failed to load related items</p>
        <p style={{ fontSize: '11px', color: 'var(--txt3)' }}>{error.message}</p>
      </div>
    );
  }

  // Flatten to count total FK items
  const totalItems = groups.reduce((sum, g) => sum + g.items.length, 0);

  // Collect FK entity_ids so signal items that already appear via FK can be
  // filtered out — no duplicates between the two sections.
  const fkEntityIds = new Set(
    groups.flatMap((g) => g.items.map((item) => item.entity_id))
  );

  // Signal items not already surfaced via FK links
  const novelSignalItems = (signalItems ?? []).filter(
    (item) => !fkEntityIds.has(item.entity_id)
  );

  // Empty state: only when there are truly no items anywhere — no FK groups,
  // no signal items, and signal is not currently loading.
  // Must NOT early-return while signal is loading or has items to show.
  if (totalItems === 0 && !signalLoading && novelSignalItems.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <p style={{ fontSize: '13px', color: 'var(--txt2)', marginBottom: '16px' }}>No related items found.</p>
        {onAddRelated && (
          <button
            onClick={onAddRelated}
            style={{ padding: '8px 16px', background: 'var(--surface-el)', borderRadius: '6px', fontSize: '13px', color: 'var(--txt)', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}
          >
            Add Related
          </button>
        )}
      </div>
    );
  }

  // Sort groups by fixed display order; groups not in the order list go last
  const orderedGroups = [...groups].sort((a, b) => {
    const ai = GROUP_DISPLAY_ORDER.indexOf(a.group_key as typeof GROUP_DISPLAY_ORDER[number]);
    const bi = GROUP_DISPLAY_ORDER.indexOf(b.group_key as typeof GROUP_DISPLAY_ORDER[number]);
    if (ai === -1 && bi === -1) return 0;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  return (
    <div style={{ padding: '12px 12px 16px', flex: 1, overflowY: 'auto', background: 'var(--surface-base)' }}>
      {orderedGroups.map((group) => (
        <RelatedGroupSection key={group.group_key} group={group} onNavigate={onNavigate} />
      ))}

      {/* Also Related — signal-discovered items not already in FK groups */}
      {(signalLoading || novelSignalItems.length > 0) && (
        <section
          data-testid="signal-also-related"
          style={{
            background: 'var(--surface)',
            borderTop: '1px solid rgba(255,255,255,0.09)',
            borderRight: '1px solid rgba(255,255,255,0.05)',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
            borderLeft: '1px solid rgba(255,255,255,0.05)',
            borderRadius: '4px',
            overflow: 'hidden',
            marginBottom: '6px',
          }}
        >
          <div style={{ fontSize: '9px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--txt)', padding: '8px 12px 4px' }}>
            Also Related
            {!signalLoading && (
              <span style={{ fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", fontWeight: 400, marginLeft: '4px' }}>{novelSignalItems.length}</span>
            )}
          </div>
          {signalLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
              <div style={{ width: '12px', height: '12px', border: '1.5px solid var(--border-sub)', borderTopColor: 'var(--txt3)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              <span style={{ fontSize: '11px', color: 'var(--txt3)' }}>Discovering related…</span>
            </div>
          ) : (
            <div>
              {novelSignalItems.map((item, idx) => (
                <button
                  key={item.entity_id}
                  type="button"
                  onClick={() => onNavigate(item.entity_type, item.entity_id)}
                  data-testid={`signal-item-${item.entity_type}-${item.entity_id}`}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    cursor: 'pointer',
                    minHeight: '44px',
                    transition: 'background 60ms',
                    borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                    background: 'none',
                    border: idx > 0 ? undefined : 'none',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.4 }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '10.5px', color: 'var(--txt2)', fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", letterSpacing: '0.03em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px' }}>
                      <span>{item.entity_type.replace(/_/g, ' ')}</span>{item.subtitle ? <><span> · </span><span>{item.subtitle}</span></> : null}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {onAddRelated && (
        <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-sub)' }}>
          <button
            onClick={onAddRelated}
            style={{ width: '100%', padding: '8px 12px', background: 'var(--surface-el)', borderRadius: '6px', fontSize: '13px', color: 'var(--txt)', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-sans)', textAlign: 'left' }}
          >
            + Add Explicit Link
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Group section ────────────────────────────────────────────────────────────

function RelatedGroupSection({
  group,
  onNavigate,
}: {
  group: RelatedGroupType;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const label = GROUP_LABELS[group.group_key] ?? group.group_key.replace(/_/g, ' ');

  return (
    <section style={{
      background: 'var(--surface)',
      borderTop: '1px solid rgba(255,255,255,0.09)',
      borderRight: '1px solid rgba(255,255,255,0.05)',
      borderBottom: '1px solid rgba(255,255,255,0.03)',
      borderLeft: '1px solid rgba(255,255,255,0.05)',
      borderRadius: '4px',
      overflow: 'hidden',
      marginBottom: '6px',
    }}>
      <div style={{ fontSize: '9px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--txt)', padding: '8px 12px 4px' }}>
        {label}
        <span style={{ fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", fontWeight: 400, marginLeft: '4px' }}>{group.items.length}</span>
      </div>
      <div>
        {group.items.map((item, idx) => (
          <RelatedItemRow key={item.entity_id} item={item} onNavigate={onNavigate} isFirst={idx === 0} />
        ))}
      </div>
    </section>
  );
}

// ─── Individual item row ──────────────────────────────────────────────────────

function RelatedItemRow({
  item,
  onNavigate,
  isFirst,
}: {
  item: RelatedItemType;
  onNavigate: (entityType: string, entityId: string) => void;
  isFirst: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(item.entity_type, item.entity_id)}
      data-testid={`related-item-${item.entity_type}-${item.entity_id}`}
      style={{
        width: '100%',
        textAlign: 'left',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 12px',
        cursor: 'pointer',
        minHeight: '44px',
        transition: 'background 60ms',
        borderTop: isFirst ? 'none' : '1px solid rgba(255,255,255,0.04)',
        background: 'none',
        border: isFirst ? 'none' : undefined,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.4 }}>
          {item.title}
        </div>
        {item.subtitle && (
          <div style={{ fontSize: '10.5px', color: 'var(--txt2)', fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", letterSpacing: '0.03em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px' }}>
            {item.subtitle}
          </div>
        )}
      </div>
    </button>
  );
}
