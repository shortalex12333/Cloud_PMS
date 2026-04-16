'use client';

/**
 * HandoverDraftPanel — Drawer + Popup CRUD for handover draft items.
 *
 * Replaces legacy ContextPanel with:
 * - Right-side drawer (460px, slide-in, backdrop)
 * - Chronological day groups with collapsible sections
 * - Click item → popup for Edit/Delete
 * - Add Note button → Create popup
 * - Export button → backend LLM pipeline
 *
 * Data: handover_items table (tenant DB), filtered by user + not exported.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  X, FileText, AlertTriangle, Package, Wrench, File,
  ChevronDown, ChevronRight, Upload, Plus, Loader2, Trash2, Save,
} from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { getEntityRoute } from '@/lib/entityRoutes';
import { toast } from 'sonner';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ============================================================================
// TYPES
// ============================================================================

interface HandoverItem {
  id: string;
  yacht_id: string;
  entity_id: string;
  entity_type: string;
  entity_url: string | null;
  section: string | null;
  summary: string | null;
  category: string | null;
  priority: number;
  status: string;
  is_critical: boolean;
  requires_action: boolean;
  action_summary: string | null;
  risk_tags: string[] | null;
  added_by: string;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, unknown> | null;
}

interface DayGroup {
  date: string;
  displayDate: string;
  items: HandoverItem[];
}

interface HandoverDraftPanelProps {
  isOpen: boolean;
  onClose: () => void;
  /** 'drawer' (default) = fixed right-side drawer with backdrop.
   *  'page' = inline content block, no backdrop, no fixed positioning.
   *  When variant='page', isOpen controls whether data is loaded but the
   *  component always renders (caller controls visibility via tab switching). */
  variant?: 'drawer' | 'page';
}

type PopupMode = null | { type: 'edit'; item: HandoverItem } | { type: 'add' } | { type: 'delete'; item: HandoverItem };

const CATEGORIES = ['critical', 'standard', 'low'] as const;
const STATUSES = ['on_going', 'not_started', 'requires_parts'] as const;
const SECTIONS = ['Engineering', 'Deck', 'Interior', 'Command'] as const;

