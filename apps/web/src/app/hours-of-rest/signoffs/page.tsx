'use client';

/**
 * Monthly Sign-Offs List Page — /hours-of-rest/signoffs
 *
 * MLC 2006 Standard A2.3 requires monthly sign-off of hours of rest records
 * by three parties in sequence: Crew → HOD → Captain (Master).
 *
 * This page is ONE page that adapts its data scope based on logged-in role:
 *   - Captain (role='captain'):       sees ALL departments — no department filter sent to API
 *   - HOD (role='chief_engineer' etc): sees their department only — department filter from DEPARTMENT_MAP
 *   - Crew (any other role):          sees only their own records — API filters by user_id in JWT
 *
 * Route structure:
 *   /hours-of-rest           → existing daily records list (crew-facing)
 *   /hours-of-rest/signoffs  → THIS page (monthly sign-off management)
 *   /hours-of-rest/signoffs/[id] → direct-link to a single sign-off detail
 *
 * Data flow:
 *   1. fetchSignoffs() → GET /v1/hours-of-rest/signoffs?yacht_id=&department=&status=
 *   2. Response: { signoffs: [...], pending_count: N }
 *   3. Client-side grouping by department + client-side filter tabs
 *   4. Clicking a row → ?id=xxx query param → EntityDetailOverlay opens with HoRSignoffContent lens
 *
 * Prototype: public/prototypes/hor-signoffs.html
 *
 * KNOWN ISSUE for tester:
 *   - The API returns user_id (UUID) per signoff. Display names depend on the API
 *     joining user data via `user:user_id(name, email)`. If the list shows truncated
 *     UUIDs instead of names, the list endpoint needs a join added (the detail endpoint
 *     already has it — see get_monthly_signoff in hours_of_rest_handlers.py:458).
 *   - The detail overlay relies on the generic entity resolver handling
 *     entityType='hours_of_rest_signoff'. If it 404s, a handler mapping is needed
 *     in the backend entity router.
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { HoRSignoffContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

// --- Types ---

interface MonthlySignoff {
  id: string;
  user_id: string;
  department: string;
  month: string;
  status: string;
  crew_signature: Record<string, unknown> | null;
  crew_signed_at: string | null;
  hod_signature: Record<string, unknown> | null;
  hod_signed_at: string | null;
  master_signature: Record<string, unknown> | null;
  master_signed_at: string | null;
  total_rest_hours: number | null;
  total_work_hours: number | null;
  violation_count: number | null;
  created_at: string;
  updated_at: string;
  // Joined user info (if available)
  user?: { name?: string; email?: string };
}

type FilterStatus = 'all' | 'pending' | 'awaiting_hod' | 'finalized';

// --- Role helpers ---
// Department derivation mirrors the DB trigger in
// database/migrations/14_add_department_to_auth_users_roles.sql (lines 39-50).
// If new roles are added to the DB trigger, update this map too.
// 'captain' maps to 'all' here (meaning: don't send department filter → see everything).

const DEPARTMENT_MAP: Record<string, string> = {
  captain: 'all',
  chief_engineer: 'engineering',
  eto: 'engineering',
  manager: 'interior',
};

function getUserDepartment(role: string): string | null {
  return DEPARTMENT_MAP[role] ?? null;
}

function isCaptain(role: string): boolean {
  return role === 'captain';
}

// --- API ---

async function fetchSignoffs(
  yachtId: string,
  token: string,
  params: { department?: string; status?: string; month?: string }
): Promise<{ signoffs: MonthlySignoff[]; pending_count: number }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const qs = new URLSearchParams({ yacht_id: yachtId });
  if (params.department) qs.set('department', params.department);
  if (params.status) qs.set('status', params.status);
  const response = await fetch(`${baseUrl}/v1/hours-of-rest/signoffs?${qs.toString()}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error(`Failed to fetch signoffs: ${response.status}`);
  const data = await response.json();
  const result = data.data ?? data;
  return {
    signoffs: result.signoffs ?? [],
    pending_count: result.pending_count ?? 0,
  };
}

// --- Status helpers ---

function getStatusLabel(status: string): string {
  switch (status) {
    case 'draft': return 'Not Submitted';
    case 'crew_signed': return 'Awaiting HOD';
    case 'hod_signed': return 'Awaiting Master';
    case 'finalized': return 'Complete';
    default: return status.replace(/_/g, ' ');
  }
}

function getStatusPillClass(status: string): string {
  switch (status) {
    case 'finalized': return 'pill-green';
    case 'crew_signed':
    case 'hod_signed': return 'pill-amber';
    default: return 'pill-neutral';
  }
}

function getWorkflowLabel(status: string): string {
  switch (status) {
    case 'draft': return 'Draft';
    case 'crew_signed': return 'Crew Signed';
    case 'hod_signed': return 'HOD Signed';
    case 'finalized': return 'Finalized';
    default: return status;
  }
}

function matchesFilter(signoff: MonthlySignoff, filter: FilterStatus): boolean {
  if (filter === 'all') return true;
  if (filter === 'pending') return ['draft', 'crew_signed', 'hod_signed'].includes(signoff.status);
  if (filter === 'awaiting_hod') return signoff.status === 'crew_signed';
  if (filter === 'finalized') return signoff.status === 'finalized';
  return true;
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getCurrentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function formatMonth(month: string): string {
  const [year, m] = month.split('-');
  const date = new Date(Number(year), Number(m) - 1);
  return date.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

// --- Components ---

function SignoffRow({
  signoff,
  isSelected,
  onClick,
}: {
  signoff: MonthlySignoff;
  isSelected: boolean;
  onClick: () => void;
}) {
  const displayName = signoff.user?.name ?? signoff.user?.email ?? signoff.user_id.slice(0, 8);
  const initials = getInitials(displayName);

  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 12px',
        borderRadius: 6,
        cursor: 'pointer',
        minHeight: 44,
        width: '100%',
        textAlign: 'left',
        border: 'none',
        fontFamily: 'var(--font-sans)',
        transition: 'background 80ms',
        background: isSelected ? 'var(--mark-hover)' : 'transparent',
      }}
      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--surface-hover)'; }}
      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
    >
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        background: 'var(--surface-el)', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 600, color: 'var(--txt3)', flexShrink: 0,
      }}>
        {initials}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)' }}>{displayName}</div>
        <div style={{ fontSize: 11, color: 'var(--txt3)', marginTop: 1 }}>
          {signoff.department}
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--txt2)', whiteSpace: 'nowrap', marginRight: 8 }}>
        {getWorkflowLabel(signoff.status)}
      </div>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
        whiteSpace: 'nowrap',
        ...(signoff.status === 'finalized'
          ? { background: 'rgba(74,148,104,0.12)', color: 'var(--green)' }
          : signoff.status === 'crew_signed' || signoff.status === 'hod_signed'
            ? { background: 'rgba(196,137,59,0.12)', color: 'var(--amber)' }
            : { background: 'var(--surface-hover)', color: 'var(--txt3)' }),
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: signoff.status === 'finalized' ? 'var(--green)'
            : signoff.status === 'crew_signed' || signoff.status === 'hod_signed' ? 'var(--amber)'
              : 'var(--txt-ghost)',
        }} />
        {getStatusLabel(signoff.status)}
      </span>
    </button>
  );
}

function FilterTabs({
  active,
  counts,
  onChange,
}: {
  active: FilterStatus;
  counts: Record<FilterStatus, number>;
  onChange: (f: FilterStatus) => void;
}) {
  const tabs: { key: FilterStatus; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'pending', label: 'Pending' },
    { key: 'awaiting_hod', label: 'Awaiting HOD' },
    { key: 'finalized', label: 'Finalized' },
  ];

  return (
    <div style={{
      display: 'flex', gap: 2, marginBottom: 24,
      background: 'var(--surface-el)', borderRadius: 8, padding: 3,
    }}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          style={{
            padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
            cursor: 'pointer', border: 'none',
            fontFamily: 'var(--font-sans)', transition: 'all 120ms',
            color: active === t.key ? 'var(--txt)' : 'var(--txt3)',
            background: active === t.key ? 'var(--surface)' : 'transparent',
            boxShadow: active === t.key ? '0 1px 3px rgba(0,0,0,0.2)' : 'none',
          }}
        >
          {t.label}
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, marginLeft: 4,
            padding: '1px 5px', borderRadius: 3,
            background: active === t.key ? 'var(--teal-bg)' : 'var(--surface-hover)',
            color: active === t.key ? 'var(--mark)' : 'inherit',
          }}>
            {counts[t.key]}
          </span>
        </button>
      ))}
    </div>
  );
}

// Lens wrapper
function LensContent() {
  return <div className={lensStyles.root}><HoRSignoffContent /></div>;
}

// --- Main ---

function SignoffsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;
  const selectedId = searchParams.get('id');

  const [filter, setFilter] = React.useState<FilterStatus>('all');

  // Determine scope based on role
  const role = user?.role ?? 'crew';
  const departmentScope = isCaptain(role) ? undefined : getUserDepartment(role) ?? undefined;

  // Fetch signoffs
  const { data, isLoading, error } = useQuery({
    queryKey: ['hor-signoffs', user?.yachtId, departmentScope],
    queryFn: () => fetchSignoffs(user?.yachtId || '', token || '', {
      department: departmentScope,
      month: getCurrentMonth(),
    }),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  const signoffs = React.useMemo(() => data?.signoffs ?? [], [data?.signoffs]);
  const pendingCount = data?.pending_count ?? 0;

  // Group by department
  const grouped = React.useMemo(() => {
    const filtered = signoffs.filter((s) => matchesFilter(s, filter));
    const groups: Record<string, MonthlySignoff[]> = {};
    for (const s of filtered) {
      const dept = s.department || 'general';
      if (!groups[dept]) groups[dept] = [];
      groups[dept].push(s);
    }
    return groups;
  }, [signoffs, filter]);

  // Filter counts
  const counts = React.useMemo(() => ({
    all: signoffs.length,
    pending: signoffs.filter((s) => ['draft', 'crew_signed', 'hod_signed'].includes(s.status)).length,
    awaiting_hod: signoffs.filter((s) => s.status === 'crew_signed').length,
    finalized: signoffs.filter((s) => s.status === 'finalized').length,
  }), [signoffs]);

  const handleSelect = React.useCallback((id: string) => {
    router.push(`/hours-of-rest/signoffs?id=${id}`, { scroll: false });
  }, [router]);

  const handleCloseDetail = React.useCallback(() => {
    router.push('/hours-of-rest/signoffs', { scroll: false });
  }, [router]);

  const departmentOrder = ['deck', 'engineering', 'interior', 'general'];

  return (
    <div style={{ minHeight: '100vh', background: 'var(--surface-base)', color: 'var(--txt)', fontFamily: 'var(--font-sans)' }}>
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px 64px' }}>
        {/* Back link */}
        <a
          href="/hours-of-rest"
          onClick={(e) => { e.preventDefault(); router.push('/hours-of-rest'); }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            fontSize: 12, color: 'var(--mark)', textDecoration: 'none',
            marginBottom: 16, padding: '4px 0',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M10 12L6 8l4-4" /></svg>
          Hours of Rest — Daily Records
        </a>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, flex: 1, margin: 0 }}>Monthly Sign-Offs</h1>
          {pendingCount > 0 && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
              padding: '2px 8px', borderRadius: 4,
              background: 'rgba(196,137,59,0.12)', color: 'var(--amber)',
            }}>
              {pendingCount} awaiting
            </span>
          )}
        </div>

        {/* Filter tabs */}
        <FilterTabs active={filter} counts={counts} onChange={setFilter} />

        {/* Loading */}
        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
            <div style={{ width: 32, height: 32, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ textAlign: 'center', padding: 32, color: 'var(--red)' }}>
            Failed to load sign-offs
          </div>
        )}

        {/* Empty */}
        {!isLoading && !error && signoffs.length === 0 && (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--txt3)' }}>
            <div style={{
              width: 48, height: 48, borderRadius: '50%',
              background: 'var(--surface-el)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--txt-ghost)' }}>
                <path d="M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
              </svg>
            </div>
            <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--txt2)', marginBottom: 4 }}>No sign-offs for this month</p>
            <p style={{ fontSize: 12 }}>Crew must create and sign their monthly hours of rest records first.</p>
          </div>
        )}

        {/* Department-grouped list */}
        {!isLoading && !error && departmentOrder
          .filter((dept) => grouped[dept] && grouped[dept].length > 0)
          .map((dept) => (
            <div key={dept} style={{ marginBottom: 20 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 0', marginBottom: 2,
                fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                letterSpacing: '0.04em', color: 'var(--txt3)',
              }}>
                {dept === 'general' ? 'General' : dept.charAt(0).toUpperCase() + dept.slice(1)}
                <span style={{ flex: 1, height: 1, background: 'var(--border-faint)' }} />
              </div>
              {grouped[dept]!.map((s) => (
                <SignoffRow
                  key={s.id}
                  signoff={s}
                  isSelected={s.id === selectedId}
                  onClick={() => handleSelect(s.id)}
                />
              ))}
            </div>
          ))}

        {/* Remaining departments not in order */}
        {!isLoading && !error && Object.keys(grouped)
          .filter((dept) => !departmentOrder.includes(dept))
          .map((dept) => (
            <div key={dept} style={{ marginBottom: 20 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 0', marginBottom: 2,
                fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                letterSpacing: '0.04em', color: 'var(--txt3)',
              }}>
                {dept.charAt(0).toUpperCase() + dept.slice(1)}
                <span style={{ flex: 1, height: 1, background: 'var(--border-faint)' }} />
              </div>
              {grouped[dept]!.map((s) => (
                <SignoffRow
                  key={s.id}
                  signoff={s}
                  isSelected={s.id === selectedId}
                  onClick={() => handleSelect(s.id)}
                />
              ))}
            </div>
          ))}
      </div>

      {/* Detail overlay */}
      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage
            entityType="hours_of_rest_signoff"
            entityId={selectedId}
            content={LensContent}
          />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function SignoffsPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--surface-base)' }}>
          <div style={{ width: 32, height: 32, border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      }
    >
      <SignoffsPageContent />
    </React.Suspense>
  );
}
