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
import { AlertTriangle, Wrench, ChevronRight, Stethoscope, Book, History, Package, StickyNote, Camera, AlertCircle } from 'lucide-react';
import { CreateWorkOrderModal } from '@/components/actions/modals/CreateWorkOrderModal';
import { DiagnoseFaultModal } from '@/components/modals/DiagnoseFaultModal';
import { ShowManualSectionModal } from '@/components/modals/ShowManualSectionModal';
import { FaultHistoryModal } from '@/components/modals/FaultHistoryModal';
import { SuggestPartsModal } from '@/components/modals/SuggestPartsModal';
import { AddNoteModal } from '@/components/modals/AddNoteModal';
import { AddPhotoModal } from '@/components/modals/AddPhotoModal';
import { ActionButton } from '@/components/actions/ActionButton';
import { RelatedEmailsPanel } from '@/components/email/RelatedEmailsPanel';
import { cn } from '@/lib/utils';
import { useActionDecisions } from '@/lib/microactions/hooks/useActionDecisions';
import type { MicroAction } from '@/types/actions';

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
  };
  actions?: MicroAction[];
  // User role for permission checks
  userRole?: string;
  // Callback when auto-run action executes
  onAutoRun?: (actionName: string, result: unknown) => void;
}

export function FaultCard({ fault, actions = [], userRole, onAutoRun }: FaultCardProps) {
  const [showCreateWO, setShowCreateWO] = useState(false);
  const [showDiagnose, setShowDiagnose] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showSuggestParts, setShowSuggestParts] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [showAddPhoto, setShowAddPhoto] = useState(false);

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

  // Get severity styling (Apple-style: subtle background, muted colors)
  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          dot: 'celeste-dot-critical',
          badge: 'celeste-badge-critical',
          label: 'Critical',
        };
      case 'high':
        return {
          dot: 'celeste-dot-high',
          badge: 'celeste-badge-high',
          label: 'High',
        };
      case 'medium':
        return {
          dot: 'celeste-dot-medium',
          badge: 'celeste-badge-medium',
          label: 'Medium',
        };
      default:
        return {
          dot: 'celeste-dot-low',
          badge: 'celeste-badge-low',
          label: 'Low',
        };
    }
  };

  const severity = getSeverityStyles(fault.severity);

  return (
    <>
      <div className="celeste-card p-4 hover:shadow-[var(--shadow-md)] transition-shadow duration-200">
        <div className="flex items-start gap-3">
          {/* Severity Indicator - Minimal dot + icon */}
          <div className="flex flex-col items-center gap-2 pt-0.5">
            <span className={cn('celeste-dot', severity.dot)} />
            <AlertTriangle className="h-4 w-4 text-zinc-400" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title Row */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <h3 className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                {fault.title}
              </h3>
              <span className={cn('celeste-badge flex-shrink-0', severity.badge)}>
                {severity.label}
              </span>
            </div>

            {/* Equipment - Subtle secondary text */}
            <p className="text-[13px] text-zinc-500 dark:text-zinc-400 mb-2">
              {fault.equipment_name}
            </p>

            {/* Description - Truncated */}
            <p className="text-[14px] text-zinc-600 dark:text-zinc-300 line-clamp-2 mb-3">
              {fault.description}
            </p>

            {/* Metadata Row */}
            <p className="text-[12px] text-zinc-400 dark:text-zinc-500 mb-4">
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
                  className="flex items-center gap-2 px-3 py-2 text-[12px] text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg"
                  data-testid="decisions-error-state"
                >
                  <AlertCircle className="h-4 w-4" />
                  <span>Actions unavailable</span>
                </div>
              )}

              {/* Loading state while fetching decisions */}
              {decisionsLoading && !failClosed && (
                <div
                  className="flex items-center gap-2 px-3 py-2 text-[12px] text-zinc-500"
                  data-testid="decisions-loading-state"
                >
                  <span className="animate-pulse">Loading actions...</span>
                </div>
              )}

              {/* Diagnose Action - shows if SERVER says allowed */}
              {showDiagnoseButton && (
                <button
                  onClick={() => setShowDiagnose(true)}
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
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
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
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
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
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
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
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
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
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
                  className="celeste-button celeste-button-secondary h-8 px-3 text-[13px]"
                  data-testid="add-photo-button"
                >
                  <Camera className="h-3.5 w-3.5" />
                  Photo
                </button>
              )}

              {/* Primary Action - Create Work Order (shows if SERVER allows) */}
              {showCreateWOButton && (
                <button
                  onClick={() => setShowCreateWO(true)}
                  className="celeste-button celeste-button-primary h-8 px-3 text-[13px]"
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
                <button className="h-8 px-2 text-[13px] text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors">
                  <ChevronRight className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Related Emails - Evidence panel */}
            <RelatedEmailsPanel
              objectType="fault"
              objectId={fault.id}
              className="mt-4"
            />
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
