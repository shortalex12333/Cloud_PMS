# IMPLEMENTATION SPEC: Role System & Department Structure

> **Document**: `IMPL_01_role_system.sql.md`
> **UX Source**: `readme.md`, `all_ranks.md`
> **Priority**: P0 (Foundation)
> **Target DB**: Master Database + Tenant Database

---

## Overview

This specification implements the **Role Operating Profiles** system. These are behavioral, operational, and cognitive models used to:
- Customize search ranking bias
- Interpret query intent per role
- Format answers appropriately
- Handle trust and uncertainty
- Define automation safety rules
- Enable department-based handover

---

## PART 1: MASTER DATABASE TABLES

### 1.1 `role_definitions` - Canonical role taxonomy

```sql
-- ============================================================================
-- TABLE: role_definitions (MASTER DB)
-- Purpose: System-wide role definitions
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_definitions (
    id TEXT PRIMARY KEY,
    -- e.g., 'captain', 'chief_engineer', 'bosun', 'deckhand'

    -- Display information
    display_name TEXT NOT NULL,
    display_name_plural TEXT NOT NULL,
    abbreviation TEXT,
    -- e.g., 'CE' for Chief Engineer, 'ETO' for Electro-Technical Officer

    -- Hierarchy
    department TEXT NOT NULL,
    -- Values: 'command', 'deck', 'engineering', 'interior', 'galley', 'security', 'admin'

    rank_order INTEGER NOT NULL,
    -- Lower = higher authority (Captain = 1)

    reports_to TEXT,
    -- Role ID of direct supervisor (NULL for Captain)

    -- Authority scope
    authority_level TEXT NOT NULL,
    -- Values: 'command', 'department_head', 'senior', 'junior'

    can_view_other_departments BOOLEAN DEFAULT FALSE,
    can_countersign_handover BOOLEAN DEFAULT FALSE,
    can_approve_work_orders BOOLEAN DEFAULT FALSE,
    can_view_audit_log BOOLEAN DEFAULT FALSE,

    -- Search behavior defaults
    default_search_scope TEXT DEFAULT 'own_department',
    -- Values: 'own_department', 'all_departments', 'assigned_only'

    search_result_limit INTEGER DEFAULT 10,

    -- UI preferences
    default_landing_view TEXT DEFAULT 'search',
    show_department_summary BOOLEAN DEFAULT FALSE,

    -- Metadata
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_department CHECK (department IN (
        'command', 'deck', 'engineering', 'interior', 'galley', 'security', 'admin', 'medical'
    )),
    CONSTRAINT valid_authority CHECK (authority_level IN (
        'command', 'department_head', 'senior', 'junior'
    ))
);

-- Seed all yacht roles from all_ranks.md
INSERT INTO public.role_definitions (id, display_name, display_name_plural, abbreviation, department, rank_order, reports_to, authority_level, can_view_other_departments, can_countersign_handover, can_approve_work_orders, can_view_audit_log) VALUES

-- Command
('captain', 'Captain', 'Captains', 'Capt', 'command', 1, NULL, 'command', TRUE, TRUE, TRUE, TRUE),
('staff_captain', 'Staff Captain', 'Staff Captains', 'SC', 'command', 2, 'captain', 'command', TRUE, TRUE, TRUE, TRUE),
('second_officer', 'Second Officer', 'Second Officers', '2/O', 'command', 3, 'staff_captain', 'senior', TRUE, FALSE, FALSE, FALSE),
('third_officer', 'Third Officer', 'Third Officers', '3/O', 'command', 4, 'second_officer', 'junior', FALSE, FALSE, FALSE, FALSE),
('safety_officer', 'Safety Officer', 'Safety Officers', 'SO', 'command', 5, 'captain', 'senior', TRUE, FALSE, TRUE, TRUE),

-- Deck Department
('chief_officer', 'Chief Officer', 'Chief Officers', 'C/O', 'deck', 6, 'staff_captain', 'department_head', FALSE, TRUE, TRUE, TRUE),
('bosun', 'Bosun', 'Bosuns', 'Bosun', 'deck', 7, 'chief_officer', 'senior', FALSE, TRUE, FALSE, FALSE),
('senior_deckhand', 'Senior Deckhand', 'Senior Deckhands', 'Sr DH', 'deck', 8, 'bosun', 'senior', FALSE, FALSE, FALSE, FALSE),
('deckhand', 'Deckhand', 'Deckhands', 'DH', 'deck', 9, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE),
('deckhand_tender', 'Deckhand / Tender Driver', 'Deckhand / Tender Drivers', 'DH/T', 'deck', 10, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE),
('deckhand_watersports', 'Deckhand / Watersports', 'Deckhand / Watersports', 'DH/WS', 'deck', 11, 'bosun', 'junior', FALSE, FALSE, FALSE, FALSE),

-- Engineering Department
('chief_engineer', 'Chief Engineer', 'Chief Engineers', 'CE', 'engineering', 14, 'captain', 'department_head', FALSE, TRUE, TRUE, TRUE),
('second_engineer', 'Second Engineer', 'Second Engineers', '2/E', 'engineering', 15, 'chief_engineer', 'senior', FALSE, TRUE, TRUE, FALSE),
('third_engineer', 'Third Engineer', 'Third Engineers', '3/E', 'engineering', 16, 'second_engineer', 'senior', FALSE, FALSE, FALSE, FALSE),
('eto', 'Electro-Technical Officer', 'ETOs', 'ETO', 'engineering', 17, 'chief_engineer', 'senior', FALSE, TRUE, FALSE, FALSE),
('avit_officer', 'AV/IT Officer', 'AV/IT Officers', 'AV/IT', 'engineering', 18, 'eto', 'senior', FALSE, FALSE, FALSE, FALSE),
('engineer_watchkeeper', 'Engineer Watchkeeper', 'Engineer Watchkeepers', 'E/W', 'engineering', 19, 'second_engineer', 'junior', FALSE, FALSE, FALSE, FALSE),
('motorman', 'Motorman', 'Motormen', 'MM', 'engineering', 20, 'third_engineer', 'junior', FALSE, FALSE, FALSE, FALSE),

-- Interior Department
('chief_stew', 'Chief Steward/ess', 'Chief Stewards', 'CS', 'interior', 23, 'captain', 'department_head', FALSE, TRUE, TRUE, TRUE),
('purser', 'Purser', 'Pursers', 'Purser', 'interior', 24, 'chief_stew', 'senior', FALSE, TRUE, TRUE, TRUE),
('deputy_chief_stew', 'Deputy Chief Steward/ess', 'Deputy Chiefs', 'DCS', 'interior', 25, 'chief_stew', 'senior', FALSE, TRUE, FALSE, FALSE),
('head_housekeeping', 'Head of Housekeeping', 'Housekeeping Heads', 'HH', 'interior', 26, 'chief_stew', 'senior', FALSE, FALSE, FALSE, FALSE),
('head_service', 'Head of Service', 'Service Heads', 'HS', 'interior', 27, 'chief_stew', 'senior', FALSE, FALSE, FALSE, FALSE),
('steward', 'Steward/ess', 'Stewards', 'Stew', 'interior', 28, 'deputy_chief_stew', 'junior', FALSE, FALSE, FALSE, FALSE),

-- Galley Department
('executive_chef', 'Executive Chef', 'Executive Chefs', 'Chef', 'galley', 35, 'captain', 'department_head', FALSE, TRUE, TRUE, FALSE),
('sous_chef', 'Sous Chef', 'Sous Chefs', 'Sous', 'galley', 36, 'executive_chef', 'senior', FALSE, FALSE, FALSE, FALSE),
('crew_chef', 'Crew Chef', 'Crew Chefs', 'CC', 'galley', 37, 'sous_chef', 'junior', FALSE, FALSE, FALSE, FALSE),

-- Security
('head_security', 'Head of Security', 'Security Heads', 'HoS', 'security', 40, 'captain', 'department_head', TRUE, TRUE, FALSE, TRUE),
('security_officer', 'Security Officer', 'Security Officers', 'SecO', 'security', 41, 'head_security', 'junior', FALSE, FALSE, FALSE, FALSE),

-- Medical
('ships_medic', 'Ship''s Medic', 'Ship''s Medics', 'Medic', 'medical', 42, 'captain', 'senior', TRUE, FALSE, FALSE, FALSE),

-- Admin (Shore-based or hybrid)
('yacht_manager', 'Yacht Manager', 'Yacht Managers', 'YM', 'admin', 0, NULL, 'command', TRUE, TRUE, TRUE, TRUE)

ON CONFLICT (id) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    rank_order = EXCLUDED.rank_order;
```

