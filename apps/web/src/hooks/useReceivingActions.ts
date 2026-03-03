'use client';

/**
 * useReceivingActions - Receiving Lens action hook (FE-01-07)
 *
 * Wires all receiving event action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   start_receiving_event, add_line_item, complete_receiving_event,
 *   accept_receiving, report_discrepancy, verify_line_item, link_invoice_document,
 *   extract_receiving_candidates, update_receiving_fields
 *
 * Workflow:
 *   1. Start receiving event (links to PO or shopping list)
 *   2. Add line items (scan/enter received goods)
 *   3. Verify line items (optional QC step)
 *   4. Complete receiving OR report discrepancy
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * ReceivingLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface ReceivingActionsState {
  isLoading: boolean;
  error: string | null;
}

/** Line item for receiving */
export interface ReceivingLineItem {
  part_id?: string;
  description?: string;
  quantity_received: number;
  unit?: string;
  condition?: 'new' | 'refurbished' | 'damaged' | 'defective';
  serial_number?: string;
  batch_number?: string;
  expiry_date?: string;
  storage_location?: string;
  notes?: string;
  shopping_list_item_id?: string;
}

/** Discrepancy report details */
export interface DiscrepancyReport {
  type: 'quantity_mismatch' | 'damaged' | 'wrong_item' | 'missing' | 'quality_issue' | 'other';
  description: string;
  expected_quantity?: number;
  actual_quantity?: number;
  affected_line_item_ids?: string[];
  photos?: string[];
  action_required?: 'return' | 'replace' | 'credit' | 'accept_as_is' | 'escalate';
}

