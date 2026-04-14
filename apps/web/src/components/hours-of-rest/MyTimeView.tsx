'use client';

/**
 * MyTimeView — every role's primary HoR surface
 *
 * Shows:
 * - Week grid (Mon–Sun) with TimeSlider per unsubmitted day
 * - "Submit Day" per day, "Submit Week For Approval" for weekly sign
 * - Compliance card (24h rolling, 7-day, MLC status)
 * - Monthly sign-off card
 * - Template selector
 * - Collapsible history (prior weeks)
 */

import * as React from 'react';
import { supabase } from '@/lib/supabaseClient';
import { TimeSlider, invertToRestPeriods, type RestPeriod } from './TimeSlider';
import { ActionPopup, type ActionPopupField } from '@/components/lens-v2/ActionPopup';

// ── Mock data (used until ENGINEER02 endpoints land) ──────────────────────────

const MOCK_MY_WEEK = {
  week_start: '2026-04-07',
  days: [
    { date: '2026-04-07', label: 'Mon', rest_periods: [{ start: '00:00', end: '05:00' }, { start: '14:00', end: '22:00' }], total_rest_hours: 13, total_work_hours: 11, is_compliant: true, submitted: true, warnings: [] },
    { date: '2026-04-08', label: 'Tue', rest_periods: [{ start: '00:00', end: '04:00' }, { start: '14:00', end: '22:00' }], total_rest_hours: 12, total_work_hours: 12, is_compliant: true, submitted: true, warnings: [] },
    { date: '2026-04-09', label: 'Wed', rest_periods: [{ start: '00:00', end: '04:00' }, { start: '14:00', end: '22:00' }], total_rest_hours: 12, total_work_hours: 12, is_compliant: true, submitted: true, warnings: [] },
    { date: '2026-04-10', label: 'Thu', rest_periods: [{ start: '00:00', end: '04:00' }, { start: '15:00', end: '22:00' }], total_rest_hours: 11, total_work_hours: 13, is_compliant: true, submitted: true, warnings: [] },
    { date: '2026-04-11', label: 'Fri', rest_periods: [], total_rest_hours: 0, total_work_hours: 0, is_compliant: null, submitted: false, warnings: [] },
    { date: '2026-04-12', label: 'Sat', rest_periods: [], total_rest_hours: 0, total_work_hours: 0, is_compliant: null, submitted: false, warnings: [] },
    { date: '2026-04-13', label: 'Sun', rest_periods: [], total_rest_hours: 0, total_work_hours: 0, is_compliant: null, submitted: false, warnings: [] },
  ],
  compliance: {
    rolling_24h_rest: 13,
    rolling_7day_rest: 48,
    rolling_7d_work: 48,
    mlc_status: 'COMPLIANT',
    min_24h: 10,
    min_7d: 77,
    violations_this_month: 0,
  },
  pending_signoff: {
    id: 'mock-signoff-1',
    month: '2026-03',
    month_label: 'March 2026',
    status: 'draft',
  },
  templates: [
    { id: 'tpl-1', name: '4-on/8-off Watch System' },
  ],
  prior_weeks: [
    { week_start: '2026-03-31', label: 'Mar 31 – Apr 6', total_rest_hours: 85, is_compliant: true },
    { week_start: '2026-03-24', label: 'Mar 24 – Mar 30', total_rest_hours: 82, is_compliant: true },
  ],
};

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── Helpers ───────────────────────────────────────────────────────────────────

/** API returns null for days with no submitted record — replace with an empty unsubmitted slot */
function normalizeDays(days: any[], weekStart: string): any[] {
  return days.map((d, i) => {
    if (d != null) return d;
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return {
      date: date.toISOString().slice(0, 10),
      label: DAY_LABELS[i],
      rest_periods: [],
      total_rest_hours: 0,
      total_work_hours: 0,
      is_compliant: null,
      submitted: false,
      warnings: [],
    };
  });
}

/**
 * Normalises the real API response shape to what the component expects.
 * Real API deviations:
 *  - compliance is flat: {rolling_24h_rest, rolling_7day_rest} — missing mlc_status, min_*, violations_this_month, rolling_7d_work
 *  - prior_weeks may be absent (backend feature not yet implemented)
 *  - templates[].name (backend renames schedule_name → name in response)
 *  - days[].record_date instead of date; no label field
 */