### 1.2 `department_definitions` - Department groupings

```sql
-- ============================================================================
-- TABLE: department_definitions (MASTER DB)
-- Purpose: Define departments and their domain mappings
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.department_definitions (
    id TEXT PRIMARY KEY,
    -- e.g., 'engineering', 'deck', 'interior'

    display_name TEXT NOT NULL,
    description TEXT,

    -- Domain associations (which data domains this department owns)
    owned_domains TEXT[] NOT NULL,
    -- e.g., ['Equipment', 'Faults', 'Work Orders'] for engineering

    -- Handover configuration
    handover_bucket_template JSONB NOT NULL,
    -- Template for what appears in department handover

    -- UI configuration
    icon TEXT,
    color TEXT,
    display_order INTEGER DEFAULT 100,

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed departments with domain mappings
INSERT INTO public.department_definitions (id, display_name, owned_domains, handover_bucket_template, icon, display_order) VALUES

('command', 'Command',
 ARRAY['Navigation', 'Compliance', 'Safety', 'Crew'],
 '{"sections": ["Bridge Operations", "Regulatory Items", "Crew Status", "Weather & Passage"]}',
 'anchor', 1),

('engineering', 'Engineering',
 ARRAY['Equipment', 'Faults', 'Work Orders', 'Technical Documents'],
 '{"sections": ["Engine Room Status", "Active Faults", "Work Orders In Progress", "Pending Parts", "Deferred Maintenance"]}',
 'settings', 2),

('deck', 'Deck',
 ARRAY['Deck Equipment', 'Tenders', 'Watersports', 'Exterior'],
 '{"sections": ["Deck Status", "Tender Operations", "Exterior Condition", "Scheduled Activities"]}',
 'ship', 3),

('interior', 'Interior',
 ARRAY['Inventory', 'Housekeeping', 'Service', 'Guest Preferences'],
 '{"sections": ["Guest Status", "Service Schedule", "Inventory Alerts", "Housekeeping Status"]}',
 'home', 4),

('galley', 'Galley',
 ARRAY['Provisions', 'Menu', 'Dietary'],
 '{"sections": ["Provisioning Status", "Menu Planning", "Dietary Requirements"]}',
 'utensils', 5),

('security', 'Security',
 ARRAY['Access Control', 'CCTV', 'Incidents'],
 '{"sections": ["Security Status", "Incident Reports", "Access Log"]}',
 'shield', 6),

('admin', 'Administration',
 ARRAY['Finance', 'HR', 'Procurement', 'Compliance'],
 '{"sections": ["Financial Overview", "Crew Admin", "Procurement Status"]}',
 'briefcase', 7)

ON CONFLICT (id) DO UPDATE SET
    owned_domains = EXCLUDED.owned_domains,
    handover_bucket_template = EXCLUDED.handover_bucket_template;
```

