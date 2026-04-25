'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useQueryClient } from '@tanstack/react-query';
import { useActiveVessel } from '@/contexts/VesselContext';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 5,
  border: '1px solid var(--border-sub)',
  background: 'var(--surface-primary)',
  color: 'var(--txt)',
  fontSize: 13,
  boxSizing: 'border-box',
  fontFamily: 'inherit',
  outline: 'none',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 10,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.05em',
  color: 'var(--txt3)',
  marginBottom: 5,
};

export interface CreatePurchaseOrderModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function CreatePurchaseOrderModal({ open, onOpenChange }: CreatePurchaseOrderModalProps) {
  const { session } = useAuth();
  const { vesselId } = useActiveVessel();
  const queryClient = useQueryClient();

  const [supplier, setSupplier] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [currency, setCurrency] = React.useState('USD');
  const [notes, setNotes] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setSupplier('');
      setDescription('');
      setCurrency('USD');
      setNotes('');
      setLoading(false);
      setError(null);
    }
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onOpenChange(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onOpenChange]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/v1/actions/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          action: 'create_purchase_order',
          context: { yacht_id: vesselId },
          payload: {
            ...(supplier.trim() && { supplier_name: supplier.trim() }),
            ...(description.trim() && { description: description.trim() }),
            currency,
            ...(notes.trim() && { notes: notes.trim() }),
          },
        }),
      });
      const result = await res.json();
      if (!res.ok || result?.success === false) {
        setError(result?.message ?? result?.detail ?? 'Failed to create purchase order');
        return;
      }
      queryClient.invalidateQueries({ queryKey: ['purchasing'] });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div
        style={{ position: 'fixed', inset: 0, background: 'var(--overlay-bg)', zIndex: 1000 }}
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-po-title"
        style={{
          position: 'fixed', left: '50%', top: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1001,
          width: 440, maxWidth: 'calc(100vw - 32px)',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border-sub)',
          borderRadius: 8,
          padding: '22px 24px 20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        <div id="create-po-title" style={{ fontSize: 14, fontWeight: 600, color: 'var(--txt)', marginBottom: 20 }}>
          New Purchase Order
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={labelStyle}>Supplier</label>
              <input
                type="text"
                value={supplier}
                onChange={(e) => setSupplier(e.target.value)}
                placeholder="Supplier name…"
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Description / Purpose</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What is this order for?"
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                {['USD', 'EUR', 'GBP', 'AUD', 'SGD'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={labelStyle}>Notes (optional)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any additional notes…"
                rows={2}
                style={{ ...inputStyle, resize: 'none' }}
              />
            </div>
          </div>

          {error && (
            <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 4, background: 'var(--red-bg)', border: '1px solid var(--red-border)', color: 'var(--red)', fontSize: 12 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              style={{
                height: 32, padding: '0 16px', borderRadius: 5,
                border: '1px solid var(--border-sub)',
                background: 'var(--surface-el)', color: 'var(--txt3)',
                fontSize: 12, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                height: 32, padding: '0 16px', borderRadius: 5,
                border: '1px solid var(--mark-hover)',
                background: loading ? 'var(--surface-raised)' : 'var(--teal-bg)',
                color: loading ? 'var(--txt-ghost)' : 'var(--mark)',
                fontSize: 12, fontWeight: 500,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? 'Creating…' : 'Create Draft PO'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
