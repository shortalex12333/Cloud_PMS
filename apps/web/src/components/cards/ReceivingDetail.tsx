/**
 * ReceivingDetail Component
 *
 * Full-screen receiving record view with enriched data:
 * - Receiving header (vendor, date, status, totals)
 * - Line items with part links
 * - Attached documents (photos, invoices)
 * - OCR extraction results
 * - Linked work order (if any)
 * - Activity history
 * - Tokenized styling (no hardcoded values)
 */

'use client';

import { useState } from 'react';
import {
  Package,
  Truck,
  Calendar,
  User,
  DollarSign,
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  History,
  StickyNote,
  Plus,
  Wrench,
  Eye,
} from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { Button } from '@/components/ui/button';
import { AddNoteModal } from '@/components/modals/AddNoteModal';
import { ReceivingDocumentUpload } from '@/components/receiving/ReceivingDocumentUpload';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

interface ReceivingItem {
  id: string;
  part_id?: string;
  part_name?: string;
  part_number?: string;
  description?: string;
  quantity_expected?: number;
  quantity_received: number;
  unit_price?: number;
  currency?: string;
}

interface ReceivingDocument {
  id: string;
  filename: string;
  doc_type: 'invoice' | 'packing_slip' | 'photo';
  comment?: string;
  storage_path?: string;
  preview_url?: string;
  created_at: string;
}

interface ReceivingExtraction {
  id: string;
  payload: {
    vendor_name?: string;
    total?: number;
    currency?: string;
    line_items?: Array<{
      description: string;
      quantity: number;
      unit_price: number;
    }>;
    confidences?: Record<string, number>;
    flags?: string[];
  };
  created_at: string;
}

interface LinkedWorkOrder {
  id: string;
  title: string;
  status: string;
}

interface AuditEntry {
  id: string;
  action: string;
  old_values?: Record<string, unknown>;
  new_values?: Record<string, unknown>;
  user_id?: string;
  created_at: string;
}

interface ReceivingDetailProps {
  receiving: {
    id: string;
    vendor_name?: string;
    vendor_reference?: string;
    received_date: string;
    received_by_name?: string;
    status: 'draft' | 'in_review' | 'accepted' | 'rejected';
    currency?: string;
    subtotal?: number;
    tax_total?: number;
    total?: number;
    notes?: string;
    // Enriched data
    items?: ReceivingItem[];
    documents?: ReceivingDocument[];
    extractions?: ReceivingExtraction[];
    linked_work_order?: LinkedWorkOrder;
    audit_history?: AuditEntry[];
  };
  actions?: MicroAction[];
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ReceivingDetail({ receiving, actions = [] }: ReceivingDetailProps) {
  const [showAddNoteModal, setShowAddNoteModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Get status styling
  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'accepted':
        return {
          bg: 'bg-[var(--celeste-green)]/10',
          text: 'text-[var(--celeste-green)]',
          icon: <CheckCircle2 className="h-5 w-5 text-[var(--celeste-green)]" />,
          label: 'Accepted',
        };
      case 'rejected':
        return {
          bg: 'bg-[var(--celeste-warning)]/10',
          text: 'text-[var(--celeste-warning)]',
          icon: <XCircle className="h-5 w-5 text-[var(--celeste-warning)]" />,
          label: 'Rejected',
        };
      case 'in_review':
        return {
          bg: 'bg-[var(--celeste-yellow)]/10',
          text: 'text-[var(--celeste-yellow)]',
          icon: <Eye className="h-5 w-5 text-[var(--celeste-yellow)]" />,
          label: 'In Review',
        };
      default:
        return {
          bg: 'bg-[var(--celeste-text-muted)]/10',
          text: 'text-[var(--celeste-text-muted)]',
          icon: <Clock className="h-5 w-5 text-[var(--celeste-text-muted)]" />,
          label: 'Draft',
        };
    }
  };

  const status = getStatusStyles(receiving.status);
  const items = receiving.items || [];
  const documents = receiving.documents || [];
  const extractions = receiving.extractions || [];
  const auditHistory = receiving.audit_history || [];

  const actionContext = {
    receiving_id: receiving.id,
  };