---

## PART 2: TENANT DATABASE TABLES

### 2.1 `user_role_assignments` - Per-yacht role assignments

```sql
-- ============================================================================
-- TABLE: user_role_assignments (TENANT DB)
-- Purpose: Assign roles to users on this yacht
-- Note: Extends existing user_roles table
-- ============================================================================

-- Add columns to existing user_roles table
ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS role_definition_id TEXT;
-- Links to role_definitions.id

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS department TEXT;

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS authority_level TEXT;

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS custom_permissions JSONB DEFAULT '{}';
-- Override default permissions for this user

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS assigned_by UUID REFERENCES auth.users(id);

ALTER TABLE public.user_roles
ADD COLUMN IF NOT EXISTS assignment_notes TEXT;

-- Update constraint
ALTER TABLE public.user_roles
DROP CONSTRAINT IF EXISTS user_roles_role_check;

ALTER TABLE public.user_roles
ADD CONSTRAINT valid_role CHECK (role IN (
    'captain', 'staff_captain', 'second_officer', 'third_officer', 'safety_officer',
    'chief_officer', 'bosun', 'senior_deckhand', 'deckhand', 'deckhand_tender', 'deckhand_watersports',
    'chief_engineer', 'second_engineer', 'third_engineer', 'eto', 'avit_officer', 'engineer_watchkeeper', 'motorman',
    'chief_stew', 'purser', 'deputy_chief_stew', 'head_housekeeping', 'head_service', 'steward',
    'executive_chef', 'sous_chef', 'crew_chef',
    'head_security', 'security_officer', 'ships_medic',
    'yacht_manager', 'member'
));

-- Index for department queries
CREATE INDEX IF NOT EXISTS idx_user_roles_department ON public.user_roles(yacht_id, department);
```

### 2.2 `role_search_profiles` - Search behavior per role

