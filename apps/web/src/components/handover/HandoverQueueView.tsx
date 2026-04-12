'use client';

/**
 * HandoverQueueView — Queue tab for /handover-export page.
 *
 * Calls GET /v1/handover/queue and renders four expandable sections:
 *   Open Faults / Overdue Work Orders / Low Stock Parts / Pending Orders
 *
 * Each row has an "Add to draft" button. Items already in handover_items
 * (already_queued) show a checkmark instead.
 *
 * The endpoint is mocked while ENGINEER02 ships it. The component handles
 * 404 gracefully with an "endpoint not yet available" empty state.
 */

import * as React from 'react';
import {
  AlertTriangle, Wrench, Package, ShoppingCart,
  ChevronDown, ChevronRight, Plus, Check, Loader2, RefreshCw,
} from 'lucide-react';
import { useActiveVessel } from '@/contexts/VesselContext';
import { fetchHandoverQueue, type HandoverQueueItem, type HandoverQueueResponse } from '@/components/shell/api';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

// ============================================================================
// TYPES
// ============================================================================

interface SectionConfig {
  key: keyof Pick<HandoverQueueResponse, 'open_faults' | 'overdue_work_orders' | 'low_stock_parts' | 'pending_orders'>;
  label: string;
  Icon: React.ElementType;
  accentVar: string;
  bgVar: string;
  entityType: string;
}

const SECTIONS: SectionConfig[] = [
  {
    key: 'open_faults',
    label: 'Open Faults',
    Icon: AlertTriangle,
    accentVar: 'var(--red)',
    bgVar: 'var(--red-bg)',
    entityType: 'fault',
  },
  {
    key: 'overdue_work_orders',
    label: 'Overdue Work Orders',
    Icon: Wrench,
    accentVar: 'var(--amber)',
    bgVar: 'var(--amber-bg)',
    entityType: 'work_order',
  },
  {
    key: 'low_stock_parts',
    label: 'Low Stock Parts',
    Icon: Package,
    accentVar: 'var(--mark)',
    bgVar: 'var(--teal-bg)',
    entityType: 'part',
  },
  {
    key: 'pending_orders',
    label: 'Pending Purchase Orders',
    Icon: ShoppingCart,
    accentVar: 'var(--txt2)',
    bgVar: 'var(--neutral-bg)',
    entityType: 'purchase_order',
  },
];

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// SKELETON ROW
// ============================================================================

function SkeletonRow() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 14px', borderTop: '1px solid var(--border-faint)',
    }}>
      <div style={{ flex: 1, height: 13, borderRadius: 4, background: 'var(--border-sub)', maxWidth: 280 }} />
      <div style={{ width: 60, height: 22, borderRadius: 4, background: 'var(--border-sub)' }} />
    </div>
  );
}

// ============================================================================
// SECTION
// ============================================================================

