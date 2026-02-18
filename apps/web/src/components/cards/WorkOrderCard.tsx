/**
 * WorkOrderCard Component
 *
 * Full-screen entity view with enriched data:
 * - Notes, Parts, Checklist, Audit History
 * - Empty state CTAs for missing data
 * - Modal flows for data entry
 * - Tokenized styling (no hardcoded values)
 */

'use client';

import { useState } from 'react';
import {
  Wrench,
  Clock,
  User,
  CheckCircle2,
  MessageSquare,
  Package,
  ClipboardList,
  History,
  Plus,
  ChevronRight,
  AlertCircle,
  StickyNote,
  Archive,
  UserPlus,
} from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { Button } from '@/components/ui/button';
import { AddNoteModal } from '@/components/modals/AddNoteModal';
import { LinkPartsToWorkOrderModal } from '@/components/modals/LinkPartsToWorkOrderModal';
import { AddChecklistItemModal } from '@/components/modals/AddChecklistItemModal';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

interface WorkOrderNote {
  id: string;
  note_text: string;
  note_type?: string;
  created_by?: string;
  created_at: string;
}

interface WorkOrderPart {
  id: string;
  part_id: string;
  quantity: number;
  notes?: string;
  created_at: string;
  pms_parts?: {
    id: string;
    name: string;
    part_number?: string;
    location?: string;
  };
}

interface WorkOrderChecklistItem {
  id: string;
  title: string;
  description?: string;
  is_completed: boolean;
  completed_by?: string;
  completed_at?: string;
  sequence?: number;
}

interface WorkOrderAuditEntry {
  id: string;
  action: string;
  old_values?: Record<string, unknown>;
  new_values?: Record<string, unknown>;
  user_id?: string;
  created_at: string;
}

interface WorkOrderCardProps {
  workOrder: {
    id: string;
    title: string;
    description: string;
    status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
    priority: 'low' | 'medium' | 'high' | 'urgent';
    equipment_id?: string;
    equipment_name?: string;
    assigned_to?: string;
    assigned_to_name?: string;
    created_at: string;
    completed_at?: string;
    due_date?: string;
    // Enriched data
    notes?: WorkOrderNote[];
    parts?: WorkOrderPart[];
    checklist?: WorkOrderChecklistItem[];
    audit_history?: WorkOrderAuditEntry[];
    notes_count?: number;
    parts_count?: number;
    checklist_count?: number;
    checklist_completed?: number;
  };
  actions?: MicroAction[];
}

// ============================================================================
// EMPTY STATE CTA COMPONENT
// ============================================================================

interface EmptyStateCTAProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionLabel: string;
  action: MicroAction;
  context: Record<string, unknown>;
}

function EmptyStateCTA({ icon, title, description, actionLabel, action, context }: EmptyStateCTAProps) {
  return (
    <div className="flex flex-col items-center justify-center py-ds-6 px-ds-4 text-center">
      <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-ds-3">
        {icon}
      </div>
      <p className="text-txt-primary font-medium mb-ds-1">
        {title}
      </p>
      <p className="text-txt-tertiary text-celeste-sm mb-ds-4">
        {description}
      </p>
      <ActionButton
        action={action}
        context={context}
        variant="secondary"
        size="sm"
        showIcon={true}
        label={actionLabel}
      />
    </div>
  );
}

// ============================================================================
// SECTION HEADER COMPONENT
// ============================================================================

interface SectionHeaderProps {
  icon: React.ReactNode;
  title: string;
  count?: number;
  action?: MicroAction;
  actionLabel?: string;
  context?: Record<string, unknown>;
}