```sql
-- ============================================================================
-- TABLE: role_search_profiles (TENANT DB)
-- Purpose: Configure search behavior for each role
-- UX Source: Role profiles define "Search behavior profile"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_search_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID,
    -- NULL = global default, yacht_id = yacht-specific override

    role_id TEXT NOT NULL,
    -- Links to role_definitions.id

    -- Query interpretation
    default_intent TEXT DEFAULT 'information',
    -- Default assumed intent for ambiguous queries

    intent_biases JSONB DEFAULT '{}',
    -- Format: {"diagnostic": 1.5, "action": 0.8}
    -- Multipliers for intent scoring

    -- Entity extraction biases
    entity_biases JSONB DEFAULT '{}',
    -- Format: {"equipment": 1.5, "guest": 0.5}
    -- Which entity types to prioritize

    -- Result ranking
    domain_weights JSONB NOT NULL,
    -- Format: {"Equipment": 2.0, "Documents": 1.5, "Inventory": 0.5}
    -- Higher weight = higher ranking

    result_type_order TEXT[] DEFAULT '{}',
    -- Order to display result types
    -- e.g., ['fault', 'work_order', 'document'] for engineers

    -- Answer formatting
    answer_style TEXT DEFAULT 'technical',
    -- Values: 'technical', 'summary', 'narrative', 'concise'

    default_detail_level TEXT DEFAULT 'normal',
    -- Values: 'minimal', 'normal', 'detailed'

    -- Time sensitivity
    recency_boost DECIMAL(3,2) DEFAULT 1.0,
    -- How much to boost recent results (1.0 = no boost)

    -- Handover relevance
    handover_auto_include TEXT[] DEFAULT '{}',
    -- Which domains auto-suggest for handover
    -- e.g., ['Faults', 'Work Orders'] for engineers

    -- Sample queries (for UI hints)
    sample_queries TEXT[] DEFAULT '{}',
    -- Examples from role profile

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, role_id)
);

-- Seed search profiles based on role documents
INSERT INTO public.role_search_profiles (yacht_id, role_id, intent_biases, entity_biases, domain_weights, result_type_order, answer_style, sample_queries, handover_auto_include) VALUES

-- Captain (from 02-captain.md)
(NULL, 'captain',
 '{"summary": 1.5, "risk": 1.5, "diagnostic": 1.0}',
 '{"risk": 2.0, "exception": 1.8, "compliance": 1.5, "crew": 1.3}',
 '{"Faults": 2.0, "Compliance": 1.8, "Safety": 1.8, "Work Orders": 1.5, "Equipment": 1.0}',
 ARRAY['fault', 'compliance', 'work_order', 'crew_issue'],
 'summary',
 ARRAY[
     'What unresolved risks exist right now?',
     'What would keep the chief engineer awake tonight?',
     'Is anything overdue that affects safety or compliance?',
     'Summarise guest-impacting issues'
 ],
 ARRAY['Faults', 'Compliance', 'Safety']
),

-- Chief Engineer (from 03-chief-engineer.md)
(NULL, 'chief_engineer',
 '{"diagnostic": 1.8, "action": 1.2, "recall": 1.5}',
 '{"equipment": 2.0, "fault": 2.0, "part": 1.5, "system": 1.5}',
 '{"Faults": 2.0, "Equipment": 2.0, "Work Orders": 1.8, "Technical Documents": 1.5, "Inventory": 1.3}',
 ARRAY['fault', 'equipment', 'work_order', 'document', 'part'],
 'technical',
 ARRAY[
     'Has this fault happened before?',
     'Show me the last time we worked on this pump',
     'What maintenance is overdue that actually matters?',
     'What did the previous chief engineer worry about?',
     'Which systems are living on borrowed time?'
 ],
 ARRAY['Faults', 'Equipment', 'Work Orders', 'Deferred Maintenance']
),

-- Engineer Watchkeeper (from 04-engineer-watchkeeper.md)
(NULL, 'engineer_watchkeeper',
 '{"diagnostic": 2.0, "action": 1.5, "information": 1.2}',
 '{"alarm": 2.0, "fault": 2.0, "equipment": 1.8, "procedure": 1.5}',
 '{"Faults": 2.5, "Equipment": 2.0, "Technical Documents": 1.5, "Work Orders": 1.0}',
 ARRAY['fault', 'alarm', 'equipment', 'procedure'],
 'technical',
 ARRAY[
     'Generator 2 alarm troubleshooting',
     'What alarms happened overnight?',
     'Normal operating parameters for main engine',
     'Procedure for transferring fuel'
 ],
 ARRAY['Faults', 'Alarms']
),

-- Bosun (from 05-bosun.md)
(NULL, 'bosun',
 '{"action": 1.5, "information": 1.2}',
 '{"deck_equipment": 2.0, "tender": 1.8, "schedule": 1.5, "weather": 1.3}',
 '{"Deck Equipment": 2.0, "Tenders": 1.8, "Work Orders": 1.5, "Weather": 1.3}',
 ARRAY['deck_equipment', 'tender', 'work_order', 'schedule'],
 'concise',
 ARRAY[
     'Anchor windlass service history',
     'Tender fuel levels',
     'Deck schedule today',
     'Weather forecast'
 ],
 ARRAY['Deck Equipment', 'Tender Operations']
),

-- Deckhand (from 06-deckhand.md)
(NULL, 'deckhand',
 '{"action": 1.3, "information": 1.0}',
 '{"task": 1.5, "equipment": 1.3, "procedure": 1.2}',
 '{"Work Orders": 1.5, "Deck Equipment": 1.3, "Procedures": 1.2}',
 ARRAY['task', 'work_order', 'procedure'],
 'concise',
 ARRAY[
     'My tasks today',
     'How to operate deck crane',
     'Tender launch checklist'
 ],
 ARRAY[]
),

-- Chief Stew (from 07-chief-stew.md)
(NULL, 'chief_stew',
 '{"information": 1.5, "recall": 1.5, "action": 1.2}',
 '{"guest": 2.5, "preference": 2.0, "inventory": 1.5, "service": 1.5}',
 '{"Guest Preferences": 2.5, "Inventory": 1.8, "Service": 1.5, "Interior": 1.3}',
 ARRAY['guest_preference', 'inventory', 'service_item', 'schedule'],
 'narrative',
 ARRAY[
     'Guest 1 preferences summary',
     'Anything pending for tonight''s dinner?',
     'Inventory of champagne?',
     'Issues left by previous chief stew?'
 ],
 ARRAY['Guest Preferences', 'Service', 'Inventory']
),

-- Steward (from 08-stew.md)
(NULL, 'steward',
 '{"information": 1.3, "action": 1.2}',
 '{"guest": 2.0, "cabin": 1.5, "inventory": 1.3}',
 '{"Guest Preferences": 2.0, "Inventory": 1.5, "Housekeeping": 1.3}',
 ARRAY['guest_preference', 'inventory', 'cabin_status'],
 'concise',
 ARRAY[
     'Cabin 3 preferences',
     'Laundry schedule',
     'Wine inventory'
 ],
 ARRAY[]
),

-- Purser (from 09-purser-admin.md)
(NULL, 'purser',
 '{"information": 1.5, "action": 1.3}',
 '{"procurement": 2.0, "financial": 1.8, "compliance": 1.5, "document": 1.5}',
 '{"Procurement": 2.0, "Finance": 1.8, "Compliance": 1.5, "Documents": 1.3}',
 ARRAY['purchase_order', 'invoice', 'compliance_doc', 'financial'],
 'summary',
 ARRAY[
     'Outstanding purchase orders',
     'Budget status',
     'Crew certification expiry',
     'Pending invoices'
 ],
 ARRAY['Procurement', 'Compliance']
),

-- ETO (from 10-eto-avit.md)
(NULL, 'eto',
 '{"diagnostic": 1.8, "technical": 1.5, "action": 1.2}',
 '{"electrical": 2.0, "network": 1.8, "av_system": 1.8, "equipment": 1.5}',
 '{"Equipment": 2.0, "Technical Documents": 1.8, "Work Orders": 1.5, "Network": 1.5}',
 ARRAY['equipment', 'fault', 'document', 'network_issue'],
 'technical',
 ARRAY[
     'Network diagram',
     'AV system status',
     'Electrical distribution overview',
     'CCTV system faults'
 ],
 ARRAY['Electrical', 'AV Systems', 'Network']
)

ON CONFLICT (yacht_id, role_id) DO UPDATE SET
    intent_biases = EXCLUDED.intent_biases,
    domain_weights = EXCLUDED.domain_weights,
    sample_queries = EXCLUDED.sample_queries;
```

