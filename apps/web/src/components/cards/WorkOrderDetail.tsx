/**
 * WorkOrderDetail Component
 *
 * ChatGPT-style Work Order template supporting light and dark mode.
 * Source: /Desktop/work_order_ux.md
 *
 * Design Philosophy:
 * - Single primary surface, no cards
 * - Evidence-first, description is the claim
 * - Mutation is explicit, status is factual
 * - Dark mode via tonal separation, not elevation
 *
 * ZERO HARDCODED VALUES - All styling via CSS tokens (wo-* classes)
 */

'use client';

import { useState, useCallback } from 'react';
import { Mail, FileText, Image as ImageIcon, Book, Clock, File } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface WorkOrderEvidence {
  id: string;
  type: 'email' | 'photo' | 'manual' | 'log';
  title: string;
  timestamp: string;
  source?: string;
}

export interface WorkOrderActivity {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  oldValue?: string;
  newValue?: string;
}

export interface WorkOrderData {
  id: string;
  title: string;
  status: 'Open' | 'In Progress' | 'Waiting' | 'Completed' | 'Closed';
  priority: 'Low' | 'Medium' | 'High' | 'Urgent';
  createdAt: string;
  createdBy: string;
  equipment?: string;
  location?: string;
  category?: string;
  dueDate?: string;
  assignedTo?: string;
  linkedFault?: string;
  description: string;
  evidence: WorkOrderEvidence[];
  activity: WorkOrderActivity[];
}

export interface WorkOrderDetailProps {
  workOrder: WorkOrderData;
  onStatusChange?: (newStatus: WorkOrderData['status']) => void;
  onAddEvidence?: () => void;
  onClose?: () => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/** Get status dot class based on status */
function getStatusDotClass(status: WorkOrderData['status']): string {
  switch (status) {
    case 'In Progress':
      return 'wo-status-dot wo-status-dot--active';
    case 'Completed':
    case 'Closed':
      return 'wo-status-dot wo-status-dot--success';
    case 'Waiting':
      return 'wo-status-dot wo-status-dot--warning';
    default:
      return 'wo-status-dot';
  }
}

/** Get evidence icon based on type */
function getEvidenceIcon(type: WorkOrderEvidence['type']) {
  switch (type) {
    case 'email':
      return <Mail className="wo-evidence-icon" />;
    case 'photo':
      return <ImageIcon className="wo-evidence-icon" />;
    case 'manual':
      return <FileText className="wo-evidence-icon" />;
    case 'log':
      return <Clock className="wo-evidence-icon" />;
    default:
      return <File className="wo-evidence-icon" />;
  }
}

/** Get evidence type label */
function getEvidenceTypeLabel(type: WorkOrderEvidence['type']): string {
  switch (type) {
    case 'email':
      return 'Email';
    case 'photo':
      return 'Photo';
    case 'manual':
      return 'Manual';
    case 'log':
      return 'Log Entry';
    default:
      return 'File';
  }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function WorkOrderDetail({
  workOrder,
  onStatusChange,
  onAddEvidence,
  onClose,
}: WorkOrderDetailProps) {
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(workOrder.status);

  // Handle status change
  const handleStatusChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newStatus = e.target.value as WorkOrderData['status'];
      setSelectedStatus(newStatus);
      onStatusChange?.(newStatus);
    },
    [onStatusChange]
  );

  // Toggle description expansion
  const toggleDescription = useCallback(() => {
    setIsDescriptionExpanded((prev) => !prev);
  }, []);

  // Check if description needs truncation (rough heuristic: > 300 chars)
  const needsTruncation = workOrder.description.length > 300;

