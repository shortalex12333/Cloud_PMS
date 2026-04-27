'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useActiveVessel } from '@/contexts/VesselContext';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabaseClient';

// ── Types ──────────────────────────────────────────────────────────────────

interface PartResult {
  id: string;
  name: string;
  part_number: string | null;
  unit: string | null;
  manufacturer: string | null;
}

interface LineItem {
  localId: string;
  part_name: string;
  quantity: string;
  unit: string;
  unit_price: string;
  part_number: string;
  source_notes: string;
  urgency: 'low' | 'normal' | 'high' | 'critical';
  required_by_date: string;
  part_id: string | null;
  linked_part_name: string | null;
  source_work_order_id: string;
  expanded: boolean;
  partQuery: string;
  partResults: PartResult[];
  partSearchFocused: boolean;
}

// ── Constants ──────────────────────────────────────────────────────────────

const DEPTS = [
  { value: 'general', label: 'General' },
  { value: 'engine', label: 'Engine' },
  { value: 'deck', label: 'Deck' },
  { value: 'galley', label: 'Galley' },
  { value: 'interior', label: 'Interior' },
  { value: 'bridge', label: 'Bridge' },
];

const CURRENCIES = [
  { value: 'EUR', label: 'EUR' },
  { value: 'USD', label: 'USD' },
  { value: 'GBP', label: 'GBP' },
  { value: 'AED', label: 'AED' },
  { value: 'CHF', label: 'CHF' },
];

