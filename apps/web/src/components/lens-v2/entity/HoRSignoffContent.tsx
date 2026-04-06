'use client';

/**
 * HoRSignoffContent — lens-v2 entity view for monthly HoR sign-offs.
 * Prototype: public/prototypes/hor-signoffs.html (detail panel)
 *
 * This is the detail panel that opens when you click a sign-off row on the
 * /hours-of-rest/signoffs list page (or via direct link at /hours-of-rest/signoffs/[id]).
 *
 * Regulatory context:
 *   MLC 2006 Standard A2.3 para 12 requires that monthly hours of rest records
 *   are signed by the seafarer AND counter-signed by the master (or authorized person).
 *   The signing workflow is: Crew signs → HOD counter-signs → Captain final-signs.
 *
 * Data flow:
 *   - Entity data from useEntityLensContext() → backend /v1/entity/hours_of_rest_signoff/{id}
 *   - The backend returns the pms_hor_monthly_signoffs row with joined user info
 *   - Actions from availableActions[] → POST /v1/actions/execute
 *   - The primary action is 'sign_monthly_signoff' — the CTA button auto-detects
 *     which signature_level to use based on the record's current status
 *
 * Sections (in display order):
 *   Identity Strip → Month Summary (KV) → Violations (KV, red) →
 *   Weekly Breakdown (KV, collapsed) → Signatures (custom, 3-row) →
 *   Crew Declaration (italic quote) → HOD/Master Notes → Notes → Audit Trail
 *
 * KNOWN ISSUES for tester:
 *   - Violations and weekly breakdown arrays may be empty if the backend
 *     get_monthly_signoff handler doesn't hydrate them (currently it returns
 *     the signoff row + is_month_complete, but no violation/weekly detail).
 *     These sections gracefully hide when empty — not a bug.
 *   - If the detail panel shows "Not Found", the generic entity resolver
 *     doesn't know about entityType='hours_of_rest_signoff'. Fix: add a
 *     mapping in the entity router backend.
 */

import * as React from 'react';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { mapActionFields, actionHasFields, getSignatureLevel } from '../mapActionFields';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

import {
  NotesSection,
  KVSection,
  AuditTrailSection,
  type NoteItem,
  type KVItem,
  type AuditEvent,
} from '../sections';

// --- Colour helpers ---

function statusToPillVariant(status: string): PillDef['variant'] {
  switch (status) {
    case 'finalized': return 'green';
    case 'crew_signed':
    case 'hod_signed': return 'amber';
    default: return 'neutral';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'draft': return 'Not Submitted';
    case 'crew_signed': return 'Awaiting HOD';
    case 'hod_signed': return 'Awaiting Master';
    case 'finalized': return 'Complete';
    default: return status.replace(/_/g, ' ');
  }
}