### 2.3 `role_handover_buckets` - Handover sections per role

```sql
-- ============================================================================
-- TABLE: role_handover_buckets (TENANT DB)
-- Purpose: Define what appears in handover for each role
-- UX Source: "Handover sensitivity" in role profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_handover_buckets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    role_id TEXT NOT NULL,
    department TEXT NOT NULL,

    -- Bucket configuration
    bucket_name TEXT NOT NULL,
    -- e.g., "Active Faults", "Deferred Maintenance", "Guest Preferences"

    bucket_order INTEGER NOT NULL,
    -- Display order within role's handover

    -- Data source
    source_entity_types TEXT[] NOT NULL,
    -- Which entity types populate this bucket
    -- e.g., ['fault', 'equipment'] or ['guest_preference']

    filter_criteria JSONB DEFAULT '{}',
    -- Additional filters
    -- e.g., {"status": ["active", "in_progress"], "severity": ["high", "critical"]}

    -- Auto-population rules
    auto_populate BOOLEAN DEFAULT TRUE,
    -- Should Celeste auto-propose items?

    auto_populate_criteria JSONB DEFAULT '{}',
    -- Rules for auto-population
    -- e.g., {"changed_today": true, "severity_min": "high"}

    -- Display
    max_items INTEGER DEFAULT 10,
    show_if_empty BOOLEAN DEFAULT FALSE,
    empty_message TEXT DEFAULT 'No items',

    -- Critical marking
    is_critical_bucket BOOLEAN DEFAULT FALSE,
    -- Items in critical buckets get priority in handover

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, role_id, bucket_name)
);

-- Seed handover buckets for key roles
INSERT INTO public.role_handover_buckets (yacht_id, role_id, department, bucket_name, bucket_order, source_entity_types, filter_criteria, auto_populate_criteria, is_critical_bucket) VALUES

-- Captain handover buckets
(NULL, 'captain', 'command', 'Safety & Compliance', 1, ARRAY['compliance', 'safety_issue'], '{"status": ["open", "pending"]}', '{"is_critical": true}', TRUE),
(NULL, 'captain', 'command', 'Department Summaries', 2, ARRAY['department_summary'], '{}', '{"changed_today": true}', FALSE),
(NULL, 'captain', 'command', 'Crew Issues', 3, ARRAY['crew_issue', 'hr_item'], '{"status": ["open"]}', '{}', FALSE),
(NULL, 'captain', 'command', 'Guest Impact Items', 4, ARRAY['fault', 'service_issue'], '{"guest_impact": true}', '{}', TRUE),

-- Chief Engineer handover buckets
(NULL, 'chief_engineer', 'engineering', 'Active Faults', 1, ARRAY['fault'], '{"status": ["active", "acknowledged"]}', '{"severity_min": "medium"}', TRUE),
(NULL, 'chief_engineer', 'engineering', 'Work Orders In Progress', 2, ARRAY['work_order'], '{"status": ["in_progress", "blocked"]}', '{}', FALSE),
(NULL, 'chief_engineer', 'engineering', 'Pending Parts', 3, ARRAY['shopping_list_item'], '{"state": ["COMMITTED", "ORDERED"]}', '{}', FALSE),
(NULL, 'chief_engineer', 'engineering', 'Deferred Maintenance', 4, ARRAY['work_order', 'maintenance_item'], '{"deferred": true}', '{}', FALSE),
(NULL, 'chief_engineer', 'engineering', 'Equipment Concerns', 5, ARRAY['equipment'], '{"status": ["maintenance", "down"]}', '{}', TRUE),

-- Engineer Watchkeeper handover buckets
(NULL, 'engineer_watchkeeper', 'engineering', 'Active Alarms', 1, ARRAY['fault', 'alarm'], '{"status": ["active"]}', '{}', TRUE),
(NULL, 'engineer_watchkeeper', 'engineering', 'Running Equipment Notes', 2, ARRAY['equipment_note'], '{}', '{"changed_today": true}', FALSE),
(NULL, 'engineer_watchkeeper', 'engineering', 'Watch Tasks', 3, ARRAY['work_order'], '{"assigned_to_watch": true}', '{}', FALSE),

-- Chief Stew handover buckets
(NULL, 'chief_stew', 'interior', 'Guest Preferences Updates', 1, ARRAY['guest_preference'], '{}', '{"changed_today": true}', TRUE),
(NULL, 'chief_stew', 'interior', 'Service Schedule', 2, ARRAY['service_schedule'], '{}', '{}', FALSE),
(NULL, 'chief_stew', 'interior', 'Inventory Alerts', 3, ARRAY['inventory_alert', 'part'], '{"stock_low": true}', '{}', FALSE),
(NULL, 'chief_stew', 'interior', 'Interior Issues', 4, ARRAY['fault', 'work_order'], '{"department": "interior"}', '{}', FALSE),

-- Bosun handover buckets
(NULL, 'bosun', 'deck', 'Deck Status', 1, ARRAY['deck_status', 'equipment'], '{"department": "deck"}', '{}', FALSE),
(NULL, 'bosun', 'deck', 'Tender Operations', 2, ARRAY['tender_log', 'tender_issue'], '{}', '{}', FALSE),
(NULL, 'bosun', 'deck', 'Scheduled Activities', 3, ARRAY['activity', 'schedule'], '{}', '{}', FALSE),
(NULL, 'bosun', 'deck', 'Deck Work Orders', 4, ARRAY['work_order'], '{"department": "deck"}', '{}', FALSE)

ON CONFLICT (yacht_id, role_id, bucket_name) DO UPDATE SET
    source_entity_types = EXCLUDED.source_entity_types,
    filter_criteria = EXCLUDED.filter_criteria;
```