const URGENCIES = [
  { value: 'low', label: 'Low' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

// ── Helpers ────────────────────────────────────────────────────────────────

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function blankRow(): LineItem {
  return {
    localId: uid(),
    part_name: '',
    quantity: '1',
    unit: '',
    unit_price: '',
    part_number: '',
    source_notes: '',
    urgency: 'normal',
    required_by_date: '',
    part_id: null,
    linked_part_name: null,
    source_work_order_id: '',
    expanded: false,
    partQuery: '',
    partResults: [],
    partSearchFocused: false,
  };
}

// ── Shared input style ─────────────────────────────────────────────────────

const INPUT: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  borderBottom: '1px solid var(--border-faint)',
  outline: 'none',
  color: 'var(--txt1)',
  fontFamily: 'var(--font-sans)',
  fontSize: 13,
  padding: '2px 0',
  width: '100%',
};

const SELECT: React.CSSProperties = {
  background: 'var(--surface-el)',
  border: '1px solid var(--border-sub)',
  borderRadius: 4,
  outline: 'none',
  color: 'var(--txt2)',
  fontFamily: 'var(--font-sans)',
  fontSize: 12,
  padding: '3px 6px',
  cursor: 'pointer',
};

// ── Main page ──────────────────────────────────────────────────────────────

function NewShoppingListContent() {
  const router = useRouter();
  const { vesselId } = useActiveVessel();
  const { user } = useAuth();
  const yachtId = vesselId || user?.yachtId || '';

  // Header state
  const [name, setName] = React.useState('');
  const [department, setDepartment] = React.useState('general');
  const [currency, setCurrency] = React.useState('EUR');
  const [notes, setNotes] = React.useState('');

  // Line items
  const [lines, setLines] = React.useState<LineItem[]>([blankRow()]);

  // Submission
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // ── Part search ──────────────────────────────────────────────────────────

  const searchTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const searchParts = React.useCallback(async (localId: string, query: string) => {
    if (query.length < 2) {
      setLines(prev => prev.map(l => l.localId === localId ? { ...l, partResults: [] } : l));
      return;
    }
    const { data } = await supabase
      .from('pms_parts')
      .select('id, name, part_number, unit, manufacturer')
      .eq('yacht_id', yachtId)
      .or(`name.ilike.%${query}%,part_number.ilike.%${query}%`)
      .limit(8);
    setLines(prev => prev.map(l => l.localId === localId ? { ...l, partResults: data ?? [] } : l));
  }, [yachtId]);

  const handlePartQueryChange = React.useCallback((localId: string, q: string) => {
    setLines(prev => prev.map(l => l.localId === localId ? { ...l, partQuery: q, part_id: null, linked_part_name: null } : l));
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => searchParts(localId, q), 280);
  }, [searchParts]);

  const linkPart = React.useCallback((localId: string, part: PartResult) => {
    setLines(prev => prev.map(l => l.localId === localId ? {
      ...l,
      part_id: part.id,
      linked_part_name: part.name,
      part_name: l.part_name || part.name,
      part_number: l.part_number || (part.part_number ?? ''),
      unit: l.unit || (part.unit ?? ''),
      partQuery: '',
      partResults: [],
      partSearchFocused: false,
    } : l));
  }, []);

  // ── Row helpers ──────────────────────────────────────────────────────────

  const updateLine = React.useCallback(<K extends keyof LineItem>(localId: string, field: K, value: LineItem[K]) => {
    setLines(prev => prev.map(l => l.localId === localId ? { ...l, [field]: value } : l));
  }, []);

  const addLine = React.useCallback(() => {
    setLines(prev => [...prev, blankRow()]);
  }, []);

  const removeLine = React.useCallback((localId: string) => {
    setLines(prev => prev.length > 1 ? prev.filter(l => l.localId !== localId) : prev);
  }, []);

  // ── Submit ───────────────────────────────────────────────────────────────

  const handleSubmit = React.useCallback(async () => {
    if (!name.trim()) { setError('List name is required'); return; }
    if (!yachtId) { setError('No vessel selected'); return; }

    const validLines = lines.filter(l => l.part_name.trim());

    setSubmitting(true);
    setError(null);

    try {
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      if (!token) { setError('Not authenticated'); return; }

      const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

      // 1. Create the list
      const createRes = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          action: 'create_shopping_list',
          context: { yacht_id: yachtId },
          payload: {
            name: name.trim(),
            department,
            currency,
            notes: notes.trim() || undefined,
          },
        }),
      });
      const createJson = await createRes.json();
      if (!createRes.ok || createJson.status === 'error') {
        setError(createJson.message || 'Failed to create list');
        return;
      }

      const listId: string =
        createJson.result?.shopping_list_id ??
        createJson.result?.list_id ??
        createJson.data?.id;
      if (!listId) { setError('No list ID returned'); return; }

      // 2. Add each item sequentially
      for (const line of validLines) {
        const qty = parseFloat(line.quantity) || 1;
        await fetch('/api/v1/actions/execute', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            action: 'add_item_to_list',
            context: { yacht_id: yachtId },
            payload: {
              shopping_list_id: listId,
              part_name: line.part_name.trim(),
              quantity_requested: qty,
              unit: line.unit.trim() || undefined,
              unit_price: line.unit_price ? parseFloat(line.unit_price) : undefined,
              part_number: line.part_number.trim() || undefined,
              part_id: line.part_id || undefined,
              urgency: line.urgency,
              source_notes: line.source_notes.trim() || undefined,
              required_by_date: line.required_by_date || undefined,
              source_work_order_id: line.source_work_order_id.trim() || undefined,
              source_type: line.part_id ? 'inventory_link' : 'manual_add',
            },
          }),
        });
      }

      router.push(`/shopping-list/${listId}`);

    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setSubmitting(false);
    }
  }, [name, department, currency, notes, lines, yachtId, router]);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--surface-base)', fontFamily: 'var(--font-sans)', minHeight: 0,
    }}>

      {/* Identity strip */}
      <div style={{
        padding: '14px 24px 0', borderBottom: '1px solid var(--border-sub)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={() => router.push('/shopping-list')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--txt3)', fontSize: 12, fontFamily: 'var(--font-mono)', padding: 0 }}
            >
              ← Lists
            </button>
            <span style={{
              display: 'inline-flex', alignItems: 'center', height: 18,
              padding: '0 7px', borderRadius: 3, fontSize: 9.5, fontWeight: 600,
              letterSpacing: '0.05em', textTransform: 'uppercase',
              color: 'var(--txt2)', background: 'var(--surface-hover)', border: '1px solid var(--border-sub)',
            }}>Draft</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => router.push('/shopping-list')}
              style={{
                padding: '6px 12px', background: 'none',
                border: '1px solid var(--border-sub)', borderRadius: 6,
                fontSize: 12, color: 'var(--txt3)', cursor: 'pointer', fontFamily: 'var(--font-sans)',
              }}
            >
              Discard
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                padding: '6px 16px', background: 'var(--mark)', color: '#fff',
                border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600,
                cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.7 : 1,
                fontFamily: 'var(--font-sans)',
              }}
            >
              {submitting ? 'Creating…' : 'Create Draft'}
            </button>
          </div>
        </div>

        {/* List name — inline edit */}
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="List name — e.g. Engine Stores Run, May 2026"
          style={{
            display: 'block', width: '100%', background: 'transparent',
            border: 'none', outline: 'none', fontSize: 20, fontWeight: 600,
            color: name ? 'var(--txt1)' : 'var(--txt-ghost)',
            fontFamily: 'var(--font-sans)', padding: '0 0 10px',
            borderBottom: '1px solid transparent',
          }}
          onFocus={e => { e.currentTarget.style.borderBottomColor = 'var(--border-sub)'; }}
          onBlur={e => { e.currentTarget.style.borderBottomColor = 'transparent'; }}
        />

        {/* Metadata row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--txt3)' }}>
            Dept
            <select value={department} onChange={e => setDepartment(e.target.value)} style={SELECT}>
              {DEPTS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--txt3)' }}>
            Currency
            <select value={currency} onChange={e => setCurrency(e.target.value)} style={SELECT}>
              {CURRENCIES.map(c => <option key={c.value} value={c.value}>{c.value}</option>)}
            </select>
          </label>
          <input
            type="text"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Notes (optional)"
            style={{
              flex: 1, background: 'transparent', border: 'none',
              borderBottom: '1px solid var(--border-faint)', outline: 'none',
              fontSize: 12, color: 'var(--txt2)', fontFamily: 'var(--font-sans)',
              padding: '2px 0',
            }}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '8px 24px', color: 'var(--red)', fontSize: 12, background: 'var(--red-bg, #1a0000)', borderBottom: '1px solid var(--border-sub)', flexShrink: 0 }}>
          {error}
        </div>
      )}

      {/* Line items */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>

        {/* Column headers */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '28px 1fr 72px 64px 88px 28px 28px',
          gap: 0, padding: '6px 24px',
          borderBottom: '1px solid var(--border-sub)',
          background: 'var(--surface-base)',
          position: 'sticky', top: 0, zIndex: 2,
        }}>
          {['', 'Part / Item', 'Qty', 'Unit', `Price (${currency})`, '', ''].map((h, i) => (
            <span key={i} style={{
              fontSize: 10, fontWeight: 600, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--txt-ghost)',
              fontFamily: 'var(--font-mono)',
            }}>{h}</span>
          ))}
        </div>

        {/* Rows */}
        {lines.map((line, idx) => (
          <LineRow
            key={line.localId}
            line={line}
            rowNum={idx + 1}
            currency={currency}
            onUpdate={updateLine}
            onRemove={removeLine}
            onPartQueryChange={handlePartQueryChange}
            onLinkPart={linkPart}
          />
        ))}

        {/* Add new line */}
        <div style={{ padding: '12px 24px' }}>
          <button
            onClick={addLine}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--mark)', fontSize: 12, fontWeight: 500,
              fontFamily: 'var(--font-sans)', padding: '4px 0',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            Add new line
          </button>
        </div>

        {/* Summary */}
        {lines.some(l => l.unit_price && l.quantity) && (
          <div style={{
            padding: '12px 24px', borderTop: '1px solid var(--border-sub)',
            display: 'flex', justifyContent: 'flex-end', gap: 16,
          }}>
            <span style={{ fontSize: 11, color: 'var(--txt3)' }}>Est. Total</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt1)', fontFamily: 'var(--font-mono)' }}>
              {currency} {lines.reduce((sum, l) => {
                const p = parseFloat(l.unit_price);
                const q = parseFloat(l.quantity) || 1;
                return sum + (isNaN(p) ? 0 : p * q);
              }, 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}
      </div>

      <style>{`@keyframes sl-fade { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }`}</style>
    </div>
  );
}

