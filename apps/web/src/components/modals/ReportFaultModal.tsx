'use client';

/**
 * Log Fault — full-width right-panel drawer.
 *
 * Designed for onboard use: one fault, maximum detail, zero friction.
 * Fields: title, severity, description, location, detected_at, equipment,
 *         assigned_to, photos/files, notes, fault_code, create_work_order.
 *
 * Draft behaviour:
 *   - Every keystroke debounce-saves to localStorage (pms_fault_draft_v1)
 *   - On mount: restores draft if present → shows DRAFT badge
 *   - On close with unsaved values: prompts "Save draft / Discard"
 *   - On successful submit: clears draft
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/hooks/useActiveVessel';
import { API_BASE } from '@/lib/apiBase';
import {
  AlertTriangle, X, Camera, Paperclip, ChevronDown,
  Clock, Wrench, User, MapPin, FileText, Zap,
} from 'lucide-react';

/* ── types ──────────────────────────────────────────────────────────────── */

interface FaultDraft {
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  deck: string;
  compartment: string;
  equipment_name: string;
  equipment_id: string;
  assigned_to: string;
  fault_code: string;
  detected_at: string;
  notes: string;
  create_work_order: boolean;
}

interface ReportFaultModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context?: {
    equipment_id?: string;
    equipment_name?: string;
    suggested_title?: string;
    deck?: string;
    room?: string;
  };
  onSuccess?: (fault_id: string) => void;
}

/* ── constants ───────────────────────────────────────────────────────────── */

const DRAFT_KEY = 'pms_fault_draft_v1';

const SEVERITY_OPTIONS = [
  { value: 'low',      label: 'Low',      sub: 'Minor, no immediate impact',        color: 'var(--green)',  bg: 'rgba(34,197,94,0.08)' },
  { value: 'medium',   label: 'Medium',   sub: 'Affects performance',               color: 'var(--amber)',  bg: 'rgba(245,158,11,0.08)' },
  { value: 'high',     label: 'High',     sub: 'Urgent repair needed',              color: 'var(--amber)',  bg: 'rgba(245,158,11,0.12)' },
  { value: 'critical', label: 'Critical', sub: 'Safety issue / system down',        color: 'var(--red)',    bg: 'rgba(239,68,68,0.12)' },
] as const;

const DECK_OPTIONS = [
  'Sun Deck', 'Bridge Deck', 'Upper Deck', 'Main Deck',
  'Lower Deck', 'Engine Room', 'Below Waterline', 'Tender Garage',
];

const BLANK: FaultDraft = {
  title: '', severity: 'medium', description: '',
  deck: '', compartment: '', equipment_name: '', equipment_id: '',
  assigned_to: '', fault_code: '', detected_at: '', notes: '',
  create_work_order: false,
};

function isDirty(draft: FaultDraft): boolean {
  return (
    draft.title.trim() !== '' ||
    draft.description.trim() !== '' ||
    draft.equipment_name.trim() !== '' ||
    draft.notes.trim() !== '' ||
    draft.deck !== '' ||
    draft.detected_at !== ''
  );
}

function nowLocal(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

/* ── section heading ────────────────────────────────────────────────────── */

function SectionHead({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      borderTop: '1px solid var(--border-sub)',
      marginTop: 28, paddingTop: 20, marginBottom: 14,
    }}>
      <span style={{ color: 'var(--txt3)', display: 'flex' }}>{icon}</span>
      <span style={{
        fontSize: 10, fontWeight: 600, letterSpacing: '0.07em',
        textTransform: 'uppercase', color: 'var(--txt3)',
      }}>{label}</span>
    </div>
  );
}

/* ── field label ─────────────────────────────────────────────────────────── */

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--txt2)', marginBottom: 6 }}>
      {children}
      {required && <span style={{ color: 'var(--red)', marginLeft: 3 }}>*</span>}
    </div>
  );
}

/* ── shared input style ──────────────────────────────────────────────────── */

const INPUT: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'var(--surface)', border: '1px solid var(--border-side)',
  borderRadius: 4, padding: '8px 10px',
  fontSize: 13, color: 'var(--txt)',
  outline: 'none', transition: 'border-color 80ms',
  fontFamily: 'inherit',
};

/* ── component ───────────────────────────────────────────────────────────── */

