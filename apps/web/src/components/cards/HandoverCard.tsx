/**
 * HandoverCard Component
 *
 * Full-screen entity view for handover items and exports:
 * - HandoverItemsSection: items from handover_items table with entity links
 * - HandoverExportsSection: exported PDFs with signature tracking
 * - Action buttons: Add Item, Export to PDF, Sign Off
 *
 * Uses semantic design tokens exclusively - zero raw hex values.
 * Follows CelesteOS card patterns from WorkOrderCard and FaultLens.
 */

'use client';

import * as React from 'react';
import { useState } from 'react';
import {
  FileText,
  AlertCircle,
  Wrench,
  Settings,
  Package,
  File,
  StickyNote,
  Plus,
  Download,
  PenTool,
  Clock,
  CheckCircle2,
  AlertTriangle,
  User,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatDateTime, formatRelativeTime } from '@/lib/utils';
import {
  SectionContainer,
  StatusPill,
  EntityLink,
  GhostButton,
  PrimaryButton,
} from '@/components/ui';
import { Button } from '@/components/ui/button';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

export type HandoverEntityType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'document'
  | 'note';

export type HandoverItemPriority = 'low' | 'medium' | 'high' | 'urgent';

export type HandoverItemStatus = 'pending' | 'acknowledged' | 'actioned' | 'closed';

export type HandoverCategory = 'fyi' | 'action_required' | 'critical' | 'resolved';

export interface HandoverItem {
  id: string;
  // Display fields
  summary: string;
  section?: string;
  priority?: HandoverItemPriority;
  status?: HandoverItemStatus;
  is_critical?: boolean;
  requires_action?: boolean;
  category?: HandoverCategory;
  // Entity linking
  entity_type: HandoverEntityType;
  entity_id: string;
  entity_url?: string;
  // Risk information
  risk_tags?: string[];
  // Acknowledgement tracking
  acknowledged_by?: string;
  acknowledged_at?: string;
  // Timestamps
  created_at: string;
  added_by?: string;
}

export interface HandoverExport {
  id: string;
  // Display fields
  export_date: string;
  department?: string;
  file_url?: string;
  // Outgoing signature
  outgoing_user_id?: string;
  outgoing_user_name?: string;
  outgoing_signed_at?: string;
  // Incoming signature
  incoming_user_id?: string;
  incoming_user_name?: string;
  incoming_signed_at?: string;
  // Status
  signoff_complete?: boolean;
}

export interface HandoverCardProps {
  /** Summary counts and state */
  summary?: {
    total_items: number;
    critical_count: number;
    action_required_count: number;
    acknowledged_count: number;
    pending_count: number;
  };
  /** Handover items to display */
  items?: HandoverItem[];
  /** Handover exports with signature tracking */
  exports?: HandoverExport[];
  /** Available actions from server */
  actions?: MicroAction[];
  /** Handler for adding a new item */
  onAddItem?: () => void;
  /** Handler for exporting to PDF */
  onExport?: () => void;
  /** Handler for signing off */
  onSignOff?: () => void;
  /** Handler for navigating to an entity */
  onNavigateToEntity?: (entityType: string, entityId: string) => void;
  /** Handler for acknowledging an item */
  onAcknowledgeItem?: (itemId: string) => void;
  /** Handler for viewing an export */
  onViewExport?: (exportId: string) => void;
  /** Handler for refreshing data */
  onRefresh?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get icon for entity type
 */
function getEntityIcon(entityType: HandoverEntityType): React.ReactNode {
  const iconProps = { className: 'h-4 w-4' };
  switch (entityType) {
    case 'fault':
      return <AlertCircle {...iconProps} />;
    case 'work_order':
      return <Wrench {...iconProps} />;
    case 'equipment':
      return <Settings {...iconProps} />;
    case 'part':
      return <Package {...iconProps} />;
    case 'document':
      return <File {...iconProps} />;
    case 'note':
      return <StickyNote {...iconProps} />;
    default:
      return <FileText {...iconProps} />;
  }
}

/**
 * Get human-readable label for entity type
 */
function getEntityTypeLabel(entityType: HandoverEntityType): string {
  const labels: Record<HandoverEntityType, string> = {
    fault: 'Fault',
    work_order: 'Work Order',
    equipment: 'Equipment',
    part: 'Part',
    document: 'Document',
    note: 'Note',
  };
  return labels[entityType] || entityType;
}

/**
 * Map priority to StatusPill color
 */
function mapPriorityToColor(
  priority?: HandoverItemPriority
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (priority) {
    case 'urgent':
      return 'critical';
    case 'high':
      return 'warning';
    case 'medium':
      return 'neutral';
    case 'low':
    default:
      return 'neutral';
  }
}

/**
 * Map status to StatusPill color
 */
function mapStatusToColor(
  status?: HandoverItemStatus
): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'pending':
      return 'warning';
    case 'acknowledged':
      return 'neutral';
    case 'actioned':
      return 'success';
    case 'closed':
      return 'success';
    default:
      return 'neutral';
  }
}