// ============================================================================
// HELPERS
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return 'Today';
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function groupItemsByDay(items: HandoverItem[]): DayGroup[] {
  const groups = new Map<string, DayGroup>();
  for (const item of items) {
    const date = new Date(item.created_at).toISOString().split('T')[0];
    if (!groups.has(date)) {
      groups.set(date, { date, displayDate: formatDate(item.created_at), items: [] });
    }
    groups.get(date)!.items.push(item);
  }
  return Array.from(groups.values()).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

function getEntityIcon(entityType: string) {
  switch (entityType) {
    case 'fault': return AlertTriangle;
    case 'work_order': return Wrench;
    case 'equipment': return Package;
    case 'document': return File;
    default: return FileText;
  }
}

function getEntityLabel(entityType: string): string {
  switch (entityType) {
    case 'fault': return 'Fault';
    case 'work_order': return 'W/O';
    case 'equipment': return 'Equipment';
    case 'part': return 'Parts';
    case 'document': return 'Document';
    case 'note': return 'Note';
    default: return entityType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
}

function categoryLabel(cat: string | null): string {
  switch (cat) {
    case 'critical': return 'Critical';
    case 'standard': return 'Standard';
    case 'low': return 'Low';
    default: return cat || 'Standard';
  }
}

function statusLabel(s: string): string {
  switch (s) {
    case 'on_going': return 'On Going';
    case 'not_started': return 'Not Started';
    case 'requires_parts': return 'Requires Parts';
    default: return s;
  }
}

// ============================================================================
// STYLES (inline objects matching prototype tokens)
// ============================================================================

const S = {
  backdrop: {
    position: 'fixed' as const, inset: 0, background: 'var(--overlay-bg)',
    zIndex: 90, transition: 'opacity 200ms ease',
  },
  drawer: {
    position: 'fixed' as const, top: 0, right: 0, bottom: 0,
    width: 460, background: 'var(--surface)',
    borderLeft: '1px solid var(--border-side)',
    boxShadow: 'var(--shadow-panel)',
    display: 'flex', flexDirection: 'column' as const, zIndex: 100,
    transition: 'transform 250ms cubic-bezier(0.16,1,0.3,1), opacity 180ms ease',
    overflow: 'hidden',
  },
  drawerHdr: {
    display: 'flex', alignItems: 'center', padding: '14px 16px',
    borderBottom: '1px solid var(--border-sub)', gap: 10, flexShrink: 0,
  },
  drawerIcon: {
    width: 28, height: 28, borderRadius: 6,
    background: 'var(--teal-bg)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  statsBar: {
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '10px 16px', borderBottom: '1px solid var(--border-faint)', flexShrink: 0,
    fontSize: 11, fontWeight: 500, color: 'var(--txt3)',
  },
  actionBar: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '10px 16px', borderBottom: '1px solid var(--border-sub)', flexShrink: 0,
  },
  body: {
    flex: 1, overflowY: 'auto' as const, padding: '8px 12px 16px',
    background: 'var(--surface-base)',
  },
  dayCard: {
    background: 'var(--surface)',
    borderTop: '1px solid var(--border-top)',
    borderRight: '1px solid var(--border-side)',
    borderBottom: '1px solid var(--border-bottom)',
    borderLeft: '1px solid var(--border-side)',
    borderRadius: 4, overflow: 'hidden', marginBottom: 6,
  },
  dayHdr: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '8px 12px', cursor: 'pointer', userSelect: 'none' as const,
    fontSize: 9, fontWeight: 600, textTransform: 'uppercase' as const,
    letterSpacing: '0.12em', color: 'var(--txt)',
  },
  item: {
    display: 'flex', alignItems: 'flex-start', gap: 10,
    padding: '10px 12px', cursor: 'pointer', minHeight: 44,
    transition: 'background 60ms', position: 'relative' as const,
  },
  itemBorder: { borderTop: '1px solid var(--border-faint)' },
  popupOverlay: {
    position: 'fixed' as const, inset: 0, zIndex: 200,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'opacity 180ms ease',
  },
  popupBg: { position: 'absolute' as const, inset: 0, background: 'var(--overlay-bg)' },
  popupBgDelete: { position: 'absolute' as const, inset: 0, background: 'rgba(0,0,0,0.60)' /* intentionally darker than --overlay-bg for delete confirm */ },
  popup: {
    position: 'relative' as const, width: '100%', maxWidth: 520,
    background: 'var(--surface-el)', borderRadius: 12,
    borderTop: '1px solid var(--border-top)',
    borderRight: '1px solid var(--border-side)',
    borderBottom: '1px solid var(--border-bottom)',
    borderLeft: '1px solid var(--border-side)',
    boxShadow: 'var(--shadow-panel)',
    overflow: 'hidden',
  },
  field: {
    display: 'flex', alignItems: 'flex-start', gap: 12,
    minHeight: 44, padding: '8px 0',
    borderTop: '1px solid var(--border-faint)',
  },
  fieldLabel: {
    fontSize: 11, fontWeight: 500, color: 'var(--txt3)',
    textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    minWidth: 100, paddingTop: 11, flexShrink: 0,
  },
  select: {
    flex: 1, height: 40, background: 'var(--surface-base)',
    border: '1px solid var(--border-chrome)', borderRadius: 6,
    padding: '0 32px 0 12px', fontSize: 13, color: 'var(--txt)',
    fontFamily: 'var(--font-sans)', cursor: 'pointer', outline: 'none',
    appearance: 'none' as const,
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center',
  },
  textarea: {
    width: '100%', boxSizing: 'border-box' as const,
    background: 'var(--surface-base)', border: '1px solid var(--border-chrome)',
    borderRadius: 6, color: 'var(--txt)', fontFamily: 'var(--font-sans)',
    fontSize: 13, padding: '10px 12px', resize: 'vertical' as const,
    minHeight: 80, lineHeight: 1.5, outline: 'none',
  },
  radioRow: { flex: 1, display: 'flex', alignItems: 'center', gap: 4, paddingTop: 8, flexWrap: 'wrap' as const },
  radioItem: (selected: boolean) => ({
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '6px 12px', borderRadius: 6, cursor: 'pointer', userSelect: 'none' as const,
    border: `1px solid ${selected ? 'var(--mark-underline)' : 'var(--border-sub)'}`,
    background: selected ? 'var(--teal-bg)' : 'none',
    fontSize: 13, color: selected ? 'var(--mark)' : 'var(--txt2)',
    fontWeight: selected ? 500 : 400, transition: 'all 60ms',
  }),
  btnPrimary: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
    cursor: 'pointer', border: '1px solid var(--mark-underline)',
    background: 'var(--teal-bg)', color: 'var(--mark)',
    fontFamily: 'var(--font-sans)', minHeight: 40,
  },
  btnSecondary: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500,
    cursor: 'pointer', border: '1px solid var(--border-sub)',
    background: 'none', color: 'var(--txt2)',
    fontFamily: 'var(--font-sans)', minHeight: 40,
  },
  btnDanger: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500,
    cursor: 'pointer', border: 'none', marginLeft: 'auto',
    background: 'none', color: 'var(--txt3)',
    fontFamily: 'var(--font-sans)',
  },
  btnDeleteConfirm: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
    cursor: 'pointer', border: 'none',
    background: 'var(--red)', color: 'var(--on-status)', fontFamily: 'var(--font-sans)',
  },
  catBadge: (cat: string | null) => {
    const map: Record<string, { bg: string; color: string; border: string }> = {
      critical: { bg: 'var(--red-bg)', color: 'var(--red)', border: 'var(--red-border)' },
      standard: { bg: 'var(--neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
      low: { bg: 'var(--green-bg)', color: 'var(--green)', border: 'var(--green-border)' },
    };
    const t = map[cat || 'standard'] || map.standard;
    return {
      display: 'inline-flex', alignItems: 'center', gap: 3,
      padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 600,
      letterSpacing: '0.04em', textTransform: 'uppercase' as const,
      background: t.bg, color: t.color, border: `1px solid ${t.border}`,
    };
  },
};