// ── Row component ──────────────────────────────────────────────────────────

interface LineRowProps {
  line: LineItem;
  rowNum: number;
  currency: string;
  onUpdate: <K extends keyof LineItem>(id: string, field: K, value: LineItem[K]) => void;
  onRemove: (id: string) => void;
  onPartQueryChange: (id: string, q: string) => void;
  onLinkPart: (id: string, part: PartResult) => void;
}

function LineRow({ line, rowNum, currency, onUpdate, onRemove, onPartQueryChange, onLinkPart }: LineRowProps) {
  const id = line.localId;

  return (
    <div style={{ borderBottom: '1px solid var(--border-faint)' }}>
      {/* Primary row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '28px 1fr 72px 64px 88px 28px 28px',
        gap: 0, padding: '8px 24px', alignItems: 'center',
      }}>
        {/* Row number + expand toggle */}
        <button
          onClick={() => onUpdate(id, 'expanded', !line.expanded)}
          title={line.expanded ? 'Collapse' : 'Expand details'}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--txt-ghost)', fontSize: 10, fontFamily: 'var(--font-mono)',
            display: 'flex', alignItems: 'center', gap: 3, padding: 0,
            transition: 'color 100ms',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--txt2)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--txt-ghost)'; }}
        >
          <svg
            width="9" height="9" viewBox="0 0 9 9" fill="none"
            style={{ transform: line.expanded ? 'rotate(90deg)' : 'none', transition: 'transform 150ms' }}
          >
            <path d="M3 1.5l3 3-3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span>{rowNum}</span>
        </button>

        {/* Part name */}
        <div style={{ position: 'relative' }}>
          {line.linked_part_name && (
            <span style={{
              fontSize: 9, fontWeight: 600, color: 'var(--mark)', letterSpacing: '0.04em',
              display: 'block', marginBottom: 1,
            }}>
              LINKED · {line.linked_part_name}
              <button
                onClick={() => { onUpdate(id, 'part_id', null); onUpdate(id, 'linked_part_name', null); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--txt-ghost)', fontSize: 9, marginLeft: 6, padding: 0 }}
              >✕</button>
            </span>
          )}
          <input
            type="text"
            value={line.part_name}
            onChange={e => onUpdate(id, 'part_name', e.target.value)}
            placeholder={`Item ${rowNum}…`}
            style={{ ...INPUT, fontSize: 13 }}
          />
        </div>

        {/* Qty */}
        <input
          type="number"
          min="0"
          step="any"
          value={line.quantity}
          onChange={e => onUpdate(id, 'quantity', e.target.value)}
          style={{ ...INPUT, textAlign: 'right', fontFamily: 'var(--font-mono)' }}
        />

        {/* Unit */}
        <input
          type="text"
          value={line.unit}
          onChange={e => onUpdate(id, 'unit', e.target.value)}
          placeholder="pcs"
          style={{ ...INPUT, textAlign: 'center', fontSize: 12 }}
        />

        {/* Price */}
        <input
          type="number"
          min="0"
          step="any"
          value={line.unit_price}
          onChange={e => onUpdate(id, 'unit_price', e.target.value)}
          placeholder="0.00"
          style={{ ...INPUT, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12 }}
        />

        {/* Urgency badge */}
        <div />

        {/* Remove */}
        <button
          onClick={() => onRemove(id)}
          title="Remove line"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--txt-ghost)', fontSize: 14, display: 'flex',
            alignItems: 'center', justifyContent: 'center', padding: 0,
            transition: 'color 100ms',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--red)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--txt-ghost)'; }}
        >×</button>
      </div>

      {/* Expanded detail section */}
      {line.expanded && (
        <div style={{
          padding: '10px 24px 14px 52px', background: 'var(--surface-raised, var(--surface-hover))',
          borderTop: '1px solid var(--border-faint)',
          animation: 'sl-fade 120ms ease-out',
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px 20px', marginBottom: 10 }}>

            {/* Part number */}
            <label style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
              Part #
              <input
                type="text"
                value={line.part_number}
                onChange={e => onUpdate(id, 'part_number', e.target.value)}
                placeholder="MAN-12345"
                style={{ ...INPUT, fontFamily: 'var(--font-mono)', fontSize: 12, marginTop: 3 }}
              />
            </label>

            {/* Urgency */}
            <label style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
              Urgency
              <select
                value={line.urgency}
                onChange={e => onUpdate(id, 'urgency', e.target.value as LineItem['urgency'])}
                style={{ ...SELECT, display: 'block', marginTop: 3, width: '100%' }}
              >
                {URGENCIES.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
              </select>
            </label>

            {/* Required by */}
            <label style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
              Required By
              <input
                type="date"
                value={line.required_by_date}
                onChange={e => onUpdate(id, 'required_by_date', e.target.value)}
                style={{ ...INPUT, fontFamily: 'var(--font-mono)', fontSize: 12, marginTop: 3 }}
              />
            </label>
          </div>

          {/* Notes */}
          <label style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', display: 'block', marginBottom: 10 }}>
            Notes
            <textarea
              value={line.source_notes}
              onChange={e => onUpdate(id, 'source_notes', e.target.value)}
              placeholder="Why is this needed?"
              rows={2}
              style={{
                display: 'block', width: '100%', background: 'transparent',
                border: '1px solid var(--border-faint)', borderRadius: 4,
                outline: 'none', color: 'var(--txt1)', fontFamily: 'var(--font-sans)',
                fontSize: 12, padding: '5px 7px', resize: 'vertical', marginTop: 3,
                boxSizing: 'border-box',
              }}
            />
          </label>

          {/* Link Part search */}
          <div style={{ marginBottom: 10 }}>
            <span style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
              Link Part
            </span>
            <div style={{ position: 'relative', marginTop: 3 }}>
              <input
                type="text"
                value={line.partQuery}
                onChange={e => onPartQueryChange(id, e.target.value)}
                onFocus={() => onUpdate(id, 'partSearchFocused', true)}
                onBlur={() => setTimeout(() => onUpdate(id, 'partSearchFocused', false), 150)}
                placeholder="Search part catalogue…"
                style={{
                  ...INPUT,
                  fontSize: 12,
                  background: 'var(--surface-el)',
                  border: '1px solid var(--border-sub)',
                  borderRadius: 4,
                  padding: '4px 8px',
                }}
              />
              {line.partSearchFocused && line.partResults.length > 0 && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                  background: 'var(--surface)', border: '1px solid var(--border-sub)',
                  borderRadius: 4, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  overflow: 'hidden', marginTop: 2,
                }}>
                  {line.partResults.map(p => (
                    <button
                      key={p.id}
                      onMouseDown={() => onLinkPart(id, p)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        width: '100%', padding: '7px 10px', background: 'none',
                        border: 'none', cursor: 'pointer', textAlign: 'left',
                        borderBottom: '1px solid var(--border-faint)',
                        transition: 'background 80ms',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
                    >
                      <span style={{ fontSize: 12, color: 'var(--txt1)', fontFamily: 'var(--font-sans)' }}>{p.name}</span>
                      <span style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>{p.part_number ?? '—'}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Link Work Order */}
          <label style={{ fontSize: 10, color: 'var(--txt-ghost)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', display: 'block' }}>
            Link Work Order (ID)
            <input
              type="text"
              value={line.source_work_order_id}
              onChange={e => onUpdate(id, 'source_work_order_id', e.target.value)}
              placeholder="WO-XXXX UUID"
              style={{ ...INPUT, fontFamily: 'var(--font-mono)', fontSize: 11, marginTop: 3 }}
            />
          </label>
        </div>
      )}
    </div>
  );
}

// ── Export ─────────────────────────────────────────────────────────────────

export default function NewShoppingListPage() {
  return (
    <React.Suspense fallback={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <div style={{ width: 24, height: 24, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    }>
      <NewShoppingListContent />
    </React.Suspense>
  );
}
