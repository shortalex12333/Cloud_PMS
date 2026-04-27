'use client';

/**
 * CreateWorkOrderModal — full-panel draft card for new work orders.
 *
 * Design contract:
 *   - Covers 96 vh, max 960 px wide, two-column layout.
 *   - Every field that matters for a real vessel WO is present.
 *   - Draft-on-exit: if title is filled and user closes without submitting,
 *     the WO is auto-saved with status='draft' and a toast confirms it.
 *   - Submitting normally creates with status='open'.
 *   - Files/photos: add from the WO card after creation (entity must exist first).
 *
 * Crash fix (React #185 — max update depth):
 *   The previous version used `context` object as a useEffect dependency.
 *   Default `context = {}` created a new reference every render → infinite loop.
 *   This version uses plain React.useState — no react-hook-form, no zod, no
 *   useEffect with object deps.
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { useRouter } from 'next/navigation';

// ── Types ──────────────────────────────────────────────────────────────────

export interface CreateWOContext {
  equipment_id?: string;
  equipment_name?: string;
  fault_id?: string;
  fault_title?: string;
  suggested_title?: string;
  suggested_description?: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: CreateWOContext;
  onSuccess?: (workOrderId: string) => void;
}

type WOType = 'corrective' | 'scheduled' | 'unplanned' | 'preventive';
type WOPriority = 'routine' | 'important' | 'critical' | 'emergency';
type WOSeverity = '' | 'low' | 'medium' | 'high' | 'critical';
type WOFrequency = '' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annual';

interface FormState {
  title: string;
  description: string;
  wo_type: WOType;
  priority: WOPriority;
  severity: WOSeverity;
  due_date: string;
  estimated_hours: string;
  estimated_minutes: string;
  frequency: WOFrequency;
  assigned_to: string;
  equipment_id: string;
  equipment_name_display: string;
  fault_id: string;
  fault_display: string;
  system_name: string;
  note_text: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function hasContent(f: FormState): boolean {
  return !!(
    f.title.trim() ||
    f.description.trim() ||
    f.assigned_to.trim() ||
    f.note_text.trim()
  );
}

function calcDurationMinutes(hours: string, mins: string): number | undefined {
  const h = parseInt(hours, 10) || 0;
  const m = parseInt(mins, 10) || 0;
  const total = h * 60 + m;
  return total > 0 ? total : undefined;
}

// ── Component ──────────────────────────────────────────────────────────────

export function CreateWorkOrderModal({ open, onOpenChange, context, onSuccess }: Props) {
  const { session, user } = useAuth();
  const { vesselId } = useActiveVessel();
  const router = useRouter();

  const initialState = (): FormState => ({
    title: context?.suggested_title ?? '',
    description: context?.suggested_description ?? '',
    wo_type: 'corrective',
    priority: 'routine',
    severity: '',
    due_date: '',
    estimated_hours: '',
    estimated_minutes: '',
    frequency: '',
    assigned_to: '',
    equipment_id: context?.equipment_id ?? '',
    equipment_name_display: context?.equipment_name ?? '',
    fault_id: context?.fault_id ?? '',
    fault_display: context?.fault_title ?? '',
    system_name: '',
    note_text: '',
  });

  const [form, setForm] = React.useState<FormState>(initialState);
  const [submitting, setSubmitting] = React.useState(false);
  const [toast, setToast] = React.useState<{ msg: string; ok: boolean } | null>(null);

  // Reset when modal opens (primitive deps — no object reference loop)
  const ctxEquipId = context?.equipment_id ?? '';
  const ctxEquipName = context?.equipment_name ?? '';
  const ctxFaultId = context?.fault_id ?? '';
  const ctxFaultTitle = context?.fault_title ?? '';
  const ctxTitle = context?.suggested_title ?? '';
  const ctxDesc = context?.suggested_description ?? '';

  React.useEffect(() => {
    if (!open) return;
    setForm({
      title: ctxTitle,
      description: ctxDesc,
      wo_type: 'corrective',
      priority: 'routine',
      severity: '',
      due_date: '',
      estimated_hours: '',
      estimated_minutes: '',
      frequency: '',
      assigned_to: '',
      equipment_id: ctxEquipId,
      equipment_name_display: ctxEquipName,
      fault_id: ctxFaultId,
      fault_display: ctxFaultTitle,
      system_name: '',
      note_text: '',
    });
    setSubmitting(false);
    setToast(null);
  }, [open, ctxTitle, ctxDesc, ctxEquipId, ctxEquipName, ctxFaultId, ctxFaultTitle]);

  // Keyboard: Escape closes (with draft logic)
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, form]);

  const set = (field: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  // ── Submit ────────────────────────────────────────────────────────────────

  const submit = React.useCallback(
    async (status: 'open' | 'draft') => {
      if (submitting) return null;
      if (!form.title.trim()) {
        setToast({ msg: 'Title is required.', ok: false });
        setTimeout(() => setToast(null), 3000);
        return null;
      }

      const yachtId = vesselId ?? user?.yachtId ?? null;
      if (!yachtId) {
        setToast({ msg: 'No vessel selected.', ok: false });
        setTimeout(() => setToast(null), 3000);
        return null;
      }

      setSubmitting(true);
      try {
        const payload: Record<string, unknown> = {
          title: form.title.trim(),
          work_order_type: form.wo_type,
          priority: form.priority,
          status,
        };
        if (form.description.trim()) payload.description = form.description.trim();
        if (form.severity) payload.severity = form.severity;
        if (form.due_date) payload.due_date = form.due_date;
        const durMins = calcDurationMinutes(form.estimated_hours, form.estimated_minutes);
        if (durMins) payload.estimated_duration_minutes = durMins;
        if (form.frequency) payload.frequency = form.frequency;
        if (form.assigned_to.trim()) payload.assigned_to = form.assigned_to.trim();
        if (form.equipment_id.trim()) payload.equipment_id = form.equipment_id.trim();
        if (form.fault_id.trim()) payload.fault_id = form.fault_id.trim();
        if (form.system_name.trim()) payload.system_name = form.system_name.trim();
        if (form.note_text.trim()) payload.note_text = form.note_text.trim();

        const res = await fetch('/api/v1/actions/execute', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session?.access_token ?? ''}`,
          },
          body: JSON.stringify({
            action: 'create_work_order',
            context: { yacht_id: yachtId },
            payload,
          }),
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data?.detail?.message ?? data?.error ?? `Error ${res.status}`);
        }

        const woId = (data?.work_order_id ?? data?.data?.work_order_id) as string | undefined;

        if (status === 'draft') {
          setToast({ msg: 'Saved as draft.', ok: true });
          setTimeout(() => {
            setToast(null);
            onOpenChange(false);
            if (woId) router.push(`/work-orders?entity=${woId}`);
          }, 1200);
        } else {
          onOpenChange(false);
          if (onSuccess && woId) onSuccess(woId);
          else if (woId) router.push(`/work-orders?entity=${woId}`);
        }
        return woId ?? null;
      } catch (err) {
        setToast({ msg: err instanceof Error ? err.message : 'Failed to create.', ok: false });
        setTimeout(() => setToast(null), 4000);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [form, submitting, session, vesselId, user, onOpenChange, onSuccess, router]
  );

  // ── Close with draft-on-exit ──────────────────────────────────────────────

  const handleClose = React.useCallback(() => {
    if (hasContent(form) && !submitting) {
      // Auto-save as draft — no confirmation dialog, just save + toast
      submit('draft');
    } else {
      onOpenChange(false);
    }
  }, [form, submitting, submit, onOpenChange]);

  if (!open) return null;

  const canSubmit = form.title.trim().length > 0 && !submitting;

  // ── Styles ────────────────────────────────────────────────────────────────

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 6,
    border: '1px solid var(--border-sub)',
    background: 'var(--bg)',
    color: 'var(--txt)',
    fontSize: 13,
    fontFamily: 'var(--font-sans)',
    boxSizing: 'border-box',
  };

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    color: 'var(--txt2)',
    marginBottom: 5,
  };

  const sectionHeadStyle: React.CSSProperties = {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--txt3)',
    borderBottom: '1px solid var(--border-faint)',
    paddingBottom: 6,
    marginBottom: 12,
    marginTop: 20,
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={handleClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 400,
          background: 'var(--overlay-heavy)',
        }}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="New Work Order"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'fixed',
          top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 401,
          width: '96vw',
          maxWidth: 960,
          maxHeight: '96vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--surface)',
          border: '1px solid var(--border-faint)',
          borderRadius: 12,
          boxShadow: 'var(--shadow-card)',
          overflow: 'hidden',
        }}
      >
        {/* ── Header ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-faint)',
          flexShrink: 0,
        }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--txt)' }}>
              New Work Order
            </div>
            <div style={{ fontSize: 12, color: 'var(--txt3)', marginTop: 2 }}>
              {ctxEquipName
                ? `Creating for ${ctxEquipName}`
                : 'Fill what you know — close to save as draft.'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => submit('draft')}
              disabled={!canSubmit}
              style={{
                padding: '7px 14px', borderRadius: 6,
                border: '1px solid var(--border-sub)',
                background: 'transparent',
                color: canSubmit ? 'var(--txt2)' : 'var(--txt3)',
                fontSize: 12, fontWeight: 500, cursor: canSubmit ? 'pointer' : 'not-allowed',
                fontFamily: 'var(--font-sans)',
              }}
            >
              Save Draft
            </button>
            <button
              type="button"
              onClick={() => submit('open')}
              disabled={!canSubmit}
              style={{
                padding: '7px 16px', borderRadius: 6, border: 'none',
                background: canSubmit ? 'var(--mark)' : 'var(--border-faint)',
                color: canSubmit ? 'var(--surface)' : 'var(--txt3)',
                fontSize: 13, fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed',
                fontFamily: 'var(--font-sans)',
              }}
            >
              {submitting ? 'Creating…' : 'Create Work Order'}
            </button>
            <button
              type="button"
              onClick={handleClose}
              aria-label="Close"
              style={{
                appearance: 'none', WebkitAppearance: 'none',
                background: 'transparent', border: '1px solid var(--border-sub)',
                borderRadius: 6, padding: '6px 10px', cursor: 'pointer',
                color: 'var(--txt2)', fontSize: 14, lineHeight: 1,
                fontFamily: 'var(--font-sans)',
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* ── Body (scrollable) ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 340px',
            gap: 32,
            alignItems: 'start',
          }}>

            {/* ── LEFT COLUMN ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* Title */}
              <div>
                <label style={labelStyle}>
                  Title <span style={{ color: 'var(--red)' }}>*</span>
                </label>
                <input
                  value={form.title}
                  onChange={set('title')}
                  placeholder="e.g. Replace main engine raw water pump impeller"
                  autoFocus
                  style={{ ...inputStyle, fontSize: 15, fontWeight: 500, padding: '11px 12px' }}
                />
              </div>

              {/* Description */}
              <div>
                <label style={labelStyle}>Description / Scope of Work</label>
                <textarea
                  value={form.description}
                  onChange={set('description')}
                  placeholder="Describe the work in detail — symptoms observed, parts needed, steps, safety considerations…"
                  rows={6}
                  style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55 }}
                />
              </div>

              {/* Type + Priority */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Type <span style={{ color: 'var(--red)' }}>*</span></label>
                  <select value={form.wo_type} onChange={set('wo_type')} style={inputStyle}>
                    <option value="corrective">Corrective</option>
                    <option value="scheduled">Scheduled / PM</option>
                    <option value="unplanned">Unplanned</option>
                    <option value="preventive">Preventive</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Priority <span style={{ color: 'var(--red)' }}>*</span></label>
                  <select value={form.priority} onChange={set('priority')} style={inputStyle}>
                    <option value="routine">Routine</option>
                    <option value="important">Important</option>
                    <option value="critical">Critical</option>
                    <option value="emergency">Emergency</option>
                  </select>
                </div>
              </div>

              {/* Severity + Due Date */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Severity</label>
                  <select value={form.severity} onChange={set('severity')} style={inputStyle}>
                    <option value="">— Not assessed —</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Due Date</label>
                  <input
                    type="date"
                    value={form.due_date}
                    onChange={set('due_date')}
                    style={inputStyle}
                  />
                </div>
              </div>

              {/* Est. Duration */}
              <div>
                <label style={labelStyle}>Estimated Duration</label>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input
                    type="number"
                    min="0"
                    max="999"
                    value={form.estimated_hours}
                    onChange={set('estimated_hours')}
                    placeholder="0"
                    style={{ ...inputStyle, width: 80 }}
                  />
                  <span style={{ color: 'var(--txt3)', fontSize: 12 }}>hrs</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={form.estimated_minutes}
                    onChange={set('estimated_minutes')}
                    placeholder="0"
                    style={{ ...inputStyle, width: 80 }}
                  />
                  <span style={{ color: 'var(--txt3)', fontSize: 12 }}>min</span>
                </div>
              </div>

              {/* Frequency (only for scheduled) */}
              {form.wo_type === 'scheduled' && (
                <div>
                  <label style={labelStyle}>Recurrence Frequency</label>
                  <select value={form.frequency} onChange={set('frequency')} style={inputStyle}>
                    <option value="">— One-off —</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="annual">Annual</option>
                  </select>
                </div>
              )}

              {/* Initial Note */}
              <div>
                <div style={sectionHeadStyle}>Initial Note</div>
                <textarea
                  value={form.note_text}
                  onChange={set('note_text')}
                  placeholder="Capture initial observations, context, or instructions. This becomes the first note on the WO."
                  rows={4}
                  style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55 }}
                />
              </div>

              {/* Files notice */}
              <div style={{
                padding: '10px 14px',
                background: 'var(--teal-bg)',
                border: '1px solid var(--mark-hover)',
                borderRadius: 6,
                fontSize: 12,
                color: 'var(--mark)',
              }}>
                Photos &amp; documents can be attached from the Work Order card after creation. Create first, then open the card.
              </div>
            </div>

            {/* ── RIGHT COLUMN ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

              <div style={{ ...sectionHeadStyle, marginTop: 0 }}>Assignment</div>

              <div>
                <label style={labelStyle}>Assign To</label>
                <input
                  value={form.assigned_to}
                  onChange={set('assigned_to')}
                  placeholder="Crew member name or ID"
                  style={inputStyle}
                />
                <div style={{ fontSize: 11, color: 'var(--txt3)', marginTop: 4 }}>
                  Leave blank — assign later from the WO card.
                </div>
              </div>

              <div style={{ ...sectionHeadStyle }}>Links</div>

              {/* Equipment */}
              <div>
                <label style={labelStyle}>Equipment</label>
                {ctxEquipName ? (
                  <div style={{
                    padding: '9px 12px', borderRadius: 6,
                    border: '1px solid var(--border-faint)',
                    background: 'var(--neutral-bg)',
                    fontSize: 13, color: 'var(--txt2)',
                  }}>
                    {ctxEquipName}
                  </div>
                ) : (
                  <input
                    value={form.equipment_name_display}
                    onChange={(e) => setForm((p) => ({
                      ...p,
                      equipment_name_display: e.target.value,
                      equipment_id: '', // cleared until lookup is built
                    }))}
                    placeholder="Search equipment by name (coming soon)"
                    disabled
                    style={{ ...inputStyle, opacity: 0.6, cursor: 'not-allowed' }}
                  />
                )}
              </div>

              {/* Fault link */}
              <div>
                <label style={labelStyle}>Linked Fault</label>
                {ctxFaultTitle ? (
                  <div style={{
                    padding: '9px 12px', borderRadius: 6,
                    border: '1px solid var(--border-faint)',
                    background: 'var(--neutral-bg)',
                    fontSize: 13, color: 'var(--txt2)',
                  }}>
                    {ctxFaultTitle}
                  </div>
                ) : (
                  <input
                    value={form.fault_display}
                    onChange={(e) => setForm((p) => ({ ...p, fault_display: e.target.value, fault_id: '' }))}
                    placeholder="Link from Fault card (coming soon)"
                    disabled
                    style={{ ...inputStyle, opacity: 0.6, cursor: 'not-allowed' }}
                  />
                )}
              </div>

              {/* System */}
              <div>
                <label style={labelStyle}>System / Area</label>
                <input
                  value={form.system_name}
                  onChange={set('system_name')}
                  placeholder="e.g. Propulsion, HVAC, Electrical"
                  style={inputStyle}
                />
              </div>

              {/* Priority quick-pick visual */}
              <div style={{ ...sectionHeadStyle }}>Priority Reference</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {([
                  ['emergency', 'var(--red)', 'Vessel safety / seaworthiness at risk'],
                  ['critical', 'var(--red)', 'Operation degraded, fix within 24h'],
                  ['important', 'var(--amber)', 'Fix this week, workaround in place'],
                  ['routine', 'var(--txt3)', 'Schedule during next maintenance window'],
                ] as [WOPriority, string, string][]).map(([val, colour, hint]) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setForm((p) => ({ ...p, priority: val }))}
                    style={{
                      appearance: 'none', WebkitAppearance: 'none',
                      textAlign: 'left', padding: '8px 10px', borderRadius: 6,
                      border: `1px solid ${form.priority === val ? colour : 'var(--border-faint)'}`,
                      background: form.priority === val ? 'var(--neutral-bg)' : 'transparent',
                      cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'flex-start',
                    }}
                  >
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: colour, flexShrink: 0, marginTop: 4 }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: colour, textTransform: 'capitalize' }}>{val}</div>
                      <div style={{ fontSize: 11, color: 'var(--txt3)', marginTop: 1 }}>{hint}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── Footer ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 24px',
          borderTop: '1px solid var(--border-faint)',
          flexShrink: 0,
          background: 'var(--surface)',
        }}>
          <div style={{ fontSize: 12, color: 'var(--txt3)' }}>
            {hasContent(form) ? 'Close will auto-save as draft.' : 'Nothing entered — close will discard.'}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={handleClose}
              style={{
                padding: '8px 16px', borderRadius: 6,
                border: '1px solid var(--border-sub)',
                background: 'transparent', color: 'var(--txt2)',
                fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-sans)',
              }}
            >
              {hasContent(form) ? 'Save & Close' : 'Cancel'}
            </button>
            <button
              type="button"
              onClick={() => submit('open')}
              disabled={!canSubmit}
              style={{
                padding: '8px 20px', borderRadius: 6, border: 'none',
                background: canSubmit ? 'var(--mark)' : 'var(--border-faint)',
                color: canSubmit ? 'var(--surface)' : 'var(--txt3)',
                fontSize: 13, fontWeight: 600,
                cursor: canSubmit ? 'pointer' : 'not-allowed',
                fontFamily: 'var(--font-sans)',
              }}
            >
              {submitting ? 'Creating…' : 'Create Work Order'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 28, right: 28, zIndex: 9999,
          padding: '11px 18px', borderRadius: 8,
          background: toast.ok ? 'var(--green-bg)' : 'var(--red-bg)',
          color: toast.ok ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${toast.ok ? 'var(--green)' : 'var(--red)'}`,
          fontSize: 13, fontWeight: 500, maxWidth: 320,
          boxShadow: 'var(--shadow-card)',
        }}>
          {toast.msg}
        </div>
      )}
    </>
  );
}