function normalizeMyWeekResponse(json: any): void {
  // 1. Derive day.date + day.label from record_date / week_start index
  if (Array.isArray(json.days)) {
    const weekStart = json.week_start ?? '';
    json.days = json.days.map((d: any, i: number) => {
      if (d == null) return d; // normalizeDays handles null slots
      const date = d.date ?? d.record_date ?? (() => {
        const dt = new Date(weekStart);
        dt.setDate(dt.getDate() + i);
        return dt.toISOString().slice(0, 10);
      })();
      const label = d.label ?? DAY_LABELS[i];
      // Remap is_daily_compliant (backend) → is_compliant (component)
      const is_compliant = d.is_compliant ?? d.is_daily_compliant ?? null;
      return { ...d, date, label, is_compliant };
    });
  }

  // 2. Normalise compliance — add missing fields with safe defaults
  const c: any = json.compliance ?? {};
  const rolling24 = c.rolling_24h_rest ?? null;
  const rolling7d = c.rolling_7day_rest ?? null;
  const min24 = c.min_24h ?? 10;
  const min7d = c.min_7d ?? 77;
  const mlcStatus: string | null = c.mlc_status ?? (
    rolling24 != null && rolling7d != null
      ? (rolling24 >= min24 && rolling7d >= min7d ? 'COMPLIANT' : 'NON-COMPLIANT')
      : null
  );
  json.compliance = {
    rolling_24h_rest: rolling24,
    rolling_7day_rest: rolling7d,
    rolling_7d_work: c.rolling_7d_work ?? null,
    min_24h: min24,
    min_7d: min7d,
    violations_this_month: c.violations_this_month ?? 0,
    mlc_status: mlcStatus,
  };

  // 3. Default prior_weeks to empty array if absent
  if (!Array.isArray(json.prior_weeks)) {
    json.prior_weeks = [];
  }

  // 4. Ensure templates is always an array (backend field: name)
  if (!Array.isArray(json.templates)) {
    json.templates = [];
  }
}

async function getAuthHeader(): Promise<string> {
  const { data: { session } } = await supabase.auth.getSession();
  return session ? `Bearer ${session.access_token}` : '';
}

function formatMonth(yyyyMm: string): string {
  const [y, m] = yyyyMm.split('-');
  const d = new Date(Number(y), Number(m) - 1, 1);
  return d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

/** Compute total hours from a periods array — always correct, ignores stored totals. */
function hoursFromPeriods(periods: RestPeriod[]): number {
  return periods.reduce((sum, p) => {
    const [sh, sm] = p.start.split(':').map(Number);
    const [eh, em] = p.end.split(':').map(Number);
    const startMin = sh * 60 + sm;
    const endMin = (p.end === '24:00' ? 24 : eh) * 60 + em;
    return sum + Math.max(0, endMin - startMin) / 60;
  }, 0);
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Skeleton({ w = '100%', h = 16 }: { w?: string | number; h?: number }) {
  return (
    <div style={{
      width: w,
      height: h,
      background: 'rgba(255,255,255,0.05)',
      borderRadius: 4,
      animation: 'pulse 1.5s ease-in-out infinite',
    }} />
  );
}

function SectionCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: 'var(--surface, #181614)',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 8,
      overflow: 'hidden',
      marginBottom: 12,
      ...style,
    }}>
      {children}
    </div>
  );
}

function SectionHeader({ label, right }: { label: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px 8px',
      borderBottom: '1px solid rgba(255,255,255,0.05)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: '0.14em',
        textTransform: 'uppercase' as const,
        color: 'rgba(255,255,255,0.35)',
      }}>{label}</span>
      {right}
    </div>
  );
}

function StatusBadge({ ok, label }: { ok: boolean | null; label?: string }) {
  if (ok === null) return <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)' }}>—</span>;
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 600,
      color: ok ? 'var(--green, #4A9468)' : 'var(--red, #C0503A)',
    }}>
      {ok ? '✓' : '⚠'} {label}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface MyTimeViewProps {
  /** If set, loads another crew member's week (read-only, HOD/Captain viewing) */
  targetUserId?: string;
  /** Force entire view into read-only mode */
  readOnly?: boolean;
}

