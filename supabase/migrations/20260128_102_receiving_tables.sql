-- ============================================================================
-- MIGRATION: 20260128_102_receiving_tables.sql
-- PURPOSE: Create Receiving Lens v1 tables
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- TABLES:
--   1. pms_receiving (header)
--   2. pms_receiving_items (line items)
--   3. pms_receiving_documents (photos/PDFs linked to receiving)
--   4. pms_receiving_extractions (advisory OCR/extraction results)
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE 1: pms_receiving (header)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,

    -- Vendor information
    vendor_name TEXT,
    vendor_reference TEXT,  -- invoice number, AWB, packing slip number

    -- Receipt metadata
    received_date DATE NOT NULL DEFAULT CURRENT_DATE,
    received_by UUID NOT NULL,  -- Who received/created this record
    status TEXT NOT NULL DEFAULT 'draft',

    -- Financial fields (set at acceptance)
    currency TEXT,
    subtotal NUMERIC(14,2),
    tax_total NUMERIC(14,2),
    total NUMERIC(14,2),

    -- Optional linkages
    linked_work_order_id UUID,  -- FK to pms_work_orders if exists
    notes TEXT,
    properties JSONB,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,  -- Same as received_by typically

    -- Status constraint (added in next migration)
    CONSTRAINT pms_receiving_status_check CHECK (
        status IN ('draft', 'in_review', 'accepted', 'rejected')
    )
);

COMMENT ON TABLE public.pms_receiving IS 'Receiving Lens v1: Header records for received invoices, packages, documents';
COMMENT ON COLUMN public.pms_receiving.vendor_reference IS 'Invoice number, AWB, packing slip, or other vendor reference';
COMMENT ON COLUMN public.pms_receiving.status IS 'Draft → in_review → accepted/rejected';
COMMENT ON COLUMN public.pms_receiving.properties IS 'Additional metadata (session_id, extracted_confidence, etc.)';

-- ============================================================================
-- TABLE 2: pms_receiving_items (line items)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Part linkage
    part_id UUID,  -- FK to pms_parts if exists

    -- Item details
    description TEXT,
    quantity_expected NUMERIC(12,2),
    quantity_received NUMERIC(12,2) NOT NULL DEFAULT 0,

    -- Pricing
    unit_price NUMERIC(14,4),
    currency TEXT,

    -- Metadata
    properties JSONB,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Quantity constraint (non-negative)
    CONSTRAINT pms_receiving_items_qty_check CHECK (quantity_received >= 0)
);

COMMENT ON TABLE public.pms_receiving_items IS 'Receiving Lens v1: Line items for received goods';
COMMENT ON COLUMN public.pms_receiving_items.description IS 'Part name or description; required if part_id is null';
COMMENT ON COLUMN public.pms_receiving_items.quantity_expected IS 'Expected quantity from PO/order; null if ad-hoc';
COMMENT ON COLUMN public.pms_receiving_items.quantity_received IS 'Actual quantity received';

-- ============================================================================
-- TABLE 3: pms_receiving_documents (attachments)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Document linkage
    document_id UUID NOT NULL,  -- FK to doc_metadata

    -- Document metadata
    doc_type TEXT,  -- 'invoice', 'packing_slip', 'photo'
    comment TEXT,   -- inline comment about this attachment

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_receiving_documents IS 'Receiving Lens v1: Photos and PDFs attached to receiving records';
COMMENT ON COLUMN public.pms_receiving_documents.document_id IS 'Foreign key to doc_metadata.id';
COMMENT ON COLUMN public.pms_receiving_documents.doc_type IS 'Document type: invoice, packing_slip, photo';
COMMENT ON COLUMN public.pms_receiving_documents.comment IS 'Inline comment from attach_receiving_image_with_comment action';

-- ============================================================================
-- TABLE 4: pms_receiving_extractions (advisory OCR results)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.pms_receiving_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    receiving_id UUID NOT NULL REFERENCES public.pms_receiving(id) ON DELETE CASCADE,

    -- Extraction source
    source_document_id UUID NOT NULL,  -- FK to doc_metadata

    -- Extraction results (advisory only)
    payload JSONB NOT NULL,  -- {vendor_name, total, line_items: [], confidences: {}, flags: []}

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_receiving_extractions IS 'Receiving Lens v1: Advisory OCR/extraction results (non-authoritative)';
COMMENT ON COLUMN public.pms_receiving_extractions.payload IS 'Extracted fields with confidence scores; advisory only - handlers must not auto-apply';
COMMENT ON COLUMN public.pms_receiving_extractions.source_document_id IS 'Document that was scanned/extracted';

COMMIT;

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Receiving Lens v1 tables created (pms_receiving, pms_receiving_items, pms_receiving_documents, pms_receiving_extractions)';
END $$;
