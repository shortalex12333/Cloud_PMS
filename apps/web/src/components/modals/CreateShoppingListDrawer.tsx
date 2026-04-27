'use client';

/**
 * Create Shopping List — right-panel drawer.
 *
 * Designed for onboard use: list name + line items in one flow.
 * Part Name IS the search — type to find from inventory catalogue,
 * or enter manually if the part isn't catalogued yet.
 *
 * Per-line details (expand): reason, urgency, required-by, WO/fault link.
 *
 * Draft behaviour:
 *   - Debounce-saves to localStorage (pms_sl_draft_v1)
 *   - On mount: restores draft if present → DRAFT badge
 *   - On close with unsaved content: prompts Save draft / Discard
 *   - On submit: clears draft, navigates to new list
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { supabase } from '@/lib/supabaseClient';
import { X, ShoppingCart, Plus, ChevronRight, Search, Link2 } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────

interface PartHit {
  id: string;
  name: string;
  part_number: string | null;
  unit: string | null;
  manufacturer: string | null;
}

interface LineItem {
  localId: string;
  // Primary fields
  part_name: string;
  quantity: string;
  unit: string;
  unit_price: string;
  // Linked part (from catalogue)
  part_id: string | null;
  part_number: string;
  // Expand-only details
  source_notes: string;
  urgency: 'low' | 'normal' | 'high' | 'critical';
  required_by_date: string;
  source_work_order_id: string; // WO or Fault UUID/title — maps to source_work_order_id
  // UI state
  expanded: boolean;
  partQuery: string;
  partHits: PartHit[];
  partDropdownOpen: boolean;
}

interface SLDraft {
  name: string;
  department: string;
  currency: string;
  notes: string;
  lines: Omit<LineItem, 'partHits' | 'partDropdownOpen'>[];
}

export interface CreateShoppingListDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ── Constants ──────────────────────────────────────────────────────────────

const DRAFT_KEY = 'pms_sl_draft_v1';

const DEPTS = ['general', 'engine', 'deck', 'galley', 'interior', 'bridge'];
const CURRENCIES = ['EUR', 'USD', 'GBP', 'AED', 'CHF'];
const URGENCIES: Array<{ value: LineItem['urgency']; label: string; color: string; bg: string }> = [
  { value: 'low',      label: 'Low',      color: 'var(--txt3)',   bg: 'transparent' },
  { value: 'normal',   label: 'Normal',   color: 'var(--green)',  bg: 'rgba(34,197,94,0.07)' },
  { value: 'high',     label: 'High',     color: 'var(--amber)',  bg: 'rgba(245,158,11,0.10)' },
  { value: 'critical', label: 'Critical', color: 'var(--red)',    bg: 'rgba(239,68,68,0.12)' },
];

function blankLine(): LineItem {
  return {
    localId: Math.random().toString(36).slice(2, 10),
    part_name: '', quantity: '1', unit: '', unit_price: '',
    part_id: null, part_number: '',
    source_notes: '', urgency: 'normal', required_by_date: '',
    source_work_order_id: '',
    expanded: false, partQuery: '', partHits: [], partDropdownOpen: false,
  };
}

const BLANK_DRAFT: SLDraft = {
  name: '', department: 'general', currency: 'EUR', notes: '', lines: [blankLine()],
};

function isDirty(name: string, lines: LineItem[]): boolean {
  return name.trim() !== '' || lines.some(l => l.part_name.trim() !== '');
}

// ── Shared styles ──────────────────────────────────────────────────────────

const INPUT: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'var(--surface)', border: '1px solid var(--border-side, var(--border-sub))',
  borderRadius: 4, padding: '8px 10px',
  fontSize: 13, color: 'var(--txt, var(--txt1))',
  outline: 'none', transition: 'border-color 80ms',
  fontFamily: 'inherit',
};

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--txt2)', marginBottom: 6 }}>
      {children}
      {required && <span style={{ color: 'var(--red)', marginLeft: 3 }}>*</span>}
    </div>
  );
}

function SectionHead({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      borderTop: '1px solid var(--border-sub)', marginTop: 28, paddingTop: 20, marginBottom: 14,
    }}>
      <span style={{ color: 'var(--txt3)', display: 'flex' }}>{icon}</span>
      <span style={{
        fontSize: 10, fontWeight: 600, letterSpacing: '0.07em',
        textTransform: 'uppercase', color: 'var(--txt3)', fontFamily: 'var(--font-mono)',
      }}>{label}</span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function CreateShoppingListDrawer({ open, onOpenChange }: CreateShoppingListDrawerProps) {
  const router = useRouter();
  const { session } = useAuth();
  const { vesselId } = useActiveVessel();
  const yachtId = vesselId ?? '';

  const [name, setName] = React.useState('');
  const [department, setDepartment] = React.useState('general');
  const [currency, setCurrency] = React.useState('EUR');
  const [notes, setNotes] = React.useState('');
  const [lines, setLines] = React.useState<LineItem[]>([blankLine()]);
  const [isDraft, setIsDraft] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState('');
  const [confirmClose, setConfirmClose] = React.useState(false);
  const nameRef = React.useRef<HTMLInputElement>(null);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchTimers = React.useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // ── restore draft on open ──────────────────────────────────────────────

  React.useEffect(() => {
    if (!open) return;
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) {
        const d: SLDraft = JSON.parse(saved);
        setName(d.name ?? '');
        setDepartment(d.department ?? 'general');
        setCurrency(d.currency ?? 'EUR');
        setNotes(d.notes ?? '');
        setLines((d.lines ?? [blankLine()]).map(l => ({
          ...l, partHits: [], partDropdownOpen: false,
        })));
        setIsDraft(true);
      } else {
        setName(''); setDepartment('general'); setCurrency('EUR'); setNotes('');
        setLines([blankLine()]); setIsDraft(false);
      }
    } catch { /* ignore */ }
    setTimeout(() => nameRef.current?.focus(), 80);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── draft autosave ─────────────────────────────────────────────────────

  const saveDraft = React.useCallback((
    n: string, dept: string, cur: string, nt: string, ls: LineItem[]
  ) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (isDirty(n, ls)) {
        const d: SLDraft = {
          name: n, department: dept, currency: cur, notes: nt,
          lines: ls.map(l => ({ ...l, partHits: [], partDropdownOpen: false })),
        };
        localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
        setIsDraft(true);
      }
    }, 500);
  }, []);

  function setN(v: string) { setName(v); saveDraft(v, department, currency, notes, lines); }
  function setDept(v: string) { setDepartment(v); saveDraft(name, v, currency, notes, lines); }
  function setCur(v: string) { setCurrency(v); saveDraft(name, department, v, notes, lines); }
  function setNt(v: string) { setNotes(v); saveDraft(name, department, currency, v, lines); }

  function setLines_(next: LineItem[]) {
    setLines(next);
    saveDraft(name, department, currency, notes, next);
  }

  // ── close guard ────────────────────────────────────────────────────────

  function handleClose() {
    if (isDirty(name, lines) && !confirmClose) { setConfirmClose(true); return; }
    setConfirmClose(false);
    onOpenChange(false);
  }

  function saveDraftAndClose() {
    const d: SLDraft = {
      name, department, currency, notes,
      lines: lines.map(l => ({ ...l, partHits: [], partDropdownOpen: false })),
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
    setIsDraft(true);
    setConfirmClose(false);
    onOpenChange(false);
  }

  function discardAndClose() {
    localStorage.removeItem(DRAFT_KEY);
    setIsDraft(false);
    setLines([blankLine()]);
    setName(''); setDepartment('general'); setCurrency('EUR'); setNotes('');
    setConfirmClose(false);
    onOpenChange(false);
  }

  // ── ESC ────────────────────────────────────────────────────────────────

  React.useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') handleClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [open, name, lines]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── line helpers ───────────────────────────────────────────────────────

  function updateLine<K extends keyof LineItem>(localId: string, field: K, value: LineItem[K]) {
    setLines_(lines.map(l => l.localId === localId ? { ...l, [field]: value } : l));
  }

  function addLine() {
    setLines_([...lines, blankLine()]);
  }

  function removeLine(localId: string) {
    if (lines.length > 1) setLines_(lines.filter(l => l.localId !== localId));
  }

  // ── part search ────────────────────────────────────────────────────────

  function handlePartQuery(localId: string, q: string) {
    // Update query + clear link
    const next = lines.map(l => l.localId === localId
      ? { ...l, partQuery: q, part_id: null }
      : l
    );
    setLines_(next);
    // Debounced Supabase search
    if (searchTimers.current[localId]) clearTimeout(searchTimers.current[localId]);
    searchTimers.current[localId] = setTimeout(async () => {
      if (q.length < 2) {
        setLines(prev => prev.map(l => l.localId === localId ? { ...l, partHits: [], partDropdownOpen: false } : l));
        return;
      }
      const { data } = await supabase
        .from('pms_parts')
        .select('id, name, part_number, unit, manufacturer')
        .eq('yacht_id', yachtId)
        .or(`name.ilike.%${q}%,part_number.ilike.%${q}%`)
        .limit(8);
      setLines(prev => prev.map(l => l.localId === localId
        ? { ...l, partHits: data ?? [], partDropdownOpen: (data?.length ?? 0) > 0 }
        : l
      ));
    }, 280);
  }

  function linkPart(localId: string, hit: PartHit) {
    setLines_(lines.map(l => l.localId === localId ? {
      ...l,
      part_id: hit.id,
      part_name: l.part_name || hit.name,
      part_number: l.part_number || (hit.part_number ?? ''),
      unit: l.unit || (hit.unit ?? ''),
      partQuery: '',
      partHits: [],
      partDropdownOpen: false,
    } : l));
  }

  function unlinkPart(localId: string) {
    setLines_(lines.map(l => l.localId === localId
      ? { ...l, part_id: null, partQuery: '' }
      : l
    ));
  }

  // ── submit ─────────────────────────────────────────────────────────────

  async function handleSubmit() {
    if (!name.trim()) { setError('List name is required.'); return; }
    if (!session?.access_token) { setError('Not authenticated.'); return; }
    setError('');
    setSubmitting(true);

    try {
      const token = session.access_token;
      const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

      // 1. Create the list
      const createRes = await fetch('/api/v1/actions/execute', {
        method: 'POST', headers,
        body: JSON.stringify({
          action: 'create_shopping_list',
          context: { yacht_id: yachtId },
          payload: { name: name.trim(), department, currency, notes: notes.trim() || undefined },
        }),
      });
      const createJson = await createRes.json();
      if (!createRes.ok || createJson.status === 'error') {
        setError(createJson.message || 'Failed to create list.');
        return;
      }
      const listId: string = createJson.result?.shopping_list_id ?? createJson.result?.list_id;
      if (!listId) { setError('No list ID in response.'); return; }

      // 2. Add each valid line
      const validLines = lines.filter(l => l.part_name.trim());
      for (const line of validLines) {
        await fetch('/api/v1/actions/execute', {
          method: 'POST', headers,
          body: JSON.stringify({
            action: 'add_item_to_list',
            context: { yacht_id: yachtId },
            payload: {
              shopping_list_id: listId,
              part_name: line.part_name.trim(),
              quantity_requested: parseFloat(line.quantity) || 1,
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

      localStorage.removeItem(DRAFT_KEY);
      setIsDraft(false);
      onOpenChange(false);
      router.push(`/shopping-list/${listId}`);

    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error.');
    } finally {
      setSubmitting(false);
    }
  }

  // ── estimated total ────────────────────────────────────────────────────

  const estTotal = lines.reduce((sum, l) => {
    const p = parseFloat(l.unit_price);
    const q = parseFloat(l.quantity) || 1;
    return sum + (isNaN(p) ? 0 : p * q);
  }, 0);
  const hasTotal = lines.some(l => l.unit_price !== '');

  if (!open) return null;

  // ── render ─────────────────────────────────────────────────────────────

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={handleClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.45)',
          zIndex: 900, backdropFilter: 'blur(2px)',
        }}
      />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 'min(720px, 100vw)',
        background: 'var(--surface-el)',
        borderLeft: '1px solid var(--border-side, var(--border-sub))',
        boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
        zIndex: 901,
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'var(--font-sans)',
      }}>

        {/* ── Panel header (glass) ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px', height: 52, flexShrink: 0,
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-glass)',
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShoppingCart style={{ width: 15, height: 15, color: 'var(--mark)' }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt, var(--txt1))' }}>
              New Shopping List
            </span>
            {isDraft && (
              <span style={{
                fontSize: 9, fontWeight: 600, letterSpacing: '0.06em',
                textTransform: 'uppercase', color: 'var(--mark)',
                background: 'var(--teal-bg, rgba(43,123,163,0.12))',
                border: '1px solid var(--mark-hover, rgba(43,123,163,0.3))',
                borderRadius: 3, padding: '2px 6px',
              }}>DRAFT</span>
            )}
          </div>
          <button
            onClick={handleClose}
            style={{
              width: 28, height: 28, borderRadius: 4,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'transparent', border: 'none',
              color: 'var(--txt3)', cursor: 'pointer',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <X style={{ width: 14, height: 14 }} />
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px 16px' }}>

          {/* List Name */}
          <div style={{ marginBottom: 18 }}>
            <FieldLabel required>List Name</FieldLabel>
            <input
              ref={nameRef}
              value={name}
              onChange={e => setN(e.target.value)}
              placeholder="e.g. Engine Stores Run, May 2026"
              style={{ ...INPUT, fontSize: 15, fontWeight: 500, padding: '10px 12px' }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side, var(--border-sub))'; }}
            />
          </div>

          {/* Department + Currency row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 18 }}>
            <div>
              <FieldLabel>Department</FieldLabel>
              <select
                value={department}
                onChange={e => setDept(e.target.value)}
                style={{ ...INPUT, cursor: 'pointer' }}
              >
                {DEPTS.map(d => (
                  <option key={d} value={d}>
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <FieldLabel>Currency</FieldLabel>
              <select
                value={currency}
                onChange={e => setCur(e.target.value)}
                style={{ ...INPUT, cursor: 'pointer' }}
              >
                {CURRENCIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <div style={{ marginBottom: 4 }}>
            <FieldLabel>Notes (optional)</FieldLabel>
            <textarea
              value={notes}
              onChange={e => setNt(e.target.value)}
              placeholder="Context for this shopping run — port, timing, budget notes..."
              rows={2}
              style={{
                ...INPUT, resize: 'vertical', lineHeight: 1.5, padding: '8px 10px',
              }}
            />
          </div>

          {/* ── LINE ITEMS ── */}
          <SectionHead
            icon={<ShoppingCart style={{ width: 13, height: 13 }} />}
            label={`Line Items (${lines.length})`}
          />

          {/* Lines */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {lines.map((line, idx) => (
              <LineRow
                key={line.localId}
                line={line}
                rowNum={idx + 1}
                currency={currency}
                yachtId={yachtId}
                onUpdate={(field, val) => updateLine(line.localId, field, val)}
                onRemove={() => removeLine(line.localId)}
                onPartQuery={q => handlePartQuery(line.localId, q)}
                onLinkPart={hit => linkPart(line.localId, hit)}
                onUnlinkPart={() => unlinkPart(line.localId)}
              />
            ))}
          </div>

          {/* Add line */}
          <button
            onClick={addLine}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, marginTop: 12,
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--mark)', fontSize: 12, fontWeight: 500, padding: '4px 0',
            }}
          >
            <Plus style={{ width: 13, height: 13 }} />
            Add line item
          </button>

          {/* Running total */}
          {hasTotal && (
            <div style={{
              marginTop: 20, padding: '12px 0',
              borderTop: '1px solid var(--border-faint)',
              display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontSize: 11, color: 'var(--txt3)' }}>Estimated Total</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--txt1)', fontFamily: 'var(--font-mono)' }}>
                {currency} {estTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          )}
        </div>

        {/* ── Confirm-close prompt ── */}
        {confirmClose && (
          <div style={{
            padding: '14px 24px', borderTop: '1px solid var(--border-sub)',
            background: 'var(--surface)', flexShrink: 0,
          }}>
            <p style={{ fontSize: 13, color: 'var(--txt1)', margin: '0 0 12px' }}>
              You have unsaved content. What would you like to do?
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={saveDraftAndClose}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 6,
                  background: 'var(--teal-bg)', border: '1px solid var(--mark-hover)',
                  color: 'var(--mark)', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                }}
              >Save draft</button>
              <button
                onClick={discardAndClose}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 6,
                  background: 'none', border: '1px solid var(--border-sub)',
                  color: 'var(--red)', fontSize: 12, fontWeight: 500, cursor: 'pointer',
                }}
              >Discard changes</button>
              <button
                onClick={() => setConfirmClose(false)}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 6,
                  background: 'none', border: '1px solid var(--border-sub)',
                  color: 'var(--txt3)', fontSize: 12, cursor: 'pointer',
                }}
              >Keep editing</button>
            </div>
          </div>
        )}

        {/* ── Footer ── */}
        {!confirmClose && (
          <div style={{
            padding: '12px 24px',
            borderTop: '1px solid var(--border-sub)',
            display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10,
            background: 'var(--surface)', flexShrink: 0,
          }}>
            {error && (
              <span style={{ flex: 1, fontSize: 12, color: 'var(--red)' }}>{error}</span>
            )}
            <button
              onClick={discardAndClose}
              style={{
                padding: '8px 16px', borderRadius: 6,
                background: 'none', border: '1px solid var(--border-sub)',
                color: 'var(--txt3)', fontSize: 12, cursor: 'pointer',
              }}
            >Discard</button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              style={{
                padding: '8px 20px', borderRadius: 6,
                background: submitting ? 'var(--surface-hover)' : 'var(--mark)',
                border: 'none', color: '#fff',
                fontSize: 12, fontWeight: 600,
                cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting ? 0.75 : 1,
              }}
            >
              {submitting ? 'Creating…' : 'Create Draft'}
            </button>
          </div>
        )}
      </div>
    </>
  );
}