  return (
    <div className="wo-container">
      {/* ================================================================
          HEADER BLOCK
          Title: 18/600/24, Subtitle: 13/400 "Created on [date] by [author]."
          ================================================================ */}
      <header className="wo-header">
        <h1 className="wo-title">Work Order #{workOrder.id}</h1>
        <p className="wo-subtitle">
          Created on {workOrder.createdAt} by {workOrder.createdBy}.
        </p>

        {/* Header Meta Row - status dot + text, priority dot + text, created time, author */}
        <div className="wo-header-meta">
          {/* Status with colored dot */}
          <div className="wo-status-indicator">
            <span className={getStatusDotClass(workOrder.status)} />
            <span className={workOrder.status === 'In Progress' ? 'wo-status-text--active' : ''}>
              Status: <strong>{workOrder.status}</strong>
            </span>
          </div>

          {/* Priority with gray dot */}
          <div className="wo-status-indicator">
            <span className="wo-status-dot" />
            <span>
              Priority: <strong>{workOrder.priority}</strong>
            </span>
          </div>

          {/* Created time */}
          <div className="wo-header-meta-item">
            <span>Created:</span>
            <span className="wo-header-meta-value">{workOrder.createdAt}</span>
          </div>

          {/* Author */}
          <div className="wo-header-meta-item">
            <span>Author:</span>
            <span className="wo-header-meta-value">{workOrder.createdBy}</span>
          </div>
        </div>
      </header>

      {/* ================================================================
          METADATA GRID
          2-column with vertical divider, column-gap: 24px, row-gap: 12px
          Format: Label: Value
          ================================================================ */}
      <div className="wo-metadata">
        {/* Left column */}
        <div className="wo-metadata-col-left">
          {workOrder.equipment && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Equipment</span>
              <span className="wo-metadata-value">{workOrder.equipment}</span>
            </div>
          )}
          {workOrder.category && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Category</span>
              <span className="wo-metadata-value">{workOrder.category}</span>
            </div>
          )}
          {workOrder.assignedTo && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Assigned To</span>
              <span className="wo-metadata-value">{workOrder.assignedTo}</span>
            </div>
          )}
        </div>

        {/* Vertical divider */}
        <div className="wo-metadata-divider" />

        {/* Right column */}
        <div className="wo-metadata-col-right">
          {workOrder.location && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Location</span>
              <span className="wo-metadata-value">{workOrder.location}</span>
            </div>
          )}
          {workOrder.dueDate && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Due Date</span>
              <span className="wo-metadata-value">{workOrder.dueDate}</span>
            </div>
          )}
          {workOrder.linkedFault && (
            <div className="wo-metadata-field">
              <span className="wo-metadata-label">Linked Fault</span>
              <span className="wo-metadata-value">{workOrder.linkedFault}</span>
            </div>
          )}
        </div>
      </div>

      {/* ================================================================
          DESCRIPTION BLOCK
          "This is not the truth - it is the claim."
          Max 6 lines collapsed, Show more control
          ================================================================ */}
      <section className="wo-section wo-description-section">
        <h2 className="wo-section-header">Description</h2>
        <p
          className={`wo-description-text ${
            !isDescriptionExpanded && needsTruncation ? 'collapsed' : ''
          }`}
        >
          {workOrder.description}
        </p>
        {needsTruncation && (
          <button
            type="button"
            className="wo-expand-control"
            onClick={toggleDescription}
          >
            {isDescriptionExpanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </section>

      {/* ================================================================
          EVIDENCE / SOURCES SECTION
          Evidence is immutable, click opens source
          Format: Icon Type: "Title" – timestamp
          Hover: bg-highlight
          ================================================================ */}
      <section className="wo-evidence-section">
        <h2 className="wo-section-header">Evidence / Sources</h2>
        {workOrder.evidence.length === 0 ? (
          <p className="wo-empty-state">No evidence attached</p>
        ) : (
          <div className="wo-evidence-list">
            {workOrder.evidence.map((item) => (
              <div
                key={item.id}
                className="wo-evidence-row"
                role="button"
                tabIndex={0}
                onClick={() => {
                  /* Click opens source, not embed */
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    /* Click opens source */
                  }
                }}
              >
                {getEvidenceIcon(item.type)}
                <span className="wo-evidence-text">
                  {getEvidenceTypeLabel(item.type)}: {item.title} – {item.timestamp}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ================================================================
          ACTIVITY LOG (AUDIT TRAIL)
          Font: 12/400/16, color: meta
          Format: [timestamp] Action (User)
          No hiding. No grouping. No summarisation.
          ================================================================ */}
      <section className="wo-activity-section">
        <h2 className="wo-section-header">Activity</h2>
        {workOrder.activity.length === 0 ? (
          <p className="wo-empty-state">No activity recorded</p>
        ) : (
          <div className="wo-activity-list">
            {workOrder.activity.map((entry) => (
              <div key={entry.id} className="wo-activity-entry">
                <File className="wo-activity-icon" />
                <span>
                  [{entry.timestamp}]{' '}
                  {entry.oldValue && entry.newValue
                    ? `${entry.action} from ${entry.oldValue} to ${entry.newValue}`
                    : entry.action}{' '}
                  ({entry.user})
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ================================================================
          BOTTOM ACTION BAR
          Right-aligned, gap: 8px, padding-top: 16px, border-top
          Order: Update Status (Primary), Add Evidence (Secondary), Close Work Order (Danger)
          ================================================================ */}
      <div className="wo-action-bar">
        <button
          type="button"
          className="btn-primary"
          onClick={() => onStatusChange?.(selectedStatus)}
        >
          Update Status
        </button>
        <button
          type="button"
          className="btn-ghost"
          onClick={onAddEvidence}
        >
          Add Evidence
        </button>
        <button
          type="button"
          className="btn-danger"
          onClick={onClose}
        >
          Close Work Order
        </button>
      </div>
    </div>
  );
}

export default WorkOrderDetail;