// ============================================================================
// ITEM POPUP (Edit / Add / Delete)
// ============================================================================

function ItemPopup({
  mode, onClose, onSave, onDelete, onSwitchToDelete, userReady = true,
}: {
  mode: NonNullable<PopupMode>;
  onClose: () => void;
  onSave: (data: { id?: string; summary: string; category: string; status: string; section: string }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onSwitchToDelete?: (item: HandoverItem) => void;
  userReady?: boolean;
}) {
  const isEdit = mode.type === 'edit';
  const isAdd = mode.type === 'add';
  const isDelete = mode.type === 'delete';
  const item = (mode.type === 'edit' || mode.type === 'delete') ? mode.item : null;

  const [summary, setSummary] = useState(item?.summary || '');
  const [category, setCategory] = useState(item?.category || '');
  const [status, setStatus] = useState((item?.metadata as any)?.ui_status || '');
  const [section, setSection] = useState(item?.section || 'Engineering');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!summary.trim()) { toast.error('Summary is required'); return; }
    setSaving(true);
    try {
      await onSave({ id: item?.id, summary: summary.trim(), category, status, section });
      onClose();
    } catch {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!item) return;
    setSaving(true);
    try {
      await onDelete(item.id);
      onClose();
    } catch {
      toast.error('Failed to delete');
    } finally {
      setSaving(false);
    }
  };

  if (isDelete && item) {
    return (
      <div style={{ ...S.popupOverlay, opacity: 1, pointerEvents: 'auto' }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
        <div style={S.popupBgDelete} onClick={onClose} />
        <div style={S.popup}>
          <div style={{ padding: '32px 24px', textAlign: 'center' }}>
            <div style={{
              width: 48, height: 48, borderRadius: 12,
              background: 'var(--red-bg)', color: 'var(--red)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12,
            }}>
              <Trash2 size={24} />
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--txt)', marginBottom: 4 }}>Delete this handover note?</div>
            <div style={{ fontSize: 13, color: 'var(--txt2)', maxWidth: 320, margin: '0 auto 20px', lineHeight: 1.5 }}>
              This will permanently remove this note from your handover draft.
              {item.entity_type !== 'note' && <> The source <strong>{getEntityLabel(item.entity_type)}</strong> will not be affected.</>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
              <button style={S.btnDeleteConfirm} onClick={handleDelete} disabled={saving || !userReady}>
                <Trash2 size={14} /> {saving ? 'Deleting...' : 'Delete Note'}
              </button>
              <button style={S.btnSecondary} onClick={onClose}>Cancel</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const Icon = item ? getEntityIcon(item.entity_type) : Plus;

  return (
    <div style={{ ...S.popupOverlay, opacity: 1, pointerEvents: 'auto' }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={S.popupBg} onClick={onClose} />
      <div style={S.popup}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', padding: '20px 24px 16px', gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, display: 'flex',
            alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            background: isAdd ? 'var(--neutral-bg)' : (item?.entity_type === 'fault' ? 'var(--red-bg)' : 'var(--teal-bg)'),
            color: isAdd ? 'var(--txt3)' : (item?.entity_type === 'fault' ? 'var(--red)' : 'var(--mark)'),
          }}>
            <Icon size={16} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--txt)' }}>
              {isAdd ? 'Add Handover Note' : 'Edit Handover Note'}
            </div>
            <div style={{ fontSize: 13, color: 'var(--txt2)', marginTop: 3 }}>
              {isAdd
                ? 'This note will be included in your next handover export'
                : <>{getEntityLabel(item!.entity_type)} · <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{item!.entity_id?.slice(0, 8)}</span> · Added <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{formatTime(item!.created_at)}</span></>
              }
            </div>
          </div>
          <button onClick={onClose} style={{
            width: 36, height: 36, borderRadius: 8, display: 'flex',
            alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            color: 'var(--txt-ghost)', background: 'none', border: 'none',
          }}>
            <X size={14} />
          </button>
        </div>

        <div style={{ height: 1, background: 'var(--border-sub)', margin: '0 24px' }} />

        {/* Body */}
        <div style={{ padding: '0 24px 20px' }}>
          {/* Summary */}
          <div style={{ padding: '12px 0' }}>
            <div style={{ ...S.fieldLabel, paddingTop: 0, marginBottom: 8 }}>Summary</div>
            <textarea
              style={S.textarea}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder={isAdd ? 'Describe what the incoming crew needs to know...' : ''}
            />
          </div>

          {/* Category */}
          <div style={S.field}>
            <div style={S.fieldLabel}>Category</div>
            <select style={S.select} value={category} onChange={(e) => setCategory(e.target.value)}>
              {!category && <option value="" disabled>Select category…</option>}
              {CATEGORIES.map(c => <option key={c} value={c}>{categoryLabel(c)}</option>)}
            </select>
          </div>

          {/* Status (radio) */}
          <div style={S.field}>
            <div style={S.fieldLabel}>Status</div>
            <div style={S.radioRow}>
              {STATUSES.map(s => (
                <div key={s} style={S.radioItem(status === s)} onClick={() => setStatus(s)}>
                  <div style={{
                    width: 14, height: 14, borderRadius: '50%',
                    border: `1.5px solid ${status === s ? 'var(--mark)' : 'var(--border-chrome)'}`,
                    background: 'var(--surface-base)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {status === s && <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--mark)' }} />}
                  </div>
                  {statusLabel(s)}
                </div>
              ))}
            </div>
          </div>

          {/* Section (Add only) */}
          {isAdd && (
            <div style={S.field}>
              <div style={S.fieldLabel}>Section</div>
              <select style={S.select} value={section} onChange={(e) => setSection(e.target.value)}>
                {SECTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          borderTop: '1px solid var(--border-sub)', padding: '16px 24px',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <button style={{ ...S.btnPrimary, opacity: (saving || !userReady) ? 0.5 : 1 }} onClick={handleSave} disabled={saving || !userReady}>
            {isAdd ? <><Plus size={14} /> {saving ? 'Adding...' : 'Add to Handover'}</> : <><Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}</>}
          </button>
          <button style={S.btnSecondary} onClick={onClose}>Cancel</button>
          {isEdit && item && (
            <button style={S.btnDanger} onClick={() => onSwitchToDelete?.(item)} onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--red)'; }} onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--txt3)'; }}>
              <Trash2 size={14} /> Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function HandoverDraftPanel({ isOpen, onClose, variant = 'drawer' }: HandoverDraftPanelProps) {
  const { user } = useAuth();
  const { vesselId: activeVesselId } = useActiveVessel();
  const router = useRouter();
  const [items, setItems] = useState<HandoverItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());
  const [popup, setPopup] = useState<PopupMode>(null);

  // Auth readiness — buttons disabled until user context is loaded
  const userReady = !!(user?.id);

  // ── Fetch — all calls go through Render API (TENANT DB, correct path) ──
  // CORS headers occasionally disappear during Render rolling deploys
  // (PR #565 is deployed, but transitions briefly serve without CORS). Cap
  // retries at 3 with exponential backoff (1s / 2s / 4s) so a deploy blip
  // doesn't produce infinite console spam.
  const fetchItems = useCallback(async () => {
    if (!user?.id) return;
    setLoading(true);
    const MAX_RETRIES = 3;
    const BACKOFFS = [1000, 2000, 4000];
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) { toast.error('Not authenticated'); return; }

      let lastError: unknown = null;
      for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
        try {
          const res = await fetch(`${RENDER_API_URL}/v1/handover/items`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const { items: fetched } = await res.json();
          setItems(fetched || []);
          setExpandedDays(new Set([new Date().toISOString().split('T')[0]]));
          return;
        } catch (err) {
          lastError = err;
          if (attempt < MAX_RETRIES - 1) {
            await new Promise((r) => setTimeout(r, BACKOFFS[attempt]));
          }
        }
      }
      console.warn('[HandoverDraftPanel] fetchItems giving up after retries:', lastError);
      toast.error('Failed to load handover items');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => { if (isOpen) fetchItems(); }, [isOpen, fetchItems]);

  // ── Save (Create + Update) — routed through Render API ──
  const handleSave = useCallback(async (data: { id?: string; summary: string; category: string; status: string; section: string }) => {
    if (!user?.id) return;
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) throw new Error('Not authenticated');

    if (data.id) {
      // Update via new PATCH endpoint
      const res = await fetch(`${RENDER_API_URL}/v1/handover/items/${data.id}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          summary: data.summary,
          category: data.category,
          status: data.status,
          section: data.section,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Update failed (${res.status})`);
      }
      toast.success('Handover note updated');
    } else {
      // Create via action router (same path as Queue + Add)
      const res = await fetch(`${RENDER_API_URL}/v1/actions/execute`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'add_to_handover',
          context: { yacht_id: activeVesselId || user.yachtId },
          payload: {
            entity_type: 'note',
            summary: data.summary,
            category: data.category,
            section: data.section,
            requires_action: data.status === 'requires_parts',
          },
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || err.detail || `Add failed (${res.status})`);
      }
      toast.success('Handover note added');
    }
    fetchItems();
  }, [user?.id, activeVesselId, user?.yachtId, fetchItems]);

  // ── Delete (soft) — routed through Render API ──
  const handleDelete = useCallback(async (id: string) => {
    if (!user?.id) return;
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) throw new Error('Not authenticated');

    const res = await fetch(`${RENDER_API_URL}/v1/handover/items/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Delete failed (${res.status})`);
    }
    toast.success('Handover note deleted');
    fetchItems();
  }, [user?.id, fetchItems]);

  // ── Export ──
  const handleExport = useCallback(async () => {
    if (!user?.id || !(activeVesselId || user?.yachtId) || items.length === 0) return;
    setExporting(true);
    // Immediate feedback: the LLM pipeline can take up to 2 minutes on a
    // cold start. Without this toast the button just spins and the user has
    // no indication anything is happening.
    const pendingToastId = toast.info(
      'Generating handover — this may take up to 2 minutes',
      { duration: 120_000 }
    );
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData?.session?.access_token;
      if (!token) throw new Error('Authentication required — please log in again');

      const response = await fetch(`${RENDER_API_URL}/v1/handover/export`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ export_type: 'html', filter_by_user: true }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Export failed' }));
        throw new Error(err.detail || `Export failed (${response.status})`);
      }

      const result = await response.json();
      // Mark items exported via Render API (not direct supabase — wrong DB)
      await fetch(`${RENDER_API_URL}/v1/handover/items/mark-exported`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: items.map(i => i.id) }),
      });

      toast.dismiss(pendingToastId);
      // 10s duration (not default 4s) so the user sees the "View" button.
      toast.success(`Handover exported — ${result.total_items} items`, {
        duration: 10_000,
        action: { label: 'View', onClick: () => router.push(`/handover-export/${result.export_id}`) },
      });
      fetchItems();
    } catch (err) {
      toast.dismiss(pendingToastId);
      toast.error(err instanceof Error ? err.message : 'Failed to export handover');
    } finally {
      setExporting(false);
    }
  }, [user?.id, activeVesselId || user?.yachtId, items, fetchItems, router]);

  // ── Toggle day ──
  const toggleDay = useCallback((date: string) => {
    setExpandedDays(prev => {
      const next = new Set(prev);
      next.has(date) ? next.delete(date) : next.add(date);
      return next;
    });
  }, []);

  // In drawer mode, don't render when closed.
  // In page mode, always render (tab visibility handled by parent).
  if (variant === 'drawer' && !isOpen) return null;

  const grouped = groupItemsByDay(items);
  const criticalCount = items.filter(i => i.category === 'critical' || i.is_critical).length;
  const actionCount = items.filter(i => i.requires_action || i.status === 'requires_parts').length;

  const content = (
    <div
      data-user-ready={userReady ? 'true' : undefined}
      style={variant === 'page'
      ? { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }
      : { ...S.drawer, transform: 'translateX(0)', opacity: 1 }
    }>

        {/* Header */}
        <div style={S.drawerHdr}>
          <div style={S.drawerIcon}>
            <FileText size={14} color="var(--mark)" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--txt)' }}>My Handover Draft</div>
            <div style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
              {items.length} item{items.length !== 1 ? 's' : ''} · {user?.role || 'Engineering'}
            </div>
          </div>
          <button onClick={onClose} style={{
            width: 32, height: 32, borderRadius: 6, display: 'flex',
            alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            color: 'var(--txt-ghost)', background: 'none', border: 'none',
          }}>
            <X size={14} />
          </button>
        </div>

        {/* Stats */}
        {items.length > 0 && (
          <div style={S.statsBar}>
            <span><span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--txt)' }}>{items.length}</span> items</span>
            {criticalCount > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--red)' }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--red)' }}>{criticalCount}</span> critical
              </span>
            )}
            {actionCount > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--amber)' }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--amber)' }}>{actionCount}</span> action
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div style={S.actionBar}>
          <button
            onClick={handleExport}
            disabled={exporting || items.length === 0}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 6,
              background: 'var(--teal-bg)', color: 'var(--mark)',
              fontSize: 12, fontWeight: 600, border: '1px solid var(--mark-underline)',
              cursor: items.length === 0 ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--font-sans)', opacity: (exporting || items.length === 0) ? 0.5 : 1,
            }}
          >
            {exporting ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
            {exporting ? 'Exporting...' : 'Export Handover'}
          </button>
          <button
            onClick={() => setPopup({ type: 'add' })}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '7px 12px', borderRadius: 6,
              background: 'none', color: 'var(--mark)',
              fontSize: 12, fontWeight: 500, border: '1px solid var(--border-sub)',
              cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}
          >
            <Plus size={12} /> Add Note
          </button>
        </div>

        {/* Body */}
        <div style={S.body}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
              <Loader2 size={24} className="animate-spin" style={{ color: 'var(--txt3)' }} />
            </div>
          ) : items.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
              <FileText size={48} style={{ color: 'var(--txt-ghost)', marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)', marginBottom: 4 }}>No handover items</div>
              <div style={{ fontSize: 12, color: 'var(--txt3)', maxWidth: 260, lineHeight: 1.6 }}>
                Add notes from faults, work orders, or equipment to include in your handover.
              </div>
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.date} style={{ marginBottom: 6 }}>
                <div style={S.dayCard}>
                  <div style={S.dayHdr} onClick={() => toggleDay(group.date)}>
                    <span style={{ flex: 1 }}>
                      {group.displayDate} <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 400, color: 'var(--txt3)' }}>· {group.items.length}</span>
                    </span>
                    {expandedDays.has(group.date)
                      ? <ChevronDown size={12} style={{ color: 'var(--txt-ghost)' }} />
                      : <ChevronRight size={12} style={{ color: 'var(--txt-ghost)' }} />
                    }
                  </div>

                  {expandedDays.has(group.date) && group.items.map((item, idx) => {
                    const Icon = getEntityIcon(item.entity_type);
                    const isCrit = item.category === 'critical' || item.is_critical;
                    return (
                      <div
                        key={item.id}
                        onClick={() => setPopup({ type: 'edit', item })}
                        style={{
                          ...S.item,
                          ...(idx > 0 ? S.itemBorder : {}),
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-hover)'; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = ''; }}
                      >
                        {/* Critical left edge */}
                        {isCrit && <div style={{ position: 'absolute', left: 0, top: 4, bottom: 4, width: 2, borderRadius: 1, background: 'var(--red)' }} />}

                        <Icon size={14} style={{ flexShrink: 0, color: isCrit ? 'var(--red)' : 'var(--txt3)', marginTop: 2 }} />

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{
                            fontSize: 13, fontWeight: 500, color: 'var(--txt)', lineHeight: 1.4,
                            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                          }}>
                            {item.summary || 'No summary'}
                          </div>
                          <div style={{
                            fontSize: 10.5, color: 'var(--txt2)', fontFamily: 'var(--font-mono)',
                            letterSpacing: '0.03em', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6,
                          }}>
                            <span>{getEntityLabel(item.entity_type).toUpperCase()}</span>
                            <span style={S.catBadge(item.category)}>{categoryLabel(item.category)}</span>
                            {(item.metadata as any)?.ui_status && (
                              <span style={{ fontSize: 9, fontWeight: 600, color: 'var(--amber)', letterSpacing: '0.04em', textTransform: 'uppercase', fontFamily: 'var(--font-sans)' }}>
                                {statusLabel((item.metadata as any).ui_status)}
                              </span>
                            )}
                          </div>
                        </div>

                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', flexShrink: 0, whiteSpace: 'nowrap', marginTop: 2 }}>
                          {formatTime(item.created_at)}
                        </span>
                        <ChevronRight size={12} style={{ color: 'var(--txt-ghost)', flexShrink: 0, marginTop: 4, opacity: 0.5 }} />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}

          {/* Footer */}
          {items.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', marginTop: 4 }}>
              <span style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
                {items.length} handover item{items.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
    </div>
  );

  if (variant === 'page') {
    return (
      <>
        {content}
        {popup && (
          <ItemPopup
            mode={popup}
            onClose={() => setPopup(null)}
            onSave={handleSave}
            onDelete={handleDelete}
            onSwitchToDelete={(item) => setPopup({ type: 'delete', item })}
            userReady={userReady}
          />
        )}
      </>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div style={{ ...S.backdrop, opacity: 1, pointerEvents: 'auto' }} onClick={onClose} />
      {content}
      {/* Popup */}
      {popup && (
        <ItemPopup
          mode={popup}
          onClose={() => setPopup(null)}
          onSave={handleSave}
          onDelete={handleDelete}
          onSwitchToDelete={(item) => setPopup({ type: 'delete', item })}
        />
      )}
    </>
  );
}
