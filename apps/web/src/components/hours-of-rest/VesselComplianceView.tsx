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
import { ActionPopup } from '@/components/lens-v2/ActionPopup';

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
  // Phase 6: sign chain fields
  signoff_id: string | null;
  status: 'draft' | 'crew_signed' | 'hod_signed' | 'finalized' | string;
  hod_signed_at: string | null;
  correction_requested: boolean;
  correction_note: string | null;
}

interface SignChain {
  all_hods_signed: boolean;
  captain_signed: boolean;
  fleet_manager_reviewed: boolean;
  ready_for_captain: boolean;
  ready_for_fleet_manager: boolean;
}

interface VesselCompliance {
  week_start: string;
  vessel_name: string;
  departments: DepartmentCard[];
  pending_final_signs: PendingFinalSign[];
  sign_chain: SignChain;
  vessel_analytics: {
    overall_compliance_pct: number;
    total_violations: number;
    avg_work_hours: number;      // weekly total average
    avg_work_hours_per_day: number;
    total_crew: number;
    fully_compliant_departments: number;
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
  if (pct >= 95) return 'var(--compliance-good)';
  if (pct >= 80) return 'var(--compliance-warn)';
  return 'var(--compliance-crit)';
}

function restHoursColor(hours: number | null): string {
  if (hours === null) return 'var(--txt-ghost)';
  if (hours < 10) return 'var(--red-strong)';    // MLC violation — minimum is 10h rest/day
  if (hours < 10.5) return 'var(--compliance-warn)'; // borderline
  return 'var(--mark-strong)';                    // ok
}

const WEEK_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── MLC declaration ──────────────────────────────────────────────────────────

const MLC_MASTER_DECLARATION =
  'I confirm I have reviewed and verified the vessel hours of rest records ' +
  'in accordance with MLC 2006 Regulation 2.3 as Master.';

// ── Response normalizer ───────────────────────────────────────────────────────
// Maps real API response to component types.
// Real API: all_crew[] (flat, has .department field), analytics{} (not vessel_analytics{})
// Real analytics fields: compliance_rate, violations_this_quarter, avg_work_hours

function normalizeVesselCompliance(raw: any, ws: string): VesselCompliance {
  const a = raw.analytics ?? raw.vessel_analytics ?? {};

  // Build departments — may have nested crew[] OR we join from all_crew[]
  const allCrewFlat: any[] = Array.isArray(raw.all_crew) ? raw.all_crew : [];
  const rawDepts: any[] = Array.isArray(raw.departments) ? raw.departments : [];

  const departments: DepartmentCard[] = rawDepts.map((d: any) => {
    // Backend uses d.department as the key, not d.name
    const deptName = d.department ?? d.name ?? '—';
    // vessel-compliance has no nested crew[]; join from flat all_crew[] by department
    const nestedCrew: any[] = Array.isArray(d.crew) ? d.crew : [];
    const flatCrew: any[] = allCrewFlat.filter((c: any) =>
      (c.department ?? '').toLowerCase() === deptName.toLowerCase()
    );
    const crewSource = nestedCrew.length > 0 ? nestedCrew : flatCrew;
    const totalCrew = d.total_crew ?? d.crew_count ?? crewSource.length;

    // Backend sends compliant_count and total_crew, not compliance_pct per dept
    const compliantCount = d.compliant_count ?? 0;
    const compliancePct = totalCrew > 0
      ? Math.round(compliantCount / totalCrew * 100)
      : (d.compliance_pct ?? 0);

    return {
      name: deptName,
      crew_count: totalCrew,
      compliance_pct: compliancePct,
      // Backend sends pending_warnings (crew with active warnings), not violations
      violations: d.violations ?? d.pending_warnings ?? 0,
      avg_work_hours: d.avg_work_hours ?? 0,
      submitted_today: d.submitted_today ?? d.submitted_count ?? 0,
      total_today: d.total_today ?? totalCrew,
      signoff_id: d.signoff_id ?? null,
      status: d.status ?? 'draft',
      hod_signed_at: d.hod_signed_at ?? null,
      correction_requested: d.correction_requested ?? false,
      correction_note: d.correction_note ?? null,
      crew: crewSource.map((m: any) => ({
        user_id: m.user_id ?? m.id ?? String(Math.random()),
        name: m.name ?? '—',
        role: m.role ?? '',
        // vessel-compliance all_crew[] has no daily[] — weekly aggregate only
        days: (m.daily ?? m.days ?? []).map((day: any) => ({
          date: day.date,
          rest_hours: day.rest_hours ?? day.total_rest_hours ?? null,
          status: day.submitted ? 'submitted' : ((day.status ?? 'missing') as DeptDay['status']),
        })),
      })),
    };
  });

  return {
    week_start: raw.week_start ?? ws,
    vessel_name: raw.vessel_name ?? raw.yacht_name ?? '—',
    departments,
    sign_chain: {
      all_hods_signed: raw.sign_chain?.all_hods_signed ?? false,
      captain_signed: raw.sign_chain?.captain_signed ?? false,
      fleet_manager_reviewed: raw.sign_chain?.fleet_manager_reviewed ?? false,
      ready_for_captain: raw.sign_chain?.ready_for_captain ?? false,
      ready_for_fleet_manager: raw.sign_chain?.ready_for_fleet_manager ?? false,
    },
    pending_final_signs: (raw.pending_final_signs ?? []).map((ps: any) => ({
      signoff_id: ps.signoff_id ?? ps.id,
      department: ps.department ?? '—',
      week_label: ps.week_label ?? formatWeekLabel(ws),
      hod_name: ps.hod_name ?? '—',
      signed_at: ps.signed_at ?? new Date().toISOString(),
    })),
    vessel_analytics: {
      overall_compliance_pct: a.compliance_pct ?? a.overall_compliance_pct ?? 0,
      total_violations: a.violations_this_week ?? a.total_violations ?? 0,
      avg_work_hours: a.avg_work_hours_per_week ?? a.avg_work_hours ?? 0,
      avg_work_hours_per_day: a.avg_work_hours_per_day ?? (a.avg_work_hours_per_week ? a.avg_work_hours_per_week / 7 : a.avg_work_hours ? a.avg_work_hours / 7 : 0),
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
  const [error, setError] = React.useState<string | null>(null);
  const [expandedDept, setExpandedDept] = React.useState<string | null>(null);
  const [signingId, setSigningId] = React.useState<string | null>(null);
  const [signingPopupId, setSigningPopupId] = React.useState<string | null>(null);
  const [signAllPopupOpen, setSignAllPopupOpen] = React.useState(false);
  const [signingAll, setSigningAll] = React.useState(false);

  // ── Load ──

  async function loadData(ws: string) {
    setLoading(true);
    setError(null);
    try {
      const token = session?.access_token;
      if (!token) throw new Error('Not authenticated');
      const res = await fetch(`/api/v1/hours-of-rest/vessel-compliance?week_start=${ws}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load vessel compliance (${res.status})`);
      const json = await res.json();
      const raw = json.success ? json.data : json;
      if (raw) { setData(normalizeVesselCompliance(raw, ws)); return; }
      throw new Error('Unexpected response shape from vessel-compliance endpoint');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load vessel compliance data');
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => { loadData(weekStart); }, [weekStart, session?.access_token]);

  // ── Final sign ──

  async function signAllDepartments(signatureName: string) {
    if (!data) return;
    // BUG-HOR-1 fix: guard session token BEFORE the loop — prevents `Bearer undefined`
    // being sent for every dept when the user has no active session.
    if (!session?.access_token) return;
    const token = session.access_token;
    const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);
    const skipped = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');
    if (skipped.length > 0) {
      // Non-fatal warning — log to console, still sign the signable ones
      console.warn(`[HoR] Skipping ${skipped.length} dept(s) not yet HOD-signed: ${skipped.map(d => d.name).join(', ')}`);
    }
    setSigningAll(true);
    try {
      for (const dept of signable) {
        await fetch('/api/v1/hours-of-rest/signoffs/sign', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            signoff_id: dept.signoff_id,
            signature_level: 'master',
            signature_data: {
              name: signatureName,
              declaration: MLC_MASTER_DECLARATION,
              timestamp: new Date().toISOString(),
            },
          }),
        });
      }
      await loadData(weekStart);
    } finally {
      setSigningAll(false);
    }
  }