  // Calculate totals from items if not provided
  const calculatedSubtotal = items.reduce((sum, item) => {
    return sum + (item.quantity_received * (item.unit_price || 0));
  }, 0);

  return (
    <div className="flex flex-col gap-[var(--celeste-spacing-6)]">
      {/* ================================================================
          HEADER SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        {/* Status Badge with Accept/Reject Actions */}
        <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-4)]">
          <span className={cn(
            'inline-flex items-center gap-[var(--celeste-spacing-1)] px-[var(--celeste-spacing-3)] py-[var(--celeste-spacing-1)] rounded-[var(--celeste-border-radius-sm)] text-sm font-medium',
            status.bg, status.text
          )}>
            {status.icon}
            {status.label}
          </span>

          {/* Accept/Reject buttons - shown when status is draft or in_review */}
          {(receiving.status === 'draft' || receiving.status === 'in_review') && (
            <>
              <ActionButton
                action="accept_receiving"
                context={actionContext}
                variant="default"
                size="sm"
                showIcon={true}
              />
              <ActionButton
                action="reject_receiving"
                context={actionContext}
                variant="outline"
                size="sm"
                showIcon={true}
              />
            </>
          )}
        </div>

        {/* Vendor Name */}
        <h1 className="text-2xl font-semibold text-[var(--celeste-text-title)] mb-[var(--celeste-spacing-2)]">
          {receiving.vendor_name || 'Unknown Vendor'}
        </h1>

        {/* Reference */}
        {receiving.vendor_reference && (
          <p className="text-[var(--celeste-text-secondary)] font-mono mb-[var(--celeste-spacing-4)]">
            Ref: {receiving.vendor_reference}
          </p>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Received Date</p>
            <div className="flex items-center gap-[var(--celeste-spacing-1)]">
              <Calendar className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
              <span className="text-[var(--celeste-text-primary)]">{formatDate(receiving.received_date)}</span>
            </div>
          </div>
          {receiving.received_by_name && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Received By</p>
              <div className="flex items-center gap-[var(--celeste-spacing-1)]">
                <User className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
                <span className="text-[var(--celeste-text-primary)]">{receiving.received_by_name}</span>
              </div>
            </div>
          )}
          <div>
            <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Items</p>
            <span className="text-[var(--celeste-text-primary)]">{items.length} line items</span>
          </div>
          {(receiving.total !== undefined || calculatedSubtotal > 0) && (
            <div>
              <p className="text-[var(--celeste-text-muted)] text-xs uppercase tracking-wide mb-1">Total</p>
              <div className="flex items-center gap-[var(--celeste-spacing-1)]">
                <DollarSign className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
                <span className="text-[var(--celeste-text-primary)] font-semibold">
                  {(receiving.total || calculatedSubtotal).toFixed(2)} {receiving.currency || 'USD'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Notes */}
        {receiving.notes && (
          <div className="mt-[var(--celeste-spacing-4)] p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
            <p className="text-xs text-[var(--celeste-text-muted)] uppercase tracking-wide mb-1">Notes</p>
            <p className="text-[var(--celeste-text-primary)]">{receiving.notes}</p>
          </div>
        )}

        {/* Primary Actions */}
        <div className="flex flex-wrap items-center gap-[var(--celeste-spacing-2)] mt-[var(--celeste-spacing-4)] pt-[var(--celeste-spacing-4)] border-t border-[var(--celeste-border-subtle)]">
          {/* Update Receiving Fields */}
          {(receiving.status === 'draft' || receiving.status === 'in_review') && (
            <ActionButton
              action="update_receiving"
              context={actionContext}
              variant="secondary"
              size="sm"
              showIcon={true}
            />
          )}

          {/* Link Invoice PDF */}
          <ActionButton
            action="link_receiving_to_invoice"
            context={actionContext}
            variant="secondary"
            size="sm"
            showIcon={true}
          />

          {/* Extract Line Items (OCR) */}
          <ActionButton
            action="extract_receiving_candidates"
            context={actionContext}
            variant="secondary"
            size="sm"
            showIcon={true}
          />

          {/* Dynamic actions from props */}
          {actions.slice(0, 2).map((action) => (
            <ActionButton
              key={action}
              action={action}
              context={actionContext}
              variant="secondary"
              size="sm"
              showIcon={true}
            />
          ))}
        </div>
      </div>

      {/* ================================================================
          LINKED WORK ORDER
          ================================================================ */}
      {receiving.linked_work_order && (
        <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
            <Wrench className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Linked Work Order</h3>
          </div>
          <div className="p-[var(--celeste-spacing-4)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
            <p className="text-[var(--celeste-text-primary)] font-medium">{receiving.linked_work_order.title}</p>
            <span className={cn(
              'text-xs uppercase',
              receiving.linked_work_order.status === 'completed' && 'text-[var(--celeste-green)]',
              receiving.linked_work_order.status === 'in_progress' && 'text-[var(--celeste-accent)]'
            )}>
              {receiving.linked_work_order.status.replace('_', ' ')}
            </span>
          </div>
        </div>
      )}

      {/* ================================================================
          LINE ITEMS SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <Package className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Line Items</h3>
            {items.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({items.length})</span>
            )}
          </div>
          {receiving.status === 'draft' && (
            <ActionButton
              action="add_receiving_item"
              context={actionContext}
              variant="ghost"
              size="sm"
              showIcon={true}
              label="Add Item"
            />
          )}
        </div>

        {items.length === 0 ? (
          <div className="text-center py-[var(--celeste-spacing-6)]">
            <Package className="h-8 w-8 text-[var(--celeste-text-muted)] mx-auto mb-[var(--celeste-spacing-2)]" />
            <p className="text-[var(--celeste-text-muted)]">No items added yet</p>
          </div>
        ) : (
          <div className="space-y-[var(--celeste-spacing-2)]">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
              >
                <div className="flex-1">
                  <p className="text-[var(--celeste-text-primary)] font-medium">
                    {item.part_name || item.description || 'Unknown Item'}
                  </p>
                  <div className="flex items-center gap-[var(--celeste-spacing-2)] text-xs text-[var(--celeste-text-muted)]">
                    {item.part_number && <span>P/N: {item.part_number}</span>}
                    {item.quantity_expected !== undefined && item.quantity_expected !== item.quantity_received && (
                      <span className="text-[var(--celeste-orange)]">
                        Expected: {item.quantity_expected}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-[var(--celeste-spacing-3)]">
                  <div className="text-right">
                    <span className="text-[var(--celeste-text-primary)] font-medium">
                      Qty: {item.quantity_received}
                    </span>
                    {item.unit_price !== undefined && (
                      <p className="text-xs text-[var(--celeste-text-muted)]">
                        @ {item.unit_price.toFixed(2)} {item.currency || receiving.currency || 'USD'}
                      </p>
                    )}
                  </div>
                  {/* Adjust line item button */}
                  {(receiving.status === 'draft' || receiving.status === 'in_review') && (
                    <ActionButton
                      action="adjust_receiving_item"
                      context={{ ...actionContext, receiving_item_id: item.id }}
                      variant="ghost"
                      size="sm"
                      showIcon={true}
                      label=""
                    />
                  )}
                </div>
              </div>
            ))}

            {/* Totals Row */}
            {(receiving.subtotal !== undefined || receiving.total !== undefined) && (
              <div className="pt-[var(--celeste-spacing-3)] border-t border-[var(--celeste-border-subtle)]">
                {receiving.subtotal !== undefined && (
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--celeste-text-muted)]">Subtotal</span>
                    <span className="text-[var(--celeste-text-primary)]">
                      {receiving.subtotal.toFixed(2)} {receiving.currency || 'USD'}
                    </span>
                  </div>
                )}
                {receiving.tax_total !== undefined && receiving.tax_total > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--celeste-text-muted)]">Tax</span>
                    <span className="text-[var(--celeste-text-primary)]">
                      {receiving.tax_total.toFixed(2)} {receiving.currency || 'USD'}
                    </span>
                  </div>
                )}
                {receiving.total !== undefined && (
                  <div className="flex justify-between text-sm font-semibold mt-[var(--celeste-spacing-2)]">
                    <span className="text-[var(--celeste-text-primary)]">Total</span>
                    <span className="text-[var(--celeste-text-primary)]">
                      {receiving.total.toFixed(2)} {receiving.currency || 'USD'}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          DOCUMENTS SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <FileText className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Documents</h3>
            {documents.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({documents.length})</span>
            )}
          </div>
          {/* + Button to upload documents - opens upload modal */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" />
            <span>Add</span>
          </Button>
        </div>

        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-[var(--celeste-spacing-8)] text-center">
            <div className="w-16 h-16 rounded-[var(--celeste-border-radius-lg)] bg-[var(--celeste-bg-tertiary)] flex items-center justify-center mb-[var(--celeste-spacing-4)]">
              <FileText className="h-8 w-8 text-[var(--celeste-text-muted)]" />
            </div>
            <p className="text-[var(--celeste-text-primary)] font-medium mb-[var(--celeste-spacing-1)]">
              No documents yet
            </p>
            <p className="text-[var(--celeste-text-muted)] text-sm mb-[var(--celeste-spacing-4)]">
              Take a photo or upload an invoice, packing slip, or delivery photo.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              <span>Add Document</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-[var(--celeste-spacing-4)]">
            {/* Photos - render inline */}
            {documents.filter(d => d.doc_type === 'photo').map((doc) => (
              <div
                key={doc.id}
                className="bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)] overflow-hidden"
              >
                {doc.preview_url ? (
                  <img
                    src={doc.preview_url}
                    alt={doc.comment || doc.filename}
                    className="max-w-full h-auto mx-auto"
                    style={{ maxHeight: '400px' }}
                  />
                ) : (
                  <div className="flex items-center justify-center py-[var(--celeste-spacing-8)] bg-[var(--celeste-bg-tertiary)]">
                    <ImageIcon className="h-8 w-8 text-[var(--celeste-text-muted)]" />
                  </div>
                )}
                <div className="p-[var(--celeste-spacing-3)] border-t border-[var(--celeste-border-subtle)]">
                  <div className="flex items-center gap-[var(--celeste-spacing-2)]">
                    <ImageIcon className="h-4 w-4 text-[var(--celeste-accent)]" />
                    <span className="text-sm text-[var(--celeste-text-primary)]">{doc.filename}</span>
                  </div>
                  {doc.comment && (
                    <p className="text-xs text-[var(--celeste-text-muted)] mt-1">{doc.comment}</p>
                  )}
                </div>
              </div>
            ))}
            {/* Non-photo documents - show as preview links */}
            {documents.filter(d => d.doc_type !== 'photo').length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-[var(--celeste-spacing-3)]">
                {documents.filter(d => d.doc_type !== 'photo').map((doc) => (
                  <div
                    key={doc.id}
                    className="p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
                  >
                    <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-2)]">
                      <FileText className="h-4 w-4 text-[var(--celeste-text-secondary)]" />
                      <span className="text-xs text-[var(--celeste-text-muted)] uppercase">
                        {doc.doc_type.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--celeste-text-primary)] truncate">{doc.filename}</p>
                    {doc.comment && (
                      <p className="text-xs text-[var(--celeste-text-muted)] mt-1 truncate">{doc.comment}</p>
                    )}
                    {doc.preview_url && (
                      <a
                        href={doc.preview_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-[var(--celeste-accent)] hover:underline mt-[var(--celeste-spacing-2)]"
                      >
                        <Eye className="h-3 w-3" />
                        View Document
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ================================================================
          OCR EXTRACTION SECTION (if available)
          ================================================================ */}
      {extractions.length > 0 && (
        <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-accent)]/30">
          <div className="flex items-center gap-[var(--celeste-spacing-2)] mb-[var(--celeste-spacing-3)]">
            <AlertCircle className="h-5 w-5 text-[var(--celeste-accent)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">OCR Extraction (Advisory)</h3>
          </div>
          <p className="text-xs text-[var(--celeste-text-muted)] mb-[var(--celeste-spacing-3)]">
            These values were extracted automatically and may need verification.
          </p>
          {extractions.map((extraction) => (
            <div key={extraction.id} className="p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]">
              {extraction.payload.vendor_name && (
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-[var(--celeste-text-muted)]">Vendor</span>
                  <span className="text-[var(--celeste-text-primary)]">{extraction.payload.vendor_name}</span>
                </div>
              )}
              {extraction.payload.total !== undefined && (
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-[var(--celeste-text-muted)]">Total</span>
                  <span className="text-[var(--celeste-text-primary)]">
                    {extraction.payload.total.toFixed(2)} {extraction.payload.currency || 'USD'}
                  </span>
                </div>
              )}
              {extraction.payload.line_items && extraction.payload.line_items.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-[var(--celeste-text-muted)]">
                    {extraction.payload.line_items.length} items detected
                  </span>
                </div>
              )}
              {extraction.payload.flags && extraction.payload.flags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {extraction.payload.flags.map((flag, idx) => (
                    <span key={idx} className="text-xs px-2 py-0.5 bg-[var(--celeste-orange)]/10 text-[var(--celeste-orange)] rounded">
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ================================================================
          ACTIVITY SECTION
          ================================================================ */}
      <div className="bg-[var(--celeste-surface)] rounded-[var(--celeste-border-radius-md)] p-[var(--celeste-spacing-6)] border border-[var(--celeste-border-subtle)]">
        <div className="flex items-center justify-between mb-[var(--celeste-spacing-3)]">
          <div className="flex items-center gap-[var(--celeste-spacing-2)]">
            <History className="h-5 w-5 text-[var(--celeste-text-secondary)]" />
            <h3 className="text-[var(--celeste-text-primary)] font-semibold">Activity</h3>
            {auditHistory.length > 0 && (
              <span className="text-[var(--celeste-text-muted)] text-sm">({auditHistory.length})</span>
            )}
          </div>
          <ActionButton
            action="view_receiving_history"
            context={actionContext}
            variant="ghost"
            size="sm"
            showIcon={true}
            label="Full History"
          />
        </div>

        {auditHistory.length === 0 ? (
          <div className="text-center py-[var(--celeste-spacing-6)]">
            <History className="h-8 w-8 text-[var(--celeste-text-muted)] mx-auto mb-[var(--celeste-spacing-2)]" />
            <p className="text-[var(--celeste-text-muted)]">No activity yet</p>
          </div>
        ) : (
          <div className="space-y-[var(--celeste-spacing-3)]">
            {auditHistory.slice(0, 10).map((entry) => {
              const actionLabels: Record<string, string> = {
                'create_receiving': 'Receiving created',
                'add_receiving_item': 'Item added',
                'update_receiving': 'Receiving updated',
                'accept_receiving': 'Receiving accepted',
                'reject_receiving': 'Receiving rejected',
                'attach_receiving_image_with_comment': 'Document attached',
                'extract_receiving_candidates': 'OCR extraction run',
              };
              const label = actionLabels[entry.action] || entry.action.replace(/_/g, ' ');

              return (
                <div
                  key={entry.id}
                  className="p-[var(--celeste-spacing-3)] bg-[var(--celeste-panel)] rounded-[var(--celeste-border-radius-sm)] border border-[var(--celeste-border-subtle)]"
                >
                  <div className="flex items-start justify-between gap-[var(--celeste-spacing-2)]">
                    <p className="text-[var(--celeste-text-primary)] font-medium text-sm">{label}</p>
                    <span className="text-xs text-[var(--celeste-text-muted)] whitespace-nowrap">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                </div>
              );
            })}
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
          entity_type: 'receiving',
          entity_id: receiving.id,
          entity_title: receiving.vendor_name || 'Receiving',
          entity_subtitle: receiving.vendor_reference,
        }}
        onSuccess={() => {}}
      />

      {/* Document Upload Modal */}
      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-[var(--celeste-accent)]" />
              Add Document
            </DialogTitle>
          </DialogHeader>
          <ReceivingDocumentUpload
            receivingId={receiving.id}
            onComplete={(receivingId, documentId, extractedData) => {
              // Close modal after successful upload and save
              // The parent should refresh data to show new document
              setShowUploadModal(false);
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ReceivingDetail;
