-- Migration: Create pms_warranty_claims table + pms-warranty-docs bucket
-- Part of: Fault Lens v1 - Warranty Claims Foundation
-- Branch: fault/entity-extraction-prefill_v1

-- Purpose: Track warranty claims from draft to approval
-- Workflow: draft (crew/HOD) → submitted (HOD) → approved (captain/manager)

BEGIN;

-- ============================================================================
-- TABLE: pms_warranty_claims
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_warranty_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Claim identification
    claim_number TEXT,  -- BACKEND_AUTO: WC-YYYY-NNNNNN

    -- Linked entities
    equipment_id UUID,
    fault_id UUID,
    work_order_id UUID,

    -- Claim details
    title TEXT NOT NULL,
    description TEXT,
    claim_type TEXT NOT NULL DEFAULT 'repair',  -- 'repair', 'replacement', 'refund'

    -- Vendor/manufacturer info
    vendor_id UUID,
    vendor_name TEXT,
    manufacturer TEXT,
    part_number TEXT,
    serial_number TEXT,
    purchase_date DATE,
    warranty_expiry DATE,

    -- Claim status
    status TEXT NOT NULL DEFAULT 'draft',  -- 'draft', 'submitted', 'under_review', 'approved', 'rejected', 'closed'

    -- Amounts
    claimed_amount NUMERIC(12, 2),
    currency TEXT DEFAULT 'USD',
    approved_amount NUMERIC(12, 2),

    -- Workflow audit
    drafted_by UUID NOT NULL,
    drafted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_by UUID,
    submitted_at TIMESTAMPTZ,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,

    -- Email composition (prepare only, never auto-send)
    email_draft JSONB,  -- {to, subject, body, attachments[]}

    -- Metadata
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_yacht FOREIGN KEY (yacht_id) REFERENCES yachts(id) ON DELETE CASCADE,
    CONSTRAINT fk_equipment FOREIGN KEY (equipment_id) REFERENCES pms_equipment(id) ON DELETE SET NULL,
    CONSTRAINT fk_fault FOREIGN KEY (fault_id) REFERENCES pms_faults(id) ON DELETE SET NULL,
    CONSTRAINT valid_status CHECK (status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'closed'))
);

-- Generate claim number
CREATE OR REPLACE FUNCTION generate_warranty_claim_number()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_year TEXT;
    v_seq INTEGER;
BEGIN
    IF NEW.claim_number IS NULL THEN
        v_year := to_char(NOW(), 'YYYY');
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(claim_number FROM 9) AS INTEGER)
        ), 0) + 1
        INTO v_seq
        FROM pms_warranty_claims
        WHERE yacht_id = NEW.yacht_id
          AND claim_number LIKE 'WC-' || v_year || '-%';

        NEW.claim_number := 'WC-' || v_year || '-' || LPAD(v_seq::TEXT, 6, '0');
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_warranty_claim_number
BEFORE INSERT ON pms_warranty_claims
FOR EACH ROW
EXECUTE FUNCTION generate_warranty_claim_number();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_warranty_claims_yacht_status
ON pms_warranty_claims(yacht_id, status);

CREATE INDEX IF NOT EXISTS idx_warranty_claims_equipment
ON pms_warranty_claims(equipment_id)
WHERE equipment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_warranty_claims_fault
ON pms_warranty_claims(fault_id)
WHERE fault_id IS NOT NULL;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_warranty_claims ENABLE ROW LEVEL SECURITY;

-- SELECT: All crew can view claims for their yacht
CREATE POLICY "crew_select_warranty_claims"
ON pms_warranty_claims FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT (draft): Crew + HOD can create drafts
CREATE POLICY "crew_insert_warranty_claims"
ON pms_warranty_claims FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND status = 'draft'
);

-- UPDATE (draft→submitted): HOD only
-- UPDATE (submitted→approved/rejected): Captain/Manager only
CREATE POLICY "hod_update_warranty_claims"
ON pms_warranty_claims FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (
        -- HOD can update drafts
        (public.is_hod(auth.uid(), public.get_user_yacht_id()) AND status IN ('draft', 'submitted'))
        -- Captain/Manager can approve/reject
        OR (public.is_manager(auth.uid(), public.get_user_yacht_id()) AND status IN ('submitted', 'under_review'))
    )
);

-- DELETE: HOD only, drafts only
CREATE POLICY "hod_delete_warranty_claims"
ON pms_warranty_claims FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND status = 'draft'
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- ============================================================================
-- STORAGE BUCKET: pms-warranty-docs
-- ============================================================================

-- Note: Bucket creation is done via Supabase dashboard or storage API
-- This documents the expected configuration

-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('pms-warranty-docs', 'pms-warranty-docs', false)
-- ON CONFLICT (id) DO NOTHING;

-- Storage policies (run after bucket exists)
-- Path pattern: {yacht_id}/claims/{claim_id}/{filename}

-- Crew + HOD can upload
CREATE POLICY "crew_upload_warranty_docs"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'pms-warranty-docs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- All crew can read (yacht-scoped)
CREATE POLICY "crew_read_warranty_docs"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'pms-warranty-docs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- HOD + captain can delete
CREATE POLICY "hod_delete_warranty_docs"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-warranty-docs'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

COMMIT;

-- ============================================================================
-- WARRANTY CLAIM WORKFLOW
-- ============================================================================
--
-- 1. draft_warranty_claim (crew/HOD)
--    - Creates claim with status='draft'
--    - Attach photos/docs to pms-warranty-docs
--    - Can edit freely
--
-- 2. submit_warranty_claim (HOD only)
--    - status: draft → submitted
--    - Validates required fields
--    - Audited with signature={}
--
-- 3. approve_warranty_claim (captain/manager)
--    - status: submitted → approved
--    - Sets approved_by, approved_at, approved_amount
--    - Audited with signature JSON
--
-- 4. reject_warranty_claim (captain/manager)
--    - status: submitted → rejected
--    - Sets rejection_reason
--    - Audited with signature JSON
--
-- ============================================================================
-- EMAIL COMPOSITION (prepare only)
-- ============================================================================
--
-- compose_warranty_email returns:
--   {
--     to: "vendor@example.com",
--     subject: "Warranty Claim WC-2026-000001",
--     body: "<paraphrased body from claim>",
--     attachments: [{name, url}]
--   }
--
-- NEVER auto-sends. User must explicitly send.
-- Send action restricted to HOD/captain/manager.
