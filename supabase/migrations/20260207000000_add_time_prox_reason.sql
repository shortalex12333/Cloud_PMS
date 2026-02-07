--
-- Add time_prox to suggested_reason CHECK constraint
-- The email_suggestion_service uses 'time_prox' for time proximity matches
--

-- Drop and recreate the constraint with the new value
ALTER TABLE public.email_links DROP CONSTRAINT IF EXISTS email_links_suggested_reason_check;

ALTER TABLE public.email_links ADD CONSTRAINT email_links_suggested_reason_check
    CHECK (suggested_reason IN (
        'token_match', 'vendor_domain', 'wo_pattern', 'po_pattern',
        'serial_match', 'part_number', 'manual', 'time_prox'
    ));

COMMENT ON COLUMN public.email_links.suggested_reason IS
'Reason for suggestion: token_match, vendor_domain, wo_pattern, po_pattern, serial_match, part_number, manual, time_prox';
