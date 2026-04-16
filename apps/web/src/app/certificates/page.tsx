'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { CertificateContent } from '@/components/lens-v2/entity';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';
import { mapActionFields } from '@/components/lens-v2/mapActionFields';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { useAuth } from '@/hooks/useAuth';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

interface Certificate {
  id: string;
  certificate_name?: string;
  certificate_number?: string;
  certificate_type?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date?: string;
  status?: string;
  domain?: 'vessel' | 'crew';
  person_name?: string;
  created_at: string;
  updated_at?: string;
}

/**
 * Available create action from /v1/actions/list.
 * Everything — label, fields, role gating — comes from the backend registry.
 * Do NOT hardcode any of this here.
 */
interface RegistryAction {
  action_id: string;
  label: string;
  variant: string;
  required_fields: string[];
  optional_fields?: string[];
  field_schema?: Array<{
    name: string;
    type: string;
    label: string;
    required: boolean;
    options?: Array<{ value: string; label: string }>;
  }>;
}

function certAdapter(c: Certificate): EntityListResult {
  const status = c.status?.replace(/_/g, ' ') || 'Valid';
  const daysLeft = c.expiry_date ? Math.ceil((new Date(c.expiry_date).getTime() - Date.now()) / 86_400_000) : null;
  const title = c.domain === 'crew'
    ? (c.person_name ? `${c.person_name} — ${c.certificate_type || 'Certificate'}` : c.certificate_type || 'Certificate')
    : (c.certificate_name || c.certificate_number || 'Certificate');
  return {
    id: c.id,
    type: c.domain === 'crew' ? 'pms_crew_certificates' : 'pms_vessel_certificates',
    title,
    subtitle: `${c.certificate_type || ''} · ${c.issuing_authority || ''}`.replace(/^ · |· $/g, ''),
    entityRef: c.certificate_number || (c.domain === 'crew' ? 'Crew' : 'Vessel'),
    status,
    statusVariant: c.status === 'expired' ? 'critical' : c.status === 'revoked' ? 'critical' : c.status === 'suspended' ? 'warning' : c.status === 'expiring_soon' ? 'warning' : c.status === 'superseded' ? 'neutral' : c.status === 'valid' ? 'success' : 'open',
    severity: c.status === 'expired' ? 'critical' : c.status === 'revoked' ? 'critical' : c.status === 'suspended' ? 'warning' : c.status === 'expiring_soon' ? 'warning' : null,
    age: daysLeft !== null ? (daysLeft < 0 ? `${Math.abs(daysLeft)}d overdue` : `${daysLeft}d`) : '\u2014',
  };
}

/**
 * Add-Certificate button — fetches create actions from the registry,
 * opens ActionPopup with fields from field_schema, submits via action router.
 *
 * Zero hardcoding:
 * - Role gating: backend omits actions the user cannot call
 * - Field list: mapActionFields reads field_schema from registry
 * - Labels, options, types: from field_schema (backend is source of truth)
 * - yacht_id: from auth context (never in payload)
 */
