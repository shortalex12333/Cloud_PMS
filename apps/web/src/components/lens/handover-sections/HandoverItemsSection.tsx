'use client';

/**
 * HandoverItemsSection
 *
 * Displays handover items grouped by priority (critical → action_required → fyi).
 * Each item links to its source entity (fault, work order, equipment, part, document).
 *
 * Used by HandoverLens (FE-03-02).
 * Extracted from HandoverCard.tsx patterns.
 */

import * as React from 'react';
import {
  FileText,
  AlertCircle,
  Wrench,
  Settings,
  Package,
  File,
  StickyNote,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  User,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer, StatusPill, EntityLink, GhostButton } from '@/components/ui';
import type { HandoverItem } from '../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getEntityIcon(entityType: string): React.ReactNode {
  const cls = 'h-4 w-4';
  switch (entityType) {
    case 'fault':       return <AlertCircle className={cls} />;
    case 'work_order':  return <Wrench className={cls} />;
    case 'equipment':   return <Settings className={cls} />;
    case 'part':        return <Package className={cls} />;
    case 'document':    return <File className={cls} />;
    case 'note':        return <StickyNote className={cls} />;
    default:            return <FileText className={cls} />;
  }
}

function getEntityTypeLabel(entityType: string): string {
  const labels: Record<string, string> = {
    fault: 'Fault',
    work_order: 'Work Order',
    equipment: 'Equipment',
    part: 'Part',
    document: 'Document',
    note: 'Note',
  };
  return labels[entityType] || entityType;
}

function mapCategoryStyles(category?: string): { pillClass: string; label: string } {
  switch (category) {
    case 'critical':
      return { pillClass: 'status-pill status-pill-critical', label: 'Critical' };
    case 'action_required':
      return { pillClass: 'status-pill status-pill-warning', label: 'Action Required' };
    case 'resolved':
      return { pillClass: 'status-pill status-pill-success', label: 'Resolved' };
    case 'fyi':
    default:
      return { pillClass: 'status-pill status-pill-neutral', label: 'FYI' };
  }
}

// ---------------------------------------------------------------------------
// HandoverItemRow
// ---------------------------------------------------------------------------

interface HandoverItemRowProps {
  item: HandoverItem;
  onNavigate?: (entityType: string, entityId: string) => void;
  onAcknowledge?: (itemId: string) => void;
}

function HandoverItemRow({ item, onNavigate, onAcknowledge }: HandoverItemRowProps) {
  const categoryStyles = mapCategoryStyles(item.category);
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
                  status={
                    item.priority === 'urgent'
                      ? 'critical'
                      : item.priority === 'high'
                      ? 'warning'
                      : 'neutral'
                  }
                  label={item.priority.charAt(0).toUpperCase() + item.priority.slice(1)}
                />
              )}
              {item.status && (
                <StatusPill
                  status={
                    item.status === 'pending'
                      ? 'warning'
                      : item.status === 'acknowledged'
                      ? 'neutral'
                      : 'success'
                  }
                  label={item.status.charAt(0).toUpperCase() + item.status.slice(1)}
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
            className="p-2 text-txt-tertiary hover:text-brand-interactive transition-colors"
            aria-label="View details"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HandoverItemsSection
// ---------------------------------------------------------------------------

export interface HandoverItemsSectionProps {
  items: HandoverItem[];
  onNavigate?: (entityType: string, entityId: string) => void;
  onAcknowledge?: (itemId: string) => void;
  onAddItem?: () => void;
  stickyTop?: number;
}

/**
 * HandoverItemsSection
 *
 * Displays handover items grouped: Critical → Action Required → FYI.
 * Shows Add Item CTA when `onAddItem` is provided (draft state + canAddItem perm).
 */
export function HandoverItemsSection({
  items,
  onNavigate,
  onAcknowledge,
  onAddItem,
  stickyTop = 0,
}: HandoverItemsSectionProps) {
  const criticalItems = items.filter((i) => i.is_critical);
  const actionItems = items.filter((i) => i.requires_action && !i.is_critical);
  const fyiItems = items.filter((i) => !i.is_critical && !i.requires_action);

  const hasItems = items.length > 0;

  return (
    <SectionContainer
      title="Handover Items"
      icon={<FileText className="h-5 w-5" />}
      count={hasItems ? items.length : undefined}
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
            Add faults, work orders, equipment, or documents to hand over.
          </p>
          {onAddItem && (
            <GhostButton onClick={onAddItem} icon={<Plus className="h-4 w-4" />}>
              Add Item
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="space-y-4">
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