function formatMonth(month: string): string {
  if (!month) return '';
  const [year, m] = month.split('-');
  const date = new Date(Number(year), Number(m) - 1);
  return date.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

// --- Component ---

export function HoRSignoffContent() {
  const { entity, availableActions, executeAction, getAction } = useEntityLensContext();
  const { user } = useAuth();

  // -- Extract entity fields --
  // The entity shape varies depending on the source:
  // - From entity route: top-level fields (entity.month, entity.status, etc.)
  // - From search result click: nested under entity.payload
  // - From signoff list: nested under entity.signoff
  // The ?? chain ensures we find the data regardless of nesting.
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const signoff = (entity?.signoff ?? payload.signoff ?? entity) as Record<string, unknown> | null;
  const raw = signoff ?? entity ?? {};

  const crewName = ((raw as Record<string, unknown>).user as Record<string, unknown>)?.name as string
    ?? ((raw as Record<string, unknown>).user as Record<string, unknown>)?.email as string
    ?? (raw.crew_name as string)
    ?? (payload.crew_name as string)
    ?? 'Crew Member';
  const department = (raw.department ?? payload.department) as string | undefined;
  const month = (raw.month ?? payload.month) as string | undefined;
  const status = ((raw.status ?? payload.status) as string) ?? 'draft';
  const totalRestHours = (raw.total_rest_hours ?? payload.total_rest_hours) as number | undefined;
  const totalWorkHours = (raw.total_work_hours ?? payload.total_work_hours) as number | undefined;
  const violationCount = (raw.violation_count ?? payload.violation_count) as number | undefined;
  const isMonthComplete = (entity?.is_month_complete ?? payload.is_month_complete) as boolean | undefined;

  // Signatures
  const crewSignature = raw.crew_signature as Record<string, unknown> | null;
  const crewSignedAt = raw.crew_signed_at as string | null;
  const crewSignedBy = raw.crew_signed_by as string | null;
  const crewDeclaration = raw.crew_declaration as string | null;
  const hodSignature = raw.hod_signature as Record<string, unknown> | null;
  const hodSignedAt = raw.hod_signed_at as string | null;
  const hodNotes = raw.hod_notes as string | null;
  const masterSignature = raw.master_signature as Record<string, unknown> | null;
  const masterSignedAt = raw.master_signed_at as string | null;
  const masterNotes = raw.master_notes as string | null;

  // Violations and weekly data (if present in payload)
  const violations = ((raw.violations ?? payload.violations) as Array<Record<string, unknown>> | undefined) ?? [];
  const weeklyBreakdown = ((raw.weekly_breakdown ?? payload.weekly_breakdown) as Array<Record<string, unknown>> | undefined) ?? [];

  // Notes and audit trail
  const notes = ((raw.notes ?? payload.notes) as Array<Record<string, unknown>> | undefined) ?? [];
  const auditTrail = ((raw.audit_trail ?? payload.audit_trail ?? entity?.audit_trail) as Array<Record<string, unknown>> | undefined) ?? [];

  // -- Action gates --
  const signAction = getAction('sign_monthly_signoff');
  // BACKEND_AUTO moved to mapActionFields.ts

  const [actionPopupConfig, setActionPopupConfig] = React.useState<{
    actionId: string; title: string; fields: ActionPopupField[]; signatureLevel: 0|1|2|3|4|5;
  } | null>(null);

  function openActionPopup(action: { action_id: string; label: string; required_fields: string[]; prefill: Record<string, unknown>; requires_signature: boolean }) {
    const fields = mapActionFields(action as any);
    const sigLevel = (action as Record<string, unknown>).signature_level as number ?? (action.requires_signature ? 2 : 0);
    setActionPopupConfig({ actionId: action.action_id, title: action.label, fields, signatureLevel: sigLevel as 0|1|2|3|4|5 });
  }

  // -- CTA state machine --
  // MLC 2006 signing chain: crew → HOD → Captain (Master).
  // The button label and enabled state depend on BOTH the record's current
  // status AND the logged-in user's role. The matrix:
  //
  //   Status         | Crew       | HOD             | Captain
  //   draft          | ✅ Sign    | ✅ Sign         | ✅ Sign
  //   crew_signed    | ❌ (wrong) | ✅ Counter-Sign | ❌ (wrong role)
  //   hod_signed     | ❌ (wrong) | ❌ (wrong role) | ✅ Final Sign
  //   finalized      | ❌ done    | ❌ done         | ❌ done
  //
  // If the backend provides a sign_monthly_signoff action, its disabled
  // state overrides the frontend logic (lines 161-164 below).
  const role = user?.role ?? '';
  const isUserHOD = isHOD(user);
  const isUserCaptain = role === 'captain';

  let ctaLabel = 'Sign';
  let ctaDisabled = true;
  let ctaDisabledReason: string | undefined;

  if (status === 'draft') {
    ctaLabel = 'Sign as Crew';
    ctaDisabled = false;
  } else if (status === 'crew_signed' && isUserHOD) {
    ctaLabel = 'Counter-Sign as HOD';
    ctaDisabled = false;
  } else if (status === 'hod_signed' && isUserCaptain) {
    ctaLabel = 'Final Sign as Master';
    ctaDisabled = false;
  } else if (status === 'finalized') {
    ctaLabel = 'Finalized';
    ctaDisabled = true;
    ctaDisabledReason = 'This sign-off has been completed';
  } else if (status === 'crew_signed' && !isUserHOD) {
    ctaLabel = 'Counter-Sign as HOD';
    ctaDisabled = true;
    ctaDisabledReason = 'Only HOD or above can counter-sign';
  } else if (status === 'hod_signed' && !isUserCaptain) {
    ctaLabel = 'Final Sign as Master';
    ctaDisabled = true;
    ctaDisabledReason = 'Only the Captain can final-sign';
  }

  // If the backend provided a sign action, override disabled state
  if (signAction) {
    ctaDisabled = signAction.disabled;
    ctaDisabledReason = signAction.disabled_reason ?? ctaDisabledReason;
  }

  const handleSign = React.useCallback(() => {
    if (!signAction) return;
    // Auto-derive signature_level from current status so the backend
    // sign_monthly_signoff handler knows which tier to apply:
    //   draft       → crew tier   (seafarer self-certifies)
    //   crew_signed → hod tier    (department head counter-signs)
    //   hod_signed  → master tier (captain final-signs)
    let signatureLevel: string;
    if (status === 'draft') signatureLevel = 'crew';
    else if (status === 'crew_signed') signatureLevel = 'hod';
    else if (status === 'hod_signed') signatureLevel = 'master';
    else return;

    openActionPopup({
      ...signAction,
      prefill: { ...signAction.prefill, signature_level: signatureLevel },
    });
  }, [signAction, status]);

  // -- Build dropdown for non-primary actions --
  const primaryActionId = 'sign_monthly_signoff';
  const dropdownItems: DropdownItem[] = availableActions
    .filter((a) => a.action_id !== primaryActionId)
    .map((a) => ({
      label: a.label,
      onClick: () => {
        const hasFields = actionHasFields(a as any);
        if (hasFields || a.requires_signature) { openActionPopup(a); } else { executeAction(a.action_id); }
      },
      disabled: a.disabled,
      disabledReason: a.disabled_reason ?? undefined,
    }));

  // -- Identity strip --
  const pills: PillDef[] = [
    { label: getStatusLabel(status), variant: statusToPillVariant(status) },
  ];
  if (violationCount && violationCount > 0) {
    pills.push({ label: `${violationCount} violation${violationCount > 1 ? 's' : ''}`, variant: 'red' });
  }

  const details: DetailLine[] = [];
  if (department) details.push({ label: 'Department', value: department.charAt(0).toUpperCase() + department.slice(1) });
  if (month) details.push({ label: 'Month', value: formatMonth(month), mono: true });
  if (totalRestHours !== undefined) details.push({ label: 'Total Rest', value: `${totalRestHours.toFixed(1)} hrs`, mono: true });
  if (totalWorkHours !== undefined) details.push({ label: 'Total Work', value: `${totalWorkHours.toFixed(1)} hrs`, mono: true });

  const contextNode = (
    <>
      {department && <>{department.charAt(0).toUpperCase() + department.slice(1)}</>}
      {month && <>{department ? ' · ' : ''}{formatMonth(month)}</>}
    </>
  );

  // -- Month Summary KV --
  const summaryItems: KVItem[] = [];
  if (totalRestHours !== undefined) summaryItems.push({ label: 'Total Rest', value: `${totalRestHours.toFixed(1)} hrs`, mono: true });
  if (totalWorkHours !== undefined) summaryItems.push({ label: 'Total Work', value: `${totalWorkHours.toFixed(1)} hrs`, mono: true });
  if (totalRestHours !== undefined && month) {
    const daysInMonth = new Date(Number(month.split('-')[0]), Number(month.split('-')[1]), 0).getDate();
    const avgDaily = totalRestHours / daysInMonth;
    summaryItems.push({ label: 'Avg Daily Rest', value: `${avgDaily.toFixed(1)} hrs`, mono: true });
  }
  if (violationCount !== undefined) {
    summaryItems.push({ label: 'Violations', value: String(violationCount), mono: true });
  }
  if (isMonthComplete !== undefined) {
    summaryItems.push({ label: 'Month Complete', value: isMonthComplete ? 'Yes' : 'No' });
  }

  // -- Violations --
  const violationItems: KVItem[] = violations.map((v, i) => ({
    label: (v.date as string) ?? `Violation ${i + 1}`,
    value: (v.description ?? v.rule ?? v.message ?? 'Violation detected') as string,
    mono: true,
  }));

  // -- Weekly Breakdown --
  const weekItems: KVItem[] = weeklyBreakdown.map((w) => ({
    label: (w.label ?? w.week ?? '') as string,
    value: `${((w.rest_hours ?? w.total_rest) as number | undefined)?.toFixed(1) ?? '—'} hrs rest${(w.compliant ?? w.is_compliant) === false ? ' ⚠' : (w.compliant ?? w.is_compliant) === true ? ' ✓' : ''}`,
    mono: true,
  }));

  // -- Notes --
  const noteItems: NoteItem[] = notes.map((n, i) => ({
    id: (n.id as string) ?? `note-${i}`,
    author: (n.author ?? n.created_by ?? n.user_name) as string ?? 'Unknown',
    timestamp: (n.created_at ?? n.timestamp) as string ?? '',
    body: (n.body ?? n.note_text ?? n.text) as string ?? '',
  }));

  // -- Audit trail --
  const auditEvents: AuditEvent[] = auditTrail.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp) as string ?? '',
  }));

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={month ? formatMonth(month) : 'Sign-Off'}
        title={crewName}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          signAction ? (
            <SplitButton
              label={ctaLabel}
              onClick={handleSign}
              disabled={ctaDisabled}
              disabledReason={ctaDisabledReason}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label={ctaLabel}
              onClick={() => {}}
              disabled={ctaDisabled}
              disabledReason={ctaDisabledReason}
              items={dropdownItems}
            />
          ) : undefined
        }
      />

      {/* Month Summary */}
      {summaryItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Month Summary"
            items={summaryItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Violations */}
      {violationItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Violations"
            items={violationItems}
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Weekly Breakdown */}
      {weekItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Weekly Breakdown"
            items={weekItems}
            defaultCollapsed
            icon={
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 20V10M18 20V4M6 20v-4" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Signatures — Three-tier MLC signing chain.
          Each row shows: green checkmark + name + timestamp if signed,
          or grey dots + "Pending" if not yet signed. The sequence is
          always Crew → HOD → Master regardless of who's viewing. */}
      <ScrollReveal>
        <div style={{ marginTop: 32, paddingTop: 24, borderTop: '1px solid var(--border-faint)' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            marginBottom: 12, fontSize: 14, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.04em', color: 'var(--txt3)',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ color: 'var(--txt3)' }}>
              <path d="M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
            </svg>
            Signatures
          </div>

          {/* Crew signature */}
          <SignatureRow
            label="Crew"
            signerName={crewSignature ? ((crewSignature.name as string) ?? crewName) : null}
            signedAt={crewSignedAt}
            done={!!crewSignature}
          />

          {/* HOD signature */}
          <SignatureRow
            label="HOD"
            signerName={hodSignature ? (hodSignature.name as string) ?? null : null}
            signedAt={hodSignedAt}
            done={!!hodSignature}
          />

          {/* Master signature */}
          <SignatureRow
            label="Master"
            signerName={masterSignature ? (masterSignature.name as string) ?? null : null}
            signedAt={masterSignedAt}
            done={!!masterSignature}
          />
        </div>
      </ScrollReveal>

      {/* Crew Declaration */}
      {crewDeclaration && (
        <ScrollReveal>
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--border-faint)' }}>
            <div style={{
              fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '0.04em', color: 'var(--txt3)', marginBottom: 8,
            }}>
              Crew Declaration
            </div>
            <p style={{
              fontSize: 12, color: 'var(--txt2)', fontStyle: 'italic', margin: 0,
              lineHeight: 1.5, maxWidth: 540,
            }}>
              &ldquo;{crewDeclaration}&rdquo;
            </p>
          </div>
        </ScrollReveal>
      )}

      {/* HOD Notes */}
      {hodNotes && (
        <ScrollReveal>
          <div style={{ marginTop: 16, padding: '10px 12px', borderRadius: 6, background: 'var(--surface-el)', fontSize: 12, color: 'var(--txt2)' }}>
            <span style={{ fontWeight: 600, color: 'var(--txt3)', fontSize: 11, textTransform: 'uppercase' }}>HOD Notes: </span>
            {hodNotes}
          </div>
        </ScrollReveal>
      )}

      {/* Master Notes */}
      {masterNotes && (
        <ScrollReveal>
          <div style={{ marginTop: 8, padding: '10px 12px', borderRadius: 6, background: 'var(--surface-el)', fontSize: 12, color: 'var(--txt2)' }}>
            <span style={{ fontWeight: 600, color: 'var(--txt3)', fontSize: 11, textTransform: 'uppercase' }}>Master Notes: </span>
            {masterNotes}
          </div>
        </ScrollReveal>
      )}

      {/* Notes */}
      <ScrollReveal>
        <NotesSection
          notes={noteItems}
          onAddNote={() => {}}
          canAddNote
        />
      </ScrollReveal>

      {/* Audit Trail */}
      <ScrollReveal>
        <AuditTrailSection events={auditEvents} defaultCollapsed />
      </ScrollReveal>

      {/* Action Popup */}
      {actionPopupConfig && (
        <ActionPopup
          mode="mutate"
          title={actionPopupConfig.title}
          fields={actionPopupConfig.fields}
          signatureLevel={actionPopupConfig.signatureLevel}
          onSubmit={async (values) => {
            await executeAction(actionPopupConfig.actionId, values);
            setActionPopupConfig(null);
          }}
          onClose={() => setActionPopupConfig(null)}
        />
      )}
    </>
  );
}

// --- Signature row sub-component ---

function SignatureRow({
  label,
  signerName,
  signedAt,
  done,
}: {
  label: string;
  signerName: string | null;
  signedAt: string | null;
  done: boolean;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 0',
    }}>
      <div style={{
        width: 20, height: 20, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        background: done ? 'rgba(74,148,104,0.12)' : 'var(--surface-hover)',
        color: done ? 'var(--green)' : 'var(--txt-ghost)',
      }}>
        {done ? (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5" /></svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="1" /><circle cx="12" cy="5" r="1" /><circle cx="12" cy="19" r="1" /></svg>
        )}
      </div>
      <span style={{ fontSize: 12, color: 'var(--txt3)', minWidth: 48 }}>{label}</span>
      <span style={{ fontSize: 12, color: done ? 'var(--txt)' : 'var(--txt-ghost)', flex: 1 }}>
        {done ? signerName ?? 'Signed' : 'Pending'}
      </span>
      {signedAt && (
        <span style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
          {formatDate(signedAt)}
        </span>
      )}
    </div>
  );
}
