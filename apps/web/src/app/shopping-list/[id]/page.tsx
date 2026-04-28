'use client';

import * as React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useActiveVessel } from '@/contexts/VesselContext';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';
import { API_BASE } from '@/lib/apiBase';
import { ActionPopup } from '@/components/lens/ActionPopup';

// ── Types ──────────────────────────────────────────────────────────────────

interface SLItem {
  id: string;
  part_name: string;
  part_number?: string;
  manufacturer?: string;
  is_candidate_part?: boolean;
  quantity_requested?: number;
  quantity_approved?: number;
  unit?: string;
  estimated_unit_price?: number;
  source_notes?: string;
  notes?: string;
  status: string;
  department?: string;
  shopping_list_id: string;
}

interface SLDoc {
  id: string;
  list_number: string;
  name: string;
  department: string;
  status: string;
  currency: string;
  estimated_total?: number;
  notes?: string;
  created_at: string;
  submitted_at?: string;
  approved_at?: string;
  converted_at?: string;
  converted_to_po_id?: string;
  items: SLItem[];
}

// ── Constants ──────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  submitted: 'Pending HOD Review',
  hod_approved: 'HOD Approved',
  converted_to_po: 'Converted to PO',
};

const STATUS_COLORS: Record<string, { fg: string; bg: string; bd: string }> = {
  draft:          { fg: 'var(--txt2)',   bg: 'var(--surface-hover)', bd: 'var(--border-sub)' },
  submitted:      { fg: 'var(--amber)',  bg: 'var(--amber-bg, #2a2000)', bd: 'var(--amber-border, #6b4e00)' },
  hod_approved:   { fg: 'var(--green)',  bg: 'var(--green-bg, #001a0d)', bd: 'var(--green-border, #004d1a)' },
  converted_to_po:{ fg: 'var(--mark)',   bg: 'var(--teal-bg, #001f26)',  bd: 'var(--mark-hover, #1a5c70)' },
};

const ITEM_STATUS_LABELS: Record<string, string> = {
  candidate: 'Candidate',
  under_review: 'Under Review',
  approved: 'Approved',
  rejected: 'Rejected',
  ordered: 'Ordered',
  partially_fulfilled: 'Part. Fulfilled',
  fulfilled: 'Fulfilled',
  installed: 'Installed',
};

const ITEM_STATUS_COLORS: Record<string, { fg: string }> = {
  candidate:          { fg: 'var(--txt3)' },
  under_review:       { fg: 'var(--amber)' },
  approved:           { fg: 'var(--green)' },
  rejected:           { fg: 'var(--red)' },
  ordered:            { fg: 'var(--mark)' },
  partially_fulfilled:{ fg: 'var(--mark)' },
  fulfilled:          { fg: 'var(--green)' },
  installed:          { fg: 'var(--green)' },
};

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtDate(iso?: string | null): string {
  if (!iso) return '—';
  try { return new Date(iso).toISOString().slice(0, 10); } catch { return '—'; }
}