/**
 * Format priority label
 */
function formatPriorityLabel(priority?: HandoverItemPriority): string {
  if (!priority) return '';
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}

/**
 * Format status label
 */
function formatStatusLabel(status?: HandoverItemStatus): string {
  if (!status) return 'Pending';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

/**
 * Get category styling
 */
function getCategoryStyles(category?: HandoverCategory): {
  pillClass: string;
  label: string;
} {
  switch (category) {
    case 'critical':
      return {
        pillClass: 'status-pill status-pill-critical',
        label: 'Critical',
      };
    case 'action_required':
      return {
        pillClass: 'status-pill status-pill-warning',
        label: 'Action Required',
      };
    case 'resolved':
      return {
        pillClass: 'status-pill status-pill-success',
        label: 'Resolved',
      };
    case 'fyi':
    default:
      return {
        pillClass: 'status-pill status-pill-neutral',
        label: 'FYI',
      };
  }
}

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/**
 * Summary stats row
 */
interface SummaryStatsProps {
  summary?: HandoverCardProps['summary'];
}

function SummaryStats({ summary }: SummaryStatsProps) {
  if (!summary) return null;

  const stats = [
    {
      label: 'Total Items',
      value: summary.total_items,
      color: 'text-txt-primary',
    },
    {
      label: 'Critical',
      value: summary.critical_count,
      color: 'text-status-critical',
    },
    {
      label: 'Action Required',
      value: summary.action_required_count,
      color: 'text-status-warning',
    },
    {
      label: 'Acknowledged',
      value: summary.acknowledged_count,
      color: 'text-status-success',
    },
    {
      label: 'Pending',
      value: summary.pending_count,
      color: 'text-txt-tertiary',
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-4 p-4 bg-surface-primary rounded-md border border-surface-border">
      {stats.map((stat) => (
        <div key={stat.label} className="text-center">
          <p className={cn('text-2xl font-semibold', stat.color)}>{stat.value}</p>
          <p className="text-[12px] text-txt-tertiary">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}

/**
 * Single handover item row
 */
interface HandoverItemRowProps {
  item: HandoverItem;
  onNavigate?: (entityType: string, entityId: string) => void;
  onAcknowledge?: (itemId: string) => void;
}

function HandoverItemRow({ item, onNavigate, onAcknowledge }: HandoverItemRowProps) {
  const categoryStyles = getCategoryStyles(item.category);
  const isAcknowledged = !!item.acknowledged_at;

  return (
    <div
      className={cn(
        'p-4 rounded-sm border transition-colors duration-fast',
        item.is_critical
          ? 'border-status-critical/30 bg-status-critical-bg'
          : 'border-surface-border-subtle bg-surface-primary',
        'hover:bg-surface-hover'
      )}
    >
      <div className="flex items-start gap-3">
        {/* Entity type icon */}
        <div className="mt-0.5 text-txt-secondary flex-shrink-0">
          {getEntityIcon(item.entity_type)}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Header row: entity type badge + category */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-[11px] font-medium text-txt-tertiary uppercase tracking-wide">
              {getEntityTypeLabel(item.entity_type)}
            </span>
            {item.section && (
              <>
                <span className="text-txt-tertiary">-</span>
                <span className="text-[11px] text-txt-tertiary">{item.section}</span>
              </>
            )}
            <span className={categoryStyles.pillClass}>
              {categoryStyles.label}
            </span>
            {item.is_critical && (
              <span className="status-pill status-pill-critical">
                <AlertTriangle className="h-3 w-3" />
                Critical
              </span>
            )}
          </div>

          {/* Summary text */}
          <p className="text-[14px] text-txt-primary font-medium mb-1 line-clamp-2">
            {item.summary}
          </p>

          {/* Entity link */}
          <div className="mb-2">
            <EntityLink
              entityType={item.entity_type}
              entityId={item.entity_id}
              label={`View ${getEntityTypeLabel(item.entity_type)}`}
              onClick={() => onNavigate?.(item.entity_type, item.entity_id)}
              className="text-[13px]"
            />
          </div>

          {/* Risk tags */}
          {item.risk_tags && item.risk_tags.length > 0 && (
            <div className="flex items-center gap-1 mb-2 flex-wrap">
              {item.risk_tags.map((tag, idx) => (
                <span
                  key={idx}
                  className="status-pill status-pill-warning"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Metadata row */}
          <div className="flex items-center gap-3 text-[12px] text-txt-tertiary">
            {item.added_by && (
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" />
                {item.added_by}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelativeTime(item.created_at)}
            </span>
            {isAcknowledged && (
              <span className="flex items-center gap-1 text-status-success">
                <CheckCircle2 className="h-3 w-3" />
                Acknowledged {item.acknowledged_by && `by ${item.acknowledged_by}`}
              </span>
            )}
          </div>

          {/* Priority and status pills */}
          {(item.priority || item.status) && (
            <div className="flex items-center gap-2 mt-2">
              {item.priority && (
                <StatusPill
                  status={mapPriorityToColor(item.priority)}
                  label={formatPriorityLabel(item.priority)}
                />
              )}
              {item.status && (
                <StatusPill
                  status={mapStatusToColor(item.status)}
                  label={formatStatusLabel(item.status)}
                />
              )}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex-shrink-0">
          {!isAcknowledged && item.requires_action && (
            <GhostButton
              onClick={() => onAcknowledge?.(item.id)}
              className="text-[12px] min-h-[32px] px-3"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Acknowledge
            </GhostButton>
          )}
          <button
            onClick={() => onNavigate?.(item.entity_type, item.entity_id)}
            className="btn-icon"
            aria-label="View details"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Handover items section
 */
interface HandoverItemsSectionProps {
  items: HandoverItem[];
  onNavigate?: (entityType: string, entityId: string) => void;
  onAcknowledge?: (itemId: string) => void;
  onAddItem?: () => void;
  stickyTop?: number;
}

function HandoverItemsSection({
  items,
  onNavigate,
  onAcknowledge,
  onAddItem,
  stickyTop = 0,
}: HandoverItemsSectionProps) {
  // Group items by category for better organization
  const criticalItems = items.filter((i) => i.is_critical);
  const actionItems = items.filter((i) => i.requires_action && !i.is_critical);
  const fyiItems = items.filter((i) => !i.is_critical && !i.requires_action);

  const hasItems = items.length > 0;

  return (
    <SectionContainer
      title="Handover Items"
      icon={<FileText className="h-5 w-5" />}
      count={items.length}
      action={onAddItem ? { label: 'Add Item', onClick: onAddItem } : undefined}
      stickyTop={stickyTop}
    >
      {!hasItems ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-3">
            <FileText className="h-6 w-6 text-txt-tertiary" />
          </div>
          <p className="text-txt-primary font-medium mb-1">No handover items</p>
          <p className="text-txt-tertiary text-[13px] mb-4">
            Add faults, work orders, equipment, or documents to the handover.
          </p>
          {onAddItem && (
            <GhostButton onClick={onAddItem} icon={<Plus className="h-4 w-4" />}>
              Add Item
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Critical items first */}
          {criticalItems.length > 0 && (
            <div className="space-y-2">
              <p className="text-[12px] font-semibold text-status-critical uppercase tracking-wide">
                Critical ({criticalItems.length})
              </p>
              <div className="space-y-2">
                {criticalItems.map((item) => (
                  <HandoverItemRow
                    key={item.id}
                    item={item}
                    onNavigate={onNavigate}
                    onAcknowledge={onAcknowledge}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Action required items */}
          {actionItems.length > 0 && (
            <div className="space-y-2">
              <p className="text-[12px] font-semibold text-status-warning uppercase tracking-wide">
                Action Required ({actionItems.length})
              </p>
              <div className="space-y-2">
                {actionItems.map((item) => (
                  <HandoverItemRow
                    key={item.id}
                    item={item}
                    onNavigate={onNavigate}
                    onAcknowledge={onAcknowledge}
                  />
                ))}
              </div>
            </div>
          )}

          {/* FYI items */}
          {fyiItems.length > 0 && (
            <div className="space-y-2">
              <p className="text-[12px] font-semibold text-txt-tertiary uppercase tracking-wide">
                For Your Information ({fyiItems.length})
              </p>
              <div className="space-y-2">
                {fyiItems.map((item) => (
                  <HandoverItemRow
                    key={item.id}
                    item={item}
                    onNavigate={onNavigate}
                    onAcknowledge={onAcknowledge}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

/**
 * Single export row with signature tracking
 */
interface HandoverExportRowProps {
  export_: HandoverExport;
  onView?: (exportId: string) => void;
}

function HandoverExportRow({ export_, onView }: HandoverExportRowProps) {
  const isFullySigned = export_.signoff_complete;
  const hasOutgoingSignature = !!export_.outgoing_signed_at;
  const hasIncomingSignature = !!export_.incoming_signed_at;

  return (
    <div className="p-4 rounded-sm border border-surface-border-subtle bg-surface-primary hover:bg-surface-hover transition-colors">
      <div className="flex items-start justify-between gap-4">
        {/* Export info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <FileText className="h-4 w-4 text-txt-secondary" />
            <span className="text-[14px] font-medium text-txt-primary">
              Handover Export - {formatDate(export_.export_date)}
            </span>
            {export_.department && (
              <span className="status-pill status-pill-neutral">
                {export_.department}
              </span>
            )}
            {isFullySigned && (
              <StatusPill status="success" label="Complete" showDot />
            )}
          </div>

          {/* Signature status */}
          <div className="grid grid-cols-2 gap-4 mt-3">
            {/* Outgoing signature */}
            <div
              className={cn(
                'p-3 rounded-sm border',
                hasOutgoingSignature
                  ? 'border-status-success/30 bg-status-success-bg'
                  : 'border-surface-border-subtle bg-surface-hover'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                {hasOutgoingSignature ? (
                  <CheckCircle2 className="h-4 w-4 text-status-success" />
                ) : (
                  <Clock className="h-4 w-4 text-txt-tertiary" />
                )}
                <span className="text-[12px] font-semibold text-txt-secondary uppercase tracking-wide">
                  Outgoing
                </span>
              </div>
              {hasOutgoingSignature ? (
                <div className="text-[13px]">
                  <p className="text-txt-primary font-medium">
                    {export_.outgoing_user_name || 'Signed'}
                  </p>
                  <p className="text-txt-tertiary text-[12px]">
                    {formatDateTime(export_.outgoing_signed_at!)}
                  </p>
                </div>
              ) : (
                <p className="text-[13px] text-txt-tertiary">Awaiting signature</p>
              )}
            </div>

            {/* Incoming signature */}
            <div
              className={cn(
                'p-3 rounded-sm border',
                hasIncomingSignature
                  ? 'border-status-success/30 bg-status-success-bg'
                  : 'border-surface-border-subtle bg-surface-hover'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                {hasIncomingSignature ? (
                  <CheckCircle2 className="h-4 w-4 text-status-success" />
                ) : (
                  <Clock className="h-4 w-4 text-txt-tertiary" />
                )}
                <span className="text-[12px] font-semibold text-txt-secondary uppercase tracking-wide">
                  Incoming
                </span>
              </div>
              {hasIncomingSignature ? (
                <div className="text-[13px]">
                  <p className="text-txt-primary font-medium">
                    {export_.incoming_user_name || 'Signed'}
                  </p>
                  <p className="text-txt-tertiary text-[12px]">
                    {formatDateTime(export_.incoming_signed_at!)}
                  </p>
                </div>
              ) : (
                <p className="text-[13px] text-txt-tertiary">Awaiting signature</p>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {export_.file_url && (
            <a
              href={export_.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-txt-tertiary hover:text-brand-interactive transition-colors"
              aria-label="Download PDF"
            >
              <Download className="h-4 w-4" />
            </a>
          )}
          <button
            onClick={() => onView?.(export_.id)}
            className="btn-icon"
            aria-label="View export"
          >
            <ExternalLink className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Handover exports section
 */
interface HandoverExportsSectionProps {
  exports: HandoverExport[];
  onExport?: () => void;
  onViewExport?: (exportId: string) => void;
  stickyTop?: number;
}

function HandoverExportsSection({
  exports,
  onExport,
  onViewExport,
  stickyTop = 0,
}: HandoverExportsSectionProps) {
  const hasExports = exports.length > 0;
  const pendingSignoffs = exports.filter((e) => !e.signoff_complete).length;

  return (
    <SectionContainer
      title="Exports & Signatures"
      icon={<PenTool className="h-5 w-5" />}
      count={exports.length}
      action={onExport ? { label: 'Export PDF', onClick: onExport } : undefined}
      stickyTop={stickyTop}
    >
      {!hasExports ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-3">
            <PenTool className="h-6 w-6 text-txt-tertiary" />
          </div>
          <p className="text-txt-primary font-medium mb-1">No exports yet</p>
          <p className="text-txt-tertiary text-[13px] mb-4">
            Export the handover to PDF for signature collection.
          </p>
          {onExport && (
            <GhostButton onClick={onExport} icon={<Download className="h-4 w-4" />}>
              Export to PDF
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {pendingSignoffs > 0 && (
            <div className="flex items-center gap-2 p-2 rounded-sm bg-status-warning-bg text-status-warning text-[13px]">
              <Clock className="h-4 w-4" />
              <span>{pendingSignoffs} export(s) awaiting signature</span>
            </div>
          )}
          {exports.map((export_) => (
            <HandoverExportRow
              key={export_.id}
              export_={export_}
              onView={onViewExport}
            />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

/**
 * HandoverCard - Full card component for handover lens
 *
 * @example
 * <HandoverCard
 *   items={handoverItems}
 *   exports={handoverExports}
 *   onAddItem={() => setShowAddModal(true)}
 *   onExport={() => handleExport()}
 *   onSignOff={() => handleSignOff()}
 *   onNavigateToEntity={(type, id) => router.push(`/${type}/${id}`)}
 * />
 */
export function HandoverCard({
  summary,
  items = [],
  exports = [],
  actions = [],
  onAddItem,
  onExport,
  onSignOff,
  onNavigateToEntity,
  onAcknowledgeItem,
  onViewExport,
  onRefresh,
  className,
}: HandoverCardProps) {
  return (
    <div className={cn('flex flex-col gap-6', className)}>
      {/* Header with summary stats */}
      <div className="bg-surface-primary rounded-md p-6 border border-surface-border-subtle">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-brand-muted flex items-center justify-center">
              <FileText className="h-5 w-5 text-brand-interactive" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-txt-primary">Handover</h1>
              <p className="text-[13px] text-txt-tertiary">
                {items.length} item{items.length !== 1 ? 's' : ''} -{' '}
                {exports.length} export{exports.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          {/* Primary action buttons */}
          <div className="flex items-center gap-2">
            {onAddItem && (
              <GhostButton onClick={onAddItem} icon={<Plus className="h-4 w-4" />}>
                Add Item
              </GhostButton>
            )}
            {onExport && (
              <GhostButton onClick={onExport} icon={<Download className="h-4 w-4" />}>
                Export PDF
              </GhostButton>
            )}
            {onSignOff && (
              <PrimaryButton onClick={onSignOff}>
                <PenTool className="h-4 w-4" />
                Sign Off
              </PrimaryButton>
            )}
          </div>
        </div>

        {/* Summary stats */}
        {summary && <SummaryStats summary={summary} />}
      </div>

      {/* Handover Items Section */}
      <HandoverItemsSection
        items={items}
        onNavigate={onNavigateToEntity}
        onAcknowledge={onAcknowledgeItem}
        onAddItem={onAddItem}
        stickyTop={56}
      />

      {/* Exports Section */}
      <HandoverExportsSection
        exports={exports}
        onExport={onExport}
        onViewExport={onViewExport}
        stickyTop={56}
      />
    </div>
  );
}

HandoverCard.displayName = 'HandoverCard';

export default HandoverCard;