---

## PART 3: RPC FUNCTIONS

### 3.1 `get_user_role_profile()` - Get role configuration for user

```sql
-- ============================================================================
-- FUNCTION: get_user_role_profile
-- Purpose: Get complete role configuration for current user
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_role_profile()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_role TEXT;
    v_department TEXT;
    v_search_profile RECORD;
    v_handover_buckets JSONB;
    v_permissions JSONB;
BEGIN
    v_user_id := auth.uid();

    -- Get user's yacht and role
    SELECT yacht_id INTO v_yacht_id FROM user_profiles WHERE id = v_user_id;

    SELECT ur.role, ur.department INTO v_role, v_department
    FROM user_roles ur
    WHERE ur.user_id = v_user_id AND ur.is_active = TRUE
    LIMIT 1;

    -- Default if no role assigned
    v_role := COALESCE(v_role, 'member');
    v_department := COALESCE(v_department, 'deck');

    -- Get search profile (yacht-specific or global default)
    SELECT * INTO v_search_profile
    FROM role_search_profiles
    WHERE role_id = v_role
    AND (yacht_id = v_yacht_id OR yacht_id IS NULL)
    ORDER BY yacht_id NULLS LAST
    LIMIT 1;

    -- Get handover buckets
    SELECT jsonb_agg(jsonb_build_object(
        'bucket_name', bucket_name,
        'bucket_order', bucket_order,
        'source_entity_types', source_entity_types,
        'is_critical', is_critical_bucket
    ) ORDER BY bucket_order)
    INTO v_handover_buckets
    FROM role_handover_buckets
    WHERE role_id = v_role
    AND (yacht_id = v_yacht_id OR yacht_id IS NULL)
    AND active = TRUE;

    -- Build permissions object
    v_permissions := jsonb_build_object(
        'can_view_other_departments', v_role IN ('captain', 'staff_captain', 'yacht_manager'),
        'can_countersign_handover', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'bosun', 'yacht_manager'),
        'can_approve_work_orders', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'yacht_manager'),
        'can_view_audit_log', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'purser', 'yacht_manager')
    );

    RETURN jsonb_build_object(
        'user_id', v_user_id,
        'yacht_id', v_yacht_id,
        'role', v_role,
        'department', v_department,
        'permissions', v_permissions,
        'search_profile', CASE WHEN v_search_profile IS NOT NULL THEN
            jsonb_build_object(
                'intent_biases', v_search_profile.intent_biases,
                'entity_biases', v_search_profile.entity_biases,
                'domain_weights', v_search_profile.domain_weights,
                'result_type_order', v_search_profile.result_type_order,
                'answer_style', v_search_profile.answer_style,
                'sample_queries', v_search_profile.sample_queries,
                'handover_auto_include', v_search_profile.handover_auto_include
            )
            ELSE NULL END,
        'handover_buckets', COALESCE(v_handover_buckets, '[]'::jsonb)
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_role_profile TO authenticated;
```

