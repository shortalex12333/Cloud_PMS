'use client';

/**
 * Hours of Rest — role-aware operational dashboard
 *
 * crew:                      My Time
 * HOD (chief_engineer,
 *      chief_officer, eto):  My Time | Department
 * captain:                   My Time | Department | All Departments
 * manager (fleet):           My Time | All Departments | Fleet
 *
 * MLC 2006 rule enforced by backend:
 *   HOD/captain cannot counter-sign until own week is submitted.
 *
 * No DomainListView. No EntityLensPage. Inline time input only.
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { MyTimeView } from '@/components/hours-of-rest/MyTimeView';
import { DepartmentView } from '@/components/hours-of-rest/DepartmentView';
import { VesselComplianceView } from '@/components/hours-of-rest/VesselComplianceView';
import { FleetView } from '@/components/hours-of-rest/FleetView';

type Tab = 'my-time' | 'department' | 'vessel' | 'fleet';

// ── Role helpers (local to HoR — do NOT use AuthContext.isHOD which is too broad) ──

function isHODRole(role: string | undefined): boolean {
  // HODs: head of a department. Responsible for counter-signing crew in their dept.
  // chief_officer = HOD of deck; chief_engineer = HOD of engine; eto = HOD of electrical.
  return ['chief_engineer', 'chief_officer', 'eto'].includes(role ?? '');
}

function isCaptainRole(role: string | undefined): boolean {
  return role === 'captain';
}

function isFleetManagerRole(role: string | undefined): boolean {
  return role === 'manager';
}

function roleLabel(role: string | undefined): string {
  if (!role) return '';
  const labels: Record<string, string> = {
    chief_engineer: 'Chief Engineer',
    chief_officer: 'Chief Officer',
    eto: 'ETO',
    captain: 'Captain',
    manager: 'Fleet Manager',
  };
  return labels[role] ?? role.replace(/_/g, ' ');
}

// ── Component ──────────────────────────────────────────────────────────────────

function useHoRUnreadCount(token: string | undefined): number {
  const [count, setCount] = React.useState(0);
  React.useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch('/api/v1/hours-of-rest/notifications/unread', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const json = await res.json();
        const data = json.success ? json.data : (json.data ?? json);
        if (!cancelled) setCount(data?.unread_count ?? 0);
      } catch { /* silent — badge is non-critical */ }
    }
    load();
    const iv = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [token]);
  return count;
}

function HoursOfRestContent() {
  const { user, session } = useAuth();
  const role = user?.role;

  const showDept    = isHODRole(role) || isCaptainRole(role);
  const showVessel  = isCaptainRole(role) || isFleetManagerRole(role);
  const showFleet   = isFleetManagerRole(role);

  const [tab, setTab] = React.useState<Tab>('my-time');
  const unreadCount = useHoRUnreadCount(showDept ? session?.access_token : undefined);

  // Clamp active tab to what this role permits (no useEffect, no loop).
  const activeTab: Tab =
    (tab === 'fleet'      && !showFleet)   ? 'my-time' :
    (tab === 'vessel'     && !showVessel)  ? 'my-time' :
    (tab === 'department' && !showDept)    ? 'my-time' :
    tab;

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: 'my-time',    label: 'My Time' },
    ...(showDept   ? [{ id: 'department' as Tab, label: 'Department', badge: unreadCount > 0 ? unreadCount : undefined }] : []),
    ...(showVessel ? [{ id: 'vessel'     as Tab, label: 'All Departments' }] : []),
    ...(showFleet  ? [{ id: 'fleet'      as Tab, label: 'Fleet' }] : []),
  ];

  return (
    <div style={{
      flex: 1,
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--surface-base, #0e0c09)',
      overflow: 'hidden',
    }}>

      {/* ── Domain header ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.7)',
            textTransform: 'uppercase',
            letterSpacing: '0.10em',
          }}>Hours of Rest</span>
          {role && (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              color: 'rgba(255,255,255,0.25)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>{roleLabel(role)}</span>
          )}
        </div>

        {tabs.length > 1 && (
          <div style={{
            display: 'flex',
            gap: 2,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6,
            padding: 2,
          }}>
            {tabs.map(t => (
              <button
                key={t.id}
                data-testid={`hor-tab-${t.id}`}
                onClick={() => setTab(t.id)}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: activeTab === t.id ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.35)',
                  background: activeTab === t.id ? 'rgba(255,255,255,0.10)' : 'transparent',
                  border: 'none',
                  borderRadius: 4,
                  padding: '5px 12px',
                  cursor: 'pointer',
                  transition: 'background 0.15s, color 0.15s',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  whiteSpace: 'nowrap',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                {t.label}
                {t.badge !== undefined && (
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: 14,
                    height: 14,
                    borderRadius: 7,
                    background: 'rgba(239,68,68,0.9)',
                    color: '#fff',
                    fontSize: 8,
                    fontWeight: 700,
                    padding: '0 3px',
                    letterSpacing: 0,
                  }}>
                    {t.badge > 9 ? '9+' : t.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Tab content ── */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '20px' }}>
        {activeTab === 'my-time'    && <MyTimeView />}
        {activeTab === 'department' && showDept   && <DepartmentView />}
        {activeTab === 'vessel'     && showVessel && <VesselComplianceView />}
        {activeTab === 'fleet'      && showFleet  && <FleetView />}
      </div>

    </div>
  );
}

export default function HoursOfRestPage() {
  return (
    <React.Suspense
      fallback={
        <div style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--surface-base, #0e0c09)',
        }}>
          <div style={{
            width: 28,
            height: 28,
            border: '2px solid rgba(255,255,255,0.08)',
            borderTopColor: 'var(--mark, rgba(90,171,204,0.8))',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
        </div>
      }
    >
      <HoursOfRestContent />
    </React.Suspense>
  );
}
