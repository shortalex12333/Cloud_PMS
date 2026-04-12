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
}

interface PendingSignoff {
  signoff_id: string;
  crew_name: string;
  week_label: string; // "Apr 7 – Apr 13"
  submitted_at: string;
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

// ── Mock data ────────────────────────────────────────────────────────────────

const WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getMockWeekDates(weekStart: string): string[] {
  const start = new Date(weekStart);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

function buildMockDepartmentStatus(weekStart: string): DepartmentStatus {
  const dates = getMockWeekDates(weekStart);
  return {
    week_start: weekStart,
    department: 'Engineering',
    today_submitted: 3,
    today_total: 5,
    today_missing: ['P. Kowalski', 'R. Singh'],
    pending_counter_signs: [
      { signoff_id: 'ps-001', crew_name: 'J. Martinez', week_label: 'Apr 7 – Apr 13', submitted_at: '2026-04-12T08:14:00Z' },
      { signoff_id: 'ps-002', crew_name: 'A. Novak', week_label: 'Apr 7 – Apr 13', submitted_at: '2026-04-11T19:55:00Z' },
    ],
    crew: [
      {
        user_id: 'u1', name: 'J. Martinez', role: 'Second Engineer',
        days: dates.map((date, i) => ({
          date,
          rest_hours: i < 5 ? [8.5, 7.0, 8.0, 8.5, 7.5, null, null][i] : null,
          status: (i < 5 ? 'submitted' : 'missing') as CrewDay['status'],
        })),
      },
      {
        user_id: 'u2', name: 'A. Novak', role: 'Third Engineer',
        days: dates.map((date, i) => ({
          date,
          rest_hours: i < 4 ? [9.0, 8.0, 7.5, 8.0, null, null, null][i] : null,
          status: (i < 4 ? 'hod_signed' : 'missing') as CrewDay['status'],
        })),
      },
      {
        user_id: 'u3', name: 'P. Kowalski', role: 'Engine Rating',
        days: dates.map((date, i) => ({
          date,
          rest_hours: i < 6 ? [8.0, 8.0, 8.0, 8.0, 8.0, 8.0, null][i] : null,
          status: (i < 6 ? 'submitted' : 'missing') as CrewDay['status'],
        })),
      },
      {
        user_id: 'u4', name: 'R. Singh', role: 'Oiler',
        days: dates.map((date, i) => ({
          date,
          rest_hours: i < 3 ? [6.5, 7.0, 8.5, null, null, null, null][i] : null,
          status: (i < 3 ? 'submitted' : 'missing') as CrewDay['status'],
        })),
      },
      {
        user_id: 'u5', name: 'M. Chen', role: 'Electrician',
        days: dates.map((date, i) => ({
          date,
          rest_hours: [8.0, 8.5, 7.0, 9.0, 8.0, 8.5, null][i] ?? null,
          status: (i < 6 ? 'finalized' : 'missing') as CrewDay['status'],
        })),
      },
    ],
    compliance: {
      compliant_days: 28,
      total_days: 30,
      violations: 2,
      avg_rest_hours: 8.1,
    },
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

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
  if (hours === null) return 'rgba(255,255,255,0.12)';
  if (hours < 6) return 'rgba(239,68,68,0.8)';   // violation
  if (hours < 7) return 'rgba(245,158,11,0.8)';  // borderline
  return 'rgba(90,171,204,0.8)';                  // ok
}

function statusDot(status: CrewDay['status']): string {
  switch (status) {
    case 'finalized':   return 'rgba(34,197,94,0.8)';
    case 'hod_signed':  return 'rgba(90,171,204,0.8)';
    case 'submitted':   return 'rgba(245,158,11,0.6)';
    default:            return 'rgba(255,255,255,0.12)';
  }
}

// ── Component ────────────────────────────────────────────────────────────────

export function DepartmentView() {
  const { session } = useAuth();

  const [weekStart, setWeekStart] = React.useState(getCurrentWeekStart);
  const [data, setData] = React.useState<DepartmentStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [signingId, setSigningId] = React.useState<string | null>(null);

  // ── Load ──

  async function loadData(ws: string) {
    setLoading(true);
    try {
      const token = session?.access_token;
      if (!token) throw new Error('no token');
      const res = await fetch(`/api/v1/hours-of-rest/department-status?week_start=${ws}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('not ready');
      const json = await res.json();
      if (json.success && json.data) {
        setData(json.data);
        return;
      }
      throw new Error('unexpected shape');
    } catch {
      // endpoint not live yet — use mock
      setData(buildMockDepartmentStatus(ws));
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => { loadData(weekStart); }, [weekStart, session?.access_token]);

  // ── Counter-sign ──

  async function counterSign(signoffId: string) {
    setSigningId(signoffId);
    try {
      const token = session?.access_token;
      await fetch('/api/v1/hours-of-rest/signoffs/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ signoff_id: signoffId, level: 'hod' }),
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

  if (loading || !data) {
    return (
      <div style={{ padding: 32, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        Loading department data…
      </div>
    );
  }

  const weekLabel = formatWeekLabel(data.week_start);
  const compliancePct = data.compliance.total_days > 0
    ? Math.round((data.compliance.compliant_days / data.compliance.total_days) * 100)
    : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Week nav ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={() => shiftWeek(-1)} style={navBtnStyle}>←</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.5)', minWidth: 140, textAlign: 'center' }}>
          {weekLabel}
        </span>
        <button onClick={() => shiftWeek(1)} style={navBtnStyle}>→</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 4 }}>
          {data.department}
        </span>
      </div>

      {/* ── Today's submission status ── */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: data.today_missing.length > 0 ? 10 : 0 }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'rgba(255,255,255,0.5)',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}>Today</span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 14,
            fontWeight: 600,
            color: data.today_submitted === data.today_total ? 'rgba(34,197,94,0.9)' : 'rgba(245,158,11,0.9)',
          }}>
            {data.today_submitted}/{data.today_total} submitted
          </span>
        </div>
        {data.today_missing.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)' }}>Missing:</span>
            {data.today_missing.map(name => (
              <span key={name} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                color: 'rgba(239,68,68,0.8)',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.2)',
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
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Pending Counter-Signs ({data.pending_counter_signs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.pending_counter_signs.map(ps => (
              <div key={ps.signoff_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>{ps.crew_name}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 8 }}>{ps.week_label}</span>
                </div>
                <button
                  onClick={() => counterSign(ps.signoff_id)}
                  disabled={signingId === ps.signoff_id}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    color: signingId === ps.signoff_id ? 'rgba(255,255,255,0.3)' : 'rgba(90,171,204,0.9)',
                    background: 'rgba(90,171,204,0.08)',
                    border: '1px solid rgba(90,171,204,0.3)',
                    borderRadius: 4,
                    padding: '4px 10px',
                    cursor: signingId === ps.signoff_id ? 'wait' : 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {signingId === ps.signoff_id ? 'Signing…' : 'Review & Counter-Sign'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Crew × day grid ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
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
              </tr>
            </thead>
            <tbody>
              {data.crew.map((member, ri) => {
                const submittedDays = member.days.filter(d => d.rest_hours !== null);
                const avg = submittedDays.length
                  ? (submittedDays.reduce((s, d) => s + (d.rest_hours ?? 0), 0) / submittedDays.length).toFixed(1)
                  : '—';

                return (
                  <tr key={member.user_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '8px 0', paddingRight: 12 }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>{member.name}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>{member.role}</div>
                    </td>
                    {member.days.map((day, di) => (
                      <td key={day.date} style={{ padding: '8px 4px', textAlign: 'center' }}>
                        {day.rest_hours !== null ? (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: 36,
                            height: 28,
                            borderRadius: 4,
                            background: `${restHoursColor(day.rest_hours)}22`,
                            border: `1px solid ${restHoursColor(day.rest_hours)}55`,
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
                            borderRadius: 4,
                          }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.15)' }}>—</span>
                          </div>
                        )}
                      </td>
                    ))}
                    <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>{avg}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Status legend */}
        <div style={{ display: 'flex', gap: 14, marginTop: 12, flexWrap: 'wrap' }}>
          {[
            { color: 'rgba(34,197,94,0.8)', label: 'Finalized' },
            { color: 'rgba(90,171,204,0.8)', label: 'HOD signed' },
            { color: 'rgba(245,158,11,0.6)', label: 'Submitted' },
            { color: 'rgba(239,68,68,0.8)', label: '<6h violation' },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Compliance summary ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          Department Compliance — {weekLabel}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { label: 'Compliance', value: `${compliancePct}%`, color: compliancePct >= 95 ? 'rgba(34,197,94,0.9)' : compliancePct >= 80 ? 'rgba(245,158,11,0.9)' : 'rgba(239,68,68,0.9)' },
            { label: 'Compliant Days', value: `${data.compliance.compliant_days}/${data.compliance.total_days}`, color: 'rgba(255,255,255,0.7)' },
            { label: 'Violations', value: String(data.compliance.violations), color: data.compliance.violations > 0 ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.9)' },
            { label: 'Avg Rest', value: `${data.compliance.avg_rest_hours.toFixed(1)}h`, color: 'rgba(90,171,204,0.9)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

// ── Shared styles ────────────────────────────────────────────────────────────

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 8,
  padding: '14px 16px',
};

const navBtnStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 12,
  color: 'rgba(255,255,255,0.5)',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 4,
  padding: '4px 10px',
  cursor: 'pointer',
};

function thStyle(extra: React.CSSProperties): React.CSSProperties {
  return {
    fontFamily: 'var(--font-mono)',
    fontSize: 9,
    color: 'rgba(255,255,255,0.3)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    fontWeight: 400,
    paddingBottom: 8,
    ...extra,
  };
}