function CreateCertificateButton({ onCreated }: { onCreated: () => void }) {
  const { user, session } = useAuth();
  const [actions, setActions] = React.useState<RegistryAction[]>([]);
  const [menuOpen, setMenuOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<RegistryAction | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch create actions for the certificates domain.
  // Backend filters by user role — actions the user cannot call are omitted.
  React.useEffect(() => {
    if (!session?.access_token) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/v1/actions/list?domain=certificates`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        const creates: RegistryAction[] = (data.actions || []).filter(
          (a: RegistryAction) => a.action_id === 'create_vessel_certificate' || a.action_id === 'create_crew_certificate'
        );
        if (!cancelled) setActions(creates);
      } catch {
        // Silent — if the fetch fails, button just doesn't render
      }
    })();
    return () => { cancelled = true; };
  }, [session?.access_token]);

  // Not rendered if the user has no create permissions (backend omitted the actions)
  if (actions.length === 0 || !user?.yachtId) return null;

  const openAction = (action: RegistryAction) => {
    setSelected(action);
    setMenuOpen(false);
    setError(null);
  };

  const handleButtonClick = () => {
    if (actions.length === 1) {
      openAction(actions[0]);
    } else {
      setMenuOpen(!menuOpen);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!selected || !session?.access_token || !user.yachtId) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({
          action: selected.action_id,
          context: { yacht_id: user.yachtId },
          payload: values,
        }),
      });
      const result = await res.json();
      if (!res.ok || result.status === 'error' || result.success === false) {
        setError(result.message ?? result.error ?? result.detail?.message ?? 'Failed to create certificate');
        return;
      }
      setSelected(null);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setSubmitting(false);
    }
  };

  // Build ActionPopup fields from the backend field_schema — no hardcoding
  const popupFields = selected
    ? mapActionFields({
        action_id: selected.action_id,
        label: selected.label,
        required_fields: selected.required_fields || [],
        optional_fields: selected.optional_fields || [],
        prefill: {},
        requires_signature: false,
        field_schema: selected.field_schema,
      })
    : [];

  return (
    <>
      <div className="relative">
        <PrimaryButton onClick={handleButtonClick}>
          New Certificate
        </PrimaryButton>
        {menuOpen && actions.length > 1 && (
          <>
            {/* Click-outside backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setMenuOpen(false)}
            />
            <div
              className="absolute right-0 mt-2 z-50 min-w-56 rounded-md overflow-hidden"
              style={{
                background: 'var(--surface-el)',
                borderTop: '1px solid var(--border-top)',
                borderRight: '1px solid var(--border-side)',
                borderBottom: '1px solid var(--border-bottom)',
                borderLeft: '1px solid var(--border-side)',
                boxShadow: 'var(--shadow-drop)',
              }}
            >
              {actions.map((a) => (
                <button
                  key={a.action_id}
                  onClick={() => openAction(a)}
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '10px 14px',
                    textAlign: 'left',
                    fontSize: 12,
                    fontWeight: 400,
                    color: 'var(--txt)',
                    background: 'transparent',
                    border: 'none',
                    borderLeft: '2px solid transparent',
                    cursor: 'pointer',
                    transition: 'background 80ms, border-color 80ms',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--teal-bg)';
                    e.currentTarget.style.borderLeftColor = 'var(--mark)';
                    e.currentTarget.style.color = 'var(--mark)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderLeftColor = 'transparent';
                    e.currentTarget.style.color = 'var(--txt)';
                  }}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {selected && (
        <ActionPopup
          mode="mutate"
          title={selected.label}
          fields={popupFields}
          signatureLevel={0}
          submitLabel={submitting ? 'Creating…' : 'Create'}
          submitDisabled={submitting}
          onSubmit={handleSubmit}
          onClose={() => { if (!submitting) { setSelected(null); setError(null); } }}
        />
      )}

      {error && (
        <div
          role="alert"
          className="fixed bottom-6 right-6 z-50 rounded-md border border-err bg-surface-raised px-4 py-3 text-sm text-err shadow-lg"
        >
          {error}
        </div>
      )}
    </>
  );
}

function LensContent() {
  return <div className={lensStyles.root}><CertificateContent /></div>;
}

function CertificatesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/certificates?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/certificates${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  const handleCreated = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['certificates'] });
  }, [queryClient]);

  return (
    <div className="h-full bg-surface-base flex flex-col">
      <div className="flex items-center justify-between px-5 pt-3 flex-shrink-0">
        <div />
        <CreateCertificateButton onCreated={handleCreated} />
      </div>

      <div className="flex-1 min-h-0">
        <FilteredEntityList<Certificate>
          domain="certificates"
          queryKey={['certificates']}
          table="v_certificates_enriched"
          columns="id,certificate_name,certificate_number,certificate_type,issuing_authority,issue_date,expiry_date,status,domain,person_name,created_at"
          adapter={certAdapter}
          filterConfig={[
            {
              key: 'domain',
              label: 'Type',
              type: 'select' as const,
              options: [
                { label: 'All', value: '' },
                { label: 'Vessel', value: 'vessel' },
                { label: 'Crew', value: 'crew' },
              ],
            },
            {
              key: 'status',
              label: 'Status',
              type: 'select' as const,
              options: [
                { label: 'All', value: '' },
                { label: 'Valid', value: 'valid' },
                { label: 'Expired', value: 'expired' },
                { label: 'Revoked', value: 'revoked' },
                { label: 'Superseded', value: 'superseded' },
                { label: 'Suspended', value: 'suspended' },
              ],
            },
          ]}
          selectedId={selectedId}
          onSelect={handleSelect}
          emptyMessage="No certificates recorded"
          sortBy="expiry_date"
        />
      </div>

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="certificate" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function CertificatesPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div className="w-8 h-8 border-2 border-border-sub border-t-mark rounded-full animate-spin" />
        </div>
      }
    >
      <CertificatesPageContent />
    </React.Suspense>
  );
}