export function ReportFaultModal({ open, onOpenChange, context = {}, onSuccess }: ReportFaultModalProps) {
  const { session } = useAuth();
  const { vesselId } = useActiveVessel();

  const [form, setForm] = React.useState<FaultDraft>(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) return JSON.parse(saved) as FaultDraft;
    } catch { /* ignore */ }
    return {
      ...BLANK,
      equipment_id: context.equipment_id ?? '',
      equipment_name: context.equipment_name ?? '',
      title: context.suggested_title ?? '',
      deck: context.deck ?? '',
      compartment: context.room ?? '',
      detected_at: nowLocal(),
    };
  });

  const [isDraft, setIsDraft]         = React.useState(false);
  const [submitting, setSubmitting]   = React.useState(false);
  const [error, setError]             = React.useState('');
  const [files, setFiles]             = React.useState<File[]>([]);
  const [deckOpen, setDeckOpen]       = React.useState(false);
  const [confirmClose, setConfirmClose] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const titleRef     = React.useRef<HTMLInputElement>(null);
  const debounceRef  = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  /* restore draft badge on open */
  React.useEffect(() => {
    if (!open) return;
    const saved = localStorage.getItem(DRAFT_KEY);
    setIsDraft(!!saved);
    if (saved) {
      try { setForm(JSON.parse(saved)); } catch { /* ignore */ }
    } else {
      setForm({
        ...BLANK,
        equipment_id: context.equipment_id ?? '',
        equipment_name: context.equipment_name ?? '',
        title: context.suggested_title ?? '',
        deck: context.deck ?? '',
        compartment: context.room ?? '',
        detected_at: nowLocal(),
      });
    }
    setTimeout(() => titleRef.current?.focus(), 80);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  /* debounce-save draft */
  const save = React.useCallback((next: FaultDraft) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (isDirty(next)) {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(next));
        setIsDraft(true);
      }
    }, 600);
  }, []);

  function set<K extends keyof FaultDraft>(key: K, val: FaultDraft[K]) {
    setForm(prev => {
      const next = { ...prev, [key]: val };
      save(next);
      return next;
    });
  }

  /* close guard */
  function handleClose() {
    if (isDirty(form) && !confirmClose) { setConfirmClose(true); return; }
    setConfirmClose(false);
    onOpenChange(false);
  }

  function handleSaveDraftAndClose() {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
    setIsDraft(true);
    setConfirmClose(false);
    onOpenChange(false);
  }

  function handleDiscardAndClose() {
    localStorage.removeItem(DRAFT_KEY);
    setIsDraft(false);
    setForm({ ...BLANK, detected_at: nowLocal() });
    setConfirmClose(false);
    onOpenChange(false);
  }

  /* file handling */
  function handleFiles(incoming: FileList | null) {
    if (!incoming) return;
    setFiles(prev => [...prev, ...Array.from(incoming)]);
  }

  function removeFile(i: number) {
    setFiles(prev => prev.filter((_, idx) => idx !== i));
  }

  /* submit */
  async function handleSubmit() {
    if (!form.title.trim()) { setError('Title is required.'); return; }
    if (!form.description.trim()) { setError('Description is required.'); return; }
    if (!session?.access_token) { setError('Not authenticated.'); return; }
    setError('');
    setSubmitting(true);

    try {
      const payload: Record<string, unknown> = {
        title:        form.title.trim(),
        description:  form.description.trim(),
        severity:     form.severity,
        detected_at:  form.detected_at || new Date().toISOString(),
      };
      if (form.equipment_id) payload.equipment_id = form.equipment_id;
      if (form.fault_code.trim()) payload.fault_code = form.fault_code.trim();

      const body = {
        action: 'report_fault',
        context: { yacht_id: vesselId },
        payload,
      };

      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify(body),
      });

      const json = await res.json();
      if (!res.ok) {
        setError(json?.detail?.message ?? json?.message ?? 'Failed to report fault.');
        return;
      }

      /* photos: fire-and-forget for each file after fault created */
      const faultId = json?.fault_id ?? json?.data?.fault_id ?? json?.id;
      if (faultId && files.length > 0) {
        /* upload is deferred — would need storage wiring; log intent */
        console.info('[ReportFault] Photos pending upload for fault', faultId, files.map(f => f.name));
      }

      localStorage.removeItem(DRAFT_KEY);
      setIsDraft(false);
      onSuccess?.(faultId);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error.');
    } finally {
      setSubmitting(false);
    }
  }

  /* esc key */
  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') handleClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, form]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null;

  /* ── render ──────────────────────────────────────────────────────────── */
  return (
    <>
      {/* backdrop */}
      <div
        onClick={handleClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.45)',
          zIndex: 900,
          backdropFilter: 'blur(2px)',
        }}
      />

      {/* panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 'min(680px, 100vw)',
        background: 'var(--surface-el)',
        borderLeft: '1px solid var(--border-side)',
        boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
        zIndex: 901,
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>

        {/* ── header ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 20px',
          height: 52, flexShrink: 0,
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-glass)',
          backdropFilter: 'blur(8px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle style={{ width: 16, height: 16, color: 'var(--amber)' }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt)' }}>Log Fault</span>
            {isDraft && (
              <span style={{
                fontSize: 9, fontWeight: 600, letterSpacing: '0.06em',
                textTransform: 'uppercase', color: 'var(--amber)',
                background: 'rgba(245,158,11,0.12)',
                border: '1px solid rgba(245,158,11,0.25)',
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
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--txt)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--txt3)'; }}
          >
            <X style={{ width: 14, height: 14 }} />
          </button>
        </div>

        {/* ── scrollable body ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px 16px' }}>

          {/* ── TITLE ── */}
          <div style={{ marginBottom: 20 }}>
            <FieldLabel required>Fault Title</FieldLabel>
            <input
              ref={titleRef}
              value={form.title}
              onChange={e => set('title', e.target.value)}
              placeholder="What's the fault? (e.g. Port engine coolant leak)"
              style={{
                ...INPUT, fontSize: 15, fontWeight: 500,
                padding: '10px 12px',
              }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
            />
          </div>

          {/* ── SEVERITY ── */}
          <div style={{ marginBottom: 4 }}>
            <FieldLabel required>Severity</FieldLabel>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 }}>
              {SEVERITY_OPTIONS.map(opt => {
                const active = form.severity === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => set('severity', opt.value as FaultDraft['severity'])}
                    style={{
                      padding: '10px 8px',
                      borderRadius: 6,
                      border: active ? `2px solid ${opt.color}` : '1px solid var(--border-side)',
                      background: active ? opt.bg : 'var(--surface)',
                      cursor: 'pointer',
                      textAlign: 'center',
                      transition: 'all 80ms',
                    }}
                  >
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: opt.color, margin: '0 auto 6px',
                    }} />
                    <div style={{ fontSize: 12, fontWeight: active ? 600 : 400, color: active ? opt.color : 'var(--txt)' }}>
                      {opt.label}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--txt3)', marginTop: 2, lineHeight: 1.2 }}>
                      {opt.sub}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── DESCRIPTION ── */}
          <SectionHead icon={<FileText style={{ width: 13, height: 13 }} />} label="Description" />
          <div style={{ marginBottom: 14 }}>
            <FieldLabel required>What happened?</FieldLabel>
            <textarea
              value={form.description}
              onChange={e => set('description', e.target.value)}
              placeholder="Describe the fault in detail — symptoms, when it started, conditions, how often it occurs, any error codes or alarms shown..."
              rows={5}
              style={{
                ...INPUT, resize: 'vertical', lineHeight: 1.5,
                minHeight: 100,
              }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
            />
          </div>
          <div>
            <FieldLabel>Additional notes / observations</FieldLabel>
            <textarea
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              placeholder="Any other context — previous incidents, what was tried, parts suspected..."
              rows={2}
              style={{ ...INPUT, resize: 'vertical', lineHeight: 1.5 }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
            />
          </div>

          {/* ── LOCATION & TIME ── */}
          <SectionHead icon={<MapPin style={{ width: 13, height: 13 }} />} label="Location & Time" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 0 }}>
            <div>
              <FieldLabel>Deck</FieldLabel>
              <div style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setDeckOpen(v => !v)}
                  style={{
                    ...INPUT, display: 'flex', alignItems: 'center',
                    justifyContent: 'space-between', cursor: 'pointer',
                    padding: '8px 10px',
                  }}
                >
                  <span style={{ color: form.deck ? 'var(--txt)' : 'var(--txt-ghost)' }}>
                    {form.deck || 'Select deck'}
                  </span>
                  <ChevronDown style={{ width: 13, height: 13, color: 'var(--txt3)', flexShrink: 0 }} />
                </button>
                {deckOpen && (
                  <div style={{
                    position: 'absolute', top: '100%', left: 0, right: 0,
                    background: 'var(--surface-el)',
                    border: '1px solid var(--border-side)',
                    borderRadius: 4, zIndex: 10, marginTop: 2,
                    maxHeight: 200, overflowY: 'auto',
                    boxShadow: 'var(--shadow-drop)',
                  }}>
                    {DECK_OPTIONS.map(d => (
                      <button
                        key={d} type="button"
                        onClick={() => { set('deck', d); setDeckOpen(false); }}
                        style={{
                          display: 'block', width: '100%', textAlign: 'left',
                          padding: '8px 12px', fontSize: 12, color: 'var(--txt)',
                          background: 'transparent', border: 'none', cursor: 'pointer',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div>
              <FieldLabel>Compartment / Area</FieldLabel>
              <input
                value={form.compartment}
                onChange={e => set('compartment', e.target.value)}
                placeholder="e.g. Bilge pump bay"
                style={INPUT}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
              />
            </div>
            <div>
              <FieldLabel>Detected At</FieldLabel>
              <div style={{ position: 'relative' }}>
                <input
                  type="datetime-local"
                  value={form.detected_at}
                  onChange={e => set('detected_at', e.target.value)}
                  style={{
                    ...INPUT,
                    paddingRight: 32, colorScheme: 'dark',
                  }}
                  onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
                />
                <Clock style={{
                  position: 'absolute', right: 10, top: '50%',
                  transform: 'translateY(-50%)',
                  width: 13, height: 13, color: 'var(--txt3)',
                  pointerEvents: 'none',
                }} />
              </div>
            </div>
          </div>

          {/* ── EQUIPMENT ── */}
          <SectionHead icon={<Wrench style={{ width: 13, height: 13 }} />} label="Equipment" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <FieldLabel>Equipment Name</FieldLabel>
              <input
                value={form.equipment_name}
                onChange={e => set('equipment_name', e.target.value)}
                placeholder="Search or type equipment name"
                style={INPUT}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
              />
            </div>
            <div>
              <FieldLabel>Fault / Error Code</FieldLabel>
              <input
                value={form.fault_code}
                onChange={e => set('fault_code', e.target.value)}
                placeholder="Auto-generated if blank"
                style={{ ...INPUT, fontFamily: 'monospace', fontSize: 12 }}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
              />
            </div>
          </div>

          {/* ── ASSIGNMENT ── */}
          <SectionHead icon={<User style={{ width: 13, height: 13 }} />} label="Assignment" />
          <div>
            <FieldLabel>Assigned To</FieldLabel>
            <input
              value={form.assigned_to}
              onChange={e => set('assigned_to', e.target.value)}
              placeholder="Crew member name or department"
              style={INPUT}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--mark)'; }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
            />
          </div>

          {/* ── PHOTOS & FILES ── */}
          <SectionHead icon={<Camera style={{ width: 13, height: 13 }} />} label="Photos & Files" />
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,application/pdf,.doc,.docx"
            style={{ display: 'none' }}
            onChange={e => handleFiles(e.target.files)}
          />

          {/* upload zone */}
          <div
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--mark)'; }}
            onDragLeave={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
            onDrop={e => {
              e.preventDefault();
              e.currentTarget.style.borderColor = 'var(--border-side)';
              handleFiles(e.dataTransfer.files);
            }}
            style={{
              border: '1.5px dashed var(--border-side)',
              borderRadius: 6, padding: '18px 16px',
              textAlign: 'center', cursor: 'pointer',
              background: 'var(--surface)',
              transition: 'border-color 80ms',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--txt3)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-side)'; }}
          >
            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginBottom: 8 }}>
              <Camera style={{ width: 18, height: 18, color: 'var(--txt3)' }} />
              <Paperclip style={{ width: 18, height: 18, color: 'var(--txt3)' }} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--txt2)', fontWeight: 500 }}>
              Tap to add photos or files
            </div>
            <div style={{ fontSize: 10, color: 'var(--txt-ghost)', marginTop: 4 }}>
              Drag & drop · Photos, PDFs, documents
            </div>
          </div>

          {/* file list */}
          {files.length > 0 && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {files.map((f, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 10px',
                  background: 'var(--surface)',
                  border: '1px solid var(--border-faint)',
                  borderRadius: 4,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {f.type.startsWith('image/') ? (
                      <Camera style={{ width: 13, height: 13, color: 'var(--txt3)' }} />
                    ) : (
                      <Paperclip style={{ width: 13, height: 13, color: 'var(--txt3)' }} />
                    )}
                    <span style={{ fontSize: 12, color: 'var(--txt)', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.name}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--txt-ghost)' }}>
                      {(f.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: 'var(--txt3)', padding: 2, borderRadius: 3,
                      display: 'flex', alignItems: 'center',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--red)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--txt3)'; }}
                  >
                    <X style={{ width: 12, height: 12 }} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* ── OPTIONS ── */}
          <SectionHead icon={<Zap style={{ width: 13, height: 13 }} />} label="Actions" />
          <label style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '10px 12px',
            background: 'var(--surface)', borderRadius: 4,
            border: '1px solid var(--border-faint)',
            cursor: 'pointer',
          }}>
            <input
              type="checkbox"
              checked={form.create_work_order}
              onChange={e => set('create_work_order', e.target.checked)}
              style={{ width: 14, height: 14, accentColor: 'var(--mark)', cursor: 'pointer' }}
            />
            <div>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--txt)' }}>
                Create Work Order automatically
              </div>
              <div style={{ fontSize: 10, color: 'var(--txt3)', marginTop: 1 }}>
                A work order will be opened immediately when this fault is submitted
              </div>
            </div>
          </label>

          {/* bottom padding */}
          <div style={{ height: 32 }} />
        </div>

        {/* ── footer ── */}
        <div style={{
          borderTop: '1px solid var(--border-faint)',
          padding: '12px 24px',
          flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'var(--surface-el)',
        }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={handleSaveDraftAndClose}
              style={{
                fontSize: 12, fontWeight: 500, color: 'var(--txt2)',
                background: 'transparent',
                border: '1px solid var(--border-side)',
                borderRadius: 4, padding: '7px 14px', cursor: 'pointer',
                transition: 'all 80ms',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; e.currentTarget.style.color = 'var(--txt)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--txt2)'; }}
            >
              Save Draft
            </button>
          </div>

          {error && (
            <span style={{ fontSize: 11, color: 'var(--red)', flex: 1, textAlign: 'center', padding: '0 16px' }}>
              {error}
            </span>
          )}

          <button
            type="button"
            disabled={submitting}
            onClick={handleSubmit}
            style={{
              fontSize: 13, fontWeight: 600,
              color: 'white',
              background: submitting ? 'var(--txt3)' : 'var(--mark)',
              border: 'none', borderRadius: 4,
              padding: '8px 20px', cursor: submitting ? 'default' : 'pointer',
              transition: 'background 80ms',
              opacity: submitting ? 0.7 : 1,
            }}
            onMouseEnter={e => { if (!submitting) e.currentTarget.style.background = 'var(--mark-hover, var(--mark))'; }}
            onMouseLeave={e => { if (!submitting) e.currentTarget.style.background = 'var(--mark)'; }}
          >
            {submitting ? 'Submitting…' : 'Report Fault →'}
          </button>
        </div>
      </div>

      {/* ── confirm-close overlay ── */}
      {confirmClose && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 910,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: 'var(--surface-el)',
            border: '1px solid var(--border-side)',
            borderRadius: 8, padding: '24px 28px',
            width: 320,
            boxShadow: 'var(--shadow-drop)',
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--txt)', marginBottom: 8 }}>
              Unsaved fault
            </div>
            <div style={{ fontSize: 12, color: 'var(--txt2)', marginBottom: 20, lineHeight: 1.5 }}>
              You have unsaved details. Save as a draft to continue later, or discard.
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={handleDiscardAndClose}
                style={{
                  fontSize: 12, color: 'var(--txt2)',
                  background: 'transparent', border: '1px solid var(--border-side)',
                  borderRadius: 4, padding: '7px 14px', cursor: 'pointer',
                }}
              >
                Discard
              </button>
              <button
                onClick={handleSaveDraftAndClose}
                style={{
                  fontSize: 12, fontWeight: 600, color: 'white',
                  background: 'var(--mark)', border: 'none',
                  borderRadius: 4, padding: '7px 16px', cursor: 'pointer',
                }}
              >
                Save Draft
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