export function MyTimeView({ targetUserId, readOnly: forceReadOnly }: MyTimeViewProps = {}) {
  const [data, setData] = React.useState<typeof MOCK_MY_WEEK | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Local state for unsubmitted days' slider values
  const [draftPeriods, setDraftPeriods] = React.useState<Record<string, RestPeriod[]>>({});
  const [submitting, setSubmitting] = React.useState<Record<string, boolean>>({});
  // Days submitted this session (before page reload) — avoids full reload on each submit
  const [submittedDays, setSubmittedDays] = React.useState<Record<string, any>>({});
  // Per-day submit errors (e.g. overlap rejection from backend)
  const [submitErrors, setSubmitErrors] = React.useState<Record<string, string>>({});
  // Once weekly submit succeeds, Undo buttons are locked
  const weekFinalised = React.useRef(false);

  // Template selector
  const [selectedTemplate, setSelectedTemplate] = React.useState('');

  // Phase 7: week locked when finalized (signoff_status === 'finalized' OR LOCKED error)
  const [weekLocked, setWeekLocked] = React.useState(false);
  const [applyingTemplate, setApplyingTemplate] = React.useState(false);

  // Sign week popup
  const [signWeekOpen, setSignWeekOpen] = React.useState(false);

  // Sign monthly popup
  const [signMonthlyOpen, setSignMonthlyOpen] = React.useState(false);

  // History expand
  const [historyOpen, setHistoryOpen] = React.useState(false);

  // Unsigned alert
  const [unsignedAlert, setUnsignedAlert] = React.useState(false);

  // Week navigation — null = current week (backend defaults)
  const [viewWeekStart, setViewWeekStart] = React.useState<string | null>(null);
  // Disable forward nav when we're already on current week
  const isCurrentWeek = viewWeekStart === null;

  function navigateWeek(direction: -1 | 1) {
    setViewWeekStart(prev => {
      const base = prev ?? data?.week_start ?? null;
      if (!base) return prev;
      const d = new Date(base);
      d.setDate(d.getDate() + direction * 7);
      const next = d.toISOString().slice(0, 10);
      // Don't go past today's week
      const todayMonday = (() => {
        const t = new Date();
        const day = t.getDay();
        const diff = day === 0 ? -6 : 1 - day;
        t.setDate(t.getDate() + diff);
        return t.toISOString().slice(0, 10);
      })();
      if (next > todayMonday) return null; // snap back to current
      return next === todayMonday ? null : next;
    });
  }

  // ── Load week data ──

  async function loadWeekData(weekStart?: string | null) {
    setLoading(true);
    setError(null);
    // Reset per-week local state when navigating
    setDraftPeriods({});
    setSubmittedDays({});
    setSubmitErrors({});
    weekFinalised.current = false;
    try {
      const auth = await getAuthHeader();
      const ws = weekStart !== undefined ? weekStart : viewWeekStart;
      const params = new URLSearchParams();
      if (targetUserId) params.set('user_id', targetUserId);
      if (ws) params.set('week_start', ws);
      const url = `/api/v1/hours-of-rest/my-week${params.toString() ? `?${params}` : ''}`;
      const resp = await fetch(url, {
        headers: { 'Authorization': auth },
      });
      if (resp.ok) {
        const json = await resp.json();
        // Normalise real API shape → component-expected shape
        normalizeMyWeekResponse(json);
        // Normalise: null day slots → default unsubmitted day objects
        if (Array.isArray(json.days)) {
          json.days = normalizeDays(json.days, json.week_start ?? '');
        }
        // Normalise: backend uses signoff_id, component uses id
        if (json.pending_signoff?.signoff_id && !json.pending_signoff.id) {
          json.pending_signoff.id = json.pending_signoff.signoff_id;
        }
        setData(json);
        // Phase 7: lock week if finalized
        const locked = json.signoff_status === 'finalized' || json.signoff_status === 'locked';
        setWeekLocked(locked);
      } else {
        const text = await resp.text().catch(() => '');
        setError(`Failed to load hours of rest (${resp.status})${text ? `: ${text.slice(0, 120)}` : ''}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load hours of rest');
    } finally {
      setLoading(false);
    }
  }

  async function checkUnsignedAlert() {
    try {
      const auth = await getAuthHeader();
      const resp = await fetch('/api/v1/notifications?type=hor_unsigned', {
        headers: { 'Authorization': auth },
      });
      if (resp.ok) {
        const json = await resp.json();
        setUnsignedAlert((json.data?.length ?? 0) > 0);
      }
      // 404 = notifications endpoint not yet deployed — silently skip
    } catch {
      // non-critical
    }
  }

  React.useEffect(() => {
    loadWeekData(viewWeekStart);
    checkUnsignedAlert();
  }, [viewWeekStart]);

  // ── Submit single day ──

  async function submitDay(date: string) {
    // draftPeriods[date] holds WORK periods from the slider.
    // Blank (no work blocks) = valid 24h rest day — still submittable.
    const workPeriods: RestPeriod[] = draftPeriods[date] ?? [];
    setSubmitting(prev => ({ ...prev, [date]: true }));
    try {
      const auth = await getAuthHeader();
      const resp = await fetch('/api/v1/hours-of-rest/upsert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': auth },
        body: JSON.stringify({ record_date: date, work_periods: workPeriods }),
      });
      const json = await resp.json().catch(() => null);

      // Phase 7: LOCKED check — HTTP 409 or envelope status:'error' + code:'LOCKED'
      const isLockedErr =
        resp.status === 409 ||
        (json?.status === 'error' && json?.error?.code === 'LOCKED');
      if (isLockedErr) {
        setWeekLocked(true);
        setSubmitErrors(prev => ({
          ...prev,
          [date]: 'This week is finalized. Ask your HOD to submit a correction.',
        }));
        return;
      }

      if (resp.ok) {
        // Patch local state from response — NO page reload
        const record = json?.data?.record ?? null;
        const compliance = json?.data?.compliance ?? null;
        const warnings = json?.data?.warnings_created ?? [];
        const dayPatch = record ? {
          date,
          work_periods: workPeriods,
          total_rest_hours: record.total_rest_hours ?? compliance?.total_rest_hours ?? null,
          total_work_hours: record.total_work_hours ?? null,
          is_compliant: record.is_daily_compliant ?? compliance?.is_daily_compliant ?? null,
          submitted: true,
          warnings,
        } : { date, work_periods: workPeriods, submitted: true, warnings: [] };
        setSubmittedDays(prev => ({ ...prev, [date]: dayPatch }));
        setSubmitErrors(prev => { const n = { ...prev }; delete n[date]; return n; });
        setDraftPeriods(prev => { const n = { ...prev }; delete n[date]; return n; });
      } else {
        const msg = json?.message ?? `Submit failed (${resp.status})`;
        setSubmitErrors(prev => ({ ...prev, [date]: msg }));
      }
    } catch {
      // handle error
    } finally {
      setSubmitting(prev => ({ ...prev, [date]: false }));
    }
  }

  function undoDay(date: string) {
    const submitted = submittedDays[date];
    if (submitted?.rest_periods?.length) {
      setDraftPeriods(prev => ({ ...prev, [date]: submitted.rest_periods }));
    }
    setSubmittedDays(prev => { const n = { ...prev }; delete n[date]; return n; });
  }

  // ── Apply template ──

  async function applyTemplate() {
    if (!selectedTemplate || !data) return;
    setApplyingTemplate(true);
    try {
      const auth = await getAuthHeader();
      const resp = await fetch('/api/v1/hours-of-rest/templates/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': auth },
        body: JSON.stringify({
          template_id: selectedTemplate,
          week_start_date: (data as any).week_start,
        }),
      });
      if (!resp.ok) {
        const json = await resp.json().catch(() => null);
        console.error('Template apply failed:', resp.status, json);
      }
      await loadWeekData();
    } catch (e) {
      console.error('Template apply error:', e);
    } finally {
      setApplyingTemplate(false);
    }
  }

  // ── Sign week (Submit Week For Approval) ──
  // Two-step flow:
  //   1. Create a weekly signoff (period_type=weekly, week_start=data.week_start, department)
  //   2. Sign it at crew level (signoff_id, signature_level=crew, signature_data)

  async function handleSignWeek(values: Record<string, unknown>) {
    if (!data) return;
    const auth = await getAuthHeader();
    const weekStart = (data as any).week_start as string;
    const department = (data as any).department || 'general';
    const month = weekStart.slice(0, 7); // YYYY-MM

    // Step 1: Create the weekly signoff
    const createResp = await fetch('/api/v1/hours-of-rest/signoffs/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': auth },
      body: JSON.stringify({
        period_type: 'weekly',
        week_start: weekStart,
        month,
        department,
      }),
    });
    const createJson = await createResp.json().catch(() => null);
    const signoffId = createJson?.data?.signoff?.id ?? createJson?.signoff?.id ?? null;

    // Tolerate duplicate — if signoff already exists for this week, fetch its id
    if (!signoffId && createJson?.error?.code === 'DUPLICATE_ERROR') {
      // Try fetching existing signoff id from data
      const existingId = (data as any).pending_signoff?.id ?? null;
      if (!existingId) {
        // Can't proceed without signoff id
        return;
      }
      await _signAtCrewLevel(existingId, auth, values);
    } else if (signoffId) {
      await _signAtCrewLevel(signoffId, auth, values);
    }

    weekFinalised.current = true;
    setSignWeekOpen(false);
    await loadWeekData();
  }

  async function _signAtCrewLevel(signoffId: string, auth: string, values: Record<string, unknown>) {
    await fetch('/api/v1/hours-of-rest/signoffs/sign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': auth },
      body: JSON.stringify({
        signoff_id: signoffId,
        signature_level: 'crew',
        signature_data: {
          name: (values as any).name ?? 'Crew member',
          timestamp: new Date().toISOString(),
        },
        notes: (values as any).notes ?? null,
      }),
    });
  }

  // ── Sign monthly ──

  async function handleSignMonthly(values: Record<string, unknown>) {
    if (!data?.pending_signoff?.id) return;
    const auth = await getAuthHeader();
    await fetch('/api/v1/hours-of-rest/signoffs/sign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': auth },
      body: JSON.stringify({
        signoff_id: data.pending_signoff.id,
        signature_level: 'crew',
        signature_data: {
          name: (values as any).name ?? 'Crew member',
          timestamp: new Date().toISOString(),
        },
        notes: (values as any).notes ?? null,
      }),
    });
    setSignMonthlyOpen(false);
    await loadWeekData();
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {[1, 2, 3].map(i => <Skeleton key={i} h={60} />)}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'rgba(255,255,255,0.35)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
        Failed to load hours of rest data.
        <button onClick={() => loadWeekData()} style={{ marginLeft: 10, color: 'var(--mark)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 11 }}>Retry</button>
      </div>
    );
  }

  const comp = data.compliance;
  const signoff = data.pending_signoff;
  const isReadOnly = forceReadOnly || weekLocked;
  const allSubmitted = data.days.filter(Boolean).every(d => d.submitted || !!submittedDays[d.date]);
  const anyUnsubmitted = data.days.filter(Boolean).some(d => !d.submitted && !submittedDays[d.date] && (draftPeriods[d.date]?.length ?? 0) > 0);
  const signoffStatus: string | null = (data as any).signoff_status ?? null;
  const correctionRequested: boolean = (data as any).correction_requested ?? false;
  const correctionNote: string | null = (data as any).correction_note ?? null;

  return (
    <div style={{ maxWidth: 680 }}>

      {/* ── Unsigned alert banner ── */}
      {unsignedAlert && (
        <div style={{
          padding: '10px 16px',
          background: 'rgba(192,80,58,0.08)',
          border: '1px solid rgba(192,80,58,0.20)',
          borderRadius: 6,
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ color: 'var(--red, #C0503A)', fontSize: 13 }}>⚠</span>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.70)' }}>
            Your hours of rest for this month are unsigned. Weekly signature is required by MLC 2006.
          </span>
          <button
            onClick={() => setSignMonthlyOpen(true)}
            style={{ marginLeft: 'auto', padding: '4px 10px', background: 'none', border: '1px solid rgba(192,80,58,0.35)', borderRadius: 4, color: 'var(--red, #C0503A)', fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer' }}
          >
            Review & Sign
          </button>
        </div>
      )}

      {/* ── THIS WEEK ── */}
      <SectionCard>
        <SectionHeader
          label={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* Prev week */}
              <button
                onClick={() => navigateWeek(-1)}
                style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.45)', cursor: 'pointer', padding: '0 2px', fontSize: 12, lineHeight: 1 }}
                title="Previous week"
              >‹</button>
              {/* Week label */}
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.10em', textTransform: 'uppercase', color: isCurrentWeek ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.35)' }}>
                {isCurrentWeek ? `This Week — ${data.week_start}` : data.week_start}
                {weekLocked ? ' 🔒' : ''}
              </span>
              {/* Next week — disabled on current */}
              <button
                onClick={() => navigateWeek(1)}
                disabled={isCurrentWeek}
                style={{ background: 'none', border: 'none', color: isCurrentWeek ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.45)', cursor: isCurrentWeek ? 'default' : 'pointer', padding: '0 2px', fontSize: 12, lineHeight: 1 }}
                title="Next week"
              >›</button>
              {/* Day-status dots — green=compliant, amber=violation, grey=not filed */}
              <div style={{ display: 'flex', gap: 3, marginLeft: 6 }}>
                {data.days.filter(Boolean).map((day: any) => {
                  const ls = submittedDays[day.date];
                  const isSubmit = day.submitted || !!ls;
                  const w = (ls?.warnings ?? day.warnings ?? []);
                  const hasViolation = w.length > 0;
                  const color = !isSubmit
                    ? 'rgba(255,255,255,0.18)'
                    : hasViolation
                    ? 'rgba(192,80,58,0.85)'
                    : 'rgba(74,148,104,0.85)';
                  return (
                    <div key={day.date} title={`${day.label}: ${!isSubmit ? 'Not filed' : hasViolation ? 'Violation' : 'Compliant'}`} style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
                  );
                })}
              </div>
            </div>
          }
          right={isReadOnly ? (
            weekLocked && !forceReadOnly ? (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.06em' }}>
                {signoffStatus === 'hod_signed' ? 'Awaiting Captain' : signoffStatus === 'finalized' ? 'Finalized' : 'Read-only'}
              </span>
            ) : undefined
          ) : isCurrentWeek ? (
            <button
              data-testid="hor-submit-week"
              onClick={() => setSignWeekOpen(true)}
              disabled={!allSubmitted}
              style={{
                padding: '5px 12px',
                background: allSubmitted ? 'var(--mark, #5AABCC)' : 'rgba(255,255,255,0.06)',
                border: 'none',
                borderRadius: 5,
                color: allSubmitted ? '#0c0b0a' : 'rgba(255,255,255,0.25)',
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor: allSubmitted ? 'pointer' : 'not-allowed',
              }}
            >
              Submit Week For Approval
            </button>
          ) : (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.06em' }}>Past week — read only</span>
          )}
        />

        {/* Finalized banner */}
        {weekLocked && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.10)',
            borderRadius: 5,
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'rgba(255,255,255,0.45)',
          }}>
            🔒 This week is finalized. To make changes, ask your HOD to submit a correction request.
          </div>
        )}

        {/* HOD signed — soft lock warning */}
        {signoffStatus === 'hod_signed' && !weekLocked && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'rgba(245,158,11,0.05)',
            border: '1px solid rgba(245,158,11,0.20)',
            borderRadius: 5,
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'rgba(245,158,11,0.75)',
          }}>
            HOD has counter-signed this week. Editing will require your HOD to re-counter-sign.
          </div>
        )}

        {/* Correction requested banner */}
        {correctionRequested && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'rgba(245,158,11,0.06)',
            border: '1px solid rgba(245,158,11,0.25)',
            borderRadius: 5,
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(245,158,11,0.8)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
              Correction Requested by HOD
            </div>
            {correctionNote && (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(245,158,11,0.7)' }}>
                {correctionNote}
              </div>
            )}
          </div>
        )}

        <div style={{ padding: '4px 0' }}>
          {data.days.filter(Boolean).map((day, idx) => {
            const localSubmit = submittedDays[day.date];
            const isSubmittedLocally = !!localSubmit;
            const isSubmitted = day.submitted || isSubmittedLocally || isReadOnly;
            const displayDay = isSubmittedLocally ? localSubmit : day;
            const warnings: any[] = displayDay.warnings ?? [];
            const hasWarning = warnings.length > 0;
            const draft = isReadOnly ? undefined : draftPeriods[day.date];
            const isSubmitting = submitting[day.date];
            const canUndo = isSubmittedLocally && !weekFinalised.current && !isReadOnly;

            return (
              <div
                key={day.date}
                style={{
                  padding: '10px 16px',
                  borderBottom: idx < 6 ? '1px solid rgba(255,255,255,0.03)' : undefined,
                  background: hasWarning && !isSubmitted ? 'rgba(192,80,58,0.04)' : undefined,
                }}
              >
                {/* Day header row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: isSubmitted ? 6 : 8 }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'rgba(255,255,255,0.55)',
                    width: 28,
                  }}>{day.label}</span>

                  {isSubmitted ? (
                    <>
                      <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
                        {(() => {
                          // Compute from periods — stored totals may be stale/wrong
                          const wp = displayDay.work_periods ?? [];
                          const rp = displayDay.rest_periods ?? [];
                          const workH = wp.length > 0
                            ? hoursFromPeriods(wp)
                            : (rp.length > 0 ? 24 - hoursFromPeriods(rp) : displayDay.total_work_hours ?? 0);
                          const restH = rp.length > 0
                            ? hoursFromPeriods(rp)
                            : (wp.length > 0 ? 24 - hoursFromPeriods(wp) : displayDay.total_rest_hours ?? 0);
                          return `${workH.toFixed(1)}h work / ${restH.toFixed(1)}h rest`;
                        })()}
                      </span>
                      <StatusBadge
                        ok={(() => {
                          const rp = displayDay.rest_periods ?? [];
                          const restH = rp.length > 0 ? hoursFromPeriods(rp) : (displayDay.total_rest_hours ?? null);
                          if (restH === null) return displayDay.is_compliant;
                          return restH >= 10; // MLC 2006 minimum daily rest
                        })()}
                        label={(() => {
                          const rp = displayDay.rest_periods ?? [];
                          const restH = rp.length > 0 ? hoursFromPeriods(rp) : (displayDay.total_rest_hours ?? null);
                          if (restH === null || restH >= 10) return 'Compliant';
                          return `Violation`;
                        })()}
                      />
                      {/* Submitted this session — show acknowledgement + Undo */}
                      {canUndo && (
                        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green, #4A9468)', fontWeight: 600 }}>Submitted ✓</span>
                          <button
                            onClick={() => undoDay(day.date)}
                            style={{
                              padding: '3px 8px',
                              background: 'none',
                              border: '1px solid rgba(255,255,255,0.15)',
                              borderRadius: 4,
                              color: 'rgba(255,255,255,0.45)',
                              fontFamily: 'var(--font-mono)',
                              fontSize: 9,
                              cursor: 'pointer',
                              letterSpacing: '0.06em',
                            }}
                          >Undo</button>
                        </span>
                      )}
                    </>
                  ) : (
                    <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.25)', fontStyle: 'italic' }}>Not submitted</span>
                  )}

                  {/* Submit day button — only when not submitted and has draft */}
                  {!isSubmitted && (draft?.length ?? 0) > 0 && (
                    <button
                      data-testid={`hor-submit-day-${day.date}`}
                      onClick={() => submitDay(day.date)}
                      disabled={isSubmitting}
                      style={{
                        marginLeft: 'auto',
                        padding: '4px 10px',
                        background: 'var(--mark, #5AABCC)',
                        border: 'none',
                        borderRadius: 4,
                        color: '#0c0b0a',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 9,
                        fontWeight: 600,
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        cursor: isSubmitting ? 'wait' : 'pointer',
                        opacity: isSubmitting ? 0.6 : 1,
                      }}
                    >
                      {isSubmitting ? 'Saving…' : 'Submit Day'}
                    </button>
                  )}
                </div>

                {/* Submit error (e.g. overlap rejection) */}
                {submitErrors[day.date] && (
                  <div style={{ marginBottom: 6, paddingLeft: 38 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(239,68,68,0.85)' }}>
                      ✕ {submitErrors[day.date]}
                    </span>
                  </div>
                )}

                {/* Violation reason (BUG 3) */}
                {isSubmitted && hasWarning && (
                  <div style={{ marginBottom: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {warnings.map((w: any, wi: number) => (
                      <span key={wi} style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 9,
                        color: 'rgba(192,80,58,0.85)',
                        paddingLeft: 38,
                      }}>⚠ {w.message ?? 'Compliance rule breached'}</span>
                    ))}
                  </div>
                )}

                {/* Slider */}
                <TimeSlider
                  value={isSubmitted ? (localSubmit?.work_periods ?? (day as any).work_periods ?? invertToRestPeriods((day as any).rest_periods ?? [])) : draft}
                  readOnly={isSubmitted}
                  onChange={periods => setDraftPeriods(prev => ({ ...prev, [day.date]: periods }))}
                />
              </div>
            );
          })}
        </div>
      </SectionCard>

      {/* ── TEMPLATE SELECTOR ── */}
      {data.templates.length > 0 && (
        <SectionCard>
          <SectionHeader label="Templates" />
          <div style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
            <select
              value={selectedTemplate}
              onChange={e => setSelectedTemplate(e.target.value)}
              style={{
                flex: 1,
                background: 'var(--surface-el, #1e1b18)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 5,
                color: 'rgba(255,255,255,0.70)',
                fontFamily: 'var(--font-body)',
                fontSize: 12,
                padding: '6px 10px',
                outline: 'none',
              }}
            >
              <option value="">Select a template…</option>
              {data.templates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <button
              onClick={applyTemplate}
              disabled={!selectedTemplate || applyingTemplate}
              style={{
                padding: '6px 14px',
                background: selectedTemplate ? 'rgba(90,171,204,0.12)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(90,171,204,0.25)',
                borderRadius: 5,
                color: selectedTemplate ? 'var(--mark, #5AABCC)' : 'rgba(255,255,255,0.25)',
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor: selectedTemplate ? 'pointer' : 'not-allowed',
                whiteSpace: 'nowrap',
              }}
            >
              {applyingTemplate ? 'Applying…' : 'Insert My Template'}
            </button>
          </div>
          <p style={{ padding: '0 16px 10px', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)', lineHeight: 1.5 }}>
            Template populates unsubmitted days only. Your signature is still required.
          </p>
        </SectionCard>
      )}

      {/* ── COMPLIANCE ── */}
      <SectionCard>
        <SectionHeader label="Compliance" />
        <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
              24h rolling — {comp.rolling_24h_rest != null ? `${comp.rolling_24h_rest}h rest` : '—'}
            </span>
            {comp.rolling_24h_rest != null
              ? <StatusBadge ok={comp.rolling_24h_rest >= comp.min_24h} label={comp.rolling_24h_rest >= comp.min_24h ? `✓ min ${comp.min_24h}h` : `⚠ min ${comp.min_24h}h`} />
              : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)' }}>No data today</span>
            }
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
              7-day rolling — {comp.rolling_7day_rest != null ? `${comp.rolling_7day_rest}h rest` : '—'}
            </span>
            {comp.rolling_7day_rest != null
              ? <StatusBadge ok={comp.rolling_7day_rest >= comp.min_7d} label={comp.rolling_7day_rest >= comp.min_7d ? `✓ min ${comp.min_7d}h` : `⚠ min ${comp.min_7d}h`} />
              : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)' }}>No data</span>
            }
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>This week — {comp.rolling_7d_work != null ? `${comp.rolling_7d_work}h worked` : '—'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)' }}>MLC 2006 Status</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
              color: comp.mlc_status === 'COMPLIANT' ? 'var(--green, #4A9468)' : 'var(--red, #C0503A)',
            }}>
              {comp.mlc_status}
            </span>
          </div>
        </div>
      </SectionCard>

      {/* ── MONTHLY SIGN-OFF ── */}
      {signoff && (
        <SectionCard>
          <SectionHeader label="Monthly Sign-Off" />
          <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.80)', marginBottom: 3 }}>
                {formatMonth(signoff.month)}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>
                {signoff.status === 'draft' ? 'Awaiting your signature' :
                  signoff.status === 'crew_signed' ? 'Submitted — awaiting HOD' :
                  signoff.status === 'hod_signed' ? 'HOD signed — awaiting Captain' :
                  signoff.status === 'finalized' ? 'Finalised ✓' : signoff.status}
              </div>
            </div>
            {signoff.status === 'draft' && (
              <button
                onClick={() => setSignMonthlyOpen(true)}
                style={{
                  padding: '6px 14px',
                  background: 'var(--mark, #5AABCC)',
                  border: 'none',
                  borderRadius: 5,
                  color: '#0c0b0a',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                }}
              >
                Review &amp; Sign
              </button>
            )}
            {signoff.status === 'crew_signed' && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green, #4A9468)' }}>Submitted ✓</span>
            )}
          </div>
        </SectionCard>
      )}

      {/* ── HISTORY ── */}
      {data.prior_weeks.length > 0 && (
        <SectionCard>
          <div
            onClick={() => setHistoryOpen(o => !o)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 16px',
              cursor: 'pointer',
            }}
          >
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)' }}>History</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2" style={{ transform: historyOpen ? 'rotate(180deg)' : undefined, transition: 'transform 0.15s' }}>
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
          {historyOpen && (
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              {data.prior_weeks.map(w => (
                <div key={w.week_start} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 16px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>Week of {w.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>{w.total_rest_hours}h rest</span>
                    <StatusBadge ok={w.is_compliant} />
                  </div>
                </div>
              ))}
              <div style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)' }}>
                Avg {((data.prior_weeks.reduce((s, w) => s + (w.total_rest_hours || 0), 0) / data.prior_weeks.length) || 0).toFixed(1)}h rest/week
              </div>
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Action popups ── */}

      {signWeekOpen && (
        <ActionPopup
          mode="mutate"
          title="Submit Week For Approval"
          fields={[]}
          signatureLevel={2}
          onSubmit={handleSignWeek}
          onClose={() => setSignWeekOpen(false)}
        />
      )}

      {signMonthlyOpen && (
        <ActionPopup
          mode="mutate"
          title={`Sign Monthly Record — ${signoff ? formatMonth(signoff.month) : ''}`}
          fields={[]}
          signatureLevel={2}
          onSubmit={handleSignMonthly}
          onClose={() => setSignMonthlyOpen(false)}
        />
      )}
    </div>
  );
}
