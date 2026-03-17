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
      <div className="flex items-center justify-center h-32">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
          <p className="text-xs text-txt-tertiary">Loading related...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-status-critical mb-2">Failed to load related items</p>
        <p className="text-xs text-txt-tertiary">{error.message}</p>
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
      <div className="p-6 text-center">
        <p className="text-sm text-txt-secondary mb-4">No related items found.</p>
        {onAddRelated && (
          <button
            onClick={onAddRelated}
            className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
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
    <div className="p-4 space-y-6">
      {orderedGroups.map((group) => (
        <RelatedGroupSection key={group.group_key} group={group} onNavigate={onNavigate} />
      ))}

      {/* Also Related — signal-discovered items not already in FK groups */}
      {(signalLoading || novelSignalItems.length > 0) && (
        <section data-testid="signal-also-related">
          <h3 className="text-xs font-medium text-txt-tertiary uppercase tracking-wider mb-2">
            Also Related
            {!signalLoading && (
              <span className="ml-2 text-txt-muted font-normal">{novelSignalItems.length}</span>
            )}
          </h3>
          {signalLoading ? (
            <div className="flex items-center gap-2 px-3 py-2">
              <div className="w-3 h-3 border border-border-subtle border-t-txt-tertiary rounded-full animate-spin" />
              <span className="text-xs text-txt-tertiary">Discovering related…</span>
            </div>
          ) : (
            <ul className="space-y-1">
              {novelSignalItems.map((item) => (
                <li key={item.entity_id}>
                  <button
                    type="button"
                    onClick={() => onNavigate(item.entity_type, item.entity_id)}
                    data-testid={`signal-item-${item.entity_type}-${item.entity_id}`}
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors group"
                  >
                    <span className="block text-sm text-txt-primary group-hover:text-accent-primary truncate">
                      {item.title}
                    </span>
                    {item.subtitle && (
                      <span className="block text-xs text-txt-tertiary truncate mt-0.5">
                        {item.subtitle}
                      </span>
                    )}
                    <span className="block text-xs text-txt-muted truncate mt-0.5 italic">
                      {item.entity_type.replace(/_/g, ' ')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {onAddRelated && (
        <div className="pt-4 border-t border-border-subtle">
          <button
            onClick={onAddRelated}
            className="w-full px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors text-left"
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
    <section>
      <h3 className="text-xs font-medium text-txt-tertiary uppercase tracking-wider mb-2">
        {label}
        <span className="ml-2 text-txt-muted font-normal">{group.items.length}</span>
      </h3>
      <ul className="space-y-1">
        {group.items.map((item) => (
          <RelatedItemRow key={item.entity_id} item={item} onNavigate={onNavigate} />
        ))}
      </ul>
    </section>
  );
}

// ─── Individual item row ──────────────────────────────────────────────────────

function RelatedItemRow({
  item,
  onNavigate,
}: {
  item: RelatedItemType;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onNavigate(item.entity_type, item.entity_id)}
        data-testid={`related-item-${item.entity_type}-${item.entity_id}`}
        className="w-full text-left px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors group"
      >
        <span className="block text-sm text-txt-primary group-hover:text-accent-primary truncate">
          {item.title}
        </span>
        {item.subtitle && (
          <span className="block text-xs text-txt-tertiary truncate mt-0.5">
            {item.subtitle}
          </span>
        )}
      </button>
    </li>
  );
}