### 3.2 `apply_role_search_bias()` - Apply role-based ranking

```sql
-- ============================================================================
-- FUNCTION: apply_role_search_bias
-- Purpose: Adjust search result ranking based on user's role
-- UX Requirement: "Search ranking bias" per role
-- ============================================================================

CREATE OR REPLACE FUNCTION public.apply_role_search_bias(
    p_results JSONB,
    p_user_role TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_profile RECORD;
    v_biased_results JSONB;
    v_result JSONB;
    v_domain_weight DECIMAL;
    v_adjusted_score DECIMAL;
BEGIN
    -- Get role's search profile
    SELECT * INTO v_profile
    FROM role_search_profiles
    WHERE role_id = p_user_role
    LIMIT 1;

    IF v_profile IS NULL THEN
        RETURN p_results;  -- No profile, return unmodified
    END IF;

    -- Apply domain weights to each result
    SELECT jsonb_agg(
        result || jsonb_build_object(
            'adjusted_score',
            COALESCE((result->>'relevance_score')::DECIMAL, 1.0) *
            COALESCE((v_profile.domain_weights->>result->>'domain')::DECIMAL, 1.0)
        )
        ORDER BY
            COALESCE((result->>'relevance_score')::DECIMAL, 1.0) *
            COALESCE((v_profile.domain_weights->>result->>'domain')::DECIMAL, 1.0) DESC
    )
    INTO v_biased_results
    FROM jsonb_array_elements(p_results) AS result;

    RETURN COALESCE(v_biased_results, '[]'::jsonb);
END;
$$;
```

