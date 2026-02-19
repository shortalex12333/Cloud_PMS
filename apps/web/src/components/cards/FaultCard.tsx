/**
 * FaultCard Component
 *
 * Apple-inspired design with:
 * - Status dot indicator (not pill badge)
 * - 12px card radius
 * - Subtle shadows
 * - Precise typography
 *
 * Phase 12: Uses server-driven decisions via useActionDecisions hook.
 * UI renders decisions - UI does NOT make decisions (E020).
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Wrench, ChevronRight, Stethoscope, Book, History, Package, StickyNote, Camera, AlertCircle, CheckCircle2, Edit, ClipboardList } from 'lucide-react';
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';
import { DiagnoseFaultModal } from '@/components/modals/DiagnoseFaultModal';
import { ShowManualSectionModal } from '@/components/modals/ShowManualSectionModal';
import { FaultHistoryModal } from '@/components/modals/FaultHistoryModal';
import { SuggestPartsModal } from '@/components/modals/SuggestPartsModal';
import { AddNoteModal } from '@/components/modals/AddNoteModal';
import { AddPhotoModal } from '@/components/modals/AddPhotoModal';
import { AcknowledgeFaultModal } from '@/components/modals/AcknowledgeFaultModal';
import { EditFaultDetailsModal } from '@/components/modals/EditFaultDetailsModal';
import { AddToHandoverQuickModal } from '@/components/modals/AddToHandoverQuickModal';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { useActionDecisions } from '@/lib/microactions/hooks/useActionDecisions';
import { SectionContainer } from '@/components/ui/SectionContainer';
import type { MicroAction } from '@/types/actions';

/**
 * Fault note type definition for display in FaultCard
 * Maps to pms_notes table with entity_type='fault'
 */
export interface FaultNote {
  id: string;
  /** Note content text */
  text: string;
  /** Note category: observation, inspection, handover, defect, maintenance, general */
  note_type: 'observation' | 'inspection' | 'handover' | 'defect' | 'maintenance' | 'general';
  /** ISO timestamp of creation */
  created_at: string;
  /** Display name of the author */
  author_name?: string;
}

interface FaultCardProps {
  fault: {
    id: string;
    title: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    equipment_id: string;
    equipment_name: string;
    reported_at: string;
    reporter: string;
    // Optional AI diagnosis for trigger conditions
    ai_diagnosis?: {
      is_known: boolean;
      diagnosis?: string;
      confidence?: number;
    };
    // Whether a work order already exists for this fault
    has_work_order?: boolean;
    // Fault notes for display in NotesSection
    notes?: FaultNote[];
  };
  actions?: MicroAction[];
  // User role for permission checks
  userRole?: string;
  // Callback when auto-run action executes
  onAutoRun?: (actionName: string, result: unknown) => void;
  // Callback to refresh data after adding a note
  onRefresh?: () => void;
}

// =============================================================================
// FAULT NOTES SECTION COMPONENT
// =============================================================================

/**
 * Format timestamp for note display
 * - Today: "Today at 14:32"
 * - Within 7 days: "Yesterday", "2 days ago"
 * - Older: "Jan 23, 2026"
 */
function formatNoteTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `Today at ${hh}:${mm}`;
  }

  if (diffDays < 7) {
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays} days ago`;
  }

  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Get note type styling based on category
 * Uses --celeste-* design tokens for consistent theming
 */
function getNoteTypeStyles(noteType: FaultNote['note_type']): {
  bgClass: string;
  borderClass: string;
  labelClass: string;
  label: string;
} {
  switch (noteType) {
    case 'defect':
    case 'inspection':
      return {
        bgClass: 'bg-red-50 dark:bg-red-900/10',
        borderClass: 'border-l-red-400 dark:border-l-red-500',
        labelClass: 'text-red-600 dark:text-red-400',
        label: noteType === 'defect' ? 'Defect' : 'Inspection',
      };
    case 'maintenance':
      return {
        bgClass: 'bg-amber-50 dark:bg-amber-900/10',
        borderClass: 'border-l-amber-400 dark:border-l-amber-500',
        labelClass: 'text-amber-600 dark:text-amber-400',
        label: 'Update',
      };
    case 'handover':
      return {
        bgClass: 'bg-blue-50 dark:bg-blue-900/10',
        borderClass: 'border-l-blue-400 dark:border-l-blue-500',
        labelClass: 'text-blue-600 dark:text-blue-400',
        label: 'Handover',
      };
    case 'observation':
    case 'general':
    default:
      return {
        bgClass: 'bg-zinc-50 dark:bg-zinc-800/50',
        borderClass: 'border-l-zinc-300 dark:border-l-zinc-600',
        labelClass: 'text-zinc-500 dark:text-zinc-400',
        label: noteType === 'observation' ? 'Observation' : 'Note',
      };
  }
}

interface FaultNotesSectionProps {
  notes: FaultNote[];
  onAddNote: () => void;
  canAddNote: boolean;
}

/**
 * FaultNotesSection - Compact notes display for FaultCard
 *
 * Uses SectionContainer with "Add Note" action button.
 * Notes are styled by note_type with left border color coding.
 * Shows most recent 3 notes with expand option.
 */
function FaultNotesSection({ notes, onAddNote, canAddNote }: FaultNotesSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Sort notes chronologically (oldest first for display, newest at bottom)
  const sortedNotes = [...notes].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  // Show first 3 notes unless expanded
  const visibleNotes = isExpanded ? sortedNotes : sortedNotes.slice(-3);
  const hasMoreNotes = notes.length > 3;

  if (notes.length === 0 && !canAddNote) {
    return null; // Don't render empty section if user can't add notes
  }

  return (
    <SectionContainer
      title="Notes"
      icon={<StickyNote className="h-4 w-4" />}
      count={notes.length}
      action={canAddNote ? { label: '+ Add Note', onClick: onAddNote } : undefined}
    >
      {notes.length === 0 ? (
        <p className="text-celeste-sm text-zinc-500 dark:text-zinc-400 py-2">
          No notes yet. Add the first note to document progress.
        </p>
      ) : (
        <div className="space-y-2">
          {/* Show expand button if more than 3 notes */}
          {hasMoreNotes && !isExpanded && (
            <button
              onClick={() => setIsExpanded(true)}
              className="text-celeste-xs text-brand-interactive hover:text-brand-hover transition-colors mb-2"
            >
              Show {notes.length - 3} earlier notes...
            </button>
          )}

          {visibleNotes.map((note) => {
            const styles = getNoteTypeStyles(note.note_type);
            return (
              <div
                key={note.id}
                className={cn(
                  'rounded-md border-l-2 px-3 py-2',
                  styles.bgClass,
                  styles.borderClass
                )}
              >
                {/* Note header: author, type badge, timestamp */}
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-celeste-xs font-medium text-zinc-900 dark:text-zinc-100">
                      {note.author_name || 'Unknown'}
                    </span>
                    <span className={cn('text-overline', styles.labelClass)}>
                      {styles.label}
                    </span>
                  </div>
                  <span className="text-overline text-zinc-400 dark:text-zinc-500">
                    {formatNoteTimestamp(note.created_at)}
                  </span>
                </div>

                {/* Note content */}
                <p className="text-celeste-sm text-zinc-700 dark:text-zinc-300 leading-relaxed line-clamp-3">
                  {note.text}
                </p>
              </div>
            );
          })}

          {/* Collapse button when expanded */}
          {hasMoreNotes && isExpanded && (
            <button
              onClick={() => setIsExpanded(false)}
              className="text-celeste-xs text-brand-interactive hover:text-brand-hover transition-colors mt-1"
            >
              Show less
            </button>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

// =============================================================================
// FAULT CARD COMPONENT
// =============================================================================

export function FaultCard({ fault, actions = [], userRole, onAutoRun, onRefresh }: FaultCardProps) {
  const [showCreateWO, setShowCreateWO] = useState(false);
  const [showDiagnose, setShowDiagnose] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showSuggestParts, setShowSuggestParts] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [showAddPhoto, setShowAddPhoto] = useState(false);
  const [showAcknowledge, setShowAcknowledge] = useState(false);
  const [showUpdate, setShowUpdate] = useState(false);
  const [showHandover, setShowHandover] = useState(false);

  // Track if auto-run has been triggered
  const hasAutoRun = useRef(false);

  // Phase 12: Server-driven decisions via useActionDecisions hook
  // UI renders decisions - UI does NOT make decisions (E020)
  const {
    isAllowed,
    getDecision,
    getDisabledReason,
    isLoading: decisionsLoading,
    error: decisionsError,
  } = useActionDecisions({
    detected_intents: ['diagnose', 'view', 'document'],
    entities: [
      {
        type: 'fault',
        id: fault.id,
        status: 'reported', // TODO: map from actual fault status
        has_work_order: fault.has_work_order,
      },
      {
        type: 'equipment',
        id: fault.equipment_id,
        name: fault.equipment_name,
        has_manual: true, // Assume manual exists for now
      },
    ],
  });

  // FAIL-CLOSED: If decisions endpoint fails, show NO actions
  // This prevents the UI from making decisions when server is unavailable
  const failClosed = decisionsError !== null;

  // Check which actions should be visible based on SERVER decisions
  const showDiagnoseButton = !failClosed && isAllowed('diagnose_fault');
  const showManualButton = !failClosed && isAllowed('show_manual_section');
  const showHistoryButton = !failClosed && isAllowed('view_fault_history');
  const showSuggestPartsButton = !failClosed && isAllowed('suggest_parts');
  const showAddNoteButton = !failClosed && isAllowed('add_fault_note');
  const showAddPhotoButton = !failClosed && isAllowed('add_fault_photo');
  const showCreateWOButton = !failClosed && isAllowed('create_work_order_from_fault');
  const showAcknowledgeButton = !failClosed && isAllowed('acknowledge_fault');
  const showUpdateButton = !failClosed && isAllowed('update_fault');
  const showHandoverButton = !failClosed && isAllowed('add_to_handover');

  // Auto-run diagnose_fault when card mounts and decisions are loaded
  // Only if action is allowed by server and diagnose_fault has auto_run flag
  const diagnoseDecision = getDecision('diagnose_fault');
  useEffect(() => {
    // Auto-run only if: decisions loaded, allowed, and hasn't run yet
    if (!hasAutoRun.current && !decisionsLoading && showDiagnoseButton) {
      hasAutoRun.current = true;
      // Open diagnose modal automatically
      setShowDiagnose(true);
    }
  }, [decisionsLoading, showDiagnoseButton]);

  // Get severity styling using semantic status-pill classes
  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          dot: 'status-dot status-dot-critical',
          pillClass: 'status-pill status-pill-critical',
          label: 'Critical',
        };
      case 'high':
        return {
          dot: 'status-dot status-dot-warning',
          pillClass: 'status-pill status-pill-warning',
          label: 'High',
        };
      case 'medium':
        return {
          dot: 'status-dot status-dot-warning',
          pillClass: 'status-pill status-pill-warning',
          label: 'Medium',
        };
      default:
        return {
          dot: 'status-dot status-dot-neutral',
          pillClass: 'status-pill status-pill-neutral',
          label: 'Low',
        };
    }
  };

  const severity = getSeverityStyles(fault.severity);

  return (
    <>
      <div className="celeste-card p-4 hover:shadow-[var(--shadow-md)] transition-shadow duration-normal">
        <div className="flex items-start gap-3">
          {/* Severity Indicator - Minimal dot + icon */}
          <div className="flex flex-col items-center gap-2 pt-0.5">
            <span className={severity.dot} />
            <AlertTriangle className="h-4 w-4 text-zinc-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-celeste-base font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                {fault.title}
              </h3>
              <span className={cn(severity.pillClass, 'flex-shrink-0')}>
                {severity.label}
              </span>
            </div>

            {/* Equipment - Subtle secondary text */}
            <p className="text-celeste-sm text-zinc-500 dark:text-zinc-400 mb-2">
              {fault.equipment_name}
            </p>

            {/* Description - Truncated */}
            <p className="text-celeste-sm text-zinc-600 dark:text-zinc-300 line-clamp-2 mb-3">
              {fault.description}
            </p>

            {/* Metadata Row */}
            <p className="text-celeste-xs text-zinc-400 dark:text-zinc-500 mb-4">
              {fault.reporter} · {new Date(fault.reported_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
              })}
            </p>

            {/* Actions - Apple-style buttons with conditional visibility */}
            {/* Phase 12: Actions driven by server decisions (E020) */}
            <div className="flex flex-wrap items-center gap-2" data-testid="fault-card-actions">
              {/* FAIL-CLOSED: Show error state if decisions endpoint failed */}
              {failClosed && (
                <div
                  className="flex items-center gap-2 px-3 py-2 text-celeste-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg"
                  data-testid="decisions-error-state"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>Actions unavailable</span>
                </div>
              )}

              {/* Loading state while fetching decisions */}
              {decisionsLoading && !failClosed && (
                <div
                  className="flex items-center gap-2 px-3 py-2 text-celeste-xs text-zinc-500"
                  data-testid="decisions-loading-state"
                >
                  <span className="animate-pulse">Loading actions...</span>
                </div>
              )}

              {/* Diagnose Action - shows if SERVER says allowed */}
              {showDiagnoseButton && (
                <button
                  onClick={() => setShowDiagnose(true)}
                  className="btn-ghost"
                  data-testid="diagnose-fault-button"
                >
                  <Stethoscope className="h-3.5 w-3.5" />
                  Diagnose
                </button>
              )}

              {/* View Manual Action - shows if SERVER allows */}
              {showManualButton && (
                <button
                  onClick={() => setShowManual(true)}
                  className="btn-ghost"
                  data-testid="view-manual-button"
                >
                  <Book className="h-3.5 w-3.5" />
                  View Manual
                </button>
              )}

              {/* View History Action - shows if SERVER allows */}
              {showHistoryButton && (
                <button
                  onClick={() => setShowHistory(true)}
                  className="btn-ghost"
                  data-testid="view-history-button"
                >
                  <History className="h-3.5 w-3.5" />
                  History
                </button>
              )}

              {/* Suggest Parts Action - shows if SERVER allows (requires known fault) */}
              {showSuggestPartsButton && (
                <button
                  onClick={() => setShowSuggestParts(true)}
                  className="btn-ghost"
                  data-testid="suggest-parts-button"
                >
                  <Package className="h-3.5 w-3.5" />
                  Parts
                </button>
              )}

              {/* Add Note Action - shows if SERVER allows */}
              {showAddNoteButton && (
                <button
                  onClick={() => setShowAddNote(true)}
                  className="btn-ghost"
                  data-testid="add-note-button"
                >
                  <StickyNote className="h-3.5 w-3.5" />
                  Note
                </button>
              )}

              {/* Add Photo Action - shows if SERVER allows */}
              {showAddPhotoButton && (
                <button
                  onClick={() => setShowAddPhoto(true)}
                  className="btn-ghost"
                  data-testid="add-photo-button"
                >
                  <Camera className="h-3.5 w-3.5" />
                  Photo
                </button>
              )}

              {/* Acknowledge Fault Action - shows if SERVER allows */}
              {showAcknowledgeButton && (
                <button
                  onClick={() => setShowAcknowledge(true)}
                  className="btn-ghost"
                  data-testid="acknowledge-fault-button"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Acknowledge
                </button>
              )}

              {/* Update Fault Action - shows if SERVER allows */}
              {showUpdateButton && (
                <button
                  onClick={() => setShowUpdate(true)}
                  className="btn-ghost"
                  data-testid="update-fault-button"
                >
                  <Edit className="h-3.5 w-3.5" />
                  Update
                </button>
              )}

              {/* Add to Handover Action - shows if SERVER allows */}
              {showHandoverButton && (
                <button
                  onClick={() => setShowHandover(true)}
                  className="btn-ghost"
                  data-testid="add-to-handover-button"
                >
                  <ClipboardList className="h-3.5 w-3.5" />
                  Handover
                </button>
              )}

              {/* Primary Action - Create Work Order (shows if SERVER allows) */}
              {showCreateWOButton && (
                <button
                  onClick={() => setShowCreateWO(true)}
                  className="btn-primary"
                  data-testid="create-work-order-button"
                >
                  <Wrench className="h-3.5 w-3.5" />
                  Create Work Order
                </button>
              )}

              {/* Secondary Actions */}
              {actions
                .filter((action) => action !== 'create_work_order')
                .slice(0, 2)
                .map((action) => (
                  <ActionButton
                    key={action}
                    action={action}
                    context={{
                      fault_id: fault.id,
                      equipment_id: fault.equipment_id,
                    }}
                    variant="secondary"
                    size="sm"
                    showIcon={true}
                  />
                ))}

              {/* More indicator */}
              {actions.filter(a => a !== 'create_work_order').length > 2 && (
                <button className="btn-icon">
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Fault Notes Section - displays notes with add action */}
            {(fault.notes && fault.notes.length > 0 || showAddNoteButton) && (
              <div className="mt-4">
                <FaultNotesSection
                  notes={fault.notes || []}
                  onAddNote={() => setShowAddNote(true)}
                  canAddNote={showAddNoteButton}
                />
              </div>
            )}

          </div>
        </div>
      </div>

      {/* Create Work Order Modal */}
      <CreateWorkOrderModal
        open={showCreateWO}
        onOpenChange={setShowCreateWO}
        context={{
          equipment_id: fault.equipment_id,
          equipment_name: fault.equipment_name,
          fault_id: fault.id,
          fault_description: fault.description,
          suggested_title: `Fix: ${fault.title}`,
        }}
        onSuccess={(workOrderId) => {
          console.log('Work order created:', workOrderId);
        }}
      />

      {/* Diagnose Fault Modal */}
      <DiagnoseFaultModal
        open={showDiagnose}
        onOpenChange={setShowDiagnose}
        context={{
          fault_id: fault.id,
          fault_title: fault.title,
          fault_description: fault.description,
          severity: fault.severity,
          equipment_name: fault.equipment_name,
        }}
      />

      {/* Show Manual Section Modal */}
      <ShowManualSectionModal
        open={showManual}
        onOpenChange={setShowManual}
        context={{
          equipment_id: fault.equipment_id,
          equipment_name: fault.equipment_name,
        }}
      />

      {/* Fault History Modal */}
      <FaultHistoryModal
        open={showHistory}
        onOpenChange={setShowHistory}
        context={{
          entity_id: fault.equipment_id,
          entity_type: 'equipment',
          entity_name: fault.equipment_name,
        }}
      />

      {/* Suggest Parts Modal */}
      <SuggestPartsModal
        open={showSuggestParts}
        onOpenChange={setShowSuggestParts}
        context={{
          fault_id: fault.id,
          fault_title: fault.title,
        }}
      />

      {/* Add Note Modal */}
      <AddNoteModal
        open={showAddNote}
        onOpenChange={setShowAddNote}
        context={{
          entity_type: 'fault',
          entity_id: fault.id,
          entity_title: fault.title,
          entity_subtitle: fault.equipment_name,
        }}
        onSuccess={onRefresh}
      />

      {/* Add Photo Modal */}
      <AddPhotoModal
        open={showAddPhoto}
        onOpenChange={setShowAddPhoto}
        context={{
          entity_type: 'fault',
          entity_id: fault.id,
          entity_title: fault.title,
          entity_subtitle: fault.equipment_name,
        }}
      />

      {/* Acknowledge Fault Modal */}
      <AcknowledgeFaultModal
        open={showAcknowledge}
        onOpenChange={setShowAcknowledge}
        context={{
          fault_id: fault.id,
          fault_title: fault.title,
          severity: fault.severity,
        }}
      />

      {/* Edit/Update Fault Modal */}
      <EditFaultDetailsModal
        open={showUpdate}
        onOpenChange={setShowUpdate}
        context={{
          fault_id: fault.id,
          current_title: fault.title,
          current_description: fault.description,
          current_severity: fault.severity,
          current_status: 'open', // TODO: get from fault object
        }}
      />

      {/* Add to Handover Modal */}
      <AddToHandoverQuickModal
        open={showHandover}
        onOpenChange={setShowHandover}
        entityType="fault"
        entityId={fault.id}
      />
    </>
  );
}

/**
 * Example Usage:
 *
 * ```tsx
 * <FaultCard
 *   fault={{
 *     id: '123',
 *     title: 'Hydraulic pump leaking',
 *     description: 'Discovered oil leak from main hydraulic pump during routine inspection.',
 *     severity: 'high',
 *     equipment_id: '456',
 *     equipment_name: 'Main Hydraulic Pump #1',
 *     reported_at: '2025-11-20T14:30:00Z',
 *     reporter: 'John Smith (Chief Engineer)',
 *   }}
 *   actions={[
 *     'diagnose_fault',
 *     'suggest_parts',
 *     'add_to_handover',
 *     'attach_photo',
 *     'add_note',
 *   ]}
 * />
 * ```
 */
