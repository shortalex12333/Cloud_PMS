'use client';

import * as React from 'react';
import { API_BASE } from '@/lib/apiBase';

// ── AddPartModal ─────────────────────────────────────────────────────────────

export interface PartRecord {
  id: string;
  name: string;
  part_number?: string;
  quantity_on_hand?: number;
  location?: string;
}

export function AddPartModal({
  open,
  onClose,
  yachtId,
  token,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  yachtId: string;
  token: string;
  onSubmit: (partId: string, quantity: number) => Promise<void>;
}) {
  const [parts, setParts] = React.useState<PartRecord[]>([]);
  const [search, setSearch] = React.useState('');
  const [selected, setSelected] = React.useState<PartRecord | null>(null);
  const [quantity, setQuantity] = React.useState(1);
  const [loading, setLoading] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!open || !token || !yachtId) return;
    setLoading(true);
    setSelected(null);
    setSearch('');
    setQuantity(1);
    fetch(`${API_BASE}/v1/${yachtId}/domain/parts/records?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => setParts((d.records ?? []) as PartRecord[]))
      .catch(() => setParts([]))
      .finally(() => setLoading(false));
  }, [open, token, yachtId]);

  if (!open) return null;

  const filtered = parts.filter(
    (p) =>
      !search ||
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.part_number?.toLowerCase().includes(search.toLowerCase()),
  );

  const handleSubmit = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await onSubmit(selected.id, quantity);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'var(--overlay-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--surface)', borderRadius: 10, padding: 24,
        width: 420, maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        border: '1px solid var(--border-sub)', boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          Add Part to Work Order
        </div>
        <input
          placeholder="Search by name or part number…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'var(--bg)', color: 'var(--txt)', fontSize: 13,
            marginBottom: 8, fontFamily: 'var(--font-sans)',
          }}
        />
        {loading ? (
          <div style={{ color: 'var(--txt3)', fontSize: 13, padding: '12px 0' }}>Loading parts…</div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-faint)', borderRadius: 6, marginBottom: 12 }}>
            {filtered.length === 0 ? (
              <div style={{ padding: 12, color: 'var(--txt3)', fontSize: 13 }}>No parts found.</div>
            ) : filtered.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelected(p)}
                style={{
                  width: '100%', textAlign: 'left', padding: '10px 12px',
                  background: selected?.id === p.id ? 'var(--teal-bg)' : 'transparent',
                  border: 'none', borderBottom: '1px solid var(--border-faint)',
                  cursor: 'pointer', color: 'var(--txt)', fontSize: 13,
                  fontFamily: 'var(--font-sans)',
                }}
              >
                <div style={{ fontWeight: 500 }}>{p.name}</div>
                {p.part_number && (
                  <div style={{ fontSize: 11, color: 'var(--txt3)' }}>
                    {p.part_number}{p.quantity_on_hand != null ? ` · Stock: ${p.quantity_on_hand}` : ''}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
        {selected && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <label style={{ fontSize: 13, color: 'var(--txt2)', whiteSpace: 'nowrap' }}>Qty:</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              style={{
                width: 72, padding: '6px 8px', borderRadius: 6,
                border: '1px solid var(--border-sub)', background: 'var(--bg)',
                color: 'var(--txt)', fontSize: 13, fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!selected || submitting}
            style={{
              padding: '8px 14px', borderRadius: 6, border: 'none',
              background: selected ? 'var(--mark)' : 'var(--border-faint)',
              color: selected ? 'var(--surface)' : 'var(--txt3)',
              fontSize: 13, cursor: selected ? 'pointer' : 'not-allowed',
              fontFamily: 'var(--font-sans)', fontWeight: 500,
            }}
          >
            {submitting ? 'Adding…' : 'Add Part'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AssignModal ──────────────────────────────────────────────────────────────

export function AssignModal({
  open,
  onClose,
  yachtId: _yachtId,
  token: _token,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  yachtId: string;
  token: string;
  onSubmit: (userId: string) => Promise<void>;
}) {
  const [userId, setUserId] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) setUserId('');
  }, [open]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!userId.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(userId.trim());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'var(--overlay-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: 'var(--surface)', borderRadius: 10, padding: 24,
        width: 360, border: '1px solid var(--border-sub)',
        boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          Assign Work Order
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 6 }}>
          User ID (crew member)
        </label>
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Paste crew member user ID…"
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!userId.trim() || submitting}
            style={{
              padding: '8px 14px', borderRadius: 6, border: 'none',
              background: userId.trim() ? 'var(--mark)' : 'var(--border-faint)',
              color: userId.trim() ? 'var(--surface)' : 'var(--txt3)',
              fontSize: 13, cursor: userId.trim() ? 'pointer' : 'not-allowed',
              fontFamily: 'var(--font-sans)', fontWeight: 500,
            }}
          >
            {submitting ? 'Assigning…' : 'Assign'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── AddChecklistItemModal ────────────────────────────────────────────────────

export function AddChecklistItemModal({
  open,
  category,
  onClose,
  onSubmit,
}: {
  open: boolean;
  category: 'general' | 'safety';
  onClose: () => void;
  onSubmit: (title: string, description: string) => Promise<void>;
}) {
  const [itemTitle, setItemTitle] = React.useState('');
  const [itemDesc, setItemDesc] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setItemTitle(''); setItemDesc(''); setSubmitting(false); }
  }, [open]);

  if (!open) return null;

  const isSafety = category === 'safety';
  const placeholder = isSafety ? 'e.g. Lock out breaker 17B' : 'e.g. Inspect filter housing';

  const handleSubmit = async () => {
    if (!itemTitle.trim() || submitting) return;
    setSubmitting(true);
    try { await onSubmit(itemTitle.trim(), itemDesc.trim()); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 420, background: 'var(--surface)',
        border: '1px solid var(--border-faint)', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 16 }}>
          {isSafety ? 'Add Safety Checkpoint' : 'Add Checklist Item'}
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Title <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <input
          value={itemTitle}
          onChange={(e) => setItemTitle(e.target.value)}
          placeholder={placeholder}
          autoFocus
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 14,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Guidance / Instructions <span style={{ color: 'var(--txt3)', fontWeight: 400 }}>(optional)</span>
        </label>
        <textarea
          value={itemDesc}
          onChange={(e) => setItemDesc(e.target.value)}
          placeholder={isSafety ? 'Isolation steps, test-for-dead procedure…' : 'Additional guidance…'}
          rows={3}
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16, resize: 'vertical',
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!itemTitle.trim() || submitting} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: itemTitle.trim() ? 'var(--mark)' : 'var(--border-faint)',
            color: itemTitle.trim() ? 'var(--surface)' : 'var(--txt3)',
            fontSize: 13, cursor: itemTitle.trim() ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Adding…' : 'Add Item'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── EditSOPModal ─────────────────────────────────────────────────────────────

export function EditSOPModal({
  open,
  current,
  onClose,
  onSubmit,
}: {
  open: boolean;
  current: string;
  onClose: () => void;
  onSubmit: (text: string) => Promise<void>;
}) {
  const [text, setText] = React.useState(current);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setText(current); setSubmitting(false); }
  }, [open, current]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try { await onSubmit(text); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 520, background: 'var(--surface)',
        border: '1px solid var(--border-faint)', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 8 }}>
          Standard Operating Procedure
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', marginBottom: 14 }}>
          Describe the step-by-step procedure. Leave blank to clear.
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="1. Isolate system&#10;2. Verify de-energised&#10;3. ..."
          rows={8}
          autoFocus
          style={{
            width: '100%', padding: '10px 12px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16, resize: 'vertical',
            fontFamily: 'var(--font-mono)', lineHeight: 1.6, boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={submitting} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: 'var(--mark)', color: 'var(--surface)',
            fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Saving…' : 'Save SOP'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ArchiveWorkOrderModal ────────────────────────────────────────────────────

export function ArchiveWorkOrderModal({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string, signature: string) => Promise<void>;
}) {
  const [reason, setReason] = React.useState('');
  const [signature, setSignature] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) { setReason(''); setSignature(''); setSubmitting(false); }
  }, [open]);

  if (!open) return null;

  const canSubmit = reason.trim().length > 3 && signature.trim().length > 2 && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try { await onSubmit(reason.trim(), signature.trim()); }
    finally { setSubmitting(false); }
  };

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--overlay-heavy)',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: '100%', maxWidth: 420, background: 'var(--surface)',
        border: '1px solid var(--red-border, var(--border-faint))', borderRadius: 10,
        padding: 24, boxShadow: 'var(--shadow-card)',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--red)', marginBottom: 8 }}>
          Archive Work Order
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', marginBottom: 16 }}>
          This action is permanent. The work order will be soft-deleted and removed
          from active views. Type your full name to confirm.
        </div>
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Reason for archiving <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Duplicate entry created in error"
          rows={3}
          autoFocus
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 14, resize: 'vertical',
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <label style={{ fontSize: 13, color: 'var(--txt2)', display: 'block', marginBottom: 4 }}>
          Your full name (signature) <span style={{ color: 'var(--red)' }}>*</span>
        </label>
        <input
          value={signature}
          onChange={(e) => setSignature(e.target.value)}
          placeholder="Type your full name to confirm"
          style={{
            width: '100%', padding: '8px 10px', borderRadius: 6,
            border: '1px solid var(--border-sub)', background: 'var(--bg)',
            color: 'var(--txt)', fontSize: 13, marginBottom: 16,
            fontFamily: 'var(--font-sans)', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!canSubmit} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: canSubmit ? 'var(--red)' : 'var(--border-faint)',
            color: canSubmit ? 'white' : 'var(--txt3)',
            fontSize: 13, cursor: canSubmit ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Archiving…' : 'Archive'}
          </button>
        </div>
      </div>
    </div>
  );
}
