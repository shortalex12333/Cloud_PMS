'use client';

/**
 * VesselComplianceView — Captain / Manager vessel-wide HoR overview
 *
 * Consumes: GET /v1/hours-of-rest/vessel-compliance?week_start=YYYY-MM-DD
 *
 * Shows:
 * - Department compliance cards (Engineering ✓, Deck ⚠, Interior ✓)
 * - Pending final signs card
 * - All-crew grid by department with daily hours
 * - Analytics (avg rest hours, compliance rate, violations)
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';

// ── Types ────────────────────────────────────────────────────────────────────

interface DeptDay {
  date: string;
  rest_hours: number | null;
  status: 'submitted' | 'hod_signed' | 'finalized' | 'missing';
}

interface DeptCrewMember {
  user_id: string;
  name: string;
  role: string;
  days: DeptDay[];
}

interface PendingFinalSign {
  signoff_id: string;
  department: string;
  week_label: string;
  hod_name: string;
  signed_at: string;
}

interface DepartmentCard {
  name: string;
  crew_count: number;
  compliance_pct: number;
  violations: number;
  avg_work_hours: number;
  submitted_today: number;
  total_today: number;
  crew: DeptCrewMember[];
}

interface VesselCompliance {
  week_start: string;
  vessel_name: string;
  departments: DepartmentCard[];
  pending_final_signs: PendingFinalSign[];
  vessel_analytics: {
    overall_compliance_pct: number;
    total_violations: number;
    avg_work_hours: number;
    total_crew: number;
    fully_compliant_departments: number;
  };
}

// ── Mock data ────────────────────────────────────────────────────────────────

function getMockWeekDates(weekStart: string): string[] {
  const start = new Date(weekStart);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

function buildMockVesselCompliance(weekStart: string): VesselCompliance {
  const dates = getMockWeekDates(weekStart);

  const makeDays = (pattern: (number | null)[]): DeptDay[] =>
    dates.map((date, i) => ({
      date,
      rest_hours: pattern[i] ?? null,
      status: (pattern[i] !== null ? 'submitted' : 'missing') as DeptDay['status'],
    }));

  return {
    week_start: weekStart,
    vessel_name: 'M/Y Test Vessel',
    departments: [
      {
        name: 'Engineering',
        crew_count: 5,
        compliance_pct: 96,
        violations: 1,
        avg_work_hours: 8.1,
        submitted_today: 4,
        total_today: 5,
        crew: [
          { user_id: 'e1', name: 'J. Martinez',  role: 'Second Engineer', days: makeDays([8.5, 7.0, 8.0, 8.5, 7.5, null, null]) },
          { user_id: 'e2', name: 'A. Novak',     role: 'Third Engineer',  days: makeDays([9.0, 8.0, 7.5, 8.0, null, null, null]) },
          { user_id: 'e3', name: 'P. Kowalski',  role: 'Engine Rating',   days: makeDays([8.0, 8.0, 8.0, 8.0, 8.0, 8.0, null]) },
          { user_id: 'e4', name: 'R. Singh',     role: 'Oiler',           days: makeDays([6.5, 7.0, 8.5, null, null, null, null]) },
          { user_id: 'e5', name: 'M. Chen',      role: 'Electrician',     days: makeDays([8.0, 8.5, 7.0, 9.0, 8.0, 8.5, null]) },
        ],
      },
      {
        name: 'Deck',
        crew_count: 4,
        compliance_pct: 75,
        violations: 3,
        avg_work_hours: 7.2,
        submitted_today: 2,
        total_today: 4,
        crew: [
          { user_id: 'd1', name: 'T. Okonkwo',   role: 'First Mate',      days: makeDays([7.0, 6.5, 7.5, 5.5, 7.0, null, null]) },
          { user_id: 'd2', name: 'S. Petrov',    role: 'Bosun',           days: makeDays([8.0, 7.5, null, 7.0, null, null, null]) },
          { user_id: 'd3', name: 'K. Williams',  role: 'Deck Hand',       days: makeDays([7.5, 8.0, 7.0, 8.0, 8.0, 8.0, null]) },
          { user_id: 'd4', name: 'L. Ferreira',  role: 'Deck Hand',       days: makeDays([8.0, null, null, null, null, null, null]) },
        ],
      },
      {
        name: 'Interior',
        crew_count: 3,
        compliance_pct: 100,
        violations: 0,
        avg_work_hours: 8.6,
        submitted_today: 3,
        total_today: 3,
        crew: [
          { user_id: 'i1', name: 'C. Dubois',    role: 'Chief Steward',   days: makeDays([9.0, 8.5, 9.0, 8.5, null, null, null]) },
          { user_id: 'i2', name: 'N. Santos',    role: 'Steward',         days: makeDays([8.5, 8.5, 8.5, 8.5, 8.5, null, null]) },
          { user_id: 'i3', name: 'V. Orlov',     role: 'Chef',            days: makeDays([8.0, 9.0, 8.0, 9.0, null, null, null]) },
        ],
      },
    ],
    pending_final_signs: [
      { signoff_id: 'fs-001', department: 'Engineering', week_label: 'Mar 31 – Apr 6', hod_name: 'Chief Engineer', signed_at: '2026-04-08T09:00:00Z' },
    ],
    vessel_analytics: {
      overall_compliance_pct: 91,
      total_violations: 4,
      avg_work_hours: 8.0,
      total_crew: 12,
      fully_compliant_departments: 2,
    },
  };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getCurrentWeekStart(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const mon = new Date(now);
  mon.setDate(now.getDate() + diff);
  return mon.toISOString().slice(0, 10);
}

function formatWeekLabel(weekStart: string): string {
  const start = new Date(weekStart);
  const end = new Date(weekStart);
  end.setDate(end.getDate() + 6);
  const m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${m[start.getMonth()]} ${start.getDate()} – ${m[end.getMonth()]} ${end.getDate()}`;
}

function complianceColor(pct: number): string {
  if (pct >= 95) return 'rgba(34,197,94,0.9)';
  if (pct >= 80) return 'rgba(245,158,11,0.9)';
  return 'rgba(239,68,68,0.9)';
}

function restHoursColor(hours: number | null): string {
  if (hours === null) return 'rgba(255,255,255,0.12)';
  if (hours < 6) return 'rgba(239,68,68,0.8)';
  if (hours < 7) return 'rgba(245,158,11,0.8)';
  return 'rgba(90,171,204,0.8)';
}

const WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── Response normalizer ───────────────────────────────────────────────────────
// Maps real API response to component types.
// Real API: all_crew[] (flat, has .department field), analytics{} (not vessel_analytics{})
// Real analytics fields: compliance_rate, violations_this_quarter, avg_work_hours

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeVesselCompliance(raw: any, ws: string): VesselCompliance {
  const a = raw.analytics ?? raw.vessel_analytics ?? {};

  // Build departments — may have nested crew[] OR we join from all_crew[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const allCrewFlat: any[] = Array.isArray(raw.all_crew) ? raw.all_crew : [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawDepts: any[] = Array.isArray(raw.departments) ? raw.departments : [];

  const departments: DepartmentCard[] = rawDepts.map((d: any) => {
    // Nested crew in dept, or join from flat all_crew by department name
    const nestedCrew: any[] = Array.isArray(d.crew) ? d.crew : [];
    const flatCrew: any[] = allCrewFlat.filter((c: any) =>
      (c.department ?? '').toLowerCase() === (d.name ?? '').toLowerCase()
    );
    const crewSource = nestedCrew.length > 0 ? nestedCrew : flatCrew;

    return {
      name: d.name ?? d.department ?? '—',
      crew_count: d.crew_count ?? d.crew_total ?? crewSource.length,
      compliance_pct: d.compliance_pct ?? d.compliance_rate ?? 0,
      violations: d.violations ?? 0,
      avg_work_hours: d.avg_work_hours ?? 0,
      submitted_today: d.submitted_today ?? 0,
      total_today: d.total_today ?? d.crew_count ?? 0,
      crew: crewSource.map((m: any) => ({
        user_id: m.user_id ?? m.id ?? String(Math.random()),
        name: m.name ?? '—',
        role: m.role ?? '',
        days: (m.daily ?? m.days ?? []).map((day: any) => ({
          date: day.date,
          rest_hours: day.rest_hours ?? day.total_rest_hours ?? null,
          status: (day.status ?? 'missing') as DeptDay['status'],
        })),
      })),
    };
  });

  return {
    week_start: raw.week_start ?? ws,
    vessel_name: raw.vessel_name ?? raw.yacht_name ?? '—',
    departments,
    pending_final_signs: (raw.pending_final_signs ?? []).map((ps: any) => ({
      signoff_id: ps.signoff_id ?? ps.id,
      department: ps.department ?? '—',
      week_label: ps.week_label ?? formatWeekLabel(ws),
      hod_name: ps.hod_name ?? '—',
      signed_at: ps.signed_at ?? new Date().toISOString(),
    })),
    vessel_analytics: {
      // real: compliance_rate (0-100 pct), violations_this_quarter, avg_work_hours
      overall_compliance_pct: a.overall_compliance_pct ?? a.compliance_rate ?? 0,
      total_violations: a.total_violations ?? a.violations_this_quarter ?? 0,
      avg_work_hours: a.avg_work_hours ?? 0,
      total_crew: a.total_crew ?? allCrewFlat.length ?? 0,
      fully_compliant_departments: a.fully_compliant_departments ?? 0,
    },
  };
}

// ── Component ────────────────────────────────────────────────────────────────

export function VesselComplianceView() {
  const { session } = useAuth();

  const [weekStart, setWeekStart] = React.useState(getCurrentWeekStart);
  const [data, setData] = React.useState<VesselCompliance | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [expandedDept, setExpandedDept] = React.useState<string | null>(null);
  const [signingId, setSigningId] = React.useState<string | null>(null);

  // ── Load ──

  async function loadData(ws: string) {
    setLoading(true);
    try {
      const token = session?.access_token;
      if (!token) throw new Error('no token');
      const res = await fetch(`/api/v1/hours-of-rest/vessel-compliance?week_start=${ws}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('not ready');
      const json = await res.json();
      const raw = json.success ? json.data : json;
      if (raw) { setData(normalizeVesselCompliance(raw, ws)); return; }
      throw new Error('unexpected shape');
    } catch {
      setData(buildMockVesselCompliance(ws));
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => { loadData(weekStart); }, [weekStart, session?.access_token]);

  // ── Final sign ──

  async function finalSign(signoffId: string) {
    setSigningId(signoffId);
    try {
      const token = session?.access_token;
      await fetch('/api/v1/hours-of-rest/signoffs/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ signoff_id: signoffId, level: 'captain' }),
      });
      await loadData(weekStart);
    } finally {
      setSigningId(null);
    }
  }

  function shiftWeek(dir: -1 | 1) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + dir * 7);
    setWeekStart(d.toISOString().slice(0, 10));
  }

  if (loading || !data) {
    return (
      <div style={{ padding: 32, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        Loading vessel compliance…
      </div>
    );
  }

  const weekLabel = formatWeekLabel(data.week_start);
  const va = data.vessel_analytics;

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
          {data.vessel_name}
        </span>
      </div>

      {/* ── Vessel analytics ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
          Vessel Analytics — {weekLabel}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[
            { label: 'Compliance', value: `${va.overall_compliance_pct}%`, color: complianceColor(va.overall_compliance_pct) },
            { label: 'Violations', value: String(va.total_violations), color: va.total_violations > 0 ? 'rgba(239,68,68,0.9)' : 'rgba(34,197,94,0.9)' },
            { label: 'Avg Work', value: `${va.avg_work_hours.toFixed(1)}h`, color: 'rgba(90,171,204,0.9)' },
            { label: 'Total Crew', value: String(va.total_crew), color: 'rgba(255,255,255,0.7)' },
            { label: 'Dept OK', value: `${va.fully_compliant_departments}/${data.departments.length}`, color: 'rgba(34,197,94,0.9)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pending final signs ── */}
      {data.pending_final_signs.length > 0 && (
        <div style={{ ...cardStyle, borderColor: 'rgba(245,158,11,0.25)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(245,158,11,0.7)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Pending Final Signs ({data.pending_final_signs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.pending_final_signs.map(ps => (
              <div key={ps.signoff_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
                    {ps.department}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', marginLeft: 8 }}>
                    {ps.week_label} · signed by {ps.hod_name}
                  </span>
                </div>
                <button
                  onClick={() => finalSign(ps.signoff_id)}
                  disabled={signingId === ps.signoff_id}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    color: signingId === ps.signoff_id ? 'rgba(255,255,255,0.3)' : 'rgba(34,197,94,0.9)',
                    background: 'rgba(34,197,94,0.08)',
                    border: '1px solid rgba(34,197,94,0.3)',
                    borderRadius: 4,
                    padding: '4px 10px',
                    cursor: signingId === ps.signoff_id ? 'wait' : 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {signingId === ps.signoff_id ? 'Signing…' : 'Final Sign'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Department cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
        {data.departments.map(dept => {
          const isExpanded = expandedDept === dept.name;
          const statusColor = complianceColor(dept.compliance_pct);
          return (
            <div key={dept.name} style={{
              ...cardStyle,
              borderColor: isExpanded ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)',
              cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}
              onClick={() => setExpandedDept(isExpanded ? null : dept.name)}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>
                  {dept.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: statusColor,
                  background: `${statusColor}15`,
                  border: `1px solid ${statusColor}40`,
                  borderRadius: 3,
                  padding: '1px 6px',
                }}>
                  {dept.compliance_pct}%
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <Stat label="Today" value={`${dept.submitted_today}/${dept.total_today}`} color="rgba(255,255,255,0.6)" />
                <Stat label="Avg Work" value={`${dept.avg_work_hours.toFixed(1)}h`} color="rgba(90,171,204,0.8)" />
                <Stat label="Crew" value={String(dept.crew_count)} color="rgba(255,255,255,0.4)" />
                <Stat label="Violations" value={String(dept.violations)} color={dept.violations > 0 ? 'rgba(239,68,68,0.8)' : 'rgba(34,197,94,0.7)'} />
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 8, textAlign: 'center' }}>
                {isExpanded ? '▲ collapse' : '▼ show crew'}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Expanded crew grid (shown below cards when a dept is expanded) ── */}
      {expandedDept && (() => {
        const dept = data.departments.find(d => d.name === expandedDept);
        if (!dept) return null;
        return (
          <div style={cardStyle}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
              {dept.name} — Crew Hours Grid
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
                  {dept.crew.map(member => {
                    const submitted = member.days.filter(d => d.rest_hours !== null);
                    const avg = submitted.length
                      ? (submitted.reduce((s, d) => s + (d.rest_hours ?? 0), 0) / submitted.length).toFixed(1)
                      : '—';
                    return (
                      <tr key={member.user_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '8px 0', paddingRight: 12 }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>{member.name}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>{member.role}</div>
                        </td>
                        {member.days.map(day => (
                          <td key={day.date} style={{ padding: '8px 4px', textAlign: 'center' }}>
                            {day.rest_hours !== null ? (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                width: 36, height: 28, borderRadius: 4,
                                background: `${restHoursColor(day.rest_hours)}22`,
                                border: `1px solid ${restHoursColor(day.rest_hours)}55`,
                              }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: restHoursColor(day.rest_hours) }}>
                                  {day.rest_hours.toFixed(1)}
                                </span>
                              </div>
                            ) : (
                              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 28 }}>
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
          </div>
        );
      })()}

    </div>
  );
}

// ── Small helpers ────────────────────────────────────────────────────────────

function Stat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color }}>{value}</span>
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
