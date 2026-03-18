'use client';

/**
 * EquipmentContent — lens-v2 Equipment entity view.
 * Matches lens-equipment.html prototype exactly.
 * Reads all data from useEntityLensContext() — zero props.
 *
 * Sections (in prototype order):
 * 1. Identity strip: overline, title, context, pills, detail lines
 * 2. Specifications (KVSection — two-column grid)
 * 3. Active Work Orders (DocRows)
 * 4. Active Faults (DocRows)
 * 5. Certificates (DocRows, collapsed)
 * 6. Maintenance History (AuditTrail)
 * 7. Attachments
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from '../lens.module.css';
import { IdentityStrip, type PillDef, type DetailLine } from '../IdentityStrip';
import { SplitButton, type DropdownItem } from '../SplitButton';
import { ScrollReveal } from '../ScrollReveal';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// Sections
import {
  AuditTrailSection,
  AttachmentsSection,
  DocRowsSection,
  KVSection,
  type AuditEvent,
  type AttachmentItem,
  type DocRowItem,
  type KVItem,
} from '../sections';

// ─── Helpers ───

function formatLabel(str: string): string {
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Component ───

export function EquipmentContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // ── Extract entity fields ──
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const equipment_code = (entity?.equipment_code ?? payload.equipment_code ?? entity?.code ?? payload.code) as string | undefined;
  const name = ((entity?.name ?? payload.name) as string | undefined) ?? 'Equipment';
  const equipment_type = ((entity?.equipment_type ?? payload.equipment_type ?? entity?.category ?? payload.category) as string | undefined) ?? 'General';
  const manufacturer = (entity?.manufacturer ?? payload.manufacturer) as string | undefined;
  const model = (entity?.model ?? payload.model) as string | undefined;
  const serial_number = (entity?.serial_number ?? payload.serial_number) as string | undefined;
  const location = (entity?.location ?? payload.location) as string | undefined;
  const installation_date = (entity?.installation_date ?? payload.installation_date) as string | undefined;
  const last_maintenance = (entity?.last_maintenance ?? payload.last_maintenance) as string | undefined;
  const next_maintenance = (entity?.next_maintenance ?? payload.next_maintenance) as string | undefined;
  const responsible = (entity?.responsible ?? payload.responsible ?? entity?.assigned_to_name ?? payload.assigned_to_name) as string | undefined;
  const criticality = (entity?.criticality ?? payload.criticality) as string | undefined;
  const running_hours = (entity?.running_hours ?? payload.running_hours) as number | string | undefined;
  const hierarchy = (entity?.hierarchy ?? payload.hierarchy) as string | undefined;

  // Specifications (custom key-value data)
  const specifications = ((entity?.specifications ?? payload.specifications) as Array<Record<string, unknown>> | undefined) ?? [];
  // Sub-entity arrays
  const work_orders = ((entity?.work_orders ?? payload.work_orders ?? entity?.active_work_orders ?? payload.active_work_orders) as Array<Record<string, unknown>> | undefined) ?? [];
  const faults = ((entity?.faults ?? payload.faults ?? entity?.active_faults ?? payload.active_faults) as Array<Record<string, unknown>> | undefined) ?? [];
  const certificates = ((entity?.certificates ?? payload.certificates) as Array<Record<string, unknown>> | undefined) ?? [];
  const history = ((entity?.audit_history ?? payload.audit_history ?? entity?.history ?? payload.history ?? entity?.maintenance_history ?? payload.maintenance_history) as Array<Record<string, unknown>> | undefined) ?? [];
  const attachments = ((entity?.attachments ?? payload.attachments) as Array<Record<string, unknown>> | undefined) ?? [];

  // ── Action gates ──
  const createWOAction = getAction('create_work_order_for_equipment');
  const flagAction = getAction('flag_equipment_attention');
  const addNoteAction = getAction('add_equipment_note');
  const decommissionAction = getAction('decommission_equipment');

  // ── Derived display ──
  // Owner correction: DO NOT render status indicators (low fidelity, misleading)
  const pills: PillDef[] = [];

  const details: DetailLine[] = [];
  if (manufacturer) {
    details.push({ label: 'Manufacturer', value: manufacturer });
  }
  if (model) {
    details.push({ label: 'Model', value: model, mono: true });
  }
  if (serial_number) {
    details.push({ label: 'Serial', value: serial_number, mono: true });
  }
  if (installation_date) {
    details.push({ label: 'Installed', value: installation_date, mono: true });
  }
  if (next_maintenance) {
    details.push({ label: 'Next Service', value: next_maintenance, mono: true });
  }
  if (running_hours !== undefined) {
    details.push({ label: 'Running Hours', value: String(running_hours), mono: true });
  }

  // Context line (location + responsible)
  const contextParts: string[] = [];
  if (location) contextParts.push(location);
  if (equipment_type && equipment_type !== 'General') contextParts.push(equipment_type);
  const contextNode = (
    <>
      {contextParts.join(' · ')}
      {responsible && (
        <>
          {contextParts.length > 0 && ' · '}
          Responsible: <span className={styles.crewLink}>{responsible}</span>
        </>
      )}
    </>
  );

  // ── Split button config ──
  const primaryLabel = 'Create Work Order';
  const primaryDisabled = createWOAction?.disabled ?? false;
  const primaryDisabledReason = createWOAction?.disabled_reason;

  const handlePrimary = React.useCallback(async () => {
    await executeAction('create_work_order_for_equipment', { type: 'corrective', priority: 'routine' });
  }, [executeAction]);

  const dropdownItems: DropdownItem[] = [];
  if (flagAction !== null) {
    dropdownItems.push({
      label: 'Log Fault',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
      onClick: () => executeAction('flag_equipment_attention', {}),
    });
  }
  if (addNoteAction !== null) {
    dropdownItems.push({
      label: 'Add Note',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" /></svg>,
      onClick: () => {},
    });
  }
  if (decommissionAction !== null) {
    dropdownItems.push({
      label: 'Decommission',
      icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>,
      onClick: () => executeAction('decommission_equipment', {}),
      danger: true,
    });
  }

  // ── Map section data ──

  // Specifications → KVItems
  const specItems: KVItem[] = specifications.map((s) => ({
    label: (s.label ?? s.key ?? s.name) as string ?? '',
    value: (s.value ?? s.val) as string ?? '',
    mono: (s.mono as boolean | undefined) ?? false,
  }));

  // Work orders → DocRows
  const woItems: DocRowItem[] = work_orders.map((wo, i) => ({
    id: (wo.id as string) ?? `wo-${i}`,
    name: (wo.title ?? wo.name) as string ?? 'Work Order',
    code: (wo.wo_number ?? wo.code) as string | undefined,
    meta: (wo.assigned_to_name ?? wo.assigned_to ?? wo.meta) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="1" /></svg>,
    onClick: wo.id ? () => router.push(getEntityRoute('work_orders' as Parameters<typeof getEntityRoute>[0], wo.id as string)) : undefined,
  }));

  // Faults → DocRows
  const faultItems: DocRowItem[] = faults.map((f, i) => ({
    id: (f.id as string) ?? `fault-${i}`,
    name: (f.title ?? f.name) as string ?? 'Fault',
    code: (f.fault_number ?? f.code) as string | undefined,
    meta: (f.reported_by ?? f.meta) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
    onClick: f.id ? () => router.push(getEntityRoute('faults' as Parameters<typeof getEntityRoute>[0], f.id as string)) : undefined,
  }));

  // Certificates → DocRows
  const certItems: DocRowItem[] = certificates.map((c, i) => ({
    id: (c.id as string) ?? `cert-${i}`,
    name: (c.title ?? c.name) as string ?? 'Certificate',
    code: (c.certificate_number ?? c.code) as string | undefined,
    meta: (c.meta ?? c.description) as string | undefined,
    date: (c.expires_at ?? c.expiry_date ?? c.date) as string | undefined,
    icon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>,
    onClick: c.id ? () => router.push(getEntityRoute('certificates' as Parameters<typeof getEntityRoute>[0], c.id as string)) : undefined,
  }));

  // History → AuditEvents
  const auditEvents: AuditEvent[] = history.map((h, i) => ({
    id: (h.id as string) ?? `audit-${i}`,
    action: (h.action ?? h.description ?? h.event ?? h.title) as string ?? '',
    actor: (h.actor ?? h.user_name ?? h.performed_by ?? h.assigned_to) as string | undefined,
    timestamp: (h.created_at ?? h.timestamp ?? h.completed_at) as string ?? '',
  }));

  // Attachments → AttachmentItems
  const attachmentItems: AttachmentItem[] = attachments.map((a, i) => ({
    id: (a.id as string) ?? `att-${i}`,
    name: (a.name ?? a.file_name ?? a.filename) as string ?? 'File',
    caption: (a.caption ?? a.description) as string | undefined,
    size: (a.size ?? a.file_size) as string | undefined,
    kind: (((a.mime_type ?? a.content_type) as string) ?? '').startsWith('image') ? 'image' as const : 'document' as const,
  }));

  return (
    <>
      {/* Identity Strip */}
      <IdentityStrip
        overline={equipment_code}
        title={manufacturer && model ? `${name} \u2014 ${manufacturer} ${model}` : name}
        context={contextNode}
        pills={pills}
        details={details}
        actionSlot={
          createWOAction !== null ? (
            <SplitButton
              label={primaryLabel}
              onClick={handlePrimary}
              disabled={primaryDisabled}
              disabledReason={primaryDisabledReason ?? undefined}
              items={dropdownItems}
            />
          ) : dropdownItems.length > 0 ? (
            <SplitButton
              label={dropdownItems[0].label}
              onClick={dropdownItems[0].onClick}
              items={dropdownItems.slice(1)}
            />
          ) : undefined
        }
      />

      {/* Specifications */}
      {specItems.length > 0 && (
        <ScrollReveal>
          <KVSection
            title="Specifications"
            items={specItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <line x1="5" y1="9" x2="11" y2="9" stroke="currentColor" strokeWidth="1.3" />
                <line x1="5" y1="12" x2="9" y2="12" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Active Work Orders */}
      {woItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Work Orders"
            docs={woItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 3H5a1 1 0 00-1 1v9a1 1 0 001 1h6a1 1 0 001-1V4a1 1 0 00-1-1h-1" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <rect x="6" y="1.5" width="4" height="3" rx="0.5" stroke="currentColor" strokeWidth="1.3" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Active Faults */}
      {faultItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Active Faults"
            docs={faultItems}
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M7.13 2.58L1.22 12a1.33 1.33 0 001.14 2h11.28a1.33 1.33 0 001.14-2L8.87 2.58a1.33 1.33 0 00-2.28 0z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                <line x1="8" y1="6" x2="8" y2="9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <circle cx="8" cy="11" r="0.5" fill="currentColor" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Certificates */}
      {certItems.length > 0 && (
        <ScrollReveal>
          <DocRowsSection
            title="Certificates"
            docs={certItems}
            defaultCollapsed
            icon={
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 14s5.33-2.67 5.33-6.67V3.33L8 1.33 2.67 3.33v4C2.67 11.33 8 14 8 14z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
              </svg>
            }
          />
        </ScrollReveal>
      )}

      {/* Maintenance History */}
      {auditEvents.length > 0 && (
        <ScrollReveal>
          <AuditTrailSection events={auditEvents} defaultCollapsed />
        </ScrollReveal>
      )}

      {/* Attachments */}
      <ScrollReveal>
        <AttachmentsSection
          attachments={attachmentItems}
          onAddFile={() => {}}
          canAddFile={false}
        />
      </ScrollReveal>
    </>
  );
}
