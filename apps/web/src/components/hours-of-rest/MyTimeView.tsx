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
import { useAuth } from '@/hooks/useAuth';
import { TimeSlider, invertToRestPeriods, type RestPeriod } from './TimeSlider';
import { ActionPopup, type ActionPopupField } from '@/components/lens-v2/ActionPopup';

// (mock removed — all data comes from GET /v1/hours-of-rest/my-week)

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

/**
 * Returns the Authorization header value, or null if no session exists.
 * BUG-HOR-2 fix: previously returned an empty string on null session, causing
 * fetches to send `Authorization: ` which backend rejects with 401. Callers
 * must now null-check before making a request.
 */
async function getAuthHeader(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session ? `Bearer ${session.access_token}` : null;
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
      background: 'var(--surface-subtle)',
      borderRadius: 'var(--radius-pill)',
      animation: 'pulse 1.5s ease-in-out infinite',
    }} />
  );
}

function SectionCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border-sub)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      marginBottom: 'var(--space-3)',
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
      borderBottom: '1px solid var(--surface-subtle)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: '0.14em',
        textTransform: 'uppercase' as const,
        color: 'var(--txt-ghost)',
      }}>{label}</span>
      {right}
    </div>
  );
}

function StatusBadge({ ok, label }: { ok: boolean | null; label?: string }) {
  if (ok === null) return <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>—</span>;
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 600,
      color: ok ? 'var(--green)' : 'var(--red)',
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
  const { user } = useAuth();
  // Fleet manager (role=manager) is read-only for MLC submission — backend rejects writes,
  // but we also suppress the CTA so they don't see a button that always fails (BUG-HOR-5b fix).
  const canSubmitWeek = user?.role !== 'manager';
  // MLC 2006 Reg 2.3 independence: fleet managers must not write crew schedule data
  const canCreateTemplate = user?.role !== 'manager';

  const [data, setData] = React.useState<any>(null);
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

  // Active warnings from backend
  const [warnings, setWarnings] = React.useState<any[]>([]);
  const [acknowledging, setAcknowledging] = React.useState<Record<string, boolean>>({});

  // Per-day crew comment — required by MLC when submitting non-compliant hours
  const [crewComments, setCrewComments] = React.useState<Record<string, string>>({});
  // True when backend returned VALIDATION_ERROR requiring a crew comment for this day
  const [commentRequired, setCommentRequired] = React.useState<Record<string, boolean>>({});

  // Create template form
  const [createTemplateOpen, setCreateTemplateOpen] = React.useState(false);
  const [newTemplateName, setNewTemplateName] = React.useState('');
  const [newTemplateDesc, setNewTemplateDesc] = React.useState('');
  const [newTemplateWorkStart, setNewTemplateWorkStart] = React.useState('08:00');
  const [newTemplateWorkEnd, setNewTemplateWorkEnd] = React.useState('18:00');
  const [creatingTemplate, setCreatingTemplate] = React.useState(false);
  const [createTemplateError, setCreateTemplateError] = React.useState<string | null>(null);

  // Month calendar
  const [calendarOpen, setCalendarOpen] = React.useState(false);
  const [calendarMonth, setCalendarMonth] = React.useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [calendarDays, setCalendarDays] = React.useState<any[]>([]);
  const [calendarLoading, setCalendarLoading] = React.useState(false);

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
      // BUG-HOR-2 fix: bail out early if no session — previously sent `Authorization: `
      if (!auth) {
        setError('Not authenticated');
        return;
      }
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
      if (!auth) return;
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

  async function loadWarnings() {
    try {
      const auth = await getAuthHeader();
      if (!auth) return;
      const resp = await fetch('/api/v1/hours-of-rest/warnings?status=active', {
        headers: { 'Authorization': auth },
      });
      if (resp.ok) {
        const json = await resp.json();
        // Response: { data: { warnings: [...], summary: {...} } }
        const list: any[] = json.data?.warnings ?? json.warnings ?? [];
        setWarnings(list);
      }
    } catch {
      // non-critical
    }
  }

  async function loadCalendar(month: string) {
    setCalendarLoading(true);
    try {
      const auth = await getAuthHeader();
      if (!auth) return;
      const resp = await fetch(`/api/v1/hours-of-rest/month-status?month=${month}`, {
        headers: { 'Authorization': auth },
      });
      if (resp.ok) {
        const json = await resp.json();
        setCalendarDays(json.days ?? []);
      }
    } catch {
      // non-critical
    } finally {
      setCalendarLoading(false);
    }
  }

  async function acknowledgeWarning(warningId: string) {
    setAcknowledging(prev => ({ ...prev, [warningId]: true }));
    try {
      const auth = await getAuthHeader();
      if (!auth) return;
      const resp = await fetch('/api/v1/hours-of-rest/warnings/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': auth },
        body: JSON.stringify({ warning_id: warningId }),
      });
      // Remove from UI regardless of response — optimistic update
      // Backend writes to ledger_events (BUG-641-8 fix in Python handler)
      if (resp.ok || resp.status === 200) {
        setWarnings(prev => prev.filter(w => w.id !== warningId));
      }
    } catch {
      // non-critical
    } finally {
      setAcknowledging(prev => { const n = { ...prev }; delete n[warningId]; return n; });
    }
  }

  React.useEffect(() => {
    loadWeekData(viewWeekStart);
    checkUnsignedAlert();
    loadWarnings();
  }, [viewWeekStart]);

  React.useEffect(() => {
    if (calendarOpen) loadCalendar(calendarMonth);
  }, [calendarOpen, calendarMonth]);

  // ── Submit single day ──

  async function submitDay(date: string) {
    // draftPeriods[date] holds WORK periods from the slider.
    // Blank (no work blocks) = valid 24h rest day — still submittable.
    const workPeriods: RestPeriod[] = draftPeriods[date] ?? [];
    const crewComment = crewComments[date] ?? '';
    setSubmitting(prev => ({ ...prev, [date]: true }));
    try {
      const auth = await getAuthHeader();
      if (!auth) {
        setSubmitErrors(prev => ({ ...prev, [date]: 'Not authenticated' }));
        return;
      }
      const body: Record<string, unknown> = { record_date: date, work_periods: workPeriods };
      if (crewComment.trim()) body.crew_comment = crewComment.trim();

      const resp = await fetch('/api/v1/hours-of-rest/upsert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': auth },
        body: JSON.stringify(body),
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

      // Action bus returns HTTP 200 even for errors — check envelope success flag
      const envelopeError = json?.success === false
        ? (json?.error?.message ?? json?.message ?? null)
        : null;

      // Crew comment required — reveal textarea and show error without marking submitted
      if (envelopeError && json?.error?.code === 'VALIDATION_ERROR' &&
          envelopeError.toLowerCase().includes('crew comment')) {
        setCommentRequired(prev => ({ ...prev, [date]: true }));
        setSubmitErrors(prev => ({ ...prev, [date]: envelopeError }));
        return;
      }

      if (resp.ok && !envelopeError) {
        // Patch local state from response — NO page reload
        const record = json?.data?.record ?? null;
        const compliance = json?.data?.compliance ?? null;
        const warnings = json?.data?.warnings_created ?? [];
        const dayPatch = record ? {
          date,
          record_id: record.id ?? null,
          work_periods: workPeriods,
          rest_periods: record.rest_periods ?? [],
          total_rest_hours: record.total_rest_hours ?? compliance?.total_rest_hours ?? null,
          total_work_hours: record.total_work_hours ?? null,
          // Use server-authoritative is_daily_compliant — not client re-derive
          is_compliant: record.is_daily_compliant ?? compliance?.is_daily_compliant ?? null,
          submitted: true,
          warnings,
        } : { date, record_id: null, work_periods: workPeriods, rest_periods: [], submitted: true, warnings: [] };
        setSubmittedDays(prev => ({ ...prev, [date]: dayPatch }));
        setSubmitErrors(prev => { const n = { ...prev }; delete n[date]; return n; });
        setCommentRequired(prev => { const n = { ...prev }; delete n[date]; return n; });
        setDraftPeriods(prev => { const n = { ...prev }; delete n[date]; return n; });
        // Keep crew comment in state for display but reset required flag
        if (warnings.length > 0) {
          // Re-load warnings list after new violation created
          await loadWarnings();
        }
      } else {
        const msg = envelopeError ?? json?.message ?? `Submit failed (${resp.status})`;
        setSubmitErrors(prev => ({ ...prev, [date]: msg }));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Submit failed — check your connection';
      setSubmitErrors(prev => ({ ...prev, [date]: msg }));
    } finally {
      setSubmitting(prev => ({ ...prev, [date]: false }));
    }
  }

  async function undoDay(date: string) {
    const submitted = submittedDays[date];
    const recordId = submitted?.record_id ?? null;

    // Restore work_periods (not rest_periods) — slider works with work blocks
    if (submitted?.work_periods?.length) {
      setDraftPeriods(prev => ({ ...prev, [date]: submitted.work_periods }));
    }
    setSubmittedDays(prev => { const n = { ...prev }; delete n[date]; return n; });

    // Call backend to write MLC correction record and reset DB row to unsubmitted
    if (recordId) {
      try {
        const auth = await getAuthHeader();
        if (!auth) return;
        await fetch('/api/v1/hours-of-rest/undo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': auth },
          body: JSON.stringify({ record_id: recordId }),
        });
        // Errors are non-fatal — local state already reverted above.
        // If backend undo fails (e.g. already signed), the user sees their day
        // back as editable locally but it'll reload as submitted on next fetch.
      } catch {
        // non-critical: local state reverted, next loadWeekData will correct it
      }
    }
  }

  // ── Apply template ──

  async function applyTemplate() {
    if (!selectedTemplate || !data) return;
    setApplyingTemplate(true);
    try {
      const auth = await getAuthHeader();
      if (!auth) return;

      // Fetch template work_periods before applying so we can populate draft state
      // without calling loadWeekData() (which resets draftPeriods via setDraftPeriods({}))
      const templateResp = await fetch(
        `/api/v1/hours-of-rest/templates/${selectedTemplate}`,
        { headers: { 'Authorization': auth } },
      ).catch(() => null);
      const templateJson = templateResp?.ok ? await templateResp.json().catch(() => null) : null;
      const templateWorkPeriods: RestPeriod[] | null =
        templateJson?.data?.work_periods ?? templateJson?.work_periods ?? null;

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
        await loadWeekData();
        return;
      }

      if (templateWorkPeriods) {
        // Populate draft state for unsubmitted days directly — avoids full reload
        // that would clear draftPeriods and leave slider blank
        const newDraft: Record<string, RestPeriod[]> = {};
        for (const day of (data as any).days ?? []) {
          if (day && !day.submitted && !submittedDays[day.date]) {
            newDraft[day.date] = templateWorkPeriods;
          }
        }
        if (Object.keys(newDraft).length > 0) {
          setDraftPeriods(prev => ({ ...prev, ...newDraft }));
          return;
        }
      }

      // Fallback: reload (draft state may appear blank until user interacts)
      await loadWeekData();
    } catch (e) {
      console.error('Template apply error:', e);
      await loadWeekData();
    } finally {
      setApplyingTemplate(false);
    }
  }

  // ── Create template ──

  async function createTemplate() {
    if (!newTemplateName.trim()) return;
    setCreatingTemplate(true);
    setCreateTemplateError(null);
    try {
      const auth = await getAuthHeader();
      if (!auth) { setCreateTemplateError('Not authenticated'); return; }

      // Build 7-day schedule_template from a single daily work block
      const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
      const schedule_template: Record<string, Array<{ start: string; end: string; type: string }>> = {};
      for (const day of DAYS) {
        schedule_template[day] = [{ start: newTemplateWorkStart, end: newTemplateWorkEnd, type: 'work' }];
      }

      const resp = await fetch('/api/v1/hours-of-rest/templates/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: auth },
        body: JSON.stringify({
          schedule_name: newTemplateName.trim(),
          ...(newTemplateDesc.trim() && { description: newTemplateDesc.trim() }),
          schedule_template,
          is_active: false,
        }),
      });
      const json = await resp.json().catch(() => null);
      const envelopeError = json?.success === false
        ? (json?.error?.message ?? 'Failed to create template')
        : null;
      if (!resp.ok || envelopeError) {
        setCreateTemplateError(envelopeError ?? `Create failed (${resp.status})`);
        return;
      }
      setCreateTemplateOpen(false);
      setNewTemplateName('');
      setNewTemplateDesc('');
      await loadWeekData();
    } catch {
      setCreateTemplateError('Network error — could not create template');
    } finally {
      setCreatingTemplate(false);
    }
  }

  // ── Sign week (Submit Week For Approval) ──
  // Two-step flow:
  //   1. Create a weekly signoff (period_type=weekly, week_start=data.week_start, department)
  //   2. Sign it at crew level (signoff_id, signature_level=crew, signature_data)

  async function handleSignWeek(values: Record<string, unknown>) {
    if (!data) return;
    const auth = await getAuthHeader();
    if (!auth) return;
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
    if (!auth) return;
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {[1, 2, 3].map(i => <Skeleton key={i} h={60} />)}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
        Failed to load hours of rest data.
        <button onClick={() => loadWeekData()} style={{ marginLeft: 10, color: 'var(--mark)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: 11 }}>Retry</button>
      </div>
    );
  }

  const comp = data.compliance;
  const signoff = data.pending_signoff;
  const isReadOnly = forceReadOnly || weekLocked;
  const allSubmitted = data.days.filter(Boolean).every((d: any) => d.submitted || !!submittedDays[d.date]);
  const anyUnsubmitted = data.days.filter(Boolean).some((d: any) => !d.submitted && !submittedDays[d.date] && (draftPeriods[d.date]?.length ?? 0) > 0);
  const signoffStatus: string | null = (data as any).signoff_status ?? null;
  const correctionRequested: boolean = (data as any).correction_requested ?? false;
  const correctionNote: string | null = (data as any).correction_note ?? null;

  return (
    <div style={{ width: '100%', minWidth: 0 }}>

      {/* ── Unsigned alert banner ── */}
      {unsignedAlert && (
        <div style={{
          padding: '10px 16px',
          background: 'var(--red-bg)',
          border: '1px solid var(--red-border)',
          borderRadius: 'var(--radius-pill)',
          marginBottom: 'var(--space-3)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}>
          <span style={{ color: 'var(--red)', fontSize: 13 }}>⚠</span>
          <span style={{ fontSize: 12, color: 'var(--txt3)' }}>
            Your hours of rest for this month are unsigned. Weekly signature is required by MLC 2006.
          </span>
          <button
            onClick={() => setSignMonthlyOpen(true)}
            style={{ marginLeft: 'auto', padding: '4px 10px', background: 'none', border: '1px solid var(--red-border-strong)', borderRadius: 'var(--radius-pill)', color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', cursor: 'pointer' }}
          >
            Review & Sign
          </button>
        </div>
      )}

      {/* ── THIS WEEK ── */}
      <SectionCard>
        <SectionHeader
          label={
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              {/* Prev week */}
              <button
                onClick={() => navigateWeek(-1)}
                style={{ background: 'none', border: 'none', color: 'var(--txt2)', cursor: 'pointer', padding: '0 2px', fontSize: 12, lineHeight: 1 }}
                title="Previous week"
              >‹</button>
              {/* Week label */}
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.10em', textTransform: 'uppercase', color: isCurrentWeek ? 'var(--txt2)' : 'var(--txt-ghost)' }}>
                {isCurrentWeek ? `This Week — ${data.week_start}` : data.week_start}
                {weekLocked ? ' 🔒' : ''}
              </span>
              {/* Next week — disabled on current */}
              <button
                onClick={() => navigateWeek(1)}
                disabled={isCurrentWeek}
                style={{ background: 'none', border: 'none', color: isCurrentWeek ? 'var(--txt-ghost)' : 'var(--txt2)', cursor: isCurrentWeek ? 'default' : 'pointer', padding: '0 2px', fontSize: 12, lineHeight: 1 }}
                title="Next week"
              >›</button>
              {/* Calendar toggle */}
              <button
                onClick={() => setCalendarOpen(o => !o)}
                title="Month calendar"
                style={{
                  background: calendarOpen ? 'var(--teal-bg)' : 'var(--border-faint)',
                  border: calendarOpen ? '1px solid var(--mark)' : '1px solid var(--border-top)',
                  borderRadius: 'var(--radius-pill)',
                  color: calendarOpen ? 'var(--mark)' : 'var(--txt2)',
                  cursor: 'pointer', padding: '3px 10px',
                  fontFamily: 'var(--font-mono)', fontSize: 10,
                  fontWeight: 500,
                  letterSpacing: '0.08em', marginLeft: 6,
                  textTransform: 'uppercase',
                  transition: 'background 0.12s, border-color 0.12s, color 0.12s',
                  whiteSpace: 'nowrap',
                }}
              >Calendar</button>
              {/* Day-status dots — green=compliant, amber=violation, grey=not filed */}
              <div style={{ display: 'flex', gap: 3, marginLeft: 6 }}>
                {data.days.filter(Boolean).map((day: any) => {
                  const ls = submittedDays[day.date];
                  const isSubmit = day.submitted || !!ls;
                  const w = (ls?.warnings ?? day.warnings ?? []);
                  const hasViolation = w.length > 0;
                  const color = !isSubmit
                    ? 'var(--txt-ghost)'
                    : hasViolation
                    ? 'var(--red-strong)'
                    : 'var(--green-strong)';
                  return (
                    <div key={day.date} title={`${day.label}: ${!isSubmit ? 'Not filed' : hasViolation ? 'Violation' : 'Compliant'}`} style={{ width: 6, height: 6, borderRadius: 'var(--radius-full)', background: color, flexShrink: 0 }} />
                  );
                })}
              </div>
            </div>
          }
          right={isReadOnly ? (
            weekLocked && !forceReadOnly ? (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', letterSpacing: '0.06em' }}>
                {signoffStatus === 'hod_signed' ? 'Awaiting Captain' : signoffStatus === 'finalized' ? 'Finalized' : 'Read-only'}
              </span>
            ) : undefined
          ) : isCurrentWeek && canSubmitWeek ? (
            <button
              data-testid="hor-submit-week"
              onClick={() => setSignWeekOpen(true)}
              disabled={!allSubmitted}
              style={{
                padding: '5px 12px',
                background: allSubmitted ? 'var(--mark)' : 'var(--surface-subtle)',
                border: 'none',
                borderRadius: 'var(--radius-pill)',
                color: allSubmitted ? 'var(--surface-base)' : 'var(--txt-ghost)',
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
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', letterSpacing: '0.06em' }}>Past week — read only</span>
          )}
        />

        {/* ── Month calendar ── */}
        {calendarOpen && (
          <div style={{
            borderBottom: '1px solid var(--border-sub)',
            padding: '12px 16px',
            background: 'var(--overlay-subtle)',
          }}>
            {/* Month nav */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 10 }}>
              <button
                onClick={() => {
                  const [y, m] = calendarMonth.split('-').map(Number);
                  const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`;
                  setCalendarMonth(prev);
                }}
                style={{ background: 'none', border: 'none', color: 'var(--txt2)', cursor: 'pointer', fontSize: 12 }}
              >‹</button>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.10em', textTransform: 'uppercase', color: 'var(--txt2)', flex: 1, textAlign: 'center' }}>
                {(() => { const [y, m] = calendarMonth.split('-'); return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }); })()}
              </span>
              <button
                onClick={() => {
                  const [y, m] = calendarMonth.split('-').map(Number);
                  const now = new Date();
                  const nowYM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
                  if (calendarMonth >= nowYM) return;
                  const next = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`;
                  setCalendarMonth(next);
                }}
                style={{ background: 'none', border: 'none', color: 'var(--txt2)', cursor: 'pointer', fontSize: 12 }}
              >›</button>
            </div>

            {/* Day-of-week headers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2, marginBottom: 4 }}>
              {['M','T','W','T','F','S','S'].map((d, i) => (
                <div key={i} style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--txt-ghost)', padding: '2px 0' }}>{d}</div>
              ))}
            </div>

            {/* Calendar grid */}
            {calendarLoading ? (
              <div style={{ textAlign: 'center', padding: '12px 0', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>Loading…</div>
            ) : (() => {
              const [cy, cm] = calendarMonth.split('-').map(Number);
              const firstDay = new Date(cy, cm - 1, 1);
              // Monday-based offset: 0=Mon…6=Sun
              const startOffset = (firstDay.getDay() + 6) % 7;
              const daysByDate: Record<string, any> = {};
              for (const d of calendarDays) daysByDate[d.date] = d;

              const cells: React.ReactNode[] = [];
              // Empty cells before first day
              for (let i = 0; i < startOffset; i++) {
                cells.push(<div key={`e${i}`} />);
              }

              const daysInMonth = new Date(cy, cm, 0).getDate();
              for (let day = 1; day <= daysInMonth; day++) {
                const dstr = `${calendarMonth}-${String(day).padStart(2, '0')}`;
                const rec = daysByDate[dstr];
                const isToday = dstr === new Date().toISOString().slice(0, 10);
                // Determine the Monday of this day's week
                const dayDate = new Date(cy, cm - 1, day);
                const dowOffset = (dayDate.getDay() + 6) % 7;
                const mondayDate = new Date(dayDate);
                mondayDate.setDate(dayDate.getDate() - dowOffset);
                const weekMonday = mondayDate.toISOString().slice(0, 10);

                let bg: string;
                if (!rec || !rec.submitted) {
                  bg = isToday ? 'var(--border-top)' : 'var(--split-bg)';
                } else if (rec.is_compliant === false) {
                  bg = 'var(--red-strong)';
                } else {
                  bg = 'var(--green-strong)';
                }

                const isViewedWeek = (() => {
                  const activeMonday = viewWeekStart ?? data?.week_start;
                  return activeMonday === weekMonday;
                })();

                cells.push(
                  <button
                    key={dstr}
                    title={`${dstr}${rec?.submitted ? (rec.is_compliant === false ? ' — Violation' : ' — Compliant') : ' — Not filed'}`}
                    onClick={() => {
                      const nowYM = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`;
                      const todayMonday = (() => {
                        const t = new Date();
                        const diff = (t.getDay() + 6) % 7;
                        t.setDate(t.getDate() - diff);
                        return t.toISOString().slice(0, 10);
                      })();
                      setViewWeekStart(weekMonday === todayMonday ? null : weekMonday);
                      setCalendarOpen(false);
                    }}
                    style={{
                      background: bg,
                      border: isViewedWeek ? '1px solid var(--mark-border)' : '1px solid transparent',
                      borderRadius: 3,
                      color: rec?.submitted ? 'var(--txt)' : 'var(--txt-ghost)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 9,
                      cursor: 'pointer',
                      padding: '4px 0',
                      textAlign: 'center',
                      transition: 'opacity 0.1s',
                    }}
                  >
                    {day}
                  </button>
                );
              }

              return (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
                  {cells}
                </div>
              );
            })()}

            {/* Legend */}
            <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 10, justifyContent: 'flex-end' }}>
              {[
                { color: 'var(--green-strong)', label: 'Compliant' },
                { color: 'var(--red-strong)', label: 'Violation' },
                { color: 'var(--split-bg)', label: 'Not filed' },
              ].map(({ color, label }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--txt-ghost)' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Finalized banner */}
        {weekLocked && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'var(--border-faint)',
            border: '1px solid var(--border-top)',
            borderRadius: 'var(--radius-pill)',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--txt-ghost)',
          }}>
            🔒 This week is finalized. To make changes, ask your HOD to submit a correction request.
          </div>
        )}

        {/* HOD signed — soft lock warning */}
        {signoffStatus === 'hod_signed' && !weekLocked && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'var(--amber-bg)',
            border: '1px solid var(--amber-border)',
            borderRadius: 'var(--radius-pill)',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--amber)',
          }}>
            HOD has counter-signed this week. Editing will require your HOD to re-counter-sign.
          </div>
        )}

        {/* Correction requested banner */}
        {correctionRequested && !forceReadOnly && (
          <div style={{
            margin: '8px 16px',
            padding: '8px 12px',
            background: 'var(--amber-bg)',
            border: '1px solid var(--amber-border)',
            borderRadius: 'var(--radius-pill)',
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--amber)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
              Correction Requested by HOD
            </div>
            {correctionNote && (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--amber)' }}>
                {correctionNote}
              </div>
            )}
          </div>
        )}

        <div style={{ padding: '4px 0' }}>
          {data.days.filter(Boolean).map((day: any, idx: number) => {
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
                  borderBottom: idx < 6 ? '1px solid var(--border-faint)' : undefined,
                  background: hasWarning && !isSubmitted ? 'var(--red-bg)' : undefined,
                }}
              >
                {/* Day header row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: isSubmitted ? 6 : 8 }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--txt2)',
                    width: 28,
                  }}>{day.label}</span>

                  {isSubmitted ? (
                    <>
                      <span style={{ fontSize: 12, color: 'var(--txt2)' }}>
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
                        ok={displayDay.is_compliant ?? displayDay.is_daily_compliant ?? null}
                        label={
                          (displayDay.is_compliant ?? displayDay.is_daily_compliant) === false
                            ? 'Violation'
                            : 'Compliant'
                        }
                      />
                      {/* Submitted this session — show acknowledgement + Undo */}
                      {canUndo && (
                        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green)', fontWeight: 600 }}>Submitted ✓</span>
                          <button
                            onClick={() => undoDay(day.date)}
                            style={{
                              padding: '3px 8px',
                              background: 'none',
                              border: '1px solid var(--border-top)',
                              borderRadius: 'var(--radius-pill)',
                              color: 'var(--txt2)',
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
                    <span style={{ fontSize: 12, color: 'var(--txt-ghost)', fontStyle: 'italic' }}>Not submitted</span>
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
                        background: 'var(--mark)',
                        border: 'none',
                        borderRadius: 'var(--radius-pill)',
                        color: 'var(--surface-base)',
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
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--red-strong)' }}>
                      ✕ {submitErrors[day.date]}
                    </span>
                  </div>
                )}

                {/* Violation warnings */}
                {isSubmitted && hasWarning && (
                  <div style={{ marginBottom: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {warnings.map((w: any, wi: number) => (
                      <span key={wi} style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 9,
                        color: 'var(--red-strong)',
                        paddingLeft: 38,
                      }}>⚠ {w.message ?? 'Compliance rule breached'}</span>
                    ))}
                  </div>
                )}

                {/* Crew comment — shown when required (MLC A2.3) or when comment was provided */}
                {!isReadOnly && commentRequired[day.date] && (
                  <div style={{ paddingLeft: 38, paddingBottom: 8 }}>
                    <textarea
                      placeholder="MLC required: explain why rest requirement could not be met…"
                      value={crewComments[day.date] ?? ''}
                      onChange={e => setCrewComments(prev => ({ ...prev, [day.date]: e.target.value }))}
                      rows={2}
                      style={{
                        width: '100%',
                        background: 'var(--surface-el)',
                        border: '1px solid var(--red-border)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--txt3)',
                        fontFamily: 'var(--font-body)',
                        fontSize: 11,
                        padding: '6px 8px',
                        resize: 'vertical',
                        outline: 'none',
                        boxSizing: 'border-box',
                      }}
                    />
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
      <SectionCard>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px 0' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.10em' }}>Templates</span>
          {canCreateTemplate && (
            <button
              onClick={() => { setCreateTemplateOpen(v => !v); setCreateTemplateError(null); }}
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                color: createTemplateOpen ? 'var(--txt-ghost)' : 'var(--mark)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                letterSpacing: '0.06em',
                padding: '2px 0',
              }}
            >{createTemplateOpen ? 'Cancel' : '+ Create Template'}</button>
          )}
        </div>

        {/* ── Apply existing template ── */}
        {data.templates.length > 0 && (
          <div style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
            <select
              value={selectedTemplate}
              onChange={e => setSelectedTemplate(e.target.value)}
              style={{
                flex: 1,
                background: 'var(--surface-el)',
                border: '1px solid var(--border-chrome)',
                borderRadius: 'var(--radius-pill)',
                color: 'var(--txt3)',
                fontFamily: 'var(--font-body)',
                fontSize: 12,
                padding: '6px 10px',
                outline: 'none',
              }}
            >
              <option value="">Select a template…</option>
              {data.templates.map((t: any) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <button
              onClick={applyTemplate}
              disabled={!selectedTemplate || applyingTemplate}
              style={{
                padding: '6px 14px',
                background: selectedTemplate ? 'var(--teal-bg)' : 'var(--border-faint)',
                border: '1px solid var(--mark-border)',
                borderRadius: 'var(--radius-pill)',
                color: selectedTemplate ? 'var(--mark)' : 'var(--txt-ghost)',
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
        )}
        {data.templates.length === 0 && !createTemplateOpen && (
          <p style={{ padding: '6px 16px 10px', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', lineHeight: 1.5 }}>
            No templates yet. Create one to prefill unsubmitted days.
          </p>
        )}
        {data.templates.length > 0 && (
          <p style={{ padding: '0 16px 10px', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', lineHeight: 1.5 }}>
            Template populates unsubmitted days only. Your signature is still required.
          </p>
        )}

        {/* ── Inline create template form ── */}
        {createTemplateOpen && (
          <div style={{ padding: '10px 16px 14px', display: 'flex', flexDirection: 'column', gap: 8, borderTop: '1px solid var(--border-faint)' }}>
            <input
              type="text"
              placeholder="Template name (required)"
              value={newTemplateName}
              onChange={e => setNewTemplateName(e.target.value)}
              style={{
                background: 'var(--surface-el)',
                border: '1px solid var(--border-chrome)',
                borderRadius: 4,
                color: 'var(--txt3)',
                fontFamily: 'var(--font-body)',
                fontSize: 12,
                padding: '6px 10px',
                outline: 'none',
                width: '100%',
              }}
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newTemplateDesc}
              onChange={e => setNewTemplateDesc(e.target.value)}
              style={{
                background: 'var(--surface-el)',
                border: '1px solid var(--border-chrome)',
                borderRadius: 4,
                color: 'var(--txt3)',
                fontFamily: 'var(--font-body)',
                fontSize: 12,
                padding: '6px 10px',
                outline: 'none',
                width: '100%',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', whiteSpace: 'nowrap' }}>Work hours (all days)</span>
              <input
                type="time"
                value={newTemplateWorkStart}
                onChange={e => setNewTemplateWorkStart(e.target.value)}
                style={{
                  background: 'var(--surface-el)',
                  border: '1px solid var(--border-chrome)',
                  borderRadius: 4,
                  color: 'var(--txt3)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  padding: '4px 6px',
                  outline: 'none',
                }}
              />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>to</span>
              <input
                type="time"
                value={newTemplateWorkEnd}
                onChange={e => setNewTemplateWorkEnd(e.target.value)}
                style={{
                  background: 'var(--surface-el)',
                  border: '1px solid var(--border-chrome)',
                  borderRadius: 4,
                  color: 'var(--txt3)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  padding: '4px 6px',
                  outline: 'none',
                }}
              />
              <button
                onClick={createTemplate}
                disabled={!newTemplateName.trim() || creatingTemplate}
                style={{
                  padding: '5px 12px',
                  background: newTemplateName.trim() ? 'var(--teal-bg)' : 'var(--border-faint)',
                  border: '1px solid var(--mark-border)',
                  borderRadius: 'var(--radius-pill)',
                  color: newTemplateName.trim() ? 'var(--mark)' : 'var(--txt-ghost)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  cursor: newTemplateName.trim() ? 'pointer' : 'not-allowed',
                  whiteSpace: 'nowrap',
                  marginLeft: 'auto',
                }}
              >{creatingTemplate ? 'Saving…' : 'Save Template'}</button>
            </div>
            {createTemplateError && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--red)' }}>{createTemplateError}</span>
            )}
          </div>
        )}
      </SectionCard>

      {/* ── COMPLIANCE ── */}
      <SectionCard>
        <SectionHeader label="Compliance" />
        <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--txt2)' }}>
              24h rolling — {comp.rolling_24h_rest != null ? `${comp.rolling_24h_rest}h rest` : '—'}
            </span>
            {comp.rolling_24h_rest != null
              ? <StatusBadge ok={comp.rolling_24h_rest >= comp.min_24h} label={comp.rolling_24h_rest >= comp.min_24h ? `✓ min ${comp.min_24h}h` : `⚠ min ${comp.min_24h}h`} />
              : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>No data today</span>
            }
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--txt2)' }}>
              7-day rolling — {comp.rolling_7day_rest != null ? `${comp.rolling_7day_rest}h rest` : '—'}
            </span>
            {comp.rolling_7day_rest != null
              ? <StatusBadge ok={comp.rolling_7day_rest >= comp.min_7d} label={comp.rolling_7day_rest >= comp.min_7d ? `✓ min ${comp.min_7d}h` : `⚠ min ${comp.min_7d}h`} />
              : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>No data</span>
            }
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: 'var(--txt2)' }}>This week — {comp.rolling_7d_work != null ? `${comp.rolling_7d_work}h worked` : '—'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4, paddingTop: 'var(--space-2)', borderTop: '1px solid var(--border-faint)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--txt-ghost)' }}>MLC 2006 Status</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
              color: comp.mlc_status === 'COMPLIANT' ? 'var(--green)' : 'var(--red)',
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
              <div style={{ fontSize: 13, color: 'var(--txt)', marginBottom: 3 }}>
                {formatMonth(signoff.month)}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>
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
                  background: 'var(--mark)',
                  border: 'none',
                  borderRadius: 'var(--radius-pill)',
                  color: 'var(--surface-base)',
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
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green)' }}>Submitted ✓</span>
            )}
          </div>
        </SectionCard>
      )}

      {/* ── ACTIVE WARNINGS ── */}
      {warnings.length > 0 && (
        <SectionCard>
          <SectionHeader label="Active Warnings" />
          <div style={{ padding: '4px 0' }}>
            {warnings.map((w: any) => (
              <div key={w.id} style={{
                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
                padding: '10px 16px', borderBottom: '1px solid var(--border-faint)', gap: 'var(--space-3)',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 3 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, color: w.severity === 'critical' ? 'var(--red)' : 'var(--amber)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      ⚠ {w.severity ?? 'warning'}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>
                      {w.record_date ?? ''}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--txt3)', lineHeight: 1.45 }}>
                    {w.message ?? w.warning_type ?? 'Compliance rule breached'}
                  </div>
                </div>
                <button
                  onClick={() => acknowledgeWarning(w.id)}
                  disabled={acknowledging[w.id]}
                  style={{
                    flexShrink: 0, padding: '4px 10px',
                    background: 'none', border: '1px solid var(--border-top)',
                    borderRadius: 'var(--radius-pill)', color: 'var(--txt-ghost)',
                    fontFamily: 'var(--font-mono)', fontSize: 9,
                    cursor: acknowledging[w.id] ? 'wait' : 'pointer',
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                    opacity: acknowledging[w.id] ? 0.5 : 1,
                  }}
                >
                  {acknowledging[w.id] ? '…' : 'Acknowledge'}
                </button>
              </div>
            ))}
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
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--txt-ghost)' }}>History</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: historyOpen ? 'rotate(180deg)' : undefined, transition: 'transform 0.15s', color: 'var(--txt-ghost)' }}>
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
          {historyOpen && (
            <div style={{ borderTop: '1px solid var(--border-faint)' }}>
              {data.prior_weeks.map((w: any) => (
                <div
                  key={w.week_start}
                  onClick={() => setViewWeekStart(w.week_start)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '9px 16px', borderBottom: '1px solid var(--border-faint)',
                    cursor: 'pointer', transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div>
                    <span style={{ fontSize: 12, color: 'var(--txt2)' }}>{w.label}</span>
                    {w.days_filed < 7 && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', marginLeft: 'var(--space-2)' }}>
                        {w.days_filed}/7 days filed
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>{w.total_rest_hours}h rest</span>
                    <StatusBadge ok={w.is_compliant} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>›</span>
                  </div>
                </div>
              ))}
              <div style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>
                Avg {((data.prior_weeks.reduce((s: number, w: any) => s + (w.total_rest_hours || 0), 0) / data.prior_weeks.length) || 0).toFixed(1)}h rest/week
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
