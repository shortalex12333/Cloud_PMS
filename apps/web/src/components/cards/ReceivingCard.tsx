/**
 * ReceivingCard Component
 *
 * Displays receiving record information (PO, invoice, delivery) with status and actions.
 * Includes child table sections for line items and attached documents.
 */

'use client';

import { Package, Calendar, FileText, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';
import {
  ReceivingLineItemsSection,
  ReceivingDocumentsSection,
  type ReceivingLineItem,
  type ReceivingDocument,
} from '@/components/lens/receiving-sections';

interface ReceivingCardProps {
  receiving: {
    id: string;
    vendor_name?: string;
    vendor_reference?: string; // PO number, invoice number, etc.
    po_number?: string; // Alternative PO field
    received_date?: string;
    status?: 'draft' | 'in_review' | 'accepted' | 'rejected';
    total?: number;
    currency?: string;
    notes?: string;
    received_by?: string;
    /** Line items from pms_receiving_items */
    items?: ReceivingLineItem[];
    /** Documents from pms_receiving_documents */
    documents?: ReceivingDocument[];
  };
  actions?: MicroAction[];
  /** Whether user can add items (HOD+ roles) */
  canAddItem?: boolean;
  /** Whether user can add documents (HOD+ roles) */
  canAddDocument?: boolean;
  /** Callback when Add Item is clicked */
  onAddItem?: () => void;
  /** Callback when Add Document is clicked */
  onAddDocument?: () => void;
  /** Callback when a part is clicked (navigate to Part lens) */
  onPartClick?: (partId: string) => void;
  /** Callback when a document is clicked (navigate to Document lens) */
  onDocumentClick?: (documentId: string) => void;
}

export function ReceivingCard({
  receiving,
  actions = [],
  canAddItem = false,
  canAddDocument = false,
  onAddItem,
  onAddDocument,
  onPartClick,
  onDocumentClick,
}: ReceivingCardProps) {
  const getStatusInfo = (status?: string) => {
    switch (status) {
      case 'accepted':
        return {
          label: 'Accepted',
          icon: CheckCircle,
          color: 'text-restricted-green bg-restricted-green/10 border-restricted-green/30',
        };
      case 'rejected':
        return {
          label: 'Rejected',
          icon: XCircle,
          color: 'text-restricted-red bg-restricted-red/10 border-restricted-red/30',
        };
      case 'in_review':
        return {
          label: 'In Review',
          icon: AlertCircle,
          color: 'text-restricted-yellow bg-restricted-yellow/10 border-restricted-yellow/30',
        };
      case 'draft':
      default:
        return {
          label: 'Draft',
          icon: Clock,
          color: 'text-celeste-text-muted bg-celeste-bg-secondary border-celeste-border',
        };
    }
  };

  const statusInfo = getStatusInfo(receiving.status);
  const StatusIcon = statusInfo.icon;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const formatTotal = (amount?: number, currency?: string) => {
    if (amount === undefined || amount === null) return null;
    const formatted = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
    return currency ? `${currency} ${formatted}` : formatted;
  };

  return (
    <div
      className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors"
      data-testid="receiving-card"
      data-entity-type="receiving"
      data-entity-id={receiving.id}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="mt-1 text-primary">
          <Package className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Vendor & Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">
              {receiving.vendor_name || 'Receiving Record'}
            </h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase inline-flex items-center gap-1',
                statusInfo.color
              )}
            >
              <StatusIcon className="h-3 w-3" />
              {statusInfo.label}
            </span>
          </div>

          {/* PO Number (if different from vendor_reference) */}
          {receiving.po_number && receiving.po_number !== receiving.vendor_reference && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-1">
              <FileText className="h-4 w-4" />
              <span className="font-medium">PO:</span>
              <span>{receiving.po_number}</span>
            </div>
          )}

          {/* Reference Number (Invoice/AWB) */}
          {receiving.vendor_reference && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-1">
              <FileText className="h-4 w-4" />
              <span className="font-medium">Ref:</span>
              <span>{receiving.vendor_reference}</span>
            </div>
          )}

          {/* Received Date */}
          {receiving.received_date && (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-1">
              <Calendar className="h-4 w-4" />
              <span className="font-medium">Received:</span>
              <span>{formatDate(receiving.received_date)}</span>
            </div>
          )}

          {/* Total Amount */}
          {formatTotal(receiving.total, receiving.currency) && (
            <div className="text-sm font-medium text-foreground mt-2">
              Total: {formatTotal(receiving.total, receiving.currency)}
            </div>
          )}

          {/* Notes */}
          {receiving.notes && (
            <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
              {receiving.notes}
            </p>
          )}

          {/* Actions */}
          {actions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {actions.map((action) => (
                <ActionButton
                  key={action}
                  action={action}
                  context={{ receiving_id: receiving.id, entity_type: 'receiving' }}
                  size="sm"
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Child Table Sections - Line Items and Documents */}
      {(receiving.items || receiving.documents) && (
        <div className="mt-4 space-y-4 border-t border-border pt-4">
          {/* Line Items Section */}
          {receiving.items !== undefined && (
            <ReceivingLineItemsSection
              items={receiving.items.map((item) => ({
                ...item,
                onPartClick: item.part_id && onPartClick
                  ? () => onPartClick(item.part_id!)
                  : undefined,
              }))}
              canAddItem={canAddItem}
              onAddItem={onAddItem}
            />
          )}

          {/* Documents Section */}
          {receiving.documents !== undefined && (
            <ReceivingDocumentsSection
              documents={receiving.documents.map((doc) => ({
                ...doc,
                onDocumentClick: onDocumentClick
                  ? () => onDocumentClick(doc.document_id)
                  : undefined,
              }))}
              canAddDocument={canAddDocument}
              onAddDocument={onAddDocument}
            />
          )}
        </div>
      )}
    </div>
  );
}
