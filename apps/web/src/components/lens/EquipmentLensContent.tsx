'use client';

import * as React from 'react';
import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { ReportFaultModal } from '@/components/modals/ReportFaultModal';
import { ScheduleMaintenanceModal } from '@/components/modals/ScheduleMaintenanceModal';
import { WorkOrderCreateModal } from './actions';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';
import { useEquipmentActions, useEquipmentPermissions, type EquipmentStatus, type SignatureData } from '@/hooks/useEquipmentActions';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { SignatureCanvas } from '@/components/lens/handover-export-sections/SignatureCanvas';
import { Flag, FileUp, Link, AlertTriangle, RefreshCw, StickyNote, Archive } from 'lucide-react';

export interface EquipmentLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'faulty':
    case 'offline': return 'critical';
    case 'maintenance': return 'warning';
    case 'operational': return 'success';
    default: return 'neutral';
  }
}

export function EquipmentLensContent({ id, data, onBack, onClose }: EquipmentLensContentProps) {
  const [reportFaultOpen, setReportFaultOpen] = useState(false);
  const [scheduleMaintenanceOpen, setScheduleMaintenanceOpen] = useState(false);
  const [createWorkOrderOpen, setCreateWorkOrderOpen] = useState(false);
  const { user } = useAuth();

  const name = (data.name as string) || 'Equipment';
  const equipment_type = (data.equipment_type as string) || (data.category as string) || 'General';
  const manufacturer = data.manufacturer as string | undefined;
  const model = data.model as string | undefined;
  const serial_number = data.serial_number as string | undefined;
  const location = (data.location as string) || 'Unknown';
  const status = (data.status as string) || 'operational';
  const installation_date = data.installation_date as string | undefined;
  const last_maintenance = data.last_maintenance as string | undefined;
  const next_maintenance = data.next_maintenance as string | undefined;

  const statusColor = mapStatusToColor(status);

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: status.charAt(0).toUpperCase() + status.slice(1), color: statusColor },
    { label: 'Type', value: equipment_type },
    { label: 'Location', value: location },
    { label: 'Manufacturer', value: manufacturer ?? '—' },
    { label: 'Model', value: model ?? '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Equipment" title={name} onBack={onBack} onClose={onClose} />
      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock title={name} subtitle={manufacturer && model ? `${manufacturer} ${model}` : undefined} status={{ label: status.charAt(0).toUpperCase() + status.slice(1), color: statusColor }} />
        </div>
        <div className="mt-3"><VitalSignsRow signs={vitalSigns} /></div>
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <PrimaryButton onClick={() => setReportFaultOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Report Fault</PrimaryButton>
          <GhostButton onClick={() => setCreateWorkOrderOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Create Work Order</GhostButton>
          <GhostButton onClick={() => setScheduleMaintenanceOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Schedule Maintenance</GhostButton>
        </div>
        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />
        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 typo-body">
              {serial_number && <><dt className="text-celeste-text-muted">Serial Number</dt><dd className="text-celeste-text-primary">{serial_number}</dd></>}
              {installation_date && <><dt className="text-celeste-text-muted">Installed</dt><dd className="text-celeste-text-primary">{formatRelativeTime(installation_date)}</dd></>}
              {last_maintenance && <><dt className="text-celeste-text-muted">Last Maintenance</dt><dd className="text-celeste-text-primary">{formatRelativeTime(last_maintenance)}</dd></>}
              {next_maintenance && <><dt className="text-celeste-text-muted">Next Maintenance</dt><dd className="text-celeste-text-primary">{formatRelativeTime(next_maintenance)}</dd></>}
            </dl>
          </SectionContainer>
        </div>
      </main>

      <ReportFaultModal
        open={reportFaultOpen}
        onOpenChange={setReportFaultOpen}
        context={{
          equipment_id: id,
          equipment_name: name,
        }}
      />

      <ScheduleMaintenanceModal
        open={scheduleMaintenanceOpen}
        onOpenChange={setScheduleMaintenanceOpen}
        context={{
          equipment_id: id,
          equipment_name: name,
        }}
      />

      {user?.yachtId && (
        <WorkOrderCreateModal
          open={createWorkOrderOpen}
          onClose={() => setCreateWorkOrderOpen(false)}
          yachtId={user.yachtId}
          extractedEntities={[name]}
          onSuccess={(workOrderId, woNumber) => {
            setCreateWorkOrderOpen(false);
            toast.success(`Created ${woNumber}`, {
              description: `Work order created for ${name}`,
            });
          }}
        />
      )}
    </div>
  );
}