  async function finalSign(signoffId: string, signatureName: string) {
    setSigningId(signoffId);
    try {
      const token = session?.access_token;
      if (!token) return;
      await fetch('/api/v1/hours-of-rest/signoffs/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          signoff_id: signoffId,
          signature_level: 'master',
          signature_data: {
            name: signatureName,
            declaration: MLC_MASTER_DECLARATION,
            timestamp: new Date().toISOString(),
          },
        }),
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

  if (loading) {
    return (
      <div style={{ padding: 32, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        Loading vessel compliance…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 32, color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        {error ?? 'No vessel compliance data available.'}
      </div>
    );
  }

  const weekLabel = formatWeekLabel(data.week_start);
  const va = data.vessel_analytics;

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
        {/* NOTE: VESSEL OVERVIEW badge uses purple inline — no purple token exists yet.
            Flagged for design decision; keeping inline rgba to avoid invented tokens. */}
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'rgba(168,85,247,0.8)',
          background: 'rgba(168,85,247,0.08)',
          border: '1px solid rgba(168,85,247,0.20)',
          borderRadius: 'var(--radius-pill)',
          padding: '3px 8px',
        }}>
          VESSEL OVERVIEW
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          All departments — captain / fleet manager view
        </span>
      </div>

      {/* ── Week nav ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <button onClick={() => shiftWeek(-1)} style={navBtnStyle}>←</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt2)', minWidth: 140, textAlign: 'center' }}>
          {weekLabel}
        </span>
        <button onClick={() => shiftWeek(1)} style={navBtnStyle}>→</button>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', marginLeft: 4 }}>
          {data.vessel_name}
        </span>
      </div>

      {/* ── Vessel analytics ── */}
      <div style={cardStyle}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-3)' }}>
          Vessel Analytics — {weekLabel}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-3)' }}>
          {[
            { label: 'Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%`, color: complianceColor(va.overall_compliance_pct) },
            { label: 'Violations', value: String(va.total_violations), color: va.total_violations > 0 ? 'var(--compliance-crit)' : 'var(--compliance-good)' },
            { label: 'Total Crew', value: String(va.total_crew), color: 'var(--txt3)' },
            { label: 'Dept OK', value: `${va.fully_compliant_departments}/${data.departments.length}`, color: 'var(--compliance-good)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
          {/* Avg Work — two lines: per day and per week */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Avg Work</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600, color: 'var(--mark-strong)' }}>
              {va.avg_work_hours_per_day.toFixed(1)}h/day
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--mark)' }}>
              {va.avg_work_hours.toFixed(1)}h/wk
            </span>
          </div>
        </div>
      </div>

      {/* ── Captain sign chain card ── */}
      {(() => {
        const sc = data.sign_chain;
        const hodSigned = data.departments.filter(d => d.status === 'hod_signed' || d.status === 'finalized');
        const hodPending = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');
        const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);

        if (sc.captain_signed) {
          return (
            <div style={{ ...cardStyle, borderColor: 'var(--green-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--green-strong)' }}>Master Signed ✓</span>
                {sc.fleet_manager_reviewed
                  ? <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)' }}>Fleet Reviewed ✓</span>
                  : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>Pending fleet review</span>
                }
              </div>
            </div>
          );
        }

        if (hodSigned.length === 0 && hodPending.length === 0) return null;

        return (
          <div style={{ ...cardStyle, borderColor: sc.all_hods_signed ? 'var(--mark-border)' : 'var(--amber-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)', marginBottom: 10 }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt3)', fontWeight: 600 }}>
                  Captain Attestation
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', marginTop: 3 }}>
                  {sc.all_hods_signed
                    ? 'All departments HOD-signed — ready for captain sign-off'
                    : `${hodPending.length} dept${hodPending.length !== 1 ? 's' : ''} awaiting HOD sign-off`}
                </div>
              </div>
              <button
                data-testid="hor-sign-all-depts"
                onClick={() => setSignAllPopupOpen(true)}
                disabled={signingAll || !sc.all_hods_signed}
                title={sc.all_hods_signed ? undefined : 'All departments must be HOD-signed before captain sign-off'}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: (signingAll || !sc.all_hods_signed) ? 'var(--txt-ghost)' : 'var(--green-strong)',
                  background: sc.all_hods_signed ? 'var(--green-bg)' : 'var(--surface-subtle)',
                  border: `1px solid ${sc.all_hods_signed ? 'var(--green-border)' : 'var(--border-chrome)'}`,
                  borderRadius: 'var(--radius-pill)',
                  padding: '5px 14px',
                  cursor: (signingAll || !sc.all_hods_signed) ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                  opacity: sc.all_hods_signed ? 1 : 0.5,
                }}
              >
                {signingAll ? 'Signing…' : `Sign ${signable.length} Dept${signable.length !== 1 ? 's' : ''}`}
              </button>
            </div>

            {/* Per-department HOD sign status */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {data.departments.map(d => {
                const dSigned = d.status === 'hod_signed' || d.status === 'finalized';
                return (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 9,
                      color: dSigned ? 'var(--green-strong)' : 'var(--amber)',
                    }}>
                      {dSigned ? '✓' : '○'}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: dSigned ? 'var(--txt2)' : 'var(--txt-ghost)' }}>
                      {d.name}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>
                      {dSigned
                        ? (d.hod_signed_at ? `HOD signed ${new Date(d.hod_signed_at).toLocaleDateString()}` : 'HOD signed')
                        : 'Awaiting HOD'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* ── Pending final signs (legacy — individual dept HOD signoffs) ── */}
      {data.pending_final_signs.length > 0 && (
        <div style={{ ...cardStyle, borderColor: 'var(--amber-border)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--amber)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Pending Final Signs ({data.pending_final_signs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {data.pending_final_signs.map(ps => (
              <div key={ps.signoff_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--txt)' }}>
                    {ps.department}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', marginLeft: 'var(--space-2)' }}>
                    {ps.week_label} · signed by {ps.hod_name}
                  </span>
                </div>
                <button
                  onClick={() => { if (!signingId) setSigningPopupId(ps.signoff_id); }}
                  disabled={signingId === ps.signoff_id}
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                    color: signingId === ps.signoff_id ? 'var(--txt-ghost)' : 'var(--green-strong)',
                    background: 'var(--green-bg)',
                    border: '1px solid var(--green-border)',
                    borderRadius: 'var(--radius-pill)',
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
              borderColor: isExpanded ? 'var(--txt-ghost)' : 'var(--border-sub)',
              cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}
              onClick={() => setExpandedDept(isExpanded ? null : dept.name)}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt3)', fontWeight: 600 }}>
                  {dept.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: statusColor,
                  background: `color-mix(in srgb, ${statusColor} 12%, transparent)`,
                  border: `1px solid color-mix(in srgb, ${statusColor} 30%, transparent)`,
                  borderRadius: 3,
                  padding: '1px 6px',
                }}>
                  {dept.compliance_pct}%
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                <Stat label="Today" value={`${dept.submitted_today}/${dept.total_today}`} color="var(--txt2)" />
                <Stat label="Avg Work" value={`${dept.avg_work_hours.toFixed(1)}h`} color="var(--mark-strong)" />
                <Stat label="Crew" value={String(dept.crew_count)} color="var(--txt-ghost)" />
                <Stat label="Violations" value={String(dept.violations)} color={dept.violations > 0 ? 'var(--red-strong)' : 'var(--green)'} />
              </div>
              {/* Sign chain status badges */}
              <div style={{ display: 'flex', gap: 4, marginTop: 'var(--space-2)', flexWrap: 'wrap' }}>
                {dept.status === 'hod_signed' && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--green-strong)', background: 'var(--green-bg)', border: '1px solid var(--green-border)', borderRadius: 3, padding: '1px 5px' }}>
                    HOD Signed ✓
                  </span>
                )}
                {dept.status === 'finalized' && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--green-strong)', background: 'var(--green-bg)', border: '1px solid var(--green-border)', borderRadius: 3, padding: '1px 5px' }}>
                    Finalized ✓
                  </span>
                )}
                {dept.correction_requested && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--compliance-warn)', background: 'var(--amber-bg)', border: '1px solid var(--amber-border)', borderRadius: 3, padding: '1px 5px' }}>
                    Correction Requested
                  </span>
                )}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', marginTop: 6, textAlign: 'center' }}>
                {isExpanded ? '▲ collapse' : '▼ show crew'}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Sign All Departments popup (L2) ── */}
      {signAllPopupOpen && (() => {
        const signable = data.departments.filter(d => d.status === 'hod_signed' && d.signoff_id);
        const skipped  = data.departments.filter(d => d.status !== 'hod_signed' && d.status !== 'finalized');
        return (
          <ActionPopup
            mode="mutate"
            title="Sign All Departments"
            subtitle="MLC 2006 Reg. 2.3 — Master's Attestation"
            signatureLevel={2}
            submitLabel={signingAll ? 'Signing…' : 'Sign All'}
            submitDisabled={signingAll}
            fields={[
              { name: 'vessel',    label: 'Vessel',            type: 'kv-read', value: data.vessel_name },
              { name: 'week',      label: 'Week',              type: 'kv-read', value: formatWeekLabel(data.week_start) },
              { name: 'signing',   label: 'Departments Signing', type: 'kv-read', value: signable.map(d => d.name).join(', ') },
              ...(skipped.length > 0 ? [{
                name: 'skipped',
                label: 'Skipped (HOD pending)',
                type: 'kv-read' as const,
                value: skipped.map(d => d.name).join(', '),
              }] : []),
              { name: 'regulation', label: 'Regulation', type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            previewRows={[
              { key: 'Vessel Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%` },
              { key: 'Total Violations',  value: String(va.total_violations) },
              { key: 'Total Crew',        value: String(va.total_crew) },
            ]}
            onClose={() => setSignAllPopupOpen(false)}
            onSubmit={(values) => {
              setSignAllPopupOpen(false);
              signAllDepartments(String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Captain final-sign popup (L2) ── */}
      {signingPopupId && (() => {
        const ps = data.pending_final_signs.find(p => p.signoff_id === signingPopupId);
        if (!ps) return null;
        return (
          <ActionPopup
            mode="mutate"
            title="Final Sign — Vessel Hours of Rest"
            subtitle="MLC 2006 Reg. 2.3 — Master's Attestation"
            signatureLevel={2}
            submitLabel="Final Sign"
            fields={[
              { name: 'department',  label: 'Department',   type: 'kv-read', value: ps.department },
              { name: 'week',        label: 'Week',         type: 'kv-read', value: ps.week_label },
              { name: 'hod_signed',  label: 'HOD Signed By', type: 'kv-read', value: ps.hod_name },
              { name: 'vessel',      label: 'Vessel',       type: 'kv-read', value: data.vessel_name },
              { name: 'regulation',  label: 'Regulation',   type: 'kv-read', value: 'MLC 2006 Regulation 2.3 — Rest Hours' },
            ]}
            previewRows={[
              { key: 'Vessel Compliance', value: `${va.overall_compliance_pct.toFixed(1)}%` },
              { key: 'Total Violations',  value: String(va.total_violations) },
              { key: 'Total Crew',        value: String(va.total_crew) },
            ]}
            onClose={() => setSigningPopupId(null)}
            onSubmit={(values) => {
              setSigningPopupId(null);
              finalSign(ps.signoff_id, String(values.signature_name ?? ''));
            }}
          />
        );
      })()}

      {/* ── Expanded crew grid (shown below cards when a dept is expanded) ── */}
      {expandedDept && (() => {
        const dept = data.departments.find(d => d.name === expandedDept);
        if (!dept) return null;
        return (
          <div style={cardStyle}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-3)' }}>
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
                    <th style={thStyle({ width: 60, textAlign: 'center' })}>HOD</th>
                  </tr>
                </thead>
                <tbody>
                  {dept.crew.map(member => {
                    const submitted = member.days.filter(d => d.rest_hours !== null);
                    const avg = submitted.length
                      ? (submitted.reduce((s, d) => s + (d.rest_hours ?? 0), 0) / submitted.length).toFixed(1)
                      : '—';
                    // HOD-signed if the department is hod_signed/finalized (sign is per-dept in this system)
                    const hodSignedForDept = dept.status === 'hod_signed' || dept.status === 'finalized';
                    const hasSubmitted = submitted.length > 0;
                    return (
                      <tr key={member.user_id} style={{ borderTop: '1px solid var(--border-faint)' }}>
                        <td style={{ padding: '8px 0', paddingRight: 'var(--space-3)' }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt)' }}>{member.name}</div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)', marginTop: 1 }}>{member.role}</div>
                        </td>
                        {member.days.map(day => (
                          <td key={day.date} style={{ padding: '8px 4px', textAlign: 'center' }}>
                            {day.rest_hours !== null ? (
                              <div style={{
                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                width: 36, height: 28, borderRadius: 'var(--radius-pill)',
                                background: `color-mix(in srgb, ${restHoursColor(day.rest_hours)} 15%, transparent)`,
                                border: `1px solid color-mix(in srgb, ${restHoursColor(day.rest_hours)} 35%, transparent)`,
                              }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: restHoursColor(day.rest_hours) }}>
                                  {day.rest_hours.toFixed(1)}
                                </span>
                              </div>
                            ) : (
                              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 28 }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>—</span>
                              </div>
                            )}
                          </td>
                        ))}
                        <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--txt2)' }}>{avg}</span>
                        </td>
                        <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                          {!hasSubmitted ? (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--txt-ghost)' }}>—</span>
                          ) : hodSignedForDept ? (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green-strong)' }}>✓</span>
                          ) : (
                            <span style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: 8,
                              color: 'var(--amber)',
                              background: 'var(--amber-bg)',
                              border: '1px solid var(--amber-border)',
                              borderRadius: 3,
                              padding: '1px 4px',
                            }}>Pending</span>
                          )}
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
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--txt-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color }}>{value}</span>
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
