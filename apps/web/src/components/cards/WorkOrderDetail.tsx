/**
 * WorkOrderDetail Component
 *
 * ChatGPT-style Work Order template in dark mode.
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
import { Mail, FileText, Image as ImageIcon, Book, Clock } from 'lucide-react';

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
  subtitle?: string;
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
// EVIDENCE ICON HELPER
// ============================================================================

function getEvidenceIcon(type: WorkOrderEvidence['type']) {
  switch (type) {
    case 'email':
      return <Mail className="wo-evidence-icon" />;
    case 'photo':
      return <ImageIcon className="wo-evidence-icon" />;
    case 'manual':
      return <Book className="wo-evidence-icon" />;
    case 'log':
      return <Clock className="wo-evidence-icon" />;
    default:
      return <FileText className="wo-evidence-icon" />;
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
          Title: 18/600/24, Subtitle: 13/400, gap: 4px
          ================================================================ */}
      <header className="wo-header">
        <h1 className="wo-title">Work Order #{workOrder.id}</h1>
        {workOrder.subtitle && (
          <p className="wo-subtitle">{workOrder.subtitle}</p>
        )}

        {/* Header Meta Row - status, priority, created, author */}
        <div className="wo-header-meta">
          <div className="wo-header-meta-item">
            <span className="wo-status-pill">{workOrder.status}</span>
          </div>
          <div className="wo-header-meta-item">
            <span>Priority:</span>
            <span className="wo-header-meta-value">{workOrder.priority}</span>
          </div>
          <div className="wo-header-meta-item">
            <span>Created:</span>
            <span className="wo-header-meta-value">{workOrder.createdAt}</span>
          </div>
          <div className="wo-header-meta-item">
            <span>Author:</span>
            <span className="wo-header-meta-value">{workOrder.createdBy}</span>
          </div>
        </div>
      </header>

      {/* ================================================================
          METADATA GRID
          2-column, column-gap: 24px, row-gap: 12px
          ================================================================ */}
      <div className="wo-metadata">
        {workOrder.equipment && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Equipment</span>
            <span className="wo-metadata-value">{workOrder.equipment}</span>
          </div>
        )}
        {workOrder.location && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Location</span>
            <span className="wo-metadata-value">{workOrder.location}</span>
          </div>
        )}
        {workOrder.category && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Category</span>
            <span className="wo-metadata-value">{workOrder.category}</span>
          </div>
        )}
        {workOrder.dueDate && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Due Date</span>
            <span className="wo-metadata-value">{workOrder.dueDate}</span>
          </div>
        )}
        {workOrder.assignedTo && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Assigned To</span>
            <span className="wo-metadata-value">{workOrder.assignedTo}</span>
          </div>
        )}
        {workOrder.linkedFault && (
          <div className="wo-metadata-field">
            <span className="wo-metadata-label">Linked Fault</span>
            <span className="wo-metadata-value">{workOrder.linkedFault}</span>
          </div>
        )}
      </div>

      {/* ================================================================
          DESCRIPTION BLOCK
          "This is not the truth - it is the claim."
          Max 6 lines collapsed, Show more control
          ================================================================ */}
      <section className="wo-section">
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
          Hover: bg-highlight (#323232)
          ================================================================ */}
      <section className="wo-evidence-section">
        <h2 className="wo-section-header">Evidence</h2>
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
                <div className="wo-evidence-content">
                  <span className="wo-evidence-title">{item.title}</span>
                  <span className="wo-evidence-meta">
                    {item.source ? `${item.source} · ` : ''}
                    {item.timestamp}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ================================================================
          ACTIVITY LOG (AUDIT TRAIL)
          Font: 12/400/16, color: #8f8f8f
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
              <p key={entry.id} className="wo-activity-entry">
                [{entry.timestamp}]{' '}
                {entry.oldValue && entry.newValue
                  ? `${entry.action} from ${entry.oldValue} → ${entry.newValue}`
                  : entry.action}{' '}
                ({entry.user})
              </p>
            ))}
          </div>
        )}
      </section>

      {/* ================================================================
          STATUS CONTROL
          Select: 36px height, 10px radius, focus: border accent only
          ================================================================ */}
      <div className="wo-section">
        <label htmlFor="wo-status-select" className="wo-section-header">
          Status
        </label>
        <select
          id="wo-status-select"
          className="wo-select"
          value={selectedStatus}
          onChange={handleStatusChange}
        >
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Waiting">Waiting</option>
          <option value="Completed">Completed</option>
          <option value="Closed">Closed</option>
        </select>
      </div>

      {/* ================================================================
          BOTTOM ACTION BAR
          Right-aligned, gap: 8px, padding-top: 16px, border-top
          Buttons: Primary, Secondary, Danger
          ================================================================ */}
      <div className="wo-action-bar">
        <button
          type="button"
          className="wo-btn-danger"
          onClick={onClose}
        >
          Close Work Order
        </button>
        <button
          type="button"
          className="wo-btn-secondary"
          onClick={onAddEvidence}
        >
          Add Evidence
        </button>
        <button
          type="button"
          className="wo-btn-primary"
          onClick={() => onStatusChange?.(selectedStatus)}
        >
          Update Status
        </button>
      </div>
    </div>
  );
}

export default WorkOrderDetail;