/** Extracted receiving candidate from OCR analysis */
export interface ExtractedReceivingCandidate {
  part_id?: string;
  description: string;
  quantity?: number;
  unit?: string;
  confidence?: number;
  source?: string;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useReceivingActions
 *
 * Returns typed action helpers for all receiving operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param eventId - UUID of the receiving event in scope (optional for start)
 */
export function useReceivingActions(eventId?: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor - wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const context: Record<string, unknown> = {
          yacht_id: user.yachtId,
        };

        // Include receiving_id in context if available (backend expects receiving_id)
        if (eventId) {
          context.receiving_id = eventId;
        }

        const result = await executeAction(actionName, context, {
          receiving_id: eventId,
          ...payload,
        });

        if (result.status === 'error') {
          const msg = result.message || `Action '${actionName}' failed`;
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, data: result.result, message: result.message };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [user, eventId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers - one per registry action
  // -------------------------------------------------------------------------

  /**
   * create_receiving - Create a new receiving record
   *
   * Creates a standalone receiving record with vendor information,
   * delivery date, and optional currency/notes.
   *
   * @param params - Receiving creation parameters
   * @param params.vendor_name - Vendor/supplier name
   * @param params.delivery_date - Expected or actual delivery date (ISO format)
   * @param params.currency - Optional: Currency code (USD, EUR, etc.)
   * @param params.notes - Optional: Additional notes for this receiving
   */
  const createReceiving = useCallback(
    (params: {
      vendor_name: string;
      delivery_date: string;
      currency?: string;
      notes?: string;
    }) =>
      execute('create_receiving', {
        vendor_name: params.vendor_name,
        delivery_date: params.delivery_date,
        currency: params.currency,
        notes: params.notes,
      }),
    [execute]
  );

  /**
   * start_receiving_event - Start a new receiving event
   *
   * Creates a receiving event linked to a purchase order or shopping list.
   *
   * @param params - Event initialization parameters
   * @param params.order_id - Optional: Link to purchase order
   * @param params.shopping_list_item_ids - Optional: Link to shopping list items
   * @param params.supplier - Supplier name
   * @param params.delivery_reference - Delivery note/packing slip reference
   * @param params.notes - Additional receiving notes
   */
  const startReceiving = useCallback(
    (params: {
      order_id?: string;
      shopping_list_item_ids?: string[];
      supplier?: string;
      delivery_reference?: string;
      notes?: string;
    }) =>
      execute('start_receiving_event', {
        order_id: params.order_id,
        shopping_list_item_ids: params.shopping_list_item_ids,
        supplier: params.supplier,
        delivery_reference: params.delivery_reference,
        notes: params.notes,
      }),
    [execute]
  );

  /**
   * add_line_item - Add a line item to the receiving event
   *
   * Records a received item with quantity, condition, and storage location.
   * Updates parts inventory upon completion.
   *
   * @param lineItem - Line item details
   */
  const addLineItem = useCallback(
    (lineItem: ReceivingLineItem) =>
      execute('add_line_item', {
        part_id: lineItem.part_id,
        description: lineItem.description,
        quantity_received: lineItem.quantity_received,
        unit: lineItem.unit || 'each',
        condition: lineItem.condition || 'new',
        serial_number: lineItem.serial_number,
        batch_number: lineItem.batch_number,
        expiry_date: lineItem.expiry_date,
        storage_location: lineItem.storage_location,
        notes: lineItem.notes,
        shopping_list_item_id: lineItem.shopping_list_item_id,
      }),
    [execute]
  );

  /**
   * complete_receiving_event - Complete the receiving event (Accept)
   *
   * Finalizes the receiving event, updates inventory quantities,
   * and marks linked shopping list items as fulfilled.
   *
   * @param params - Completion parameters
   * @param params.completion_notes - Optional notes on completion
   * @param params.verified_by - Optional: User who verified the receiving
   */
  const completeReceiving = useCallback(
    (params?: { completion_notes?: string; verified_by?: string }) =>
      execute('complete_receiving_event', {
        completion_notes: params?.completion_notes,
        verified_by: params?.verified_by,
      }),
    [execute]
  );

  /**
   * accept_receiving - Accept delivery and auto-update stock levels
   *
   * Accepts the delivery, updates stock levels, and applies signature-based
   * verification (PIN hash + TOTP code). Updates inventory quantities for
   * all line items in the receiving event.
   *
   * @param params - Acceptance parameters
   * @param params.signature - Signature verification data
   * @param params.signature.pin_hash - Hash of the PIN code
   * @param params.signature.totp_code - Time-based one-time password
   * @param params.notes - Optional acceptance notes
   */
  const acceptReceiving = useCallback(
    (params: { signature: { pin_hash: string; totp_code: string }; notes?: string }) =>
      execute('accept_receiving', {
        signature: params.signature,
        notes: params.notes,
      }),
    [execute]
  );

  /**
   * report_discrepancy - Report a discrepancy (Reject/Issue)
   *
   * Documents issues with the received goods and triggers
   * appropriate follow-up actions (return, credit, escalation).
   *
   * @param discrepancy - Discrepancy details
   */
  const reportDiscrepancy = useCallback(
    (discrepancy: DiscrepancyReport) =>
      execute('report_discrepancy', {
        discrepancy_type: discrepancy.type,
        description: discrepancy.description,
        expected_quantity: discrepancy.expected_quantity,
        actual_quantity: discrepancy.actual_quantity,
        affected_line_item_ids: discrepancy.affected_line_item_ids,
        photos: discrepancy.photos,
        action_required: discrepancy.action_required,
      }),
    [execute]
  );

  /**
   * verify_line_item - Verify a specific line item (QC step)
   *
   * Optional quality control verification for individual line items.
   * Updates line item status and records verifier.
   *
   * @param params - Verification parameters
   * @param params.line_item_id - ID of the line item to verify
   * @param params.verified - Whether the item passes verification
   * @param params.notes - Verification notes
   */
  const verifyLineItem = useCallback(
    (params: { line_item_id: string; verified: boolean; notes?: string }) =>
      execute('verify_line_item', {
        line_item_id: params.line_item_id,
        verified: params.verified,
        verification_notes: params.notes,
      }),
    [execute]
  );

  /**
   * link_invoice_document - Attach invoice PDF to receiving record
   *
   * Associates an invoice document with the receiving event for
   * reconciliation and audit trail purposes.
   *
   * @param params - Link parameters
   * @param params.document_id - ID of the invoice document to attach
   */
  const linkInvoice = useCallback(
    (params: { document_id: string }) =>
      execute('link_invoice_document', {
        document_id: params.document_id,
      }),
    [execute]
  );

  /**
   * extract_receiving_candidates - Extract receiving candidates from OCR analysis
   *
   * Analyzes invoice images or OCR text to extract potential line items
   * for receiving. Returns an array of matched parts with confidence scores.
   *
   * @param params - Extraction parameters
   * @param params.invoice_image_id - Optional: ID of invoice image to analyze
   * @param params.ocr_text - Optional: Raw OCR text from invoice
   */
  const extractCandidates = useCallback(
    (params: { invoice_image_id?: string; ocr_text?: string }) =>
      execute('extract_receiving_candidates', {
        invoice_image_id: params.invoice_image_id,
        ocr_text: params.ocr_text,
      }),
    [execute]
  );


  /**
   * attachImage - Attach image with optional comment to receiving event
   *
   * Attaches an image to the receiving event with an optional comment.
   * Supports categorized image types for better organization and retrieval.
   *
   * @param params - Image attachment parameters
   * @param params.image_path - Path or reference to the image file
   * @param params.comment - Optional comment/description for the image
   * @param params.image_type - Optional image category (invoice, packing_slip, damage, other)
   */
  const attachImage = useCallback(
    (params: {
      image_path: string;
      comment?: string;
      image_type?: 'invoice' | 'packing_slip' | 'damage' | 'other';
    }) =>
      execute('attach_receiving_image_with_comment', {
        image_path: params.image_path,
        comment: params.comment,
        image_type: params.image_type || 'other',
      }),
    [execute]
  );


  // -------------------------------------------------------------------------
  /**
   * update_receiving_fields - Update receiving event fields
   *
   * Updates one or more fields on the receiving event.
   * Allows modification of vendor name, delivery date, currency, notes, and status.
   *
   * @param params - Fields to update
   * @param params.vendor_name - Optional: Vendor/supplier name
   * @param params.delivery_date - Optional: Delivery date
   * @param params.currency - Optional: Currency code
   * @param params.notes - Optional: Receiving notes
   * @param params.status - Optional: Event status
   */
  const updateFields = useCallback(
    (params: {
      vendor_name?: string;
      delivery_date?: string;
      currency?: string;
      notes?: string;
      status?: string;
    }) =>
      execute('update_receiving_fields', {
        vendor_name: params.vendor_name,
        delivery_date: params.delivery_date,
        currency: params.currency,
        notes: params.notes,
        status: params.status,
      }),
    [execute]
  );

  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Actions
    createReceiving,
    startReceiving,
    addLineItem,
    completeReceiving,
    acceptReceiving,
    reportDiscrepancy,
    verifyLineItem,
    linkInvoice,
    extractCandidates,
    attachImage,
    updateFields,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Receiving lens in lens_matrix.json defines role_restricted arrays.
// Permissions are now derived from the centralized service.

export interface ReceivingPermissions {
  /** Can start a new receiving event */
  canStart: boolean;
  /** Can add line items to receiving event */
  canAdd: boolean;
  /** Can complete receiving event (HOD+) */
  canComplete: boolean;
  /** Can accept receiving and auto-update stock (signature required) */
  canAccept: boolean;
  /** Can report discrepancies */
  canReject: boolean;
  /** Can verify line items (QC) */
  canVerify: boolean;
  /** Can extract receiving candidates from OCR analysis */
  canExtractCandidates: boolean;
  /** Can link invoice documents */
  canLinkInvoice: boolean;
  /** Can attach images to receiving event */
  canAttachImage: boolean;
  /** Can update receiving fields */
  canUpdateFields: boolean;
}

import { useReceivingPermissions as useCentralizedReceivingPermissions } from '@/hooks/permissions/useReceivingPermissions';

/**
 * useReceivingPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 * These are used to conditionally show (not disable) action buttons.
 */
export function useReceivingPermissions(): ReceivingPermissions {
  const central = useCentralizedReceivingPermissions();

  return {
    canStart: central.canStartReceivingEvent,
    canAdd: central.canAddLineItem,
    canComplete: central.canCompleteReceivingEvent,
    canAccept: central.canAcceptReceiving,
    canReject: central.canReportDiscrepancy,
    canVerify: central.canVerifyLineItem,
    canExtractCandidates: central.canExtractReceivingCandidates,
    canLinkInvoice: central.canLinkInvoiceDocument,
    canAttachImage: central.canAddLineItem, // Uses same permission as add
    canUpdateFields: central.canUpdateReceivingFields,
  };
}
