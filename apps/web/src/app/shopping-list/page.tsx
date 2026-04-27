'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useActiveVessel } from '@/contexts/VesselContext';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { API_BASE } from '@/lib/apiBase';

// ── Types ─────────────────────────────────────────────────────────────────

interface ShoppingListDoc {
  id: string;
  list_number: string;
  name: string;
  department: string;
  status: string;
  currency: string;
  estimated_total: number | null;
  item_count: number;
  created_at: string;
  submitted_at: string | null;
  approved_at: string | null;
  converted_at: string | null;
}

// ── Status config ─────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Pending Review',
  hod_approved: 'HOD Approved',
  converted_to_po: 'Converted to PO',
};

const STATUS_COLORS: Record<string, { fg: string; bg: string; bd: string }> = {
  draft:          { fg: 'var(--txt2)',   bg: 'var(--surface-hover)', bd: 'var(--border-sub)' },
  submitted:      { fg: 'var(--amber)',  bg: 'var(--amber-bg, #2a2000)', bd: 'var(--amber-border, #6b4e00)' },
  hod_approved:   { fg: 'var(--green)',  bg: 'var(--green-bg, #001a0d)', bd: 'var(--green-border, #004d1a)' },
  converted_to_po:{ fg: 'var(--mark)',   bg: 'var(--teal-bg, #001f26)',  bd: 'var(--mark-hover, #1a5c70)' },
};

// ── Helpers ───────────────────────────────────────────────────────────────

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try { return new Date(iso).toISOString().slice(0, 10); } catch { return '—'; }
}

function fmtTotal(val: number | null | undefined, currency: string): string {
  if (val == null || val === 0) return '—';
  return `${currency} ${Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDept(dept: string): string {
  return dept ? dept.charAt(0).toUpperCase() + dept.slice(1) : '—';
}

function StatusPill({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.draft;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', height: 18,
      padding: '0 7px', borderRadius: 3, fontSize: 9.5, fontWeight: 600,
      letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap',
      color: c.fg, background: c.bg, border: `1px solid ${c.bd}`,
    }}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

function ShoppingListPageContent() {
  const router = useRouter();
  const { vesselId } = useActiveVessel();
  const { user } = useAuth();
  const yachtId = vesselId || user?.yachtId || '';

  const [rows, setRows] = React.useState<ShoppingListDoc[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchLists = React.useCallback(async () => {
    if (!yachtId) return;
    setLoading(true);
    setError(null);
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      const res = await fetch(`${API_BASE}/v1/shopping-list?yacht_id=${yachtId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Failed to load');
      setRows(json.data || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [yachtId]);

  React.useEffect(() => { fetchLists(); }, [fetchLists]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--surface-base)', minHeight: 0 }}>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 120 }}>
            <div style={{ width: 24, height: 24, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          </div>
        )}
        {!loading && error && (
          <div style={{ padding: 24, color: 'var(--red)', fontSize: 13, fontFamily: 'var(--font-sans)' }}>{error}</div>
        )}
        {!loading && !error && rows.length === 0 && (
          <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--txt3)', fontSize: 13, fontFamily: 'var(--font-sans)' }}>
            No shopping lists yet. Create the first one.
          </div>
        )}
        {!loading && !error && rows.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-sans)', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-sub)' }}>
                {['List #', 'Name', 'Dept', 'Status', 'Items', 'Est. Total', 'Created'].map(h => (
                  <th key={h} style={{
                    padding: '8px 12px', textAlign: 'left', fontSize: 10.5,
                    fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: 'var(--txt3)', fontFamily: 'var(--font-mono)',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr
                  key={row.id}
                  onClick={() => router.push(`/shopping-list/${row.id}`)}
                  style={{ borderBottom: '1px solid var(--border-faint)', cursor: 'pointer', transition: 'background 0.1s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt2)', whiteSpace: 'nowrap' }}>
                    {row.list_number}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--txt1)', fontWeight: 500, maxWidth: 280 }}>
                    {row.name}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--txt3)', fontSize: 12 }}>
                    {fmtDept(row.department)}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <StatusPill status={row.status} />
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--txt2)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    {row.item_count}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--txt2)', fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'nowrap' }}>
                    {fmtTotal(row.estimated_total, row.currency)}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'nowrap' }}>
                    {fmtDate(row.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}


export default function ShoppingListPage() {
  return (
    <React.Suspense fallback={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: 'var(--surface-base)' }}>
        <div style={{ width: 28, height: 28, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      </div>
    }>
      <ShoppingListPageContent />
    </React.Suspense>
  );
}
