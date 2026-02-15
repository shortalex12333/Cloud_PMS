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
    <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-6)] px-[var(--celeste-spacing-4)] text-center">
      <div className="w-12 h-12 rounded-[var(--celeste-border-radius-md)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-3)]">
        {icon}
      </div>
      <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
        {title}
      </p>
      <p className="text-[var(--celeste-text-muted)] text-sm mb-[var(--celeste-spacing-4)]">
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
    <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
      <div className="flex items-center gap-[var(--celeste-spacing-2)]">
        {icon}
        <h3 className="text-[var(--celeste-text-primary)] font-semibold">
          {title}
        </h3>
        {count !== undefined && count > 0 && (
          <span className="text-[var(--celeste-text-muted)] text-sm">
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
          bg: 'bg-[var(--celeste-green)]/10',
          text: 'text-[var(--celeste-green)]',
          icon: <CheckCircle2 className="h-5 w-5 text-[var(--celeste-green)]" />,
          label: 'Completed',
        };
      case 'in_progress':
        return {
          bg: 'bg-[var(--celeste-accent)]/10',
          text: 'text-[var(--celeste-accent)]',
          icon: <Clock className="h-5 w-5 text-[var(--celeste-accent)]" />,
          label: 'In Progress',
        };
      case 'cancelled':
        return {
          bg: 'bg-[var(--celeste-text-muted)]/10',
          text: 'text-[var(--celeste-text-muted)]',
          icon: <AlertCircle className="h-5 w-5 text-[var(--celeste-text-muted)]" />,
          label: 'Cancelled',
        };
      default:
        return {
          bg: 'bg-[var(--celeste-orange)]/10',
          text: 'text-[var(--celeste-orange)]',
          icon: <Wrench className="h-5 w-5 text-[var(--celeste-orange)]" />,
          label: 'Pending',
        };
    }
  };

  // Get priority styling
  const getPriorityStyles = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return { bg: 'bg-[var(--celeste-warning)]/10', text: 'text-[var(--celeste-warning)]', label: 'Urgent' };
      case 'high':
        return { bg: 'bg-[var(--celeste-orange)]/10', text: 'text-[var(--celeste-orange)]', label: 'High' };
      case 'medium':
        return { bg: 'bg-[var(--celeste-yellow)]/10', text: 'text-[var(--celeste-yellow)]', label: 'Medium' };
      default:
        return { bg: 'bg-[var(--celeste-text-muted)]/10', text: 'text-[var(--celeste-text-muted)]', label: 'Low' };
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
    <div className="flex flex-col gap-[var(--celeste-spacing-6)]">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        {/* Status & Priority Row */}
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-4)]">
          <span className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-1)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>
          <span className={cn(
            'inline-flex items-center px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            priority.bg, priority.text
          )}>
            {priority.label}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-[var(--celeste-text-title)] mb-[var(--celeste-spacing-2)]">
          {workOrder.title}
        </h1>

        {/* Equipment */}
        {workOrder.equipment_name && (
          <p className="text-[var(--celeste-text-secondary)] mb-[var(--celeste-spacing-4)]">
            {workOrder.equipment_name}
          </p>
        )}

        {/* Description */}
        {workOrder.description && (
          <p className="text-[var(--celeste-text-primary)] mb-[var(--celeste-spacing-4)]">
            {workOrder.description}
          </p>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
          {workOrder.assigned_to_name && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Assigned To</p>
              <div className="flex items-center gap-[var(--celeste-spacing-1)]">
                <User className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
                <span className="text-[var(--celeste-text-primary)]">{workOrder.assigned_to_name}</span>
              </div>
            </div>
          )}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Created</p>
            <span className="text-[var(--celeste-text-primary)]">{formatDate(workOrder.created_at)}</span>
          </div>
          {workOrder.due_date && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Due Date</p>
              <span className="text-[var(--celeste-orange)]">{formatDate(workOrder.due_date)}</span>
            </div>
          )}
          {workOrder.completed_at && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Completed</p>
              <span className="text-[var(--celeste-green)]">{formatDate(workOrder.completed_at)}</span>
            </div>
          )}
        </div>

        {/* Primary Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-[var(--celeste-spacing-2)] mt-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
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
              <button className="h-8 px-[var(--celeste-spacing-2)] text-sm text-[var(--celeste-text-muted)] hover:text-[var(--celeste-text-primary)] transition-colors">
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          NOTES SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <MessageSquare className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Notes</h3>
            {notes.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({notes.length})</span>
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
          <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-6)] px-[var(--celeste-spacing-4)] text-center">
            <div className="w-12 h-12 rounded-[var(--celeste-border-radius-md)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-3)]">
              <MessageSquare className="h-6 w-6 text-[var(--celeste-text-muted)]" />
            </div>
            <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
              No notes yet
            </p>
            <p className="text-[var(--celeste-text-muted)] text-sm mb-[var(--celeste-spacing-4)]">
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
          <div className="space-y-[var(--celeste-spacing-3)]">
            {notes.map((note) => (
              <div
                key={note.id}
                className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
              >
                <p className="text-[var(--celeste-text-primary)] whitespace-pre-wrap">
                  {note.note_text}
                </p>
                <div className="flex items-center gap-[var(--celeste-spacing-2)] mt-[var(--celeste-spacing-2)] text-xs text-[var(--celeste-text-muted)]">
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
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <Package className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Parts Used</h3>
            {parts.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({parts.length})</span>
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
          <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-6)] px-[var(--celeste-spacing-4)] text-center">
            <div className="w-12 h-12 rounded-[var(--celeste-border-radius-md)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-3)]">
              <Package className="h-6 w-6 text-[var(--celeste-text-muted)]" />
            </div>
            <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
              No parts linked
            </p>
            <p className="text-[var(--celeste-text-muted)] text-sm mb-[var(--celeste-spacing-4)]">
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
          <div className="space-y-[var(--celeste-spacing-2)]">
            {parts.map((part) => (
              <div
                key={part.id}
                className="flex items-center justify-between p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
              >
                <div className="flex-1">
                  <p className="text-[var(--celeste-text-primary)] font-medium">
                    {part.pms_parts?.name || 'Unknown Part'}
                  </p>
                  <div className="flex items-center gap-[var(--celeste-spacing-2)] text-xs text-[var(--celeste-text-muted)]">
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
                  <span className="text-[var(--celeste-text-primary)] font-medium">
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
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <ClipboardList className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Checklist</h3>
            {checklist.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({checklist.length})</span>
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
          <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-6)] px-[var(--celeste-spacing-4)] text-center">
            <div className="w-12 h-12 rounded-[var(--celeste-border-radius-md)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-3)]">
              <ClipboardList className="h-6 w-6 text-[var(--celeste-text-muted)]" />
            </div>
            <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
              No checklist items
            </p>
            <p className="text-[var(--celeste-text-muted)] text-sm mb-[var(--celeste-spacing-4)]">
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
          <div className="space-y-[var(--celeste-spacing-2)]">
            {/* Progress bar */}
            {checklist.length > 0 && (
              <div className="mb-[var(--celeste-spacing-4)]">
                <div className="flex items-center justify-between text-sm mb-[var(--celeste-spacing-1)]">
                  <span className="text-[var(--celeste-text-muted)]">Progress</span>
                  <span className="text-[var(--celeste-text-primary)]">
                    {checklist.filter(c => c.is_completed).length} / {checklist.length}
                  </span>
                </div>
                <div className="h-2 bg-[var(--celeste-bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--celeste-green)] transition-all duration-[var(--celeste-duration-normal)]"
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
                  'flex items-start gap-[var(--celeste-spacing-3)] p-[var(--celeste-spacing-3)] rounded-[var(--celeste-border-radius-sm)] border',
                  item.is_completed
                    ? 'bg-[var(--celeste-green)]/5 border-[var(--celeste-green)]/20'
                    : 'bg-[var(--celeste-panel)] border-[var(--celeste-border-subtle)]'
                )}
              >
                <div className={cn(
                  'flex-shrink-0 w-5 h-5 rounded-[var(--celeste-border-radius-sm)] border-2 flex items-center justify-center mt-0.5',
                  item.is_completed
                    ? 'bg-[var(--celeste-green)] border-[var(--celeste-green)]'
                    : 'border-[var(--celeste-border)]'
                )}>
                  {item.is_completed && (
                    <CheckCircle2 className="h-3 w-3 text-white" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={cn(
                    'text-[var(--celeste-text-primary)]',
                    item.is_completed && 'line-through opacity-70'
                  )}>
                    {item.title}
                  </p>
                  {item.description && (
                    <p className="text-sm text-[var(--celeste-text-muted)] mt-1">
                      {item.description}
                    </p>
                  )}
                  {item.completed_at && (
                    <p className="text-xs text-[var(--celeste-text-muted)] mt-1">
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
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
          <History className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
          <h3 className="text-[var(--celeste-text-primary)] font-semibold">Activity</h3>
          {auditHistory.length > 0 && (
            <span className="text-[var(--celeste-text-muted)] text-sm">({auditHistory.length})</span>
          )}
        </div>

        {auditHistory.length === 0 ? (
          <div className="text-center py-[var(--celeste-spacing-6)]">
            <History className="h-8 w-8 text-[var(--celeste-text-muted)] mx-auto mb-[var(--celeste-spacing-2)]" />
            <p className="text-[var(--celeste-text-muted)]">No activity yet</p>
          </div>
        ) : (
          <div className="space-y-[var(--celeste-spacing-3)]">
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
                  summary = entry.new_values.note_text;
                } else if (entry.new_values.title) {
                  summary = entry.new_values.title;
                } else if (entry.new_values.part_name) {
                  summary = entry.new_values.part_name;
                }
              }

              return (
                <div
                  key={entry.id}
                  className="p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
                >
                  <div className="flex items-start justify-between gap-[var(--celeste-spacing-2)]">
                    <p className="text-[var(--celeste-text-primary)] font-medium text-sm">
                      {label}
                    </p>
                    <span className="text-xs text-[var(--celeste-text-muted)] whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  {summary && (
                    <p className="text-sm text-[var(--celeste-text-secondary)] mt-1 line-clamp-2">
                      {summary}
                    </p>
                  )}
                </div>
              );
            })}
            {auditHistory.length > 10 && (
              <p className="text-xs text-[var(--celeste-text-muted)] text-center pt-2">
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
