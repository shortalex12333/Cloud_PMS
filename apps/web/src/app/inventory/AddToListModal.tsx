'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { API_BASE } from '@/lib/apiBase';

interface DraftList {
  id: string;
  list_number: string;
  name: string;
  department: string;
  item_count: number;
}

interface Props {
  partId: string;
  partName: string;
  partNumber?: string;
  yachtId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function AddToListModal({ partId, partName, partNumber, yachtId, onClose, onSuccess }: Props) {
  const router = useRouter();
  const [lists, setLists] = React.useState<DraftList[]>([]);
  const [loadingLists, setLoadingLists] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [quantity, setQuantity] = React.useState('1');
  const [urgency, setUrgency] = React.useState('normal');
  const [notes, setNotes] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    async function fetchDraftLists() {
      if (!yachtId) { setLoadingLists(false); return; }
      try {
        const { data: sess } = await supabase.auth.getSession();
        const token = sess.session?.access_token;
        const res = await fetch(`${API_BASE}/v1/shopping-list?yacht_id=${yachtId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        const json = await res.json();
        if (res.ok) {
          const draft = (json.data || []).filter((l: DraftList & { status: string }) => l.status === 'draft');
          setLists(draft);
          if (draft.length === 1) setSelectedId(draft[0].id);
        }
      } catch {
        // silent — empty state handles it
      } finally {
        setLoadingLists(false);
      }
    }
    fetchDraftLists();
  }, [yachtId]);

  async function handleSubmit() {
    if (!selectedId) { setError('Select a shopping list'); return; }
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) { setError('Enter a valid quantity'); return; }

    setSubmitting(true);
    setError(null);
    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      if (!token) { setError('Not authenticated'); setSubmitting(false); return; }

      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          action: 'add_to_shopping_list',
          context: { yacht_id: yachtId },
          payload: {
            part_id: partId,
            shopping_list_id: selectedId,
            quantity_requested: qty,
            urgency,
            source_notes: notes || undefined,
          },
        }),
      });
      const json = await res.json();
      if (!res.ok || json.status === 'error') {
        setError(json.message || 'Failed to add part');
        return;
      }
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: 'fixed', inset: 0, zIndex: 1200,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div style={{
        width: 480, maxHeight: '80vh',
        background: 'var(--surface-base)',
        border: '1px solid var(--border-sub)',
        borderRadius: 10,
        display: 'flex', flexDirection: 'column',
        fontFamily: 'var(--font-sans)',
        overflow: 'hidden',
      }}>

        {/* Header */}
        <div style={{
          padding: '16px 20px 12px',
          borderBottom: '1px solid var(--border-sub)',
          flexShrink: 0,
        }}>
          <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--txt3)', fontFamily: 'var(--font-mono)', margin: 0 }}>
            Add to Shopping List
          </p>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--txt1)', margin: '4px 0 0' }}>
            {partName}
          </p>
          {partNumber && (
            <p style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', margin: '2px 0 0' }}>
              {partNumber}
            </p>
          )}
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>

          {/* List picker */}
          <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 8 }}>
            Select Draft List
          </p>

          {loadingLists && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', color: 'var(--txt3)', fontSize: 13 }}>
              <div style={{ width: 16, height: 16, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
              Loading lists…
            </div>
          )}

          {!loadingLists && lists.length === 0 && (
            <div style={{
              padding: 16, borderRadius: 6,
              border: '1px solid var(--border-sub)',
              background: 'var(--surface-hover)',
              textAlign: 'center',
            }}>
              <p style={{ fontSize: 13, color: 'var(--txt2)', margin: '0 0 8px' }}>
                No draft shopping lists found.
              </p>
              <p style={{ fontSize: 12, color: 'var(--txt3)', margin: '0 0 12px' }}>
                Create a list first, then come back to add parts.
              </p>
              <button
                onClick={() => { onClose(); router.push('/shopping-list'); }}
                style={{
                  padding: '6px 14px', background: 'var(--mark)', color: '#fff',
                  border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600,
                  cursor: 'pointer', fontFamily: 'var(--font-sans)',
                }}
              >
                Go to Shopping Lists
              </button>
            </div>
          )}

          {!loadingLists && lists.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
              {lists.map(list => {
                const active = selectedId === list.id;
                return (
                  <button
                    key={list.id}
                    onClick={() => setSelectedId(list.id)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '10px 14px', borderRadius: 6, cursor: 'pointer',
                      border: `1px solid ${active ? 'var(--mark)' : 'var(--border-sub)'}`,
                      background: active ? 'rgba(44,144,183,0.08)' : 'var(--surface-hover)',
                      textAlign: 'left', width: '100%',
                      transition: 'border-color 0.1s, background 0.1s',
                    }}
                  >
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 600, color: active ? 'var(--mark)' : 'var(--txt1)', margin: 0 }}>
                        {list.name}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', margin: '2px 0 0' }}>
                        {list.list_number} · {list.department}
                      </p>
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', marginLeft: 12 }}>
                      {list.item_count} item{list.item_count !== 1 ? 's' : ''}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {!loadingLists && lists.length > 0 && (
            <>
              {/* Quantity + urgency */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.05em', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                    Quantity
                  </label>
                  <input
                    type="number"
                    min="0.01"
                    step="any"
                    value={quantity}
                    onChange={e => setQuantity(e.target.value)}
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      padding: '8px 10px',
                      background: 'var(--surface-hover)',
                      border: '1px solid var(--border-sub)',
                      borderRadius: 6, color: 'var(--txt1)', fontSize: 13,
                      fontFamily: 'var(--font-mono)', outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.05em', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                    Urgency
                  </label>
                  <select
                    value={urgency}
                    onChange={e => setUrgency(e.target.value)}
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      padding: '8px 10px',
                      background: 'var(--surface-hover)',
                      border: '1px solid var(--border-sub)',
                      borderRadius: 6, color: 'var(--txt1)', fontSize: 13,
                      fontFamily: 'var(--font-sans)', outline: 'none', cursor: 'pointer',
                    }}
                  >
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              {/* Notes */}
              <div style={{ marginBottom: 4 }}>
                <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.05em', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                  Notes (optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Why this part is needed, or sourcing notes…"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  style={{
                    width: '100%', boxSizing: 'border-box',
                    padding: '8px 10px', resize: 'vertical',
                    background: 'var(--surface-hover)',
                    border: '1px solid var(--border-sub)',
                    borderRadius: 6, color: 'var(--txt1)', fontSize: 13,
                    fontFamily: 'var(--font-sans)', outline: 'none',
                  }}
                />
              </div>
            </>
          )}

          {error && (
            <p style={{ fontSize: 12, color: 'var(--red)', marginTop: 8 }}>{error}</p>
          )}
        </div>

        {/* Footer */}
        {!loadingLists && lists.length > 0 && (
          <div style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--border-sub)',
            display: 'flex', justifyContent: 'flex-end', gap: 8,
            flexShrink: 0,
          }}>
            <button
              onClick={onClose}
              disabled={submitting}
              style={{
                padding: '7px 16px', background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 6, fontSize: 12, fontWeight: 600,
                color: 'var(--txt2)', cursor: 'pointer', fontFamily: 'var(--font-sans)',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || !selectedId}
              style={{
                padding: '7px 16px',
                background: submitting || !selectedId ? 'var(--border-sub)' : 'var(--mark)',
                border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600,
                color: submitting || !selectedId ? 'var(--txt3)' : '#fff',
                cursor: submitting || !selectedId ? 'default' : 'pointer',
                fontFamily: 'var(--font-sans)',
                transition: 'background 0.1s',
              }}
            >
              {submitting ? 'Adding…' : 'Add to List'}
            </button>
          </div>
        )}
        {!loadingLists && lists.length === 0 && (
          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--border-sub)',
            display: 'flex', justifyContent: 'flex-end',
          }}>
            <button
              onClick={onClose}
              style={{
                padding: '7px 16px', background: 'transparent',
                border: '1px solid var(--border-sub)',
                borderRadius: 6, fontSize: 12, fontWeight: 600,
                color: 'var(--txt2)', cursor: 'pointer', fontFamily: 'var(--font-sans)',
              }}
            >
              Close
            </button>
          </div>
        )}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
