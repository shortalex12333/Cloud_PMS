'use client';

/**
 * LedgerPanel — Right-side drawer showing activity timeline.
 * Replaces legacy centered modal with drawer matching handover/show-related pattern.
 * Day groups in cards, Me/Department pill toggle, Reads toggle.
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { X, BookOpen, Edit3, Eye, ChevronDown, ChevronRight, Plus, Trash2, CheckSquare } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { getEntityRoute } from '@/lib/featureFlags';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// TYPES
// ============================================================================

interface LedgerEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  action: string;
  change_summary?: string;
  user_role?: string;
  metadata: {
    domain?: string;
    user_name?: string;
    work_order_id?: string;
    checklist_item_id?: string;
    note_text?: string;
    note_preview?: string;
    checklist_title?: string;
    display_name?: string;
    artefact_type?: string;
    artefact_id?: string;
    [key: string]: unknown;
  } | null;
  created_at: string;
}

interface DayGroup {
  date: string;
  displayDate: string;
  mutationCount: number;
  readCount: number;
  events: LedgerEvent[];
}

interface LedgerPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// HELPERS
// ============================================================================

const READ_ACTIONS = ['artefact_opened', 'situation_ended', 'view', 'open'];

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function groupEventsByDay(events: LedgerEvent[]): DayGroup[] {
  const groups = new Map<string, DayGroup>();
  for (const event of events) {
    const date = new Date(event.created_at).toISOString().split('T')[0];
    if (!groups.has(date)) {
      groups.set(date, { date, displayDate: formatDate(event.created_at), mutationCount: 0, readCount: 0, events: [] });
    }
    const g = groups.get(date)!;
    g.events.push(event);
    READ_ACTIONS.includes(event.action) ? g.readCount++ : g.mutationCount++;
  }
  return Array.from(groups.values()).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

function formatActionVerb(action: string): string {
  const map: Record<string, string> = {
    add_note: 'note added', add_checklist_item: 'checklist item added',
    add_checklist_note: 'checklist note added', add_checklist_photo: 'checklist photo added',
    add_work_order_photo: 'photo added', add_parts_to_work_order: 'parts added',
    mark_checklist_item_complete: 'item completed', mark_work_order_complete: 'completed',
    reassign_work_order: 'reassigned', archive_work_order: 'archived',
    create: 'created', update: 'updated', delete: 'deleted',
    artefact_opened: 'opened', situation_ended: 'ended', view: 'viewed', open: 'opened',
    relation_added: 'relation added',
  };
  return map[action] || action.replace(/_/g, ' ');
}

const entityTypeMap: Record<string, string> = {
  pms_work_orders: 'work_order', pms_work_order_notes: 'work_order',
  pms_work_order_checklist_items: 'work_order', pms_faults: 'fault',
  pms_equipment: 'equipment', pms_parts: 'part', pms_receiving: 'receiving',
  pms_documents: 'document', pms_certificates: 'certificate',
  pms_handovers: 'handover', handover_export: 'handover_export',
  pms_hours_of_rest: 'hours_of_rest', pms_hor_monthly_signoffs: 'hours_of_rest_signoff',
  pms_warranties: 'warranty', pms_shopping_lists: 'shopping_list',
};

function getEntityLabel(t: string): string {
  const map: Record<string, string> = {
    work_order: 'WORK ORDER', fault: 'FAULT', equipment: 'EQUIPMENT',
    part: 'PARTS', receiving: 'RECEIVING', document: 'DOCUMENT',
    certificate: 'CERTIFICATE', handover: 'HANDOVER',
  };
  const key = entityTypeMap[t] || t;
  return map[key] || t.replace(/^pms_/, '').replace(/_/g, ' ').toUpperCase();
}

// ============================================================================
// STYLES
// ============================================================================

const S = {
  backdrop: { position: 'fixed' as const, inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 90, transition: 'opacity 200ms ease' },
  drawer: {
    position: 'fixed' as const, top: 0, right: 0, bottom: 0,
    width: 480, background: 'var(--surface)',
    borderLeft: '1px solid var(--border-side)',
    boxShadow: 'var(--shadow-panel, -20px 0 80px rgba(0,0,0,0.50))',
    display: 'flex', flexDirection: 'column' as const, zIndex: 100, overflow: 'hidden',
  },
  hdr: { display: 'flex', alignItems: 'center', padding: '14px 16px', borderBottom: '1px solid var(--border-sub)', gap: 10, flexShrink: 0 },
  icon: { width: 28, height: 28, borderRadius: 6, background: 'var(--amber-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  close: { width: 32, height: 32, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--txt-ghost)', background: 'none', border: 'none' },
  toggleBar: { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderBottom: '1px solid var(--border-faint)', flexShrink: 0 },
  pillGroup: { display: 'flex', alignItems: 'center', padding: 2, background: 'var(--surface-base)', borderRadius: 6, border: '1px solid var(--border-sub)' },
  pill: (active: boolean) => ({
    padding: '5px 14px', borderRadius: 4, fontSize: 11, fontWeight: 600,
    cursor: 'pointer', border: 'none', fontFamily: 'var(--font-sans)',
    background: active ? 'var(--teal-bg)' : 'none',
    color: active ? 'var(--mark)' : 'var(--txt3)',
    transition: 'all 80ms',
  }),
  readsBtn: (active: boolean) => ({
    display: 'flex', alignItems: 'center', gap: 4,
    padding: '5px 10px', borderRadius: 4, fontSize: 11, fontWeight: 500,
    cursor: 'pointer', fontFamily: 'var(--font-sans)',
    background: active ? 'var(--teal-bg)' : 'none',
    color: active ? 'var(--mark)' : 'var(--txt3)',
    border: `1px solid ${active ? 'var(--mark-hover)' : 'var(--border-sub)'}`,
  }),
  body: { flex: 1, overflowY: 'auto' as const, padding: '8px 12px 16px', background: 'var(--surface-base)' },
  dayCard: {
    background: 'var(--surface)',
    borderTop: '1px solid var(--border-top)',
    borderRight: '1px solid var(--border-side)',
    borderBottom: '1px solid var(--border-bottom)',
    borderLeft: '1px solid var(--border-side)',
    borderRadius: 4, overflow: 'hidden', marginBottom: 6,
  },
  dayHdr: {
    display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
    cursor: 'pointer', userSelect: 'none' as const,
    fontSize: 9, fontWeight: 600, textTransform: 'uppercase' as const,
    letterSpacing: '0.12em', color: 'var(--txt)',
  },
  event: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '8px 12px', minHeight: 44, cursor: 'pointer',
    transition: 'background 60ms', borderTop: '1px solid var(--border-faint)',
  },
};

// ============================================================================
// COMPONENT
// ============================================================================

export function LedgerPanel({ isOpen, onClose }: LedgerPanelProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [events, setEvents] = useState<LedgerEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [showReads, setShowReads] = useState(false);
  const [viewMode, setViewMode] = useState<'me' | 'department'>('me');
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const LIMIT = 50;

  const handleItemClick = useCallback((event: LedgerEvent) => {
    if (!event.entity_type || !event.entity_id) return;
    const lensType = entityTypeMap[event.entity_type] || event.entity_type;
    const entityId = (event.metadata?.work_order_id as string) || event.entity_id;
    router.push(getEntityRoute(lensType as Parameters<typeof getEntityRoute>[0], entityId));
    onClose();
  }, [router, onClose]);

  const fetchEvents = useCallback(async (reset = false) => {
    if (!user || loading) return;
    setLoading(true);
    try {
      const offset = reset ? 0 : events.length;
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) return;

      const endpoint = viewMode === 'me' ? '/v1/ledger/events' : '/v1/ledger/timeline';
      const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
      if (viewMode === 'me' && user?.id) params.set('user_id', user.id);

      const response = await fetch(`${RENDER_API_URL}${endpoint}?${params}`, {
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (!response.ok) return;

      const result = await response.json();
      const fetched = result.events || [];
      reset ? setEvents(fetched) : setEvents(prev => [...prev, ...fetched]);
      setHasMore(result.has_more ?? fetched.length === LIMIT);

      if (reset && fetched.length > 0) {
        setExpandedDays(new Set([new Date(fetched[0].created_at).toISOString().split('T')[0]]));
      }
    } catch (err) {
      console.error('[LedgerPanel] Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [user, loading, events.length, viewMode]);

  useEffect(() => { if (isOpen && events.length === 0) fetchEvents(true); }, [isOpen]);
  useEffect(() => { if (isOpen) { setEvents([]); setHasMore(true); fetchEvents(true); } }, [viewMode]);

  useEffect(() => {
    if (!isOpen || !hasMore || loading) return;
    const obs = new IntersectionObserver(([e]) => { if (e?.isIntersecting) fetchEvents(); }, { threshold: 0.1 });
    const el = sentinelRef.current;
    if (el) obs.observe(el);
    return () => { if (el) obs.unobserve(el); };
  }, [isOpen, hasMore, loading, fetchEvents]);

  const toggleDay = (date: string) => {
    setExpandedDays(prev => { const n = new Set(prev); n.has(date) ? n.delete(date) : n.add(date); return n; });
  };

  if (!isOpen) return null;
  const dayGroups = groupEventsByDay(events);

  return (
    <>
      <div style={{ ...S.backdrop, opacity: 1, pointerEvents: 'auto' }} onClick={onClose} />

      <div style={S.drawer}>
        {/* Header */}
        <div style={S.hdr}>
          <div style={S.icon}><BookOpen size={14} color="var(--amber)" /></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--txt)' }}>Ledger</div>
            <div style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>Activity timeline</div>
          </div>
          <button style={S.close} onClick={onClose}><X size={14} /></button>
        </div>

        {/* Toggle bar */}
        <div style={S.toggleBar}>
          <div style={S.pillGroup}>
            <button style={S.pill(viewMode === 'me')} onClick={() => setViewMode('me')}>Me</button>
            <button style={S.pill(viewMode === 'department')} onClick={() => setViewMode('department')}>Department</button>
          </div>
          <div style={{ flex: 1 }} />
          <button style={S.readsBtn(showReads)} onClick={() => setShowReads(!showReads)}>
            <Eye size={12} /> Reads
          </button>
        </div>

        {/* Body */}
        <div ref={scrollRef} style={S.body}>
          {dayGroups.length === 0 && !loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
              <BookOpen size={48} style={{ color: 'var(--txt-ghost)', marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)' }}>No events recorded yet</div>
            </div>
          ) : (
            dayGroups.map(group => (
              <div key={group.date} style={{ marginBottom: 6 }}>
                <div style={S.dayCard}>
                  <div style={S.dayHdr} onClick={() => toggleDay(group.date)}>
                    <span style={{ flex: 1 }}>
                      {group.displayDate}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 400 }}>
                      <span style={{ color: 'var(--green)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <Edit3 size={10} /> {group.mutationCount}
                      </span>
                      {showReads && group.readCount > 0 && (
                        <span style={{ color: 'var(--amber)', display: 'flex', alignItems: 'center', gap: 3 }}>
                          <Eye size={10} /> {group.readCount}
                        </span>
                      )}
                    </span>
                    {expandedDays.has(group.date)
                      ? <ChevronDown size={12} style={{ color: 'var(--txt-ghost)' }} />
                      : <ChevronRight size={12} style={{ color: 'var(--txt-ghost)' }} />}
                  </div>

                  {expandedDays.has(group.date) && group.events
                    .filter(e => showReads || !READ_ACTIONS.includes(e.action))
                    .map((event, idx) => {
                      const isMut = !READ_ACTIONS.includes(event.action);
                      const displayName = event.change_summary || event.metadata?.display_name || event.metadata?.checklist_title || event.metadata?.domain || event.entity_type || 'Action';
                      const userName = (event.metadata?.user_name as string) || event.user_role || '';
                      return (
                        <div
                          key={event.id}
                          style={{ ...S.event, ...(idx === 0 ? {} : {}) }}
                          onClick={() => handleItemClick(event)}
                          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
                          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = ''; }}
                        >
                          {isMut
                            ? <Edit3 size={14} style={{ flexShrink: 0, color: 'var(--green)' }} />
                            : <Eye size={14} style={{ flexShrink: 0, color: 'var(--amber)' }} />
                          }
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{
                              fontSize: 13, fontWeight: 500, color: 'var(--txt)',
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                            }}>
                              <span style={{ color: 'var(--mark)' }}>{displayName}</span>
                              <span style={{ color: 'var(--txt3)' }}> — </span>
                              {formatActionVerb(event.action)}
                            </div>
                            <div style={{
                              fontSize: 10.5, color: 'var(--txt2)', fontFamily: 'var(--font-mono)',
                              letterSpacing: '0.03em', marginTop: 1,
                            }}>
                              {getEntityLabel(event.entity_type)}{userName ? ` · ${userName.toUpperCase()}` : ''}
                            </div>
                          </div>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', flexShrink: 0 }}>
                            {formatTime(event.created_at)}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))
          )}

          {hasMore && (
            <div ref={sentinelRef} style={{ height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {loading && (
                <div style={{
                  width: 20, height: 20, border: '2px solid var(--border-sub)',
                  borderTopColor: 'var(--mark)', borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }} />
              )}
            </div>
          )}

          {events.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', padding: '8px 12px', marginTop: 4 }}>
              <span style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
                {events.length} event{events.length !== 1 ? 's' : ''} · {dayGroups.length} day{dayGroups.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
