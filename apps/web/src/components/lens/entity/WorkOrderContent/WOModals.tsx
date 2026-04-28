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
    fetch(`${API_BASE}/api/vessel/${yachtId}/domain/parts/records?limit=200`, {
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

export interface ChecklistRowItem {
  id: string;
  description: string;
  itemType: 'tick' | 'text';
}

export function AddChecklistItemModal({
  open,
  category,
  onClose,
  onSubmit,
}: {
  open: boolean;
  category: 'general' | 'safety';
  onClose: () => void;
  onSubmit: (items: ChecklistRowItem[]) => Promise<void>;
}) {
  const [rows, setRows] = React.useState<ChecklistRowItem[]>([
    { id: '1', description: '', itemType: 'tick' },
  ]);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setRows([{ id: '1', description: '', itemType: 'tick' }]);
      setSubmitting(false);
    }
  }, [open]);

  if (!open) return null;

  const isSafety = category === 'safety';
  const placeholder = isSafety ? 'e.g. Lock out breaker 17B' : 'e.g. Inspect filter housing';

  const updateRow = (id: string, field: keyof ChecklistRowItem, value: string) => {
    setRows((prev) => {
      const updated = prev.map((r) => r.id === id ? { ...r, [field]: value } : r);
      const last = updated[updated.length - 1];
      if (last.id === id && field === 'description' && value.trim()) {
        return [...updated, { id: String(Date.now()), description: '', itemType: 'tick' as const }];
      }
      return updated;
    });
  };

  const removeRow = (id: string) => {
    setRows((prev) => prev.length > 1 ? prev.filter((r) => r.id !== id) : prev);
  };

  const validRows = rows.filter((r) => r.description.trim());

  const handleSubmit = async () => {
    if (!validRows.length || submitting) return;
    setSubmitting(true);
    try { await onSubmit(validRows); }
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
        maxHeight: '80vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--txt)', marginBottom: 4 }}>
          {isSafety ? 'Add Safety Checkpoints' : 'Add Checklist Items'}
        </div>
        <div style={{ fontSize: 12, color: 'var(--txt3)', marginBottom: 16 }}>
          Type an item — a new row appears automatically.
        </div>

        <div style={{ overflowY: 'auto', flex: 1, marginBottom: 16 }}>
          {rows.map((row, idx) => (
            <div key={row.id} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--txt3)', minWidth: 18, textAlign: 'right' }}>
                {idx + 1}
              </span>
              <input
                value={row.description}
                onChange={(e) => updateRow(row.id, 'description', e.target.value)}
                placeholder={idx === 0 ? placeholder : 'Next item…'}
                autoFocus={idx === 0}
                style={{
                  flex: 1, padding: '7px 10px', borderRadius: 6,
                  border: '1px solid var(--border-sub)', background: 'var(--bg)',
                  color: 'var(--txt)', fontSize: 13, fontFamily: 'var(--font-sans)',
                }}
              />
              <select
                value={row.itemType}
                onChange={(e) => updateRow(row.id, 'itemType', e.target.value)}
                style={{
                  padding: '7px 8px', borderRadius: 6, fontSize: 12,
                  border: '1px solid var(--border-sub)', background: 'var(--bg)',
                  color: 'var(--txt2)', fontFamily: 'var(--font-sans)', cursor: 'pointer',
                }}
              >
                <option value="tick">Tick</option>
                <option value="text">Text</option>
              </select>
              {rows.length > 1 && (
                <button type="button" onClick={() => removeRow(row.id)} style={{
                  background: 'none', border: 'none', color: 'var(--txt3)',
                  cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: '0 2px',
                }}>×</button>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!validRows.length || submitting} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: validRows.length ? 'var(--mark)' : 'var(--border-faint)',
            color: validRows.length ? 'var(--surface)' : 'var(--txt3)',
            fontSize: 13, cursor: validRows.length ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Adding…' : validRows.length > 1 ? `Add ${validRows.length} Items` : 'Add Item'}
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

// ── SetFrequencyModal ────────────────────────────────────────────────────────

export function SetFrequencyModal({
  open,
  currentFrequency,
  currentDueDate,
  onClose,
  onSubmit,
}: {
  open: boolean;
  currentFrequency?: number | null;
  currentDueDate?: string | null;
  onClose: () => void;
  onSubmit: (frequency: number, dueDate: string) => Promise<void>;
}) {
  const [frequency, setFrequency] = React.useState<string>(currentFrequency ? String(currentFrequency) : '');
  const [dueDate, setDueDate] = React.useState<string>(currentDueDate ?? '');
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState('');

  React.useEffect(() => {
    if (open) {
      setFrequency(currentFrequency ? String(currentFrequency) : '');
      setDueDate(currentDueDate ?? '');
      setError('');
    }
  }, [open, currentFrequency, currentDueDate]);

  const PRESETS = [
    { label: 'Daily', days: 1 },
    { label: 'Weekly', days: 7 },
    { label: 'Monthly', days: 30 },
    { label: 'Quarterly', days: 90 },
    { label: 'Annual', days: 365 },
  ];

  const freqNum = parseFloat(frequency);
  const canSubmit = !submitting && !isNaN(freqNum) && freqNum > 0 && dueDate.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError('');
    try {
      await onSubmit(freqNum, dueDate);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to set frequency');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  const labelStyle: React.CSSProperties = { fontSize: 12, fontWeight: 500, color: 'var(--txt2)',
    marginBottom: 4, display: 'block', fontFamily: 'var(--font-sans)' };
  const inputStyle: React.CSSProperties = { width: '100%', padding: '7px 10px', fontSize: 13,
    borderRadius: 6, border: '1px solid var(--border-sub)', background: 'var(--surface)',
    color: 'var(--txt)', fontFamily: 'var(--font-sans)', outline: 'none', boxSizing: 'border-box' };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'var(--surface)', borderRadius: 10, padding: 24, width: 360,
        boxShadow: '0 8px 32px rgba(0,0,0,0.18)', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--txt)', fontFamily: 'var(--font-sans)' }}>
          Set Frequency
        </div>

        {/* Presets */}
        <div>
          <label style={labelStyle}>Quick select</label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {PRESETS.map((p) => (
              <button key={p.days} type="button"
                onClick={() => setFrequency(String(p.days))}
                style={{ padding: '4px 10px', borderRadius: 4, fontSize: 11,
                  border: '1px solid var(--border-sub)', cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                  background: parseFloat(frequency) === p.days ? 'var(--mark)' : 'transparent',
                  color: parseFloat(frequency) === p.days ? 'var(--on-mark, #fff)' : 'var(--txt2)' }}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom days */}
        <div>
          <label style={labelStyle}>Frequency / days</label>
          <input style={inputStyle} type="number" min="1" step="1"
            placeholder="e.g. 14 (fortnightly)"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value)} />
          <div style={{ fontSize: 11, color: 'var(--txt3)', marginTop: 3, fontFamily: 'var(--font-sans)' }}>
            {freqNum > 0 ? `Next WO due ${freqNum} days after completion` : 'Enter number of days'}
          </div>
        </div>

        {/* Due date */}
        <div>
          <label style={labelStyle}>Due date / {currentDueDate ?? 'not set'}</label>
          <input style={inputStyle} type="date" value={dueDate}
            onChange={(e) => setDueDate(e.target.value)} />
        </div>

        {error && <div style={{ fontSize: 12, color: 'var(--red)', fontFamily: 'var(--font-sans)' }}>{error}</div>}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={{
            padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>Cancel</button>
          <button type="button" onClick={handleSubmit} disabled={!canSubmit} style={{
            padding: '8px 14px', borderRadius: 6, border: 'none',
            background: canSubmit ? 'var(--mark)' : 'var(--border-faint)',
            color: canSubmit ? 'var(--on-mark, #fff)' : 'var(--txt3)',
            fontSize: 13, cursor: canSubmit ? 'pointer' : 'not-allowed',
            fontFamily: 'var(--font-sans)', fontWeight: 500,
          }}>
            {submitting ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── WOFaultLinkModal ──────────────────────────────────────────────────────────

export interface FaultRecord {
  id: string;
  fault_code?: string;
  title?: string;
  status?: string;
  severity?: string;
}

export function WOFaultLinkModal({
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
  onSubmit: (faultId: string) => Promise<void>;
}) {
  const [faults, setFaults] = React.useState<FaultRecord[]>([]);
  const [search, setSearch] = React.useState('');
  const [selected, setSelected] = React.useState<FaultRecord | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!open || !token || !yachtId) return;
    setLoading(true);
    setSelected(null);
    setSearch('');
    fetch(`${API_BASE}/api/vessel/${yachtId}/domain/faults/records?limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const records = (d.records ?? []) as FaultRecord[];
        records.sort((a, b) => {
          const ac = (a.fault_code ?? '').toLowerCase();
          const bc = (b.fault_code ?? '').toLowerCase();
          if (ac && bc && ac !== bc) return ac.localeCompare(bc);
          return (a.title ?? '').toLowerCase().localeCompare((b.title ?? '').toLowerCase());
        });
        setFaults(records);
      })
      .catch(() => setFaults([]))
      .finally(() => setLoading(false));
  }, [open, token, yachtId]);

  if (!open) return null;

  const filtered = faults.filter(
    (f) =>
      !search ||
      (f.fault_code ?? '').toLowerCase().includes(search.toLowerCase()) ||
      (f.title ?? '').toLowerCase().includes(search.toLowerCase()),
  );

  const handleSubmit = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await onSubmit(selected.id);
      onClose();
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
          Link Fault to Work Order
        </div>
        <input
          placeholder="Search by code or title…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-sub)',
            background: 'var(--bg)', color: 'var(--txt)', fontSize: 13,
            marginBottom: 8, fontFamily: 'var(--font-sans)',
          }}
        />
        {loading ? (
          <div style={{ color: 'var(--txt3)', fontSize: 13, padding: '12px 0' }}>Loading faults…</div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', border: '1px solid var(--border-faint)', borderRadius: 6, marginBottom: 12 }}>
            {filtered.length === 0 ? (
              <div style={{ padding: '12px 10px', color: 'var(--txt3)', fontSize: 13 }}>
                {search ? 'No matching faults.' : 'No open faults.'}
              </div>
            ) : (
              filtered.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setSelected(selected?.id === f.id ? null : f)}
                  style={{
                    appearance: 'none', WebkitAppearance: 'none',
                    width: '100%', textAlign: 'left',
                    padding: '8px 10px',
                    background: selected?.id === f.id ? 'var(--teal-bg)' : 'transparent',
                    border: 0,
                    borderBottom: '1px solid var(--border-faint)',
                    cursor: 'pointer', color: 'var(--txt)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                    {f.fault_code && (
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt2)', flexShrink: 0 }}>
                        {f.fault_code}
                      </span>
                    )}
                    <span style={{ fontWeight: 500 }}>{f.title ?? 'Fault'}</span>
                  </div>
                  {(f.severity || f.status) && (
                    <div style={{ marginTop: 2, fontSize: 11, color: 'var(--txt3)' }}>
                      {[f.severity, f.status].filter(Boolean).join(' · ')}
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border-sub)',
              background: 'transparent', color: 'var(--txt2)', fontSize: 13, cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!selected || submitting}
            style={{
              padding: '8px 14px', borderRadius: 6, border: 0,
              background: selected ? 'var(--mark)' : 'var(--border-sub)',
              color: selected ? '#fff' : 'var(--txt3)',
              fontSize: 13, fontWeight: 600, cursor: selected ? 'pointer' : 'default',
            }}
          >
            {submitting ? 'Linking…' : 'Link Fault'}
          </button>
        </div>
      </div>
    </div>
  );
}
