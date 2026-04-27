'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useActiveVessel } from '@/contexts/VesselContext';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { API_BASE } from '@/lib/apiBase';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';

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
  const [showCreate, setShowCreate] = React.useState(false);

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

  const handleCreated = React.useCallback(() => {
    setShowCreate(false);
    fetchLists();
  }, [fetchLists]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--surface-base)', minHeight: 0 }}>

      {/* Subbar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px', height: 44, borderBottom: '1px solid var(--border-sub)',
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt1)', fontFamily: 'var(--font-sans)' }}>
          Shopping Lists
        </span>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', background: 'var(--mark)', color: '#fff',
            border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600,
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          New List
        </button>
      </div>

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

      {/* Create modal */}
      {showCreate && (
        <CreateListModal
          yachtId={yachtId}
          onClose={() => setShowCreate(false)}
          onSuccess={handleCreated}
        />
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Create list modal ─────────────────────────────────────────────────────

function CreateListModal({
  yachtId,
  onClose,
  onSuccess,
}: {
  yachtId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [submitting, setSubmitting] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);

  const handleSubmit = React.useCallback(async (values: Record<string, unknown>) => {
    if (!yachtId) { setErr('No vessel selected'); return; }
    setSubmitting(true);
    setErr(null);
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      if (!token) { setErr('Not authenticated'); return; }
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          action: 'create_shopping_list',
          context: { yacht_id: yachtId },
          payload: {
            name: values.name,
            department: values.department || 'general',
            currency: values.currency || 'EUR',
            notes: values.notes || undefined,
          },
        }),
      });
      const json = await res.json();
      if (!res.ok || json.status === 'error') { setErr(json.message || 'Failed'); return; }
      onSuccess();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  }, [yachtId, onSuccess]);

  return (
    <ActionPopup
      mode="mutate"
      title="New Shopping List"
      subtitle="Create a named requisition document. Add items after creation."
      fields={[
        { name: 'name', label: 'List Name', type: 'kv-edit', placeholder: 'e.g. Engine Stores Run — May 2026', required: true },
        { name: 'department', label: 'Department', type: 'select', options: [
          { value: 'general', label: 'General' },
          { value: 'engine', label: 'Engine' },
          { value: 'deck', label: 'Deck' },
          { value: 'galley', label: 'Galley' },
          { value: 'interior', label: 'Interior' },
          { value: 'bridge', label: 'Bridge' },
        ]},
        { name: 'currency', label: 'Currency', type: 'select', options: [
          { value: 'EUR', label: 'EUR — Euro' },
          { value: 'USD', label: 'USD — US Dollar' },
          { value: 'GBP', label: 'GBP — British Pound' },
          { value: 'AED', label: 'AED — UAE Dirham' },
          { value: 'MED', label: 'USD — Med Charter' },
        ]},
        { name: 'notes', label: 'Notes (optional)', type: 'text-area', placeholder: 'Context for this shopping run...' },
      ]}
      signatureLevel={1}
      submitLabel={submitting ? 'Creating…' : 'Create List'}
      submitDisabled={submitting}
      previewRows={err ? [{ key: 'Error', value: err }] : undefined}
      onSubmit={handleSubmit}
      onClose={onClose}
    />
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
