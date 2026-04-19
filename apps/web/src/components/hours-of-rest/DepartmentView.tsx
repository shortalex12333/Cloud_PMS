'use client';

/**
 * DepartmentView — HOD (chief_engineer, eto) department overview
 *
 * Consumes: GET /v1/hours-of-rest/department-status?week_start=YYYY-MM-DD
 *
 * Shows:
 * - Today's submission status (X/Y submitted, missing names)
 * - Pending counter-signs card with "Review & Counter-Sign" action
 * - Crew × day matrix with daily rest hours
 * - Department compliance summary
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { MyTimeView } from './MyTimeView';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';

// ── Types ────────────────────────────────────────────────────────────────────

interface CrewDay {
  date: string;       // "YYYY-MM-DD"
  rest_hours: number | null;
  status: 'submitted' | 'hod_signed' | 'finalized' | 'missing';
}

interface CrewMember {
  user_id: string;
  name: string;
  role: string;
  days: CrewDay[];    // 7 entries for the week
  is_weekly_compliant: boolean | null;
}

interface PendingSignoff {
  signoff_id: string;
  crew_user_id: string;
  crew_name: string;
  week_label: string; // "Apr 7 – Apr 13"
  submitted_at: string;
}

interface HoRNotification {
  id: string;
  notification_type: 'violation_alert' | 'correction_notice' | 'sign_request' | string;
  title: string;
  body: string;
  entity_id: string;
  metadata: {
    crew_user_id?: string;
    record_date?: string;
    total_rest_hours?: number;
  };
  is_read: boolean;
  created_at: string;
}

interface DepartmentStatus {
  week_start: string;
  department: string;
  today_submitted: number;
  today_total: number;
  today_missing: string[];       // names of crew who haven't submitted today
  pending_counter_signs: PendingSignoff[];
  crew: CrewMember[];
  compliance: {
    compliant_days: number;
    total_days: number;
    violations: number;
    avg_rest_hours: number;
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getCurrentWeekStart(): string {
  const now = new Date();
  const day = now.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day; // adjust to Monday
  const mon = new Date(now);
  mon.setDate(now.getDate() + diff);
  return mon.toISOString().slice(0, 10);
}

function formatWeekLabel(weekStart: string): string {
  const start = new Date(weekStart);
  const end = new Date(weekStart);
  end.setDate(end.getDate() + 6);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[start.getMonth()]} ${start.getDate()} – ${months[end.getMonth()]} ${end.getDate()}`;
}

function restHoursColor(hours: number | null): string {
  if (hours === null) return 'var(--txt-ghost)';
  if (hours < 10) return 'var(--red-strong)';    // MLC violation — minimum is 10h rest/day
  if (hours < 10.5) return 'var(--compliance-warn)'; // borderline
  return 'var(--mark-strong)';                    // ok
}

function statusDot(status: CrewDay['status']): string {
  switch (status) {
    case 'finalized':   return 'var(--green-strong)';
    case 'hod_signed':  return 'var(--mark-strong)';
    case 'submitted':   return 'var(--amber)';
    default:            return 'var(--txt-ghost)';
  }
}

// ── MLC declaration ──────────────────────────────────────────────────────────

const MLC_HOD_DECLARATION =
  'I confirm I have reviewed and verified the above crew member\'s hours of rest ' +
  'in accordance with MLC 2006 Regulation 2.3.';

// ── Response normalizer ───────────────────────────────────────────────────────
// Maps real API response shapes to component types.
// Real API uses: crew[].daily[], pending_signoffs{awaiting_hod,signoff_ids}, compliance.missing_today[]

function normalizeDepStatus(raw: any, ws: string): DepartmentStatus {
  const comp = raw.compliance ?? {};
  const ps = raw.pending_signoffs ?? {};
  const crewRaw: any[] = raw.crew ?? [];

  // Name lookup from crew array (backend sends signoff_ids + crew_user_ids, not crew_names)
  const nameByUserId: Record<string, string> = {};
  for (const m of crewRaw) {
    if (m.user_id && m.name) nameByUserId[m.user_id] = m.name;
  }

  const pending_counter_signs: PendingSignoff[] = [];
  const signoffIds: string[] = Array.isArray(ps.signoff_ids) ? ps.signoff_ids : [];
  const crewUserIds: string[] = Array.isArray(ps.crew_user_ids) ? ps.crew_user_ids : [];
  signoffIds.forEach((id: string, i: number) => {
    const uid = crewUserIds[i] ?? '';
    pending_counter_signs.push({
      signoff_id: id,
      crew_user_id: uid,
      crew_name: nameByUserId[uid] ?? `Crew member ${i + 1}`,
      week_label: formatWeekLabel(ws),
      submitted_at: new Date().toISOString(),
    });
  });

  const crew: CrewMember[] = crewRaw.map((m: any) => ({
    user_id: m.user_id ?? m.id ?? String(Math.random()),
    name: m.name ?? '—',
    role: m.role ?? '',
    is_weekly_compliant: m.is_weekly_compliant ?? null,
    // Backend sends daily[] with {date, rest_hours, work_hours, submitted, compliant}
    days: (m.daily ?? m.days ?? []).map((d: any) => ({
      date: d.date,
      rest_hours: d.rest_hours ?? d.total_rest_hours ?? null,
      // Backend sends submitted:bool, not status string
      status: d.submitted ? 'submitted' : ((d.status ?? 'missing') as CrewDay['status']),
    })),
  }));

  // Compute compliance summary from crew aggregate fields (backend doesn't nest these under compliance{})
  let totalCompliantDays = 0;
  let totalSubmittedDays = 0;
  let totalViolations = 0;
  let totalRestHours = 0;
  for (const m of crewRaw) {
    totalCompliantDays += m.days_compliant ?? 0;
    totalSubmittedDays += m.days_submitted ?? 0;
    if (m.has_active_warnings) totalViolations++;
    if (m.total_rest_hours != null) totalRestHours += m.total_rest_hours;
  }
  // avg_rest_hours = daily average across all submitted crew-days
  const avgRestHours = totalSubmittedDays > 0
    ? parseFloat((totalRestHours / totalSubmittedDays).toFixed(1))
    : 0;

  return {
    week_start: raw.week_start ?? ws,
    department: raw.department ?? '',
    // Backend sends submitted_count and total_crew at top level, not inside compliance{}
    today_submitted: raw.submitted_count ?? 0,
    today_total: raw.total_crew ?? 0,
    today_missing: comp.missing_today ?? raw.today_missing ?? [],
    pending_counter_signs,
    crew,
    compliance: {
      compliant_days: totalCompliantDays,
      total_days: totalSubmittedDays,
      violations: totalViolations,
      avg_rest_hours: avgRestHours,
    },
  };
}

// ── Component ────────────────────────────────────────────────────────────────

export function DepartmentView() {
  const { session } = useAuth();

  const [weekStart, setWeekStart] = React.useState(getCurrentWeekStart);
  const [data, setData] = React.useState<DepartmentStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [signingId, setSigningId] = React.useState<string | null>(null);
  const [signingPopupId, setSigningPopupId] = React.useState<string | null>(null);
  const [viewingUserId, setViewingUserId] = React.useState<string | null>(null);
  // Per-crew sign popup — opened from the "View" modal
  const [crewSignPopupUserId, setCrewSignPopupUserId] = React.useState<string | null>(null);
  const [notifications, setNotifications] = React.useState<HoRNotification[]>([]);
  const [correctionPopupSignoff, setCorrectionPopupSignoff] = React.useState<PendingSignoff | null>(null);
  const [submittingCorrection, setSubmittingCorrection] = React.useState(false);

  // ── Load ──

  async function loadData(ws: string) {
    setLoading(true);
    setError(null);
    try {
      const token = session?.access_token;
      if (!token) throw new Error('Not authenticated');
      const res = await fetch(`/api/v1/hours-of-rest/department-status?week_start=${ws}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load department status (${res.status})`);
      const json = await res.json();
      const raw = json.success ? json.data : json;
      if (raw) {
        setData(normalizeDepStatus(raw, ws));
        return;
      }
      throw new Error('Unexpected response shape from department-status endpoint');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load department data');
    } finally {
      setLoading(false);
    }
  }

  async function loadNotifications() {
    try {
      const token = session?.access_token;
      if (!token) return;
      const res = await fetch('/api/v1/hours-of-rest/notifications/unread', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const json = await res.json();
      const d = json.success ? json.data : (json.data ?? json);
      setNotifications(d?.notifications ?? []);
    } catch { /* silent */ }
  }

  async function markNotificationsRead(ids: string[]) {
    try {
      const token = session?.access_token;
      if (!token || ids.length === 0) return;
      await fetch('/api/v1/hours-of-rest/notifications/mark-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ notification_ids: ids }),
      });
    } catch { /* silent */ }
  }

  async function requestCorrection(ps: PendingSignoff, note: string) {
    setSubmittingCorrection(true);
    try {
      const token = session?.access_token;
      if (!token) return;
      await fetch('/api/v1/hours-of-rest/request-correction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          signoff_id: ps.signoff_id,
          target_user_id: ps.crew_user_id,
          correction_note: note,
          role: 'hod',
        }),
      });
    } finally {
      setSubmittingCorrection(false);
    }
  }

  React.useEffect(() => {
    loadData(weekStart);
    loadNotifications();
  }, [weekStart, session?.access_token]);

  // ── Counter-sign ──

  async function counterSign(signoffId: string, signatureName: string) {
    setSigningId(signoffId);
    try {
      const token = session?.access_token;
      if (!token) return;
      await fetch('/api/v1/hours-of-rest/signoffs/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          signoff_id: signoffId,
          signature_level: 'hod',
          signature_data: {
            name: signatureName,
            declaration: MLC_HOD_DECLARATION,
            timestamp: new Date().toISOString(),
          },
        }),
      });
      await loadData(weekStart);
    } finally {
      setSigningId(null);
    }
  }

  // ── Week nav ──

  function shiftWeek(dir: -1 | 1) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + dir * 7);
    setWeekStart(d.toISOString().slice(0, 10));
  }

  if (loading) {
    return (
      <div style={{ padding: 32, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        Loading department data…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 32, color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        {error ?? 'No department data available.'}
      </div>
    );
  }

  const weekLabel = formatWeekLabel(data.week_start);
  const compliancePct = data.compliance.total_days > 0
    ? Math.round((data.compliance.compliant_days / data.compliance.total_days) * 100)
    : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

      {/* ── View identity header ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        paddingBottom: 'var(--space-3)',
        borderBottom: '1px solid var(--border-sub)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'var(--mark-strong)',
          background: 'var(--teal-bg)',
          border: '1px solid var(--mark-border)',
          borderRadius: 'var(--radius-pill)',
          padding: '3px 8px',
        }}>
          {data.department ? `${data.department.toUpperCase()} DEPT` : 'YOUR DEPARTMENT'}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          HOD view — crew under your supervision only
        </span>
      </div>

      {/* ── Week nav ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <button onClick={() => shiftWeek(-1)} style={navBtnStyle}>←</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt2)', minWidth: 140, textAlign: 'center' }}>
          {weekLabel}
        </span>
        <button onClick={() => shiftWeek(1)} style={navBtnStyle}>→</button>
      </div>

      {/* ── Violation alert notifications ── */}
      {notifications.filter(n => n.notification_type === 'violation_alert' && !n.is_read).length > 0 && (() => {
        const alerts = notifications.filter(n => n.notification_type === 'violation_alert' && !n.is_read);
        return (
          <div style={{
            background: 'var(--red-bg)',
            border: '1px solid var(--red-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--red)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                MLC Violations — {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={() => {
                  markNotificationsRead(alerts.map(n => n.id));
                  setNotifications(prev => prev.map(n =>
                    alerts.some(a => a.id === n.id) ? { ...n, is_read: true } : n
                  ));
                }}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9,
                  color: 'var(--txt-ghost)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  letterSpacing: '0.04em',
                }}
              >Dismiss all</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {alerts.map(n => (
                <div key={n.id} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>
                  {n.body || n.title}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── Today's submission status ── */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: data.today_missing.length > 0 ? 10 : 0 }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--txt2)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}>Today</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 14,
            fontWeight: 600,
            color: data.today_submitted === data.today_total ? 'var(--green-strong)' : 'var(--compliance-warn)',
          }}>
            {data.today_submitted}/{data.today_total} submitted
          </span>
        </div>
        {data.today_missing.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>Missing:</span>
            {data.today_missing.map(name => (
              <span key={name} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                color: 'var(--red)',
                background: 'var(--red-bg)',
                border: '1px solid var(--red-border)',
                borderRadius: 3,
                padding: '1px 6px',
              }}>{name}</span>
            ))}
          </div>
        )}
      </div>

      {/* ── Pending counter-signs ── */}
      {data.pending_counter_signs.length > 0 && (
        <div style={cardStyle}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Pending Counter-Signs ({data.pending_counter_signs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {data.pending_counter_signs.map(ps => (
              <div key={ps.signoff_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt)' }}>{ps.crew_name}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', marginLeft: 'var(--space-2)' }}>{ps.week_label}</span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => setCorrectionPopupSignoff(ps)}
                    disabled={signingId === ps.signoff_id}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10,
                      color: 'var(--amber)',
                      background: 'var(--amber-bg)',
                      border: '1px solid var(--amber-border)',
                      borderRadius: 'var(--radius-pill)',
                      padding: '4px 10px',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >Request Correction</button>
                  <button
                    data-testid={`hor-counter-sign-${ps.signoff_id}`}
                    onClick={() => { if (!signingId) setSigningPopupId(ps.signoff_id); }}
                    disabled={signingId === ps.signoff_id}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10,
                      color: signingId === ps.signoff_id ? 'var(--txt-ghost)' : 'var(--mark-strong)',
                      background: 'var(--teal-bg)',
                      border: '1px solid var(--mark-border)',
                      borderRadius: 'var(--radius-pill)',
                      padding: '4px 10px',
                      cursor: signingId === ps.signoff_id ? 'wait' : 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {signingId === ps.signoff_id ? 'Signing…' : 'Review & Counter-Sign'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Crew × day grid ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-3)' }}>
          Crew Hours Grid
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 480 }}>
            <thead>
              <tr>
                <th style={thStyle({ width: 140, textAlign: 'left' })}>Crew</th>
                {WEEK_DAYS.map(d => (
                  <th key={d} style={thStyle({ width: 52, textAlign: 'center' })}>{d}</th>
                ))}
                <th style={thStyle({ width: 52, textAlign: 'center' })}>Avg</th>
                <th style={thStyle({ width: 72, textAlign: 'center' })}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.crew.map((member) => {
                const daysWithData = member.days.filter(d => d.rest_hours !== null);
                const avg = daysWithData.length
                  ? (daysWithData.reduce((s, d) => s + (d.rest_hours ?? 0), 0) / daysWithData.length).toFixed(1)
                  : '—';
                const hasViolation = member.is_weekly_compliant === false;

                return (
                  <tr key={member.user_id} style={{ borderTop: '1px solid var(--border-faint)' }}>
                    <td style={{ padding: '8px 0', paddingRight: 'var(--space-3)' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt)' }}>{member.name}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', marginTop: 1 }}>{member.role}</div>
                    </td>
                    {member.days.map((day) => (
                      <td key={day.date} style={{ padding: '8px 4px', textAlign: 'center' }}>
                        {day.rest_hours !== null ? (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 36,
                            height: 28,
                            borderRadius: 'var(--radius-pill)',
                            background: `color-mix(in srgb, ${restHoursColor(day.rest_hours)} 15%, transparent)`,
                            border: `1px solid color-mix(in srgb, ${restHoursColor(day.rest_hours)} 35%, transparent)`,
                          }}>
                            <span style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: 11,
                              color: restHoursColor(day.rest_hours),
                            }}>{day.rest_hours.toFixed(1)}</span>
                          </div>
                        ) : (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 36,
                            height: 28,
                            borderRadius: 'var(--radius-pill)',
                          }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>—</span>
                          </div>
                        )}
                      </td>
                    ))}
                    <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt2)' }}>{avg}</span>
                    </td>
                    <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                        <button
                          onClick={() => setViewingUserId(member.user_id)}
                          style={{
                            padding: '3px 8px',
                            background: hasViolation ? 'var(--red-bg)' : 'var(--surface-subtle)',
                            border: `1px solid ${hasViolation ? 'var(--red-border-strong)' : 'var(--border-chrome)'}`,
                            borderRadius: 'var(--radius-pill)',
                            color: hasViolation ? 'var(--red-strong)' : 'var(--txt2)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: 9,
                            fontWeight: hasViolation ? 600 : 400,
                            cursor: 'pointer',
                            letterSpacing: '0.06em',
                          }}
                        >View</button>
                        {member.is_weekly_compliant === true && (
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--green-strong)' }}>✓</span>
                        )}
                        {hasViolation && (
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red-strong)' }}>⚠</span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Status legend */}
        <div style={{ display: 'flex', gap: 14, marginTop: 'var(--space-3)', flexWrap: 'wrap' }}>
          {[
            { color: 'var(--green-strong)', label: 'Finalized' },
            { color: 'var(--mark-strong)', label: 'HOD signed' },
            { color: 'var(--amber)', label: 'Submitted' },
            { color: 'var(--red-strong)', label: '<10h rest (MLC violation)' },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Compliance summary ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-3)' }}>
          Department Compliance — {weekLabel}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-3)' }}>
          {[
            { label: 'Compliance', value: `${compliancePct}%`, color: compliancePct >= 95 ? 'var(--compliance-good)' : compliancePct >= 80 ? 'var(--compliance-warn)' : 'var(--compliance-crit)' },
            { label: 'Compliant Days', value: `${data.compliance.compliant_days}/${data.compliance.total_days}`, color: 'var(--txt3)' },
            { label: 'Violations', value: String(data.compliance.violations), color: data.compliance.violations > 0 ? 'var(--compliance-crit)' : 'var(--compliance-good)' },
            { label: 'Avg Rest', value: `${data.compliance.avg_rest_hours.toFixed(1)}h`, color: 'var(--mark-strong)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Correction request popup (L1) ── */}
      {correctionPopupSignoff && (
        <ActionPopup
          mode="mutate"
          title="Request Correction"
          subtitle={`${correctionPopupSignoff.crew_name} — ${correctionPopupSignoff.week_label}`}
          signatureLevel={1}
          submitLabel={submittingCorrection ? 'Sending…' : 'Send Request'}
          submitDisabled={submittingCorrection}
          fields={[
            { name: 'crew_member', label: 'Crew Member', type: 'kv-read', value: correctionPopupSignoff.crew_name },
            { name: 'week',        label: 'Week',         type: 'kv-read', value: correctionPopupSignoff.week_label },
            {
              name: 'correction_note',
              label: 'Note to crew member',
              type: 'text-area',
              required: true,
              placeholder: 'Describe what needs to be corrected (e.g. "Day 3 shows 8.5h rest — MLC minimum is 10h, please re-enter your rest periods.")',
            },
          ]}
          onClose={() => setCorrectionPopupSignoff(null)}
          onSubmit={async (values) => {
            const note = String(values.correction_note ?? '').trim();
            if (!note) return;
            setCorrectionPopupSignoff(null);
            await requestCorrection(correctionPopupSignoff, note);
          }}
        />
      )}

      {/* ── HOD counter-sign popup (L2) ── */}
      {signingPopupId && (() => {
        const ps = data.pending_counter_signs.find(p => p.signoff_id === signingPopupId);
        if (!ps) return null;
        return (
          <ActionPopup
            mode="mutate"
            title="Counter-Sign Hours of Rest"
            subtitle={`MLC 2006 Reg. 2.3 — HOD Attestation`}
            signatureLevel={2}
            submitLabel="Counter-Sign"
            fields={[
              { name: 'crew_member', label: 'Crew Member', type: 'kv-read', value: ps.crew_name },
              { name: 'week',        label: 'Week',         type: 'kv-read', value: ps.week_label },
              { name: 'department',  label: 'Department',   type: 'kv-read', value: data.department },
              { name: 'regulation',  label: 'Regulation',   type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            previewRows={[
              { key: 'Dept Compliance', value: `${compliancePct}%` },
              { key: 'Violations',      value: String(data.compliance.violations) },
              { key: 'Avg Rest',        value: `${data.compliance.avg_rest_hours.toFixed(1)}h` },
            ]}
            onClose={() => setSigningPopupId(null)}
            onSubmit={(values) => {
              setSigningPopupId(null);
              counterSign(ps.signoff_id, String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Per-crew HOD sign popup (opened from view modal Sign Off button) ── */}
      {crewSignPopupUserId && (() => {
        const member = data.crew.find(m => m.user_id === crewSignPopupUserId);
        const ps = data.pending_counter_signs.find(p => p.crew_user_id === crewSignPopupUserId);
        if (!ps) return null;
        return (
          <ActionPopup
            mode="mutate"
            title="Sign Off for Approval"
            subtitle="MLC 2006 Reg. 2.3 — HOD Attestation"
            signatureLevel={2}
            submitLabel="Sign Off"
            fields={[
              { name: 'crew_member', label: 'Crew Member', type: 'kv-read', value: member?.name ?? ps.crew_name },
              { name: 'week',        label: 'Week',         type: 'kv-read', value: ps.week_label },
              { name: 'department',  label: 'Department',   type: 'kv-read', value: data.department },
              { name: 'regulation',  label: 'Regulation',   type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            onClose={() => setCrewSignPopupUserId(null)}
            onSubmit={(values) => {
              setCrewSignPopupUserId(null);
              setViewingUserId(null);
              counterSign(ps.signoff_id, String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Read-only My Time overlay (HOD viewing a crew member's violation) ── */}
      {viewingUserId && (() => {
        const member = data.crew.find(m => m.user_id === viewingUserId);
        return (
          <div
            style={{
              position: 'fixed', inset: 0, zIndex: 50,
              background: 'var(--overlay-bg)',
              display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
              paddingTop: 48, overflowY: 'auto',
            }}
            onClick={e => { if (e.target === e.currentTarget) setViewingUserId(null); }}
          >
            <div style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-top)',
              borderRadius: 'var(--radius-md)',
              width: '100%',
              maxWidth: 720,
              padding: 'var(--space-6)',
              margin: '0 16px 48px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--txt3)' }}>
                    {member?.name ?? 'Crew Member'} — Hours of Rest
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', marginLeft: 10 }}>Read-only</span>
                </div>
                <button
                  onClick={() => setViewingUserId(null)}
                  style={{ background: 'none', border: 'none', color: 'var(--txt2)', fontSize: 18, cursor: 'pointer', lineHeight: 1 }}
                >×</button>
              </div>
              {/* Sign Off button — shown when this crew member has a pending signoff */}
              {(() => {
                const ps = data.pending_counter_signs.find(p => p.crew_user_id === viewingUserId);
                if (!ps) return null;
                return (
                  <div style={{
                    marginBottom: 'var(--space-4)',
                    paddingBottom: 'var(--space-4)',
                    borderBottom: '1px solid var(--border-sub)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                  }}>
                    <button
                      onClick={() => setCrewSignPopupUserId(viewingUserId)}
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 10,
                        color: 'var(--mark-strong)',
                        background: 'var(--teal-bg)',
                        border: '1px solid var(--mark-border)',
                        borderRadius: 'var(--radius-pill)',
                        padding: '6px 14px',
                        cursor: 'pointer',
                        letterSpacing: '0.06em',
                        whiteSpace: 'nowrap',
                      }}
                    >Sign Off for Approval</button>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 9,
                      color: 'var(--txt-ghost)',
                    }}>
                      MLC 2006 — HOD attestation required before captain sign-off
                    </span>
                  </div>
                );
              })()}
              <MyTimeView targetUserId={viewingUserId} readOnly />
            </div>
          </div>
        );
      })()}

    </div>
  );
}

// ── Shared styles ────────────────────────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  background: 'var(--surface-card)',
  border: '1px solid var(--border-sub)',
  borderRadius: 'var(--radius-sm)',
  padding: '14px 16px',
};

const navBtnStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  color: 'var(--txt2)',
  background: 'var(--surface-subtle)',
  border: '1px solid var(--border-chrome)',
  borderRadius: 'var(--radius-pill)',
  padding: '4px 10px',
  cursor: 'pointer',
};

function thStyle(extra: React.CSSProperties): React.CSSProperties {
  return {
    fontFamily: 'var(--font-mono)',
    fontSize: 9,
    color: 'var(--txt-ghost)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    fontWeight: 400,
    paddingBottom: 'var(--space-2)',
    ...extra,
  };
}