function QueueSection({
  config,
  items,
  alreadyQueued,
  loading,
  onAdd,
  addingId,
}: {
  config: SectionConfig;
  items: HandoverQueueItem[];
  alreadyQueued: Set<string>;
  loading: boolean;
  onAdd: (item: HandoverQueueItem, entityType: string) => Promise<void>;
  addingId: string | null;
}) {
  const [expanded, setExpanded] = React.useState(true);
  const { Icon, label, accentVar, bgVar, key } = config;
  const count = items.length;

  return (
    <div style={{
      background: 'var(--surface)',
      borderTop: '1px solid var(--border-top)',
      borderRight: '1px solid var(--border-side)',
      borderBottom: '1px solid var(--border-bottom)',
      borderLeft: '1px solid var(--border-side)',
      borderRadius: 6, overflow: 'hidden', marginBottom: 8,
    }}>
      {/* Section header */}
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', cursor: 'pointer', userSelect: 'none',
        }}
        onClick={() => setExpanded(v => !v)}
      >
        <div style={{
          width: 26, height: 26, borderRadius: 5,
          background: bgVar, display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <Icon size={13} style={{ color: accentVar }} />
        </div>
        <span style={{ flex: 1, fontSize: 12, fontWeight: 600, color: 'var(--txt)', letterSpacing: '0.01em' }}>
          {label}
        </span>
        {loading ? (
          <Loader2 size={12} style={{ color: 'var(--txt-ghost)', animation: 'spin 0.8s linear infinite' }} />
        ) : (
          <span style={{
            fontSize: 10, fontWeight: 600, fontFamily: 'var(--font-mono)',
            color: count > 0 ? accentVar : 'var(--txt-ghost)',
            background: count > 0 ? bgVar : 'var(--neutral-bg)',
            border: `1px solid ${count > 0 ? accentVar : 'var(--border-sub)'}20`,
            padding: '1px 7px', borderRadius: 3,
          }}>
            {count}
          </span>
        )}
        {expanded
          ? <ChevronDown size={13} style={{ color: 'var(--txt-ghost)', flexShrink: 0 }} />
          : <ChevronRight size={13} style={{ color: 'var(--txt-ghost)', flexShrink: 0 }} />
        }
      </div>

      {/* Rows */}
      {expanded && (
        <>
          {loading ? (
            [0, 1, 2].map(i => <SkeletonRow key={i} />)
          ) : count === 0 ? (
            <div style={{
              padding: '14px 14px', borderTop: '1px solid var(--border-faint)',
              fontSize: 12, color: 'var(--txt-ghost)', textAlign: 'center',
            }}>
              No items in this category
            </div>
          ) : (
            items.map((item, idx) => {
              const queued = alreadyQueued.has(item.entity_id);
              const adding = addingId === item.entity_id;
              return (
                <div
                  key={item.entity_id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 14px',
                    borderTop: '1px solid var(--border-faint)',
                    background: queued ? 'var(--teal-bg)' : undefined,
                    transition: 'background 60ms',
                  }}
                  onMouseEnter={e => { if (!queued) (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { if (!queued) (e.currentTarget as HTMLElement).style.background = ''; }}
                >
                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 13, fontWeight: 500, color: 'var(--txt)',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.ref && (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt3)', marginRight: 6 }}>
                          {item.ref}
                        </span>
                      )}
                      {item.title}
                    </div>
                    <div style={{
                      marginTop: 2, display: 'flex', alignItems: 'center', gap: 8,
                      fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--txt3)',
                    }}>
                      {item.status && (
                        <span style={{
                          padding: '1px 6px', borderRadius: 3,
                          background: 'var(--neutral-bg)', color: 'var(--txt3)',
                          border: '1px solid var(--border-sub)',
                          fontSize: 9, fontWeight: 600, letterSpacing: '0.04em',
                          textTransform: 'uppercase',
                        }}>
                          {item.status.replace(/_/g, ' ')}
                        </span>
                      )}
                      {item.age_display && <span>{item.age_display}</span>}
                    </div>
                  </div>

                  {/* Add button */}
                  <button
                    disabled={queued || adding}
                    onClick={() => onAdd(item, config.entityType)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5,
                      padding: '5px 10px', borderRadius: 5,
                      fontSize: 11, fontWeight: 600, flexShrink: 0,
                      cursor: queued ? 'default' : 'pointer',
                      border: queued
                        ? '1px solid rgba(90,171,204,0.2)'
                        : '1px solid var(--border-sub)',
                      background: queued ? 'var(--teal-bg)' : 'none',
                      color: queued ? 'var(--mark)' : 'var(--txt2)',
                      fontFamily: 'var(--font-sans)',
                      transition: 'all 60ms',
                      opacity: adding ? 0.5 : 1,
                    }}
                  >
                    {adding ? (
                      <Loader2 size={11} style={{ animation: 'spin 0.8s linear infinite' }} />
                    ) : queued ? (
                      <><Check size={11} /> Added</>
                    ) : (
                      <><Plus size={11} /> Add</>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function HandoverQueueView() {
  const { vesselId } = useActiveVessel();
  const { user } = useAuth();

  const [data, setData] = React.useState<HandoverQueueResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  // Optimistic set of entity_ids already queued
  const [alreadyQueued, setAlreadyQueued] = React.useState<Set<string>>(new Set());
  const [addingId, setAddingId] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    if (!vesselId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHandoverQueue(vesselId);
      setData(result);
      setAlreadyQueued(new Set(result.already_queued));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load queue';
      // 404 means endpoint not yet deployed — show graceful message
      if (msg.includes('404') || msg.includes('not found')) {
        setError('endpoint_pending');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [vesselId]);

  React.useEffect(() => { load(); }, [load]);

  const handleAdd = React.useCallback(async (item: HandoverQueueItem, entityType: string) => {
    if (!user?.id || !vesselId) return;
    setAddingId(item.entity_id);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) throw new Error('Not authenticated');

      const res = await fetch(`${RENDER_API_URL}/v1/actions/execute`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'add_to_handover',
          context: { yacht_id: vesselId },
          payload: {
            entity_id: item.entity_id,
            entity_type: entityType,
            summary: item.title,
            category: 'standard',
          },
        }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody?.message || `Failed (${res.status})`);
      }
      // Optimistic update
      setAlreadyQueued(prev => new Set([...prev, item.entity_id]));
      toast.success('Added to handover draft');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to add to draft');
    } finally {
      setAddingId(null);
    }
  }, [user?.id, vesselId]);

  if (error === 'endpoint_pending') {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '60px 24px', textAlign: 'center', gap: 8,
      }}>
        <Loader2 size={28} style={{ color: 'var(--txt-ghost)', marginBottom: 4 }} />
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)' }}>Queue endpoint deploying</div>
        <div style={{ fontSize: 12, color: 'var(--txt-ghost)', maxWidth: 320 }}>
          The handover queue endpoint is being deployed. Once available, this view will automatically populate with open faults, overdue work orders, and more.
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '60px 24px', textAlign: 'center', gap: 8,
      }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)' }}>Failed to load queue</div>
        <div style={{ fontSize: 12, color: 'var(--txt-ghost)', marginBottom: 8 }}>{error}</div>
        <button
          onClick={load}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px',
            borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border-sub)', background: 'none', color: 'var(--txt2)',
            fontFamily: 'var(--font-sans)',
          }}
        >
          <RefreshCw size={12} /> Retry
        </button>
      </div>
    );
  }

  const totalItems = data
    ? (data.open_faults.length + data.overdue_work_orders.length + data.low_stock_parts.length + data.pending_orders.length)
    : 0;

  return (
    <div style={{ padding: '16px 16px 32px' }}>
      {/* Header row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 12,
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt)' }}>Handover Queue</div>
          <div style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {loading ? 'Loading…' : `${totalItems} items detected · ${alreadyQueued.size} added to draft`}
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px',
            borderRadius: 5, fontSize: 11, fontWeight: 500, cursor: 'pointer',
            border: '1px solid var(--border-sub)', background: 'none', color: 'var(--txt3)',
            fontFamily: 'var(--font-sans)', opacity: loading ? 0.5 : 1,
          }}
        >
          <RefreshCw size={11} style={loading ? { animation: 'spin 0.8s linear infinite' } : {}} /> Refresh
        </button>
      </div>

      {/* Sections */}
      {SECTIONS.map(section => (
        <QueueSection
          key={section.key}
          config={section}
          items={data ? data[section.key] : []}
          alreadyQueued={alreadyQueued}
          loading={loading}
          onAdd={handleAdd}
          addingId={addingId}
        />
      ))}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