// ── LineRow component ──────────────────────────────────────────────────────

interface LineRowProps {
  line: LineItem;
  rowNum: number;
  currency: string;
  yachtId: string;
  onUpdate: <K extends keyof LineItem>(field: K, val: LineItem[K]) => void;
  onRemove: () => void;
  onPartQuery: (q: string) => void;
  onLinkPart: (hit: PartHit) => void;
  onUnlinkPart: () => void;
}

function LineRow({ line, rowNum, currency, onUpdate, onRemove, onPartQuery, onLinkPart, onUnlinkPart }: LineRowProps) {

  const isLinked = !!line.part_id;

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border-sub)',
      borderRadius: 6,
      overflow: 'visible',
    }}>
      {/* ── Primary row ── */}
      <div style={{ padding: '10px 12px' }}>

        {/* Row header: number + collapse toggle + remove */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <button
            onClick={() => onUpdate('expanded', !line.expanded)}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--txt-ghost)', padding: 0, fontSize: 10,
              fontFamily: 'var(--font-mono)',
            }}
          >
            <ChevronRight
              style={{
                width: 12, height: 12,
                transform: line.expanded ? 'rotate(90deg)' : 'none',
                transition: 'transform 150ms',
                color: line.expanded ? 'var(--mark)' : undefined,
              }}
            />
            {rowNum.toString().padStart(2, '0')}
          </button>

          {/* Linked part badge */}
          {isLinked && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              fontSize: 9, fontWeight: 600, letterSpacing: '0.05em',
              textTransform: 'uppercase', color: 'var(--mark)',
              background: 'var(--teal-bg)', border: '1px solid var(--mark-hover)',
              borderRadius: 3, padding: '1px 6px',
            }}>
              <Link2 style={{ width: 9, height: 9 }} />
              LINKED
              <button
                onClick={onUnlinkPart}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--txt-ghost)', padding: '0 0 0 2px', fontSize: 10 }}
              >×</button>
            </span>
          )}

          <div style={{ flex: 1 }} />
          <button
            onClick={onRemove}
            title="Remove line"
            style={{
              width: 22, height: 22, borderRadius: 3,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--txt-ghost)', fontSize: 14, transition: 'color 100ms',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--red)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--txt-ghost)'; }}
          >×</button>
        </div>

        {/* Part name / catalogue search */}
        <div style={{ position: 'relative', marginBottom: 10 }}>
          <div style={{ position: 'relative' }}>
            <Search style={{
              position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)',
              width: 12, height: 12, color: 'var(--txt-ghost)', pointerEvents: 'none',
            }} />
            <input
              type="text"
              value={isLinked ? line.part_name : (line.partQuery || line.part_name)}
              onChange={e => {
                onUpdate('part_name', e.target.value);
                onPartQuery(e.target.value);
              }}
              placeholder={`Part or item name — type to search catalogue…`}
              style={{
                ...INPUT,
                paddingLeft: 28,
                fontSize: 13, fontWeight: 500,
              }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => {
                e.currentTarget.style.borderColor = 'var(--border-side, var(--border-sub))';
                setTimeout(() => onUpdate('partDropdownOpen', false), 150);
              }}
            />
          </div>

          {/* Catalogue dropdown */}
          {line.partDropdownOpen && line.partHits.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 200,
              background: 'var(--surface)', border: '1px solid var(--border-sub)',
              borderRadius: 4, boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
              overflow: 'hidden', marginTop: 2,
            }}>
              {line.partHits.map(hit => (
                <button
                  key={hit.id}
                  onMouseDown={() => onLinkPart(hit)}
                  style={{
                    display: 'grid', gridTemplateColumns: '1fr auto auto',
                    alignItems: 'center', gap: 12,
                    width: '100%', padding: '9px 12px',
                    background: 'none', border: 'none', cursor: 'pointer',
                    borderBottom: '1px solid var(--border-faint)', textAlign: 'left',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
                >
                  <span style={{ fontSize: 13, color: 'var(--txt1)', fontWeight: 500 }}>{hit.name}</span>
                  <span style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
                    {hit.part_number ?? '—'}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--txt-ghost)' }}>
                    {hit.unit ?? ''}
                  </span>
                </button>
              ))}
              <div style={{ padding: '6px 12px 7px' }}>
                <span style={{ fontSize: 10, color: 'var(--txt-ghost)' }}>
                  Not here? Keep typing to add manually.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Qty / Unit / Price row */}
        <div style={{ display: 'grid', gridTemplateColumns: '80px 80px 1fr', gap: 10 }}>
          <div>
            <div style={{ fontSize: 10, color: 'var(--txt-ghost)', marginBottom: 4, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Qty</div>
            <input
              type="number" min="0" step="any"
              value={line.quantity}
              onChange={e => onUpdate('quantity', e.target.value)}
              style={{ ...INPUT, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13 }}
            />
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--txt-ghost)', marginBottom: 4, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Unit</div>
            <input
              type="text"
              value={line.unit}
              onChange={e => onUpdate('unit', e.target.value)}
              placeholder="pcs"
              style={{ ...INPUT, fontSize: 12 }}
            />
          </div>
          <div>
            <div style={{ fontSize: 10, color: 'var(--txt-ghost)', marginBottom: 4, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Est. Price ({currency})
            </div>
            <input
              type="number" min="0" step="any"
              value={line.unit_price}
              onChange={e => onUpdate('unit_price', e.target.value)}
              placeholder="0.00"
              style={{ ...INPUT, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13 }}
            />
          </div>
        </div>
      </div>

      {/* ── Expanded detail section ── */}
      {line.expanded && (
        <div style={{
          padding: '14px 12px 16px',
          borderTop: '1px solid var(--border-faint)',
          background: 'var(--surface-hover)',
        }}>

          {/* Reason / Notes */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
              Reason for ordering
            </div>
            <textarea
              value={line.source_notes}
              onChange={e => onUpdate('source_notes', e.target.value)}
              placeholder="Why is this needed? Describe the context — worn component, stock depletion, planned maintenance..."
              rows={2}
              style={{
                ...INPUT, resize: 'vertical', lineHeight: 1.5,
                background: 'var(--surface)',
              }}
            />
          </div>

          {/* Urgency */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', marginBottom: 8 }}>
              Urgency
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
              {URGENCIES.map(u => {
                const active = line.urgency === u.value;
                return (
                  <button
                    key={u.value}
                    type="button"
                    onClick={() => onUpdate('urgency', u.value)}
                    style={{
                      padding: '8px 4px', borderRadius: 6, cursor: 'pointer',
                      border: active ? `2px solid ${u.color}` : '1px solid var(--border-sub)',
                      background: active ? u.bg : 'var(--surface)',
                      transition: 'all 80ms', textAlign: 'center',
                    }}
                  >
                    <div style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: u.color, margin: '0 auto 5px',
                    }} />
                    <div style={{
                      fontSize: 11, fontWeight: active ? 600 : 400,
                      color: active ? u.color : 'var(--txt2)',
                    }}>{u.label}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Required By + Part Number row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
                Required By
              </div>
              <input
                type="date"
                value={line.required_by_date}
                onChange={e => onUpdate('required_by_date', e.target.value)}
                style={{ ...INPUT, fontFamily: 'var(--font-mono)', fontSize: 12 }}
              />
            </div>
            <div>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
                Part Number
              </div>
              <input
                type="text"
                value={line.part_number}
                onChange={e => onUpdate('part_number', e.target.value)}
                placeholder="MAN-12345"
                style={{ ...INPUT, fontFamily: 'var(--font-mono)', fontSize: 12 }}
              />
            </div>
          </div>

          {/* Link Fault / Work Order */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--txt3)', letterSpacing: '0.06em', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
              Related Fault / Work Order ID
            </div>
            <div style={{ position: 'relative' }}>
              <Link2 style={{
                position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)',
                width: 11, height: 11, color: 'var(--txt-ghost)', pointerEvents: 'none',
              }} />
              <input
                type="text"
                value={line.source_work_order_id}
                onChange={e => onUpdate('source_work_order_id', e.target.value)}
                placeholder="Paste fault or work order UUID…"
                style={{ ...INPUT, paddingLeft: 28, fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
            </div>
            <p style={{ fontSize: 10, color: 'var(--txt-ghost)', margin: '4px 0 0' }}>
              Copy the ID from the fault or WO card. Links this purchase reason to the source event.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
