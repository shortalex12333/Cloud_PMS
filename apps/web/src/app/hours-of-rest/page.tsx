'use client';

/**
 * Hours of Rest — role-aware operational dashboard
 *
 * Crew (all roles):             My Time tab only
 * HOD (chief_engineer, eto):    My Time | Department View
 * Captain / Manager:            My Time | All Departments
 *
 * No DomainListView. No EntityLensPage. Inline time input only.
 */

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { MyTimeView } from '@/components/hours-of-rest/MyTimeView';
import { DepartmentView } from '@/components/hours-of-rest/DepartmentView';
import { VesselComplianceView } from '@/components/hours-of-rest/VesselComplianceView';

type Tab = 'my-time' | 'department' | 'vessel';

function isCaptainOrManager(role: string | undefined): boolean {
  return role === 'captain' || role === 'manager';
}

function isHODOnly(role: string | undefined): boolean {
  return role === 'chief_engineer' || role === 'eto';
}

function HoursOfRestContent() {
  const { user } = useAuth();
  const role = user?.role;

  const showDept = isHOD(user);
  const showVessel = isCaptainOrManager(role);

  const [tab, setTab] = React.useState<Tab>('my-time');

  // Constrain the active tab to what the current role permits.
  // Computed inline — no useEffect, no setTab call, no re-render loop.
  const activeTab: Tab =
    (tab === 'vessel' && !showVessel) ? 'my-time' :
    (tab === 'department' && !showDept) ? 'my-time' :
    tab;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'my-time', label: 'My Time' },
    ...(isHODOnly(role) ? [{ id: 'department' as Tab, label: 'Department' }] : []),
    ...(showVessel ? [{ id: 'department' as Tab, label: 'Department' }, { id: 'vessel' as Tab, label: 'All Departments' }] : []),
  ];

  const dedupedTabs = tabs.filter((t, i, arr) => arr.findIndex(x => x.id === t.id) === i);

  return (
    <div style={{
      height: '100%',
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
          {user?.role && (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              color: 'rgba(255,255,255,0.25)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>{user.role.replace(/_/g, ' ')}</span>
          )}
        </div>

        {dedupedTabs.length > 1 && (
          <div style={{
            display: 'flex',
            gap: 2,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6,
            padding: 2,
          }}>
            {dedupedTabs.map(t => (
              <button
                key={t.id}
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
                }}
              >{t.label}</button>
            ))}
          </div>
        )}
      </div>

      {/* ── Tab content ── */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '20px',
      }}>
        {activeTab === 'my-time' && <MyTimeView />}
        {activeTab === 'department' && showDept && <DepartmentView />}
        {activeTab === 'vessel' && showVessel && <VesselComplianceView />}
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