### 3.3 `get_department_handover_template()` - Generate handover for role

```sql
-- ============================================================================
-- FUNCTION: get_department_handover_template
-- Purpose: Generate handover document structure for a role
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_department_handover_template(
    p_yacht_id UUID,
    p_role_id TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_template JSONB;
    v_buckets JSONB;
BEGIN
    -- Get bucket definitions for this role
    SELECT jsonb_agg(jsonb_build_object(
        'bucket_id', id,
        'bucket_name', bucket_name,
        'bucket_order', bucket_order,
        'source_entity_types', source_entity_types,
        'filter_criteria', filter_criteria,
        'auto_populate', auto_populate,
        'is_critical', is_critical_bucket,
        'max_items', max_items,
        'show_if_empty', show_if_empty
    ) ORDER BY bucket_order)
    INTO v_buckets
    FROM role_handover_buckets
    WHERE (yacht_id = p_yacht_id OR yacht_id IS NULL)
    AND role_id = p_role_id
    AND active = TRUE;

    -- Build template
    v_template := jsonb_build_object(
        'role_id', p_role_id,
        'buckets', COALESCE(v_buckets, '[]'::jsonb),
        'template_version', '1.0',
        'generated_at', NOW()
    );

    RETURN v_template;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_department_handover_template TO authenticated;
```

---

## PART 4: RLS POLICIES

```sql
-- ============================================================================
-- RLS POLICIES: Role tables
-- ============================================================================

-- role_search_profiles: Read for authenticated users
ALTER TABLE public.role_search_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "search_profiles_read" ON public.role_search_profiles
    FOR SELECT USING (
        yacht_id IS NULL OR
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );

-- role_handover_buckets: Read for authenticated users
ALTER TABLE public.role_handover_buckets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "handover_buckets_read" ON public.role_handover_buckets
    FOR SELECT USING (
        yacht_id IS NULL OR
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );
```

---

## PART 5: API CONTRACT

### 5.1 Role Profile Response

```typescript
interface RoleProfile {
  user_id: string;
  yacht_id: string;
  role: string;              // 'captain', 'chief_engineer', etc.
  department: string;        // 'command', 'engineering', etc.

  permissions: {
    can_view_other_departments: boolean;
    can_countersign_handover: boolean;
    can_approve_work_orders: boolean;
    can_view_audit_log: boolean;
  };

  search_profile: {
    intent_biases: Record<string, number>;
    entity_biases: Record<string, number>;
    domain_weights: Record<string, number>;
    result_type_order: string[];
    answer_style: 'technical' | 'summary' | 'narrative' | 'concise';
    sample_queries: string[];
    handover_auto_include: string[];
  };

  handover_buckets: Array<{
    bucket_name: string;
    bucket_order: number;
    source_entity_types: string[];
    is_critical: boolean;
  }>;
}
```

---

## PART 6: VALIDATION CHECKLIST

Before deployment, verify:

- [ ] `role_definitions` seeded with all yacht roles
- [ ] `department_definitions` seeded with domain mappings
- [ ] `user_role_assignments` links to role_definitions
- [ ] `role_search_profiles` configured for key roles
- [ ] `role_handover_buckets` defined for department heads
- [ ] `get_user_role_profile()` returns complete configuration
- [ ] `apply_role_search_bias()` correctly weights results
- [ ] Captain sees cross-department results
- [ ] Engineers see technical-first results
- [ ] Interior sees guest-first results
- [ ] Sample queries appear in search UI
- [ ] Handover buckets populate correctly per role

---

## RELATED DOCUMENTS

- `readme.md` - Role profiles overview
- `all_ranks.md` - Complete rank hierarchy
- `02-captain.md` through `10-eto-avit.md` - Individual role profiles
- `IMPL_01_search_intelligence.sql.md` - Search integration
- `IMPL_03_handover_continuity.sql.md` - Handover integration
