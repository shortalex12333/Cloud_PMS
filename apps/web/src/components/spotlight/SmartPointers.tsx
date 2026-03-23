'use client';

/**
 * SmartPointers — "Needs your attention" section
 * Two-phase rendering:
 *   Collapsed (default): max 5 items, one per domain, highest-scored
 *   Expanded: full sorted list in a scroll container with infinite scroll
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  AlertTriangle, ClipboardList, Package, Shield, ArrowRightLeft, Clock,
  Wrench, ShoppingCart, FileText, Activity,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { ScoredPointer, AttentionCounts, EntitySource } from '@/lib/attention/types';
import type { CrewRole } from '@/lib/attention/types';
import type { LucideIcon } from 'lucide-react';

const ICON_MAP: Record<EntitySource, LucideIcon> = {
  fault: AlertTriangle,
  work_order: ClipboardList,
  certificate: Shield,
  equipment: Wrench,
  parts: Package,
  hor_warning: Clock,
  hor_signoff: Clock,
  receiving: ArrowRightLeft,
  handover: FileText,
  shopping_list: ShoppingCart,
};

/** Pick top-scored item per source, max 5 */
function deduplicateBySource(pointers: ScoredPointer[]): ScoredPointer[] {
  const seen = new Set<string>();
  const result: ScoredPointer[] = [];
  for (const p of pointers) {
    if (!seen.has(p.source)) {
      seen.add(p.source);
      result.push(p);
    }
    if (result.length >= 5) break;
  }
  return result;
}

interface SmartPointersProps {
  pointers: ScoredPointer[];
  counts: AttentionCounts;
  loading: boolean;
  role: CrewRole;
}

export default function SmartPointers({ pointers, loading, role }: SmartPointersProps) {
  const router = useRouter();
  const [sectionCollapsed, setSectionCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [visibleCount, setVisibleCount] = useState(10);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Reset to collapsed when data changes
  useEffect(() => {
    setExpanded(false);
    setVisibleCount(10);
  }, [pointers.length]);

  // Scoped IntersectionObserver — only when expanded, observes within scroll container
  useEffect(() => {
    if (!expanded || !sentinelRef.current || visibleCount >= pointers.length) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) setVisibleCount(p => Math.min(p + 10, pointers.length));
    }, { root: scrollContainerRef.current, threshold: 0.1 });
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [expanded, visibleCount, pointers.length]);

  const handleItemClick = useCallback((route: string) => {
    if (route) router.push(route);
  }, [router]);

  if (loading && pointers.length === 0) return null;
  if (pointers.length === 0) return null;

  const dedupedItems = deduplicateBySource(pointers);
  const showViewAll = pointers.length > dedupedItems.length;
  const displayItems = expanded ? pointers.slice(0, visibleCount) : dedupedItems;
  const remainingCount = expanded ? pointers.length - visibleCount : 0;

  return (
    <div style={{ width: '100%', marginTop: 8, display: 'flex', flexDirection: 'column' }}>
      {/* Section header */}
      <div
        onClick={() => setSectionCollapsed(!sectionCollapsed)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 2px 6px', cursor: 'pointer', userSelect: 'none' }}
      >
        <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--txt-ghost)', transition: 'color 80ms' }}>
          Needs your attention
        </span>
        {sectionCollapsed && (
          <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--txt-ghost)' }}>
            ({pointers.length})
          </span>
        )}
        <svg
          style={{ width: 10, height: 10, color: 'var(--txt-ghost)', transition: 'transform 200ms', marginLeft: 'auto', transform: sectionCollapsed ? 'rotate(-90deg)' : 'none' }}
          viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M2 3.5l3 3 3-3" />
        </svg>
      </div>

      {!sectionCollapsed && (
        <div>
          {/* Scroll container — only constrained when expanded */}
          <div
            ref={scrollContainerRef}
            style={expanded ? { maxHeight: 400, overflowY: 'auto' } : undefined}
          >
            {displayItems.map(pointer => {
              const Icon = ICON_MAP[pointer.source] || AlertTriangle;
              const borderColor = pointer.severity === 'critical' ? 'var(--red)' : pointer.severity === 'warning' ? 'var(--amber)' : pointer.severity === 'info' ? 'var(--teal)' : 'var(--green)';
              const iconColor = borderColor;
              const timeColor = pointer.severity === 'critical' ? 'var(--red)' : pointer.severity === 'warning' ? 'var(--amber)' : 'var(--txt-ghost)';
              return (
                <div
                  key={pointer.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleItemClick(pointer.route)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleItemClick(pointer.route); } }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '9px 13px 9px 12px', borderRadius: 4, cursor: 'pointer',
                    transition: 'background 80ms', background: 'var(--surface-el)',
                    borderTop: '1px solid var(--border-t)',
                    borderRight: '1px solid var(--border-s)',
                    borderBottom: '1px solid var(--border-b)',
                    borderLeft: `2px solid ${borderColor}`,
                    marginBottom: 4,
                  }}
                >
                  <Icon style={{ width: 14, height: 14, flexShrink: 0, color: iconColor }} strokeWidth={1.6} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{ fontSize: 13, color: 'var(--txt)', lineHeight: 1.4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                      dangerouslySetInnerHTML={{ __html: pointer.main }}
                    />
                    <div style={{ fontSize: 10.5, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', letterSpacing: '0.03em', marginTop: 1 }}>
                      {pointer.sub}
                    </div>
                  </div>
                  <div style={{ fontSize: 10.5, color: timeColor, fontFamily: 'var(--font-mono)', flexShrink: 0, whiteSpace: 'nowrap' }}>
                    {pointer.time}
                  </div>
                </div>
              );
            })}

            {/* Sentinel for infinite scroll (expanded mode only) */}
            {expanded && remainingCount > 0 && (
              <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />
            )}
          </div>

          {/* View all / Show less toggle */}
          {!expanded && showViewAll && (
            <div
              role="button"
              tabIndex={0}
              onClick={() => setExpanded(true)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(true); } }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 6, padding: '8px 0', cursor: 'pointer',
                color: 'var(--teal)', fontSize: 11,
                fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
                userSelect: 'none',
              }}
            >
              View all ({pointers.length})
            </div>
          )}

          {expanded && (
            <div
              role="button"
              tabIndex={0}
              onClick={() => setExpanded(false)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(false); } }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                gap: 6, padding: '8px 0', cursor: 'pointer',
                color: 'var(--teal)', fontSize: 11,
                fontFamily: 'var(--font-mono)', letterSpacing: '0.04em',
                userSelect: 'none',
              }}
            >
              Show less
            </div>
          )}
        </div>
      )}
    </div>
  );
}