function SectionHeader({ icon, title, count, action, actionLabel, context }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-ds-3">
      <div className="flex items-center gap-ds-2">
        {icon}
        <h3 className="text-txt-primary font-semibold">
          {title}
        </h3>
        {count !== undefined && count > 0 && (
          <span className="text-txt-tertiary text-celeste-sm">
            ({count})
          </span>
        )}
      </div>
      {action && actionLabel && context && (
        <ActionButton
          action={action}
          context={context}
          variant="ghost"
          size="sm"
          showIcon={true}
          label={actionLabel}
        />
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function WorkOrderCard({ workOrder, actions = [] }: WorkOrderCardProps) {
  // Modal state
  const [showAddNoteModal, setShowAddNoteModal] = useState(false);
  const [showAddPartModal, setShowAddPartModal] = useState(false);
  const [showAddChecklistModal, setShowAddChecklistModal] = useState(false);

  // Get status styling
  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          bg: 'bg-status-success-bg',
          text: 'text-status-success',
          icon: <CheckCircle2 className="h-5 w-5 text-status-success" />,
          label: 'Completed',
        };
      case 'in_progress':
        return {
          bg: 'bg-brand-muted',
          text: 'text-brand-interactive',
          icon: <Clock className="h-5 w-5 text-brand-interactive" />,
          label: 'In Progress',
        };
      case 'cancelled':
        return {
          bg: 'bg-txt-tertiary/10',
          text: 'text-txt-tertiary',
          icon: <AlertCircle className="h-5 w-5 text-txt-tertiary" />,
          label: 'Cancelled',
        };
      default:
        return {
          bg: 'bg-status-warning-bg',
          text: 'text-status-warning',
          icon: <Wrench className="h-5 w-5 text-status-warning" />,
          label: 'Pending',
        };
    }
  };

  // Get priority styling
  const getPriorityStyles = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return { bg: 'bg-status-critical-bg', text: 'text-status-critical', label: 'Urgent' };
      case 'high':
        return { bg: 'bg-status-warning-bg', text: 'text-status-warning', label: 'High' };
      case 'medium':
        return { bg: 'bg-status-warning-bg', text: 'text-status-warning', label: 'Medium' };
      default:
        return { bg: 'bg-txt-tertiary/10', text: 'text-txt-tertiary', label: 'Low' };
    }
  };

  const status = getStatusStyles(workOrder.status);
  const priority = getPriorityStyles(workOrder.priority);

  const notes = workOrder.notes || [];
  const parts = workOrder.parts || [];
  const checklist = workOrder.checklist || [];
  const auditHistory = workOrder.audit_history || [];

  const actionContext = {
    work_order_id: workOrder.id,
    equipment_id: workOrder.equipment_id,
  };

  return (
    <div className="flex flex-col gap-ds-6">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        {/* Status & Priority Row */}
        <div className="flex items-center gap-ds-2 mb-ds-4">
          <span className={cn(
            'inline-flex items-center gap-ds-1 px-ds-3 py-ds-1 rounded-sm text-celeste-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center px-ds-3 py-ds-1 rounded-sm text-celeste-sm font-medium',
            priority.bg, priority.text
          )}>
            {priority.label}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-txt-primary mb-ds-2">
          {workOrder.title}
        </h1>

        {/* Equipment */}
        {workOrder.equipment_name && (
          <p className="text-txt-secondary mb-ds-4">
            {workOrder.equipment_name}
          </p>
        )}

        {/* Description */}
        {workOrder.description && (
          <p className="text-txt-primary mb-ds-4">
            {workOrder.description}
          </p>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-ds-4 pt-ds-4 border-t border-surface-border">
          {workOrder.assigned_to_name && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">Assigned To</p>
              <div className="flex items-center gap-ds-1">
                <User className="h-4 w-4 text-txt-secondary" />
                <span className="text-txt-primary">{workOrder.assigned_to_name}</span>
              </div>
            </div>
          )}
          <div>
            <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">Created</p>
            <span className="text-txt-primary">{formatDate(workOrder.created_at)}</span>
          </div>
          {workOrder.due_date && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">Due Date</p>
              <span className="text-status-warning">{formatDate(workOrder.due_date)}</span>
            </div>
          )}
          {workOrder.completed_at && (
            <div>
              <p className="text-txt-tertiary text-celeste-xs uppercase tracking-wide mb-1">Completed</p>
              <span className="text-status-success">{formatDate(workOrder.completed_at)}</span>
            </div>
          )}
        </div>

        {/* Primary Actions */}
        <div className="flex flex-wrap items-center gap-ds-2 mt-ds-4 pt-ds-4 border-t border-surface-border">
          {actions.slice(0, 4).map((action) => (
            <ActionButton
              key={action}
              action={action}
              context={actionContext}
              variant="secondary"
              size="sm"
              showIcon={true}
            />
          ))}
          {actions.length > 4 && (
            <button className="h-8 px-ds-2 text-celeste-sm text-txt-tertiary hover:text-txt-primary transition-colors">
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
          {/* Reassign action - available for non-archived work orders */}
          {workOrder.status !== 'cancelled' && (
            <ActionButton
              action="reassign_work_order"
              context={actionContext}
              variant="ghost"
              size="sm"
              showIcon={true}
            />
          )}
          {/* Archive action - only for completed or cancelled work orders */}
          {(workOrder.status === 'completed' || workOrder.status === 'cancelled') && (
            <ActionButton
              action="archive_work_order"
              context={actionContext}
              variant="ghost"
              size="sm"
              showIcon={true}
            />
          )}
        </div>
      </div>

      {/* ================================================================
          NOTES SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center justify-between mb-ds-3">
          <div className="flex items-center gap-ds-2">
            <MessageSquare className="h-5 w-5 text-txt-secondary" />
            <h3 className="text-txt-primary font-semibold">Notes</h3>
            {notes.length > 0 && (
              <span className="text-txt-tertiary text-celeste-sm">({notes.length})</span>
            )}
          </div>
          {notes.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAddNoteModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <StickyNote className="h-3.5 w-3.5" />
              <span>Add Note</span>
            </Button>
          )}
        </div>

        {notes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-ds-6 px-ds-4 text-center">
            <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-ds-3">
              <MessageSquare className="h-6 w-6 text-txt-tertiary" />
            </div>
            <p className="text-txt-primary font-medium mb-ds-1">
              No notes yet
            </p>
            <p className="text-txt-tertiary text-celeste-sm mb-ds-4">
              Add notes to track progress, issues, or important observations.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAddNoteModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <StickyNote className="h-3.5 w-3.5" />
              <span>Add Note</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-ds-3">
            {notes.map((note) => (
              <div
                key={note.id}
                className="p-ds-4 bg-surface-elevated rounded-sm border border-surface-border"
              >
                <p className="text-txt-primary whitespace-pre-wrap">
                  {note.note_text}
                </p>
                <div className="flex items-center gap-ds-2 mt-ds-2 text-celeste-xs text-txt-tertiary">
                  {note.created_by && <span>{note.created_by}</span>}
                  {note.created_by && note.created_at && <span>•</span>}
                  {note.created_at && <span>{formatDate(note.created_at)}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================
          PARTS SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center justify-between mb-ds-3">
          <div className="flex items-center gap-ds-2">
            <Package className="h-5 w-5 text-txt-secondary" />
            <h3 className="text-txt-primary font-semibold">Parts Used</h3>
            {parts.length > 0 && (
              <span className="text-txt-tertiary text-celeste-sm">({parts.length})</span>
            )}
          </div>
          {parts.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAddPartModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <Package className="h-3.5 w-3.5" />
              <span>Add Part</span>
            </Button>
          )}
        </div>

        {parts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-ds-6 px-ds-4 text-center">
            <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-ds-3">
              <Package className="h-6 w-6 text-txt-tertiary" />
            </div>
            <p className="text-txt-primary font-medium mb-ds-1">
              No parts linked
            </p>
            <p className="text-txt-tertiary text-celeste-sm mb-ds-4">
              Track parts used for this work order to maintain accurate inventory.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAddPartModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <Package className="h-3.5 w-3.5" />
              <span>Add Part</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-ds-2">
            {parts.map((part) => (
              <div
                key={part.id}
                className="flex items-center justify-between p-ds-3 bg-surface-elevated rounded-sm border border-surface-border"
              >
                <div className="flex-1">
                  <p className="text-txt-primary font-medium">
                    {part.pms_parts?.name || 'Unknown Part'}
                  </p>
                  <div className="flex items-center gap-ds-2 text-celeste-xs text-txt-tertiary">
                    {part.pms_parts?.part_number && (
                      <span>#{part.pms_parts.part_number}</span>
                    )}
                    {part.pms_parts?.location && (
                      <>
                        <span>•</span>
                        <span>{part.pms_parts.location}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-txt-primary font-medium">
                    Qty: {part.quantity}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================
          CHECKLIST SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center justify-between mb-ds-3">
          <div className="flex items-center gap-ds-2">
            <ClipboardList className="h-5 w-5 text-txt-secondary" />
            <h3 className="text-txt-primary font-semibold">Checklist</h3>
            {checklist.length > 0 && (
              <span className="text-txt-tertiary text-celeste-sm">({checklist.length})</span>
            )}
          </div>
          {checklist.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAddChecklistModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              <span>Add Item</span>
            </Button>
          )}
        </div>

        {checklist.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-ds-6 px-ds-4 text-center">
            <div className="w-12 h-12 rounded-md bg-surface-hover flex items-center justify-center mb-ds-3">
              <ClipboardList className="h-6 w-6 text-txt-tertiary" />
            </div>
            <p className="text-txt-primary font-medium mb-ds-1">
              No checklist items
            </p>
            <p className="text-txt-tertiary text-celeste-sm mb-ds-4">
              Add checklist items to ensure all steps are completed.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAddChecklistModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              <span>Add Checklist Item</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-ds-2">
            {/* Progress bar */}
            {checklist.length > 0 && (
              <div className="mb-ds-4">
                <div className="flex items-center justify-between text-celeste-sm mb-ds-1">
                  <span className="text-txt-tertiary">Progress</span>
                  <span className="text-txt-primary">
                    {checklist.filter(c => c.is_completed).length} / {checklist.length}
                  </span>
                </div>
                <div className="h-2 bg-surface-hover rounded-full overflow-hidden">
                  <div
                    className="h-full bg-status-success transition-all duration-200"
                    style={{
                      width: `${(checklist.filter(c => c.is_completed).length / checklist.length) * 100}%`
                    }}
                  />
                </div>
              </div>
            )}

            {checklist.map((item) => (
              <div
                key={item.id}
                className={cn(
                  'flex items-start gap-ds-3 p-ds-3 rounded-sm border',
                  item.is_completed
                    ? 'bg-status-success/5 border-status-success/20'
                    : 'bg-surface-elevated border-surface-border'
                )}
              >
                <div className={cn(
                  'flex-shrink-0 w-5 h-5 rounded-sm border-2 flex items-center justify-center mt-0.5',
                  item.is_completed
                    ? 'bg-status-success border-status-success'
                    : 'border-surface-border'
                )}>
                  {item.is_completed && (
                    <CheckCircle2 className="h-3 w-3 text-white" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={cn(
                    'text-txt-primary',
                    item.is_completed && 'line-through opacity-70'
                  )}>
                    {item.title}
                  </p>
                  {item.description && (
                    <p className="text-celeste-sm text-txt-tertiary mt-1">
                      {item.description}
                    </p>
                  )}
                  {item.completed_at && (
                    <p className="text-celeste-xs text-txt-tertiary mt-1">
                      Completed {formatDate(item.completed_at)}
                      {item.completed_by && ` by ${item.completed_by}`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ================================================================
          AUDIT HISTORY SECTION
          ================================================================ */}
      <div className="bg-surface-primary rounded-md p-ds-6 border border-surface-border">
        <div className="flex items-center gap-ds-2 mb-ds-3">
          <History className="h-5 w-5 text-txt-secondary" />
          <h3 className="text-txt-primary font-semibold">Activity</h3>
          {auditHistory.length > 0 && (
            <span className="text-txt-tertiary text-celeste-sm">({auditHistory.length})</span>
          )}
        </div>

        {auditHistory.length === 0 ? (
          <div className="text-center py-ds-6">
            <History className="h-8 w-8 text-txt-tertiary mx-auto mb-ds-2" />
            <p className="text-txt-tertiary">No activity yet</p>
          </div>
        ) : (
          <div className="space-y-ds-3">
            {auditHistory.slice(0, 10).map((entry) => {
              // Convert action to human-readable label
              const actionLabels: Record<string, string> = {
                'add_work_order_note': 'Note added',
                'add_parts_to_work_order': 'Part linked',
                'add_checklist_note': 'Checklist item added',
                'mark_work_order_complete': 'Marked complete',
                'complete_work_order': 'Completed',
                'assign_work_order': 'Assigned',
                'update_work_order': 'Updated',
                'create_work_order': 'Created',
              };
              const label = actionLabels[entry.action] || entry.action.replace(/_/g, ' ');

              // Extract summary from new_values
              let summary = '';
              if (entry.new_values) {
                if (entry.new_values.note_text) {
                  summary = String(entry.new_values.note_text);
                } else if (entry.new_values.title) {
                  summary = String(entry.new_values.title);
                } else if (entry.new_values.part_name) {
                  summary = String(entry.new_values.part_name);
                }
              }

              return (
                <div
                  key={entry.id}
                  className="p-ds-3 bg-surface-elevated rounded-sm border border-surface-border"
                >
                  <div className="flex items-start justify-between gap-ds-2">
                    <p className="text-txt-primary font-medium text-celeste-sm">
                      {label}
                    </p>
                    <span className="text-celeste-xs text-txt-tertiary whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  {summary && (
                    <p className="text-celeste-sm text-txt-secondary mt-1 line-clamp-2">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
            {auditHistory.length > 10 && (
              <p className="text-celeste-xs text-txt-tertiary text-center pt-2">
                +{auditHistory.length - 10} more activities
              </p>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          MODALS
          ================================================================ */}
      <AddNoteModal
        open={showAddNoteModal}
        onOpenChange={setShowAddNoteModal}
        context={{
          entity_type: 'work_order',
          entity_id: workOrder.id,
          entity_title: workOrder.title,
          entity_subtitle: workOrder.equipment_name,
        }}
        onSuccess={() => {
          // Optionally trigger a refresh here
        }}
      />

      <LinkPartsToWorkOrderModal
        open={showAddPartModal}
        onOpenChange={setShowAddPartModal}
        context={{
          work_order_id: workOrder.id,
          work_order_title: workOrder.title,
        }}
        onSuccess={() => {
          // Optionally trigger a refresh here
        }}
      />

      <AddChecklistItemModal
        open={showAddChecklistModal}
        onOpenChange={setShowAddChecklistModal}
        context={{
          work_order_id: workOrder.id,
          work_order_title: workOrder.title,
        }}
        onSuccess={() => {
          // Optionally trigger a refresh here
        }}
      />
    </div>
  );
}