function fmtPrice(val?: number | null, currency?: string): string {
  if (val == null) return '—';
  const prefix = currency ? `${currency} ` : '';
  return `${prefix}${Number(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtQty(val?: number | null): string {
  if (val == null) return '—';
  const n = Number(val);
  return n === Math.floor(n) ? String(Math.floor(n)) : n.toFixed(2);
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

function ItemStatusDot({ status }: { status: string }) {
  const c = ITEM_STATUS_COLORS[status] ?? { fg: 'var(--txt3)' };
  return (
    <span style={{ fontSize: 11, color: c.fg, fontWeight: 500 }}>
      {ITEM_STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ── Action popup types ─────────────────────────────────────────────────────

type ActiveAction =
  | { type: 'add_item' }
  | { type: 'update_item'; item: SLItem }
  | { type: 'delete_item'; item: SLItem }
  | { type: 'hod_review'; item: SLItem }
  | { type: 'submit' }
  | { type: 'approve' };

// ── Main page ──────────────────────────────────────────────────────────────

function ShoppingListDocContent({ listId }: { listId: string }) {
  const router = useRouter();
  const { vesselId } = useActiveVessel();
  const { user } = useAuth();
  const yachtId = vesselId || user?.yachtId || '';
  const role = user?.role || 'crew';

  const [doc, setDoc] = React.useState<SLDoc | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [action, setAction] = React.useState<ActiveAction | null>(null);
  const [actionSubmitting, setActionSubmitting] = React.useState(false);
  const [actionErr, setActionErr] = React.useState<string | null>(null);

  const fetchDoc = React.useCallback(async () => {
    if (!yachtId || !listId) return;
    setLoading(true);
    setError(null);
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      const res = await fetch(`${API_BASE}/v1/shopping-list/${listId}?yacht_id=${yachtId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const json = await res.json();
      if (!res.ok || json.status === 'error') throw new Error(json.detail || json.message || 'Failed');
      setDoc(json.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [yachtId, listId]);

  React.useEffect(() => { fetchDoc(); }, [fetchDoc]);

  const execAction = React.useCallback(async (actionId: string, payload: Record<string, unknown>) => {
    setActionSubmitting(true);
    setActionErr(null);
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      if (!token) { setActionErr('Not authenticated'); return; }
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          action: actionId,
          context: { yacht_id: yachtId },
          payload,
        }),
      });
      const json = await res.json();
      if (!res.ok || json.status === 'error') { setActionErr(json.message || 'Action failed'); return; }
      setAction(null);
      fetchDoc();
    } catch (e) {
      setActionErr(e instanceof Error ? e.message : 'Network error');
    } finally {
      setActionSubmitting(false);
    }
  }, [yachtId, fetchDoc]);

  const isHod = ['chief_engineer', 'chief_officer', 'captain', 'manager'].includes(role);
  const isDraft = doc?.status === 'draft';
  const isSubmitted = doc?.status === 'submitted';
  const isHodApproved = doc?.status === 'hod_approved';
  const isConverted = doc?.status === 'converted_to_po';

  // ── Estimated total from items ─────────────────────────────────────────
  const estimatedTotal = React.useMemo(() => {
    if (!doc?.items) return null;
    let sum = 0;
    let hasAny = false;
    for (const it of doc.items) {
      if (it.estimated_unit_price != null) {
        const qty = it.quantity_approved ?? it.quantity_requested ?? 0;
        sum += Number(it.estimated_unit_price) * Number(qty);
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  }, [doc?.items]);

  // ── Render popup for active action ────────────────────────────────────
  const renderPopup = () => {
    if (!action || !doc) return null;

    const close = () => { setAction(null); setActionErr(null); };

    if (action.type === 'add_item') {
      return (
        <ActionPopup
          mode="mutate"
          title="Add Item to List"
          subtitle={`Adding to ${doc.list_number} — ${doc.name}`}
          fields={[
            { name: 'part_name', label: 'Item / Part Name', type: 'kv-edit', placeholder: 'e.g. Fuel filter 20μm', required: true },
            { name: 'quantity_requested', label: 'Qty', type: 'kv-edit', placeholder: '1', required: true },
            { name: 'unit', label: 'Unit', type: 'kv-edit', placeholder: 'pcs, L, kg…' },
            { name: 'unit_price', label: `Unit Price (${doc.currency})`, type: 'kv-edit', placeholder: '0.00' },
            { name: 'part_number', label: 'Part Number', type: 'kv-edit', placeholder: 'MAN-12345' },
            { name: 'manufacturer', label: 'Manufacturer', type: 'kv-edit', placeholder: 'Volvo, Parker…' },
            { name: 'source_notes', label: 'Notes', type: 'text-area', placeholder: 'Why is this needed?' },
          ]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Adding…' : 'Add Item'}
          submitDisabled={actionSubmitting}
          previewRows={actionErr ? [{ key: 'Error', value: actionErr }] : undefined}
          onSubmit={async (vals) => {
            await execAction('add_item_to_list', {
              shopping_list_id: listId,
              part_name: vals.part_name,
              quantity_requested: Number(vals.quantity_requested) || 1,
              unit: vals.unit || undefined,
              unit_price: vals.unit_price ? Number(vals.unit_price) : undefined,
              part_number: vals.part_number || undefined,
              manufacturer: vals.manufacturer || undefined,
              source_notes: vals.source_notes || undefined,
              source_type: 'manual_add',
            });
          }}
          onClose={close}
        />
      );
    }

    if (action.type === 'update_item') {
      const it = action.item;
      return (
        <ActionPopup
          mode="mutate"
          title="Edit Line Item"
          subtitle={it.part_name}
          fields={[
            { name: 'quantity_requested', label: 'Quantity', type: 'kv-edit', placeholder: String(it.quantity_requested ?? 1) },
            { name: 'unit_price', label: `Unit Price (${doc.currency})`, type: 'kv-edit', placeholder: String(it.estimated_unit_price ?? '') },
            { name: 'source_notes', label: 'Notes', type: 'text-area', placeholder: it.source_notes || it.notes || '' },
          ]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Saving…' : 'Save Changes'}
          submitDisabled={actionSubmitting}
          previewRows={actionErr ? [{ key: 'Error', value: actionErr }] : undefined}
          onSubmit={async (vals) => {
            await execAction('update_list_item', {
              item_id: it.id,
              quantity_requested: vals.quantity_requested ? Number(vals.quantity_requested) : undefined,
              unit_price: vals.unit_price ? Number(vals.unit_price) : undefined,
              source_notes: vals.source_notes || undefined,
            });
          }}
          onClose={close}
        />
      );
    }

    if (action.type === 'delete_item') {
      const it = action.item;
      return (
        <ActionPopup
          mode="mutate"
          title="Remove Item"
          subtitle={`Remove "${it.part_name}" from this list?`}
          fields={[]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Removing…' : 'Remove Item'}
          submitDisabled={actionSubmitting}
          previewRows={actionErr ? [{ key: 'Error', value: actionErr }] : undefined}
          onSubmit={async () => {
            await execAction('delete_list_item', { item_id: it.id });
          }}
          onClose={close}
        />
      );
    }

    if (action.type === 'hod_review') {
      const it = action.item;
      return (
        <ActionPopup
          mode="mutate"
          title="Review Item"
          subtitle={it.part_name}
          fields={[
            { name: 'decision', label: 'Decision', type: 'select', options: [
              { value: 'approved', label: 'Approve' },
              { value: 'rejected', label: 'Reject' },
            ], required: true },
            { name: 'quantity_approved', label: 'Approved Qty (leave blank = requested qty)', type: 'kv-edit', placeholder: String(it.quantity_requested ?? '') },
            { name: 'reject_reason', label: 'Rejection Reason (if rejecting)', type: 'text-area', placeholder: 'Out of budget, duplicate…' },
          ]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Saving…' : 'Submit Decision'}
          submitDisabled={actionSubmitting}
          previewRows={actionErr ? [{ key: 'Error', value: actionErr }] : undefined}
          onSubmit={async (vals) => {
            await execAction('hod_review_list_item', {
              item_id: it.id,
              decision: vals.decision,
              quantity_approved: vals.quantity_approved ? Number(vals.quantity_approved) : undefined,
              reject_reason: vals.reject_reason || undefined,
            });
          }}
          onClose={close}
        />
      );
    }

    if (action.type === 'submit') {
      return (
        <ActionPopup
          mode="mutate"
          title="Submit for HOD Review"
          subtitle={`Submit ${doc.list_number} — ${doc.name}?`}
          fields={[]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Submitting…' : 'Submit List'}
          submitDisabled={actionSubmitting}
          previewRows={[
            { key: 'List', value: `${doc.list_number} — ${doc.name}` },
            { key: 'Items', value: String(doc.items.length) },
            ...(actionErr ? [{ key: 'Error', value: actionErr }] : []),
          ]}
          onSubmit={async () => {
            await execAction('submit_shopping_list', { shopping_list_id: listId });
          }}
          onClose={close}
        />
      );
    }

    if (action.type === 'approve') {
      const approved = doc.items.filter(i => i.status === 'approved').length;
      const total = doc.items.length;
      return (
        <ActionPopup
          mode="mutate"
          title="Approve Entire List"
          subtitle={`Approve ${doc.list_number} — ${doc.name}?`}
          fields={[]}
          signatureLevel={1}
          submitLabel={actionSubmitting ? 'Approving…' : 'Approve List'}
          submitDisabled={actionSubmitting}
          previewRows={[
            { key: 'Items approved', value: `${approved} / ${total}` },
            { key: 'Remaining', value: `${total - approved} items will be auto-approved` },
            ...(actionErr ? [{ key: 'Error', value: actionErr }] : []),
          ]}
          onSubmit={async () => {
            await execAction('approve_shopping_list', { shopping_list_id: listId });
          }}
          onClose={close}
        />
      );
    }

    return null;
  };

  // ── Loading / error ────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: 'var(--surface-base)' }}>
        <div style={{ width: 28, height: 28, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, background: 'var(--surface-base)' }}>
        <span style={{ color: 'var(--red)', fontSize: 13, fontFamily: 'var(--font-sans)' }}>{error ?? 'Not found'}</span>
        <button onClick={() => router.push('/shopping-list')} style={{ color: 'var(--mark)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}>
          ← Back to lists
        </button>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--surface-base)', minHeight: 0, fontFamily: 'var(--font-sans)' }}>

      {/* Identity strip */}
      <div style={{
        padding: '16px 24px 0', borderBottom: '1px solid var(--border-sub)',
        flexShrink: 0,
      }}>
        {/* Back + number row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={() => router.push('/shopping-list')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--txt3)', fontSize: 12, fontFamily: 'var(--font-mono)', padding: 0 }}
            >
              ← Lists
            </button>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--txt3)', letterSpacing: '0.05em' }}>
              {doc.list_number}
            </span>
            <StatusPill status={doc.status} />
          </div>

          {/* Primary action */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {/* PDF export — always available */}
            <a
              href={`${API_BASE}/v1/shopping-list/${listId}/pdf?yacht_id=${yachtId}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '6px 12px', border: '1px solid var(--border-sub)',
                borderRadius: 6, fontSize: 12, fontWeight: 500, color: 'var(--txt2)',
                textDecoration: 'none', background: 'var(--surface)',
              }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 1v7M3 6l3 3 3-3M1 10h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Export PDF
            </a>

            {isDraft && (
              <button
                onClick={() => setAction({ type: 'submit' })}
                style={{ padding: '6px 14px', background: 'var(--mark)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Submit for Review
              </button>
            )}
            {isSubmitted && isHod && (
              <button
                onClick={() => setAction({ type: 'approve' })}
                style={{ padding: '6px 14px', background: 'var(--green, #009933)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Approve List
              </button>
            )}
            {isHodApproved && isHod && (
              <button
                onClick={() => {
                  // convert_to_po — PURCHASE05-owned action
                  execAction('convert_to_po', { shopping_list_id: listId });
                }}
                style={{ padding: '6px 14px', background: 'var(--mark)', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                Convert to PO
              </button>
            )}
            {isConverted && doc.converted_to_po_id && (
              <button
                onClick={() => router.push(`/purchase-orders/${doc.converted_to_po_id}`)}
                style={{ padding: '6px 14px', background: 'none', border: '1px solid var(--mark)', color: 'var(--mark)', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}
              >
                View PO →
              </button>
            )}
          </div>
        </div>

        {/* Title */}
        <h1 style={{ margin: '0 0 8px', fontSize: 22, fontWeight: 600, color: 'var(--txt1)', lineHeight: 1.2 }}>
          {doc.name}
        </h1>

        {/* Meta row */}
        <div style={{ display: 'flex', gap: 20, paddingBottom: 14, fontSize: 12, color: 'var(--txt3)' }}>
          <span>{doc.department ? doc.department.charAt(0).toUpperCase() + doc.department.slice(1) : 'General'}</span>
          <span>·</span>
          <span>{doc.currency}</span>
          <span>·</span>
          <span>Created {fmtDate(doc.created_at)}</span>
          {doc.submitted_at && <><span>·</span><span>Submitted {fmtDate(doc.submitted_at)}</span></>}
          {doc.approved_at && <><span>·</span><span>Approved {fmtDate(doc.approved_at)}</span></>}
          {doc.notes && <><span>·</span><span style={{ color: 'var(--txt2)', fontStyle: 'italic' }}>{doc.notes}</span></>}
        </div>
      </div>

      {/* Items section */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>

        {/* Section header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 24px 8px',
          borderTop: '1px solid var(--border-sub)',
          marginTop: 0,
        }}>
          <span style={{ fontSize: 10.5, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--txt3)' }}>
            Line Items ({doc.items.length})
          </span>
          {(isDraft || isSubmitted) && (
            <button
              onClick={() => setAction({ type: 'add_item' })}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mark)', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-sans)' }}
            >
              + Add Item
            </button>
          )}
        </div>

        {doc.items.length === 0 ? (
          <div style={{ padding: '32px 24px', color: 'var(--txt3)', fontSize: 13, textAlign: 'center' }}>
            No items yet. Add the first item to this list.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-sub)' }}>
                {['#', 'Part Name', 'Part No.', 'Qty Req', 'Qty Appr', 'Unit', 'Unit Price', 'Total', 'Status', ''].map((h, i) => (
                  <th key={i} style={{
                    padding: '6px 12px', textAlign: i >= 3 && i <= 7 ? 'right' : 'left',
                    fontSize: 10, fontWeight: 600, letterSpacing: '0.06em',
                    textTransform: 'uppercase', color: 'var(--txt3)',
                    fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {doc.items.map((item, idx) => {
                const rowTotal = item.estimated_unit_price != null
                  ? Number(item.estimated_unit_price) * Number(item.quantity_approved ?? item.quantity_requested ?? 0)
                  : null;
                const isCandidate = !!item.is_candidate_part;
                return (
                  <tr
                    key={item.id}
                    style={{ borderBottom: '1px solid var(--border-faint)', background: idx % 2 === 1 ? 'var(--surface, transparent)' : 'transparent' }}
                  >
                    <td style={{ padding: '9px 12px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', fontSize: 11, width: 32 }}>
                      {idx + 1}
                    </td>
                    <td style={{ padding: '9px 12px', color: isCandidate ? 'var(--amber)' : 'var(--txt1)', fontWeight: 500, maxWidth: 240 }}>
                      {isCandidate && <span title="Candidate part — not yet in catalogue" style={{ marginRight: 4 }}>⚠</span>}
                      {item.part_name}
                      {(item.source_notes || item.notes) && (
                        <div style={{ fontSize: 10.5, color: 'var(--txt3)', fontWeight: 400, marginTop: 2 }}>{item.source_notes || item.notes}</div>
                      )}
                    </td>
                    <td style={{ padding: '9px 12px', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                      {item.part_number || '—'}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt2)' }}>
                      {fmtQty(item.quantity_requested)}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: item.quantity_approved != null ? 'var(--txt1)' : 'var(--txt3)' }}>
                      {fmtQty(item.quantity_approved)}
                    </td>
                    <td style={{ padding: '9px 12px', color: 'var(--txt3)', fontSize: 11 }}>
                      {item.unit || '—'}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt2)' }}>
                      {item.estimated_unit_price != null ? fmtPrice(item.estimated_unit_price) : '—'}
                    </td>
                    <td style={{ padding: '9px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt2)', fontWeight: 500 }}>
                      {rowTotal != null ? fmtPrice(rowTotal) : '—'}
                    </td>
                    <td style={{ padding: '9px 12px' }}>
                      <ItemStatusDot status={item.status} />
                    </td>
                    {/* Row actions */}
                    <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {isDraft && (
                          <>
                            <button
                              onClick={() => setAction({ type: 'update_item', item })}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-sans)', padding: 0 }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => setAction({ type: 'delete_item', item })}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--red)', fontSize: 11, fontFamily: 'var(--font-sans)', padding: 0 }}
                            >
                              Remove
                            </button>
                          </>
                        )}
                        {isSubmitted && isHod && item.status !== 'approved' && item.status !== 'rejected' && (
                          <button
                            onClick={() => setAction({ type: 'hod_review', item })}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mark)', fontSize: 11, fontFamily: 'var(--font-sans)', padding: 0 }}
                          >
                            Review
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* Totals footer */}
        {doc.items.length > 0 && (
          <div style={{
            display: 'flex', justifyContent: 'flex-end',
            padding: '12px 24px', borderTop: '1px solid var(--border-sub)',
            gap: 16,
          }}>
            <span style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-sans)' }}>
              Estimated Total
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt1)', fontFamily: 'var(--font-mono)' }}>
              {estimatedTotal != null ? fmtPrice(estimatedTotal, doc.currency) : '—'}
            </span>
          </div>
        )}
      </div>

      {/* Action popup overlay */}
      {renderPopup()}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function ShoppingListDetailPage() {
  const params = useParams();
  const listId = params.id as string;
  return (
    <React.Suspense fallback={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: 'var(--surface-base)' }}>
        <div style={{ width: 28, height: 28, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    }>
      <ShoppingListDocContent listId={listId} />
    </React.Suspense>
  );
}
