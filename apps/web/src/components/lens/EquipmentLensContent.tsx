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
import { useEquipmentActions, useEquipmentPermissions, type EquipmentStatus, type SignatureData, type PinTotpSignature } from '@/hooks/useEquipmentActions';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { SignatureCanvas } from '@/components/lens/handover-export-sections/SignatureCanvas';
import { Flag, FileUp, Link, AlertTriangle, RefreshCw, StickyNote, Archive, Settings, XCircle, ShieldAlert, Lock, Key } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';

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
    case 'offline':
    case 'out_of_service': return 'critical';
    case 'maintenance':
    case 'degraded': return 'warning';
    case 'operational': return 'success';
    default: return 'neutral';
  }
}

/** Valid equipment status values for updates */
const EQUIPMENT_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'operational', label: 'Operational' },
  { value: 'degraded', label: 'Degraded' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'out_of_service', label: 'Out of Service' },
];

interface UpdateStatusModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentStatus: string;
  equipmentId: string;
  equipmentName: string;
  onStatusUpdated?: () => void;
}

function UpdateStatusModal({
  open,
  onOpenChange,
  currentStatus,
  equipmentId,
  equipmentName,
  onStatusUpdated,
}: UpdateStatusModalProps) {
  const [selectedStatus, setSelectedStatus] = useState<string>(currentStatus);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { updateEquipmentStatus } = useEquipmentActions(equipmentId);

  // Reset form when modal opens
  React.useEffect(() => {
    if (open) {
      setSelectedStatus(currentStatus);
      setNotes('');
    }
  }, [open, currentStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedStatus === currentStatus && !notes) {
      toast.error('Please select a different status or add notes');
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await updateEquipmentStatus(selectedStatus as EquipmentStatus, notes || undefined);
      if (result.success) {
        toast.success('Status updated', {
          description: `${equipmentName} is now ${selectedStatus}`,
        });
        onOpenChange(false);
        onStatusUpdated?.();
      } else {
        toast.error('Failed to update status', {
          description: result.error || 'Please try again',
        });
      }
    } catch (err) {
      toast.error('Failed to update status', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]" data-testid="update-status-modal">
        <DialogHeader>
          <DialogTitle>Update Equipment Status</DialogTitle>
          <DialogDescription>
            Change the operational status of {equipmentName}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="status-select">Status</Label>
            <Select
              value={selectedStatus}
              onValueChange={setSelectedStatus}
            >
              <SelectTrigger id="status-select" data-testid="status-dropdown">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {EQUIPMENT_STATUS_OPTIONS.map((option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    data-testid={`status-option-${option.value}`}
                  >
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="status-notes">Notes (optional)</Label>
            <Textarea
              id="status-notes"
              placeholder="Add notes about this status change..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              data-testid="status-notes"
            />
          </div>
          <DialogFooter>
            <GhostButton
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </GhostButton>
            <PrimaryButton
              type="submit"
              disabled={isSubmitting}
              data-testid="update-status-submit"
            >
              {isSubmitting ? 'Updating...' : 'Update Status'}
            </PrimaryButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface DecommissionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  equipmentId: string;
  equipmentName: string;
  currentStatus: string;
  onDecommissioned?: () => void;
}

function DecommissionModal({
  open,
  onOpenChange,
  equipmentId,
  equipmentName,
  currentStatus,
  onDecommissioned,
}: DecommissionModalProps) {
  const [reason, setReason] = useState('');
  const [pin, setPin] = useState('');
  const [totp, setTotp] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { decommissionEquipment } = useEquipmentActions(equipmentId);
  const { user } = useAuth();

  // Reset form when modal opens
  React.useEffect(() => {
    if (open) {
      setReason('');
      setPin('');
      setTotp('');
    }
  }, [open]);

  // Check if already decommissioned
  const isAlreadyDecommissioned = currentStatus === 'decommissioned';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isAlreadyDecommissioned) {
      toast.error('Equipment is already decommissioned');
      return;
    }

    if (!reason.trim()) {
      toast.error('Please provide a reason for decommissioning');
      return;
    }

    if (!pin.trim() || !totp.trim()) {
      toast.error('PIN and TOTP are required for signed actions');
      return;
    }

    setIsSubmitting(true);
    try {
      const signature: PinTotpSignature = {
        pin: pin.trim(),
        totp: totp.trim(),
        signer_id: user?.id || '',
        signed_at: new Date().toISOString(),
      };

      const result = await decommissionEquipment(reason.trim(), signature);
      if (result.success) {
        toast.success('Equipment decommissioned', {
          description: `${equipmentName} has been decommissioned`,
        });
        onOpenChange(false);
        onDecommissioned?.();
      } else {
        toast.error('Failed to decommission equipment', {
          description: result.error || 'Please try again',
        });
      }
    } catch (err) {
      toast.error('Failed to decommission equipment', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]" data-testid="decommission-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-400">
            <ShieldAlert className="h-5 w-5" />
            Decommission Equipment
          </DialogTitle>
          <DialogDescription>
            This is a permanent action. {equipmentName} will be marked as decommissioned and cannot be restored.
          </DialogDescription>
        </DialogHeader>

        {isAlreadyDecommissioned ? (
          <div className="py-4">
            <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-md">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <span className="text-sm text-amber-400">
                This equipment is already decommissioned and cannot be decommissioned again.
              </span>
            </div>
            <DialogFooter className="mt-4">
              <GhostButton onClick={() => onOpenChange(false)}>
                Close
              </GhostButton>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="decommission-reason">
                Reason <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="decommission-reason"
                placeholder="Why is this equipment being decommissioned?"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                data-testid="decommission-reason"
                required
              />
            </div>

            <div className="border-t border-surface-border pt-4">
              <div className="flex items-center gap-2 mb-3 text-sm text-amber-400">
                <Lock className="h-4 w-4" />
                <span>Signature Required (Captain/Manager)</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="decommission-pin" className="flex items-center gap-1.5">
                    <Key className="h-3.5 w-3.5" />
                    PIN
                  </Label>
                  <Input
                    id="decommission-pin"
                    type="password"
                    placeholder="Enter PIN"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    data-testid="decommission-pin"
                    required
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="decommission-totp" className="flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5" />
                    TOTP
                  </Label>
                  <Input
                    id="decommission-totp"
                    type="text"
                    placeholder="6-digit code"
                    value={totp}
                    onChange={(e) => setTotp(e.target.value)}
                    data-testid="decommission-totp"
                    required
                    maxLength={6}
                    autoComplete="off"
                  />
                </div>
              </div>
            </div>

            <DialogFooter>
              <GhostButton
                type="button"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </GhostButton>
              <PrimaryButton
                type="submit"
                disabled={isSubmitting || !reason.trim() || !pin.trim() || !totp.trim()}
                className="bg-red-600 hover:bg-red-700"
                data-testid="sign-decommission-button"
              >
                {isSubmitting ? 'Decommissioning...' : 'Sign & Decommission'}
              </PrimaryButton>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function EquipmentLensContent({ id, data, onBack, onClose, onRefresh }: EquipmentLensContentProps) {
  const [reportFaultOpen, setReportFaultOpen] = useState(false);
  const [scheduleMaintenanceOpen, setScheduleMaintenanceOpen] = useState(false);
  const [createWorkOrderOpen, setCreateWorkOrderOpen] = useState(false);
  const [flagAttentionOpen, setFlagAttentionOpen] = useState(false);
  const [updateStatusOpen, setUpdateStatusOpen] = useState(false);
  const [decommissionOpen, setDecommissionOpen] = useState(false);
  const [attentionReason, setAttentionReason] = useState('');
  const { user } = useAuth();
  const { flagEquipmentAttention, isLoading: actionLoading } = useEquipmentActions(id);
  const permissions = useEquipmentPermissions();

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
  const attention_flag = data.attention_flag as boolean | undefined;
  const attention_reason = data.attention_reason as string | undefined;

  const statusColor = mapStatusToColor(status);

  // Handle flagging equipment for attention
  const handleFlagAttention = useCallback(async () => {
    if (attention_flag) {
      // Remove flag - no reason needed
      const result = await flagEquipmentAttention(false);
      if (result.success) {
        toast.success('Attention flag removed');
        onRefresh?.();
      } else {
        toast.error(result.error || 'Failed to remove attention flag');
      }
    } else {
      // Show modal to enter reason
      setFlagAttentionOpen(true);
    }
  }, [attention_flag, flagEquipmentAttention, onRefresh]);

  const handleSubmitAttentionFlag = useCallback(async () => {
    if (!attentionReason.trim()) {
      toast.error('Please provide a reason for flagging');
      return;
    }
    const result = await flagEquipmentAttention(true, attentionReason.trim());
    if (result.success) {
      toast.success('Equipment flagged for attention');
      setFlagAttentionOpen(false);
      setAttentionReason('');
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to flag equipment');
    }
  }, [attentionReason, flagEquipmentAttention, onRefresh]);

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
          {/* Attention flag indicator */}
          {attention_flag && (
            <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-md" data-testid="attention-flag-indicator">
              <Flag className="h-4 w-4 text-amber-500" />
              <span className="text-sm text-amber-400">Flagged for attention</span>
              {attention_reason && (
                <span className="text-sm text-amber-300/80">- {attention_reason}</span>
              )}
            </div>
          )}
        </div>
        <div className="mt-3"><VitalSignsRow signs={vitalSigns} /></div>
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <PrimaryButton onClick={() => setReportFaultOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Report Fault</PrimaryButton>
          <GhostButton onClick={() => setCreateWorkOrderOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Create Work Order</GhostButton>
          <GhostButton onClick={() => setScheduleMaintenanceOpen(true)} className="text-[13px] min-h-9 px-4 py-2">Schedule Maintenance</GhostButton>
          {permissions.canUpdateStatus && (
            <GhostButton
              onClick={() => setUpdateStatusOpen(true)}
              className="text-[13px] min-h-9 px-4 py-2"
              data-testid="update-status-button"
            >
              <Settings className="h-4 w-4 mr-1.5" />
              Update Status
            </GhostButton>
          )}
          {permissions.canFlagAttention && (
            <GhostButton
              onClick={handleFlagAttention}
              disabled={actionLoading}
              className={cn(
                "text-[13px] min-h-9 px-4 py-2",
                attention_flag && "text-amber-400 border-amber-500/50 hover:bg-amber-500/10"
              )}
              data-testid="flag-attention-button"
            >
              <Flag className="h-4 w-4 mr-1.5" />
              {attention_flag ? 'Remove Flag' : 'Flag for Attention'}
            </GhostButton>
          )}
          {permissions.canDecommission && status !== 'decommissioned' && (
            <GhostButton
              onClick={() => setDecommissionOpen(true)}
              className="text-[13px] min-h-9 px-4 py-2 text-red-400 border-red-500/50 hover:bg-red-500/10"
              data-testid="decommission-button"
            >
              <XCircle className="h-4 w-4 mr-1.5" />
              Decommission
            </GhostButton>
          )}
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

      {/* Flag for Attention Modal */}
      <Dialog open={flagAttentionOpen} onOpenChange={setFlagAttentionOpen}>
        <DialogContent className="max-w-md" data-testid="flag-attention-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Flag className="h-5 w-5 text-amber-500" />
              Flag for Attention
            </DialogTitle>
            <DialogDescription>
              Flag this equipment to highlight it for the team. Provide a reason to help others understand why it needs attention.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="attention-reason">
                Reason <span className="text-red-500">*</span>
              </Label>
              <Textarea
                id="attention-reason"
                value={attentionReason}
                onChange={(e) => setAttentionReason(e.target.value)}
                placeholder="Why does this equipment need attention?"
                rows={3}
                data-testid="attention-reason-input"
              />
            </div>
          </div>
          <DialogFooter>
            <GhostButton
              onClick={() => {
                setFlagAttentionOpen(false);
                setAttentionReason('');
              }}
              disabled={actionLoading}
            >
              Cancel
            </GhostButton>
            <PrimaryButton
              onClick={handleSubmitAttentionFlag}
              disabled={actionLoading || !attentionReason.trim()}
              data-testid="submit-flag-button"
            >
              {actionLoading ? 'Flagging...' : 'Flag Equipment'}
            </PrimaryButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Update Status Modal */}
      {permissions.canUpdateStatus && (
        <UpdateStatusModal
          open={updateStatusOpen}
          onOpenChange={setUpdateStatusOpen}
          currentStatus={status}
          equipmentId={id}
          equipmentName={name}
          onStatusUpdated={onRefresh}
        />
      )}

      {/* Decommission Modal - Captain/Manager only */}
      {permissions.canDecommission && (
        <DecommissionModal
          open={decommissionOpen}
          onOpenChange={setDecommissionOpen}
          equipmentId={id}
          equipmentName={name}
          currentStatus={status}
          onDecommissioned={onRefresh}
        />
      )}
    </div>
  );
}

