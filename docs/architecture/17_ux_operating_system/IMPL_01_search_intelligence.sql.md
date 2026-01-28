# IMPLEMENTATION SPEC: Search Intelligence System

> **Document**: `IMPL_01_search_intelligence.sql.md`
> **UX Source**: `02-search-as-interface.md`
> **Priority**: P0 (Foundation)
> **Target DB**: Tenant Database

---

## Overview

This specification implements the **Search as Interface** paradigm defined in `02-search-as-interface.md`. Search is the PRIMARY interface - not a feature. The backend must stream search in three phases:

1. **Interpretation** - entity extraction, intent detection, uncertainty resolution
2. **Acknowledgement** - UI renders understanding strip
3. **Results & Microactions** - cards, evidence, proposed actions

---

## PART 1: NEW TABLES

### 1.1 `search_sessions` - Tracks each search interaction

```sql
-- ============================================================================
-- TABLE: search_sessions
-- Purpose: Track each search interaction for reconstruction and audit
-- UX Requirement: "users can reconstruct what they were doing"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.search_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id),

    -- Original query
    query_text TEXT NOT NULL,
    query_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Interpretation phase output (streamed first)
    interpreted_entities JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"type": "equipment", "value": "Generator", "confidence": 0.95, "source_span": [0,9]}]

    interpreted_intent TEXT,
    -- Values: 'information', 'action', 'navigation', 'recall', 'diagnostic'

    confidence_branches JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"interpretation": "Generator alarm history", "confidence": 0.7}, {"interpretation": "Generator cooling manual", "confidence": 0.3}]

    uncertainty_shown BOOLEAN DEFAULT FALSE,
    -- True if user was shown disambiguation options

    -- User corrections (if any)
    user_corrections JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"removed_entity": "Cooling", "added_entity": "Alarm", "timestamp": "..."}]

    -- Final interpretation after corrections
    final_entities JSONB,
    final_intent TEXT,

    -- Results phase
    results_count INTEGER DEFAULT 0,
    microactions_offered JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"action_id": "create_work_order", "relevance": 0.9}]

    -- User action taken
    action_selected TEXT,
    -- Action ID if user clicked a microaction

    result_clicked_id UUID,
    result_clicked_type TEXT,
    -- What result did the user click (if any)

    -- Session metadata
    duration_ms INTEGER,
    -- Time from query to final action/abandonment

    abandoned BOOLEAN DEFAULT FALSE,
    -- True if user left without action

    session_context JSONB,
    -- Additional context: device, previous_session_id, etc.

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_intent CHECK (interpreted_intent IN (
        'information', 'action', 'navigation', 'recall', 'diagnostic', NULL
    ))
);

-- Indexes for search session analysis
CREATE INDEX idx_search_sessions_yacht_timestamp ON public.search_sessions(yacht_id, query_timestamp DESC);
CREATE INDEX idx_search_sessions_user ON public.search_sessions(user_id, query_timestamp DESC);
CREATE INDEX idx_search_sessions_intent ON public.search_sessions(yacht_id, interpreted_intent);
CREATE INDEX idx_search_sessions_abandoned ON public.search_sessions(yacht_id, abandoned) WHERE abandoned = TRUE;
CREATE INDEX idx_search_sessions_entities ON public.search_sessions USING GIN (interpreted_entities);

-- RLS Policy
ALTER TABLE public.search_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "search_sessions_yacht_isolation" ON public.search_sessions
    FOR ALL USING (yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

### 1.2 `entity_definitions` - Canonical entity types for extraction

```sql
-- ============================================================================
-- TABLE: entity_definitions
-- Purpose: Define extractable entity types for search understanding
-- UX Requirement: "extracted entities shown as neutral, pill-style tokens"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.entity_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID,
    -- NULL = global/shared definitions, yacht_id = yacht-specific

    entity_type TEXT NOT NULL,
    -- Values: 'equipment', 'system', 'fault', 'part', 'document', 'person',
    --         'location', 'date', 'action_verb', 'status', 'severity'

    canonical_name TEXT NOT NULL,
    -- The standardized name shown in UI

    aliases TEXT[] DEFAULT '{}',
    -- Alternative names that map to this entity
    -- e.g., ["gen", "genset", "generator set"] -> "Generator"

    parent_type TEXT,
    -- For hierarchical entities (e.g., "Cooling System" parent of "Sea Water Pump")

    linked_table TEXT,
    -- Which table this entity links to (e.g., 'pms_equipment', 'pms_parts')

    icon TEXT,
    -- Icon identifier for UI rendering

    color_hint TEXT,
    -- Optional color for entity pill (neutral by default)

    priority INTEGER DEFAULT 100,
    -- Lower = higher priority in disambiguation

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, entity_type, canonical_name)
);

-- Indexes
CREATE INDEX idx_entity_definitions_yacht ON public.entity_definitions(yacht_id);
CREATE INDEX idx_entity_definitions_type ON public.entity_definitions(entity_type);
CREATE INDEX idx_entity_definitions_aliases ON public.entity_definitions USING GIN (aliases);

-- RLS Policy (read-only for users, service role manages)
ALTER TABLE public.entity_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "entity_definitions_read" ON public.entity_definitions
    FOR SELECT USING (
        yacht_id IS NULL OR
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );
```

### 1.3 `intent_patterns` - Query intent classification rules

```sql
-- ============================================================================
-- TABLE: intent_patterns
-- Purpose: Patterns for classifying query intent
-- UX Requirement: "Search must accept natural language, fragments, uncertainty"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.intent_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    intent_type TEXT NOT NULL,
    -- Values: 'information', 'action', 'navigation', 'recall', 'diagnostic'

    pattern_type TEXT NOT NULL,
    -- Values: 'keyword', 'regex', 'semantic_embedding'

    pattern_value TEXT NOT NULL,
    -- The actual pattern (keyword, regex, or embedding vector reference)

    pattern_examples TEXT[],
    -- Example queries that match this pattern

    weight DECIMAL(3,2) DEFAULT 1.00,
    -- Contribution to intent score (0.00-1.00)

    role_boost JSONB DEFAULT '{}',
    -- Role-specific weight adjustments
    -- Format: {"captain": 1.2, "chief_engineer": 0.8}

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed data for intent patterns
INSERT INTO public.intent_patterns (intent_type, pattern_type, pattern_value, pattern_examples) VALUES
-- Information seeking
('information', 'keyword', 'what', ARRAY['what is the status', 'what happened']),
('information', 'keyword', 'show', ARRAY['show me', 'show history']),
('information', 'keyword', 'find', ARRAY['find the manual', 'find spare']),
('information', 'keyword', 'where', ARRAY['where is', 'where did we']),

-- Action intent
('action', 'keyword', 'add', ARRAY['add to handover', 'add note']),
('action', 'keyword', 'create', ARRAY['create work order', 'create fault']),
('action', 'keyword', 'log', ARRAY['log usage', 'log hours']),
('action', 'keyword', 'update', ARRAY['update status', 'update inventory']),
('action', 'keyword', 'mark', ARRAY['mark complete', 'mark resolved']),

-- Recall intent (memory reconstruction)
('recall', 'keyword', 'did i', ARRAY['did I update', 'did I log']),
('recall', 'keyword', 'what did', ARRAY['what did I change', 'what did we order']),
('recall', 'keyword', 'today', ARRAY['changes today', 'my work today']),
('recall', 'keyword', 'yesterday', ARRAY['yesterday''s work', 'what happened yesterday']),
('recall', 'keyword', 'last', ARRAY['last time', 'last week', 'last service']),

-- Diagnostic intent
('diagnostic', 'keyword', 'alarm', ARRAY['alarm history', 'alarm again']),
('diagnostic', 'keyword', 'fault', ARRAY['fault code', 'recurring fault']),
('diagnostic', 'keyword', 'error', ARRAY['error message', 'error history']),
('diagnostic', 'keyword', 'problem', ARRAY['problem with', 'same problem']),
('diagnostic', 'keyword', 'why', ARRAY['why is', 'why does']);

-- Index
CREATE INDEX idx_intent_patterns_type ON public.intent_patterns(intent_type);
CREATE INDEX idx_intent_patterns_active ON public.intent_patterns(active) WHERE active = TRUE;
```

---

## PART 2: NEW COLUMNS ON EXISTING TABLES

### 2.1 `pms_document_chunks` - Add search relevance metadata

```sql
-- ============================================================================
-- ALTER TABLE: pms_document_chunks
-- Add columns for improved search relevance
-- ============================================================================

-- Entity references extracted from chunk content
ALTER TABLE public.pms_document_chunks
ADD COLUMN IF NOT EXISTS extracted_entities JSONB DEFAULT '[]'::jsonb;
-- Format: [{"type": "equipment", "value": "Generator", "spans": [[12,21], [45,54]]}]

-- Semantic intent classification of chunk
ALTER TABLE public.pms_document_chunks
ADD COLUMN IF NOT EXISTS chunk_intent TEXT;
-- Values: 'procedure', 'specification', 'troubleshooting', 'safety', 'parts_list', 'diagram'

-- Confidence score for entity extraction
ALTER TABLE public.pms_document_chunks
ADD COLUMN IF NOT EXISTS extraction_confidence DECIMAL(3,2);

-- Last time this chunk was returned in search results
ALTER TABLE public.pms_document_chunks
ADD COLUMN IF NOT EXISTS last_retrieved_at TIMESTAMPTZ;

-- Retrieval count for relevance boosting
ALTER TABLE public.pms_document_chunks
ADD COLUMN IF NOT EXISTS retrieval_count INTEGER DEFAULT 0;

-- Index for entity-based search
CREATE INDEX IF NOT EXISTS idx_chunks_extracted_entities
ON public.pms_document_chunks USING GIN (extracted_entities);

CREATE INDEX IF NOT EXISTS idx_chunks_intent
ON public.pms_document_chunks(chunk_intent);
```

### 2.2 `pms_equipment` - Add search aliases and entity links

```sql
-- ============================================================================
-- ALTER TABLE: pms_equipment
-- Add columns for natural language search matching
-- ============================================================================

-- Alternative names users might search for
ALTER TABLE public.pms_equipment
ADD COLUMN IF NOT EXISTS search_aliases TEXT[] DEFAULT '{}';
-- e.g., ["gen 1", "main generator", "MTU port"]

-- System classification for entity extraction
ALTER TABLE public.pms_equipment
ADD COLUMN IF NOT EXISTS system_path TEXT;
-- e.g., "Propulsion > Main Engines > Port Engine > Cooling"

-- Common fault keywords associated with this equipment
ALTER TABLE public.pms_equipment
ADD COLUMN IF NOT EXISTS fault_keywords TEXT[] DEFAULT '{}';
-- e.g., ["high temp", "low pressure", "vibration"]

-- Index for alias search
CREATE INDEX IF NOT EXISTS idx_equipment_aliases
ON public.pms_equipment USING GIN (search_aliases);

CREATE INDEX IF NOT EXISTS idx_equipment_fault_keywords
ON public.pms_equipment USING GIN (fault_keywords);
```

### 2.3 `pms_faults` - Add recurrence tracking for diagnostic search

```sql
-- ============================================================================
-- ALTER TABLE: pms_faults
-- Add columns for diagnostic search and pattern recognition
-- ============================================================================

-- Hash of fault signature for recurrence detection
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS fault_signature_hash TEXT;
-- SHA256 of (equipment_id + fault_code + key_symptoms)

-- Related fault IDs (for "has this happened before" queries)
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS related_fault_ids UUID[] DEFAULT '{}';

-- Root cause classification (for diagnostic search)
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS root_cause_category TEXT;
-- Values: 'mechanical', 'electrical', 'software', 'human_error', 'wear', 'contamination', 'unknown'

-- Environmental conditions at fault occurrence
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS environmental_context JSONB;
-- Format: {"sea_state": "rough", "outside_temp": 35, "running_hours": 12500}

-- Index for recurrence queries
CREATE INDEX IF NOT EXISTS idx_faults_signature
ON public.pms_faults(fault_signature_hash);

CREATE INDEX IF NOT EXISTS idx_faults_related
ON public.pms_faults USING GIN (related_fault_ids);

CREATE INDEX IF NOT EXISTS idx_faults_root_cause
ON public.pms_faults(root_cause_category);
```

---

## PART 3: RPC FUNCTIONS

### 3.1 `search_with_interpretation()` - Main search RPC

```sql
-- ============================================================================
-- FUNCTION: search_with_interpretation
-- Purpose: Execute search with entity extraction and intent detection
-- UX Requirement: "Interpretation appears BEFORE results"
-- Returns: Streaming-compatible result set
-- ============================================================================

CREATE OR REPLACE FUNCTION public.search_with_interpretation(
    p_query TEXT,
    p_yacht_id UUID,
    p_user_role TEXT DEFAULT 'member',
    p_limit INTEGER DEFAULT 10,
    p_include_microactions BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    phase TEXT,                    -- 'interpretation', 'results', 'microactions'
    sequence_num INTEGER,          -- Order within phase
    payload JSONB                  -- Phase-specific data
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_session_id UUID;
    v_entities JSONB;
    v_intent TEXT;
    v_confidence_branches JSONB;
    v_has_uncertainty BOOLEAN;
BEGIN
    -- Create search session
    INSERT INTO search_sessions (yacht_id, user_id, query_text)
    VALUES (p_yacht_id, auth.uid(), p_query)
    RETURNING id INTO v_session_id;

    -- ========================================
    -- PHASE 1: INTERPRETATION
    -- Must be returned FIRST before any results
    -- ========================================

    -- Extract entities from query
    SELECT jsonb_agg(entity_data) INTO v_entities
    FROM (
        SELECT jsonb_build_object(
            'type', ed.entity_type,
            'value', ed.canonical_name,
            'confidence',
                CASE
                    WHEN p_query ILIKE '%' || ed.canonical_name || '%' THEN 0.95
                    WHEN EXISTS (SELECT 1 FROM unnest(ed.aliases) a WHERE p_query ILIKE '%' || a || '%') THEN 0.85
                    ELSE 0.70
                END,
            'icon', ed.icon
        ) as entity_data
        FROM entity_definitions ed
        WHERE ed.active = TRUE
        AND (ed.yacht_id IS NULL OR ed.yacht_id = p_yacht_id)
        AND (
            p_query ILIKE '%' || ed.canonical_name || '%'
            OR EXISTS (SELECT 1 FROM unnest(ed.aliases) a WHERE p_query ILIKE '%' || a || '%')
        )
        ORDER BY ed.priority ASC
        LIMIT 5
    ) extracted;

    -- Detect intent
    SELECT ip.intent_type INTO v_intent
    FROM intent_patterns ip
    WHERE ip.active = TRUE
    AND (
        p_query ILIKE '%' || ip.pattern_value || '%'
    )
    GROUP BY ip.intent_type
    ORDER BY SUM(ip.weight) DESC
    LIMIT 1;

    -- Default intent if none detected
    v_intent := COALESCE(v_intent, 'information');

    -- Check for uncertainty (multiple interpretations)
    v_has_uncertainty := (
        SELECT COUNT(DISTINCT entity_type) > 1
        FROM jsonb_array_elements(COALESCE(v_entities, '[]'::jsonb)) e
    );

    -- Build confidence branches if uncertain
    IF v_has_uncertainty THEN
        v_confidence_branches := jsonb_build_array(
            jsonb_build_object('interpretation', 'Primary interpretation', 'confidence', 0.7),
            jsonb_build_object('interpretation', 'Alternative interpretation', 'confidence', 0.3)
        );
    ELSE
        v_confidence_branches := '[]'::jsonb;
    END IF;

    -- Return interpretation phase
    phase := 'interpretation';
    sequence_num := 1;
    payload := jsonb_build_object(
        'session_id', v_session_id,
        'interpreted_entities', COALESCE(v_entities, '[]'::jsonb),
        'interpreted_intent', v_intent,
        'confidence_branches', v_confidence_branches,
        'uncertainty_shown', v_has_uncertainty
    );
    RETURN NEXT;

    -- Update session with interpretation
    UPDATE search_sessions SET
        interpreted_entities = COALESCE(v_entities, '[]'::jsonb),
        interpreted_intent = v_intent,
        confidence_branches = v_confidence_branches,
        uncertainty_shown = v_has_uncertainty
    WHERE id = v_session_id;

    -- ========================================
    -- PHASE 2: RESULTS
    -- Returned after interpretation is visible
    -- ========================================

    -- Search documents with vector similarity
    FOR phase, sequence_num, payload IN
        SELECT
            'results',
            ROW_NUMBER() OVER (ORDER BY
                CASE WHEN dc.content ILIKE '%' || p_query || '%' THEN 0 ELSE 1 END,
                dc.importance_score DESC NULLS LAST
            )::INTEGER,
            jsonb_build_object(
                'result_type', 'document_chunk',
                'id', dc.id,
                'document_id', dc.document_id,
                'title', d.title,
                'content_preview', LEFT(dc.content, 200),
                'page_number', dc.page_number,
                'section_title', dc.section_title,
                'relevance_score', dc.importance_score,
                'document_type', d.document_type,
                'chunk_intent', dc.chunk_intent
            )
        FROM pms_document_chunks dc
        JOIN pms_documents d ON d.id = dc.document_id
        WHERE d.yacht_id = p_yacht_id
        AND (
            dc.content ILIKE '%' || p_query || '%'
            OR d.title ILIKE '%' || p_query || '%'
        )
        LIMIT p_limit
    LOOP
        RETURN NEXT;
    END LOOP;

    -- Search equipment
    FOR phase, sequence_num, payload IN
        SELECT
            'results',
            (p_limit + ROW_NUMBER() OVER ())::INTEGER,
            jsonb_build_object(
                'result_type', 'equipment',
                'id', e.id,
                'name', e.name,
                'system', e.system,
                'status', e.status,
                'location', e.location,
                'critical', e.critical
            )
        FROM pms_equipment e
        WHERE e.yacht_id = p_yacht_id
        AND (
            e.name ILIKE '%' || p_query || '%'
            OR e.system ILIKE '%' || p_query || '%'
            OR EXISTS (SELECT 1 FROM unnest(e.search_aliases) a WHERE a ILIKE '%' || p_query || '%')
        )
        LIMIT 5
    LOOP
        RETURN NEXT;
    END LOOP;

    -- Search faults (for diagnostic intent)
    IF v_intent = 'diagnostic' THEN
        FOR phase, sequence_num, payload IN
            SELECT
                'results',
                (p_limit + 10 + ROW_NUMBER() OVER ())::INTEGER,
                jsonb_build_object(
                    'result_type', 'fault',
                    'id', f.id,
                    'title', f.title,
                    'severity', f.severity,
                    'status', f.status,
                    'occurrence_count', f.occurrence_count,
                    'equipment_name', e.name,
                    'last_occurrence', f.last_occurrence
                )
            FROM pms_faults f
            LEFT JOIN pms_equipment e ON e.id = f.equipment_id
            WHERE f.yacht_id = p_yacht_id
            AND (
                f.title ILIKE '%' || p_query || '%'
                OR f.description ILIKE '%' || p_query || '%'
                OR f.code ILIKE '%' || p_query || '%'
            )
            ORDER BY f.last_occurrence DESC NULLS LAST
            LIMIT 5
        LOOP
            RETURN NEXT;
        END LOOP;
    END IF;

    -- ========================================
    -- PHASE 3: MICROACTIONS
    -- Proposed actions based on context
    -- ========================================

    IF p_include_microactions THEN
        -- Suggest relevant actions based on intent
        FOR phase, sequence_num, payload IN
            SELECT
                'microactions',
                ROW_NUMBER() OVER ()::INTEGER,
                jsonb_build_object(
                    'action_id', ar.id,
                    'action_name', ar.name,
                    'action_type', ar.action_type,
                    'icon', ar.icon,
                    'description', ar.description,
                    'prefill', ar.prefill_template
                )
            FROM action_registry ar
            WHERE ar.active = TRUE
            AND (
                (v_intent = 'action' AND ar.action_type = 'mutate')
                OR (v_intent = 'diagnostic' AND ar.id IN ('create_work_order_from_fault', 'add_to_handover'))
                OR (v_intent = 'information' AND ar.action_type = 'read')
            )
            AND (ar.required_roles IS NULL OR p_user_role = ANY(ar.required_roles))
            ORDER BY ar.priority ASC
            LIMIT 4
        LOOP
            RETURN NEXT;
        END LOOP;
    END IF;

    -- Update session with results count
    UPDATE search_sessions SET
        results_count = (SELECT COUNT(*) FROM search_sessions WHERE id = v_session_id)
    WHERE id = v_session_id;

    RETURN;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.search_with_interpretation TO authenticated;
```

### 3.2 `record_search_action()` - Track user action from search

```sql
-- ============================================================================
-- FUNCTION: record_search_action
-- Purpose: Record when user takes action from search results
-- UX Requirement: "Every mutation is attributable, reviewable, and immutable"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.record_search_action(
    p_session_id UUID,
    p_action_type TEXT,           -- 'result_click', 'microaction_execute', 'correction', 'abandon'
    p_action_data JSONB DEFAULT '{}'
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Verify session belongs to current user
    IF NOT EXISTS (
        SELECT 1 FROM search_sessions
        WHERE id = p_session_id AND user_id = auth.uid()
    ) THEN
        RAISE EXCEPTION 'Invalid session or unauthorized';
    END IF;

    -- Update session based on action type
    CASE p_action_type
        WHEN 'result_click' THEN
            UPDATE search_sessions SET
                result_clicked_id = (p_action_data->>'result_id')::UUID,
                result_clicked_type = p_action_data->>'result_type',
                duration_ms = EXTRACT(EPOCH FROM (NOW() - query_timestamp)) * 1000
            WHERE id = p_session_id;

        WHEN 'microaction_execute' THEN
            UPDATE search_sessions SET
                action_selected = p_action_data->>'action_id',
                microactions_offered = microactions_offered || p_action_data,
                duration_ms = EXTRACT(EPOCH FROM (NOW() - query_timestamp)) * 1000
            WHERE id = p_session_id;

        WHEN 'correction' THEN
            UPDATE search_sessions SET
                user_corrections = user_corrections || p_action_data,
                final_entities = p_action_data->'corrected_entities',
                final_intent = p_action_data->>'corrected_intent'
            WHERE id = p_session_id;

        WHEN 'abandon' THEN
            UPDATE search_sessions SET
                abandoned = TRUE,
                duration_ms = EXTRACT(EPOCH FROM (NOW() - query_timestamp)) * 1000
            WHERE id = p_session_id;

        ELSE
            RAISE EXCEPTION 'Unknown action type: %', p_action_type;
    END CASE;

    RETURN TRUE;
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_search_action TO authenticated;
```

### 3.3 `get_search_recall()` - Memory reconstruction query

```sql
-- ============================================================================
-- FUNCTION: get_search_recall
-- Purpose: Help users reconstruct what they did ("what did I change today")
-- UX Requirement: "Search must allow users to reconstruct"
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_search_recall(
    p_yacht_id UUID,
    p_user_id UUID DEFAULT NULL,   -- NULL = current user
    p_date_from TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    p_date_to TIMESTAMPTZ DEFAULT NOW(),
    p_entity_types TEXT[] DEFAULT NULL,  -- Filter by entity type
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    event_timestamp TIMESTAMPTZ,
    event_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    entity_name TEXT,
    action_verb TEXT,
    summary TEXT,
    user_name TEXT,
    is_mutation BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    v_user_id := COALESCE(p_user_id, auth.uid());

    RETURN QUERY
    SELECT
        al.timestamp as event_timestamp,
        al.entity_type as event_type,
        al.entity_type,
        al.entity_id,
        COALESCE(al.details->>'name', al.details->>'title', al.entity_id::TEXT) as entity_name,
        al.action as action_verb,
        COALESCE(al.details->>'summary', al.action || ' ' || al.entity_type) as summary,
        al.user_name,
        al.action_category IN ('create', 'update', 'delete', 'status_change') as is_mutation
    FROM pms_audit_log al
    WHERE al.yacht_id = p_yacht_id
    AND al.user_id = v_user_id
    AND al.timestamp BETWEEN p_date_from AND p_date_to
    AND (p_entity_types IS NULL OR al.entity_type = ANY(p_entity_types))
    ORDER BY al.timestamp DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_search_recall TO authenticated;
```

---

## PART 4: RLS POLICIES

### 4.1 Search Sessions RLS

```sql
-- ============================================================================
-- RLS POLICIES: search_sessions
-- ============================================================================

-- Users can only see their own search sessions
CREATE POLICY "search_sessions_select_own" ON public.search_sessions
    FOR SELECT
    USING (user_id = auth.uid());

-- Users can only insert their own sessions
CREATE POLICY "search_sessions_insert_own" ON public.search_sessions
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can only update their own sessions
CREATE POLICY "search_sessions_update_own" ON public.search_sessions
    FOR UPDATE
    USING (user_id = auth.uid());

-- Captains and managers can view department search patterns (anonymized)
CREATE POLICY "search_sessions_department_view" ON public.search_sessions
    FOR SELECT
    USING (
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid()
            AND ur.role IN ('captain', 'manager', 'chief_engineer')
            AND ur.is_active = TRUE
        )
    );
```

### 4.2 Entity Definitions RLS

```sql
-- ============================================================================
-- RLS POLICIES: entity_definitions
-- ============================================================================

-- All authenticated users can read entity definitions
CREATE POLICY "entity_definitions_read_all" ON public.entity_definitions
    FOR SELECT
    USING (
        yacht_id IS NULL  -- Global definitions
        OR yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );

-- Only service role can modify entity definitions
-- (No INSERT/UPDATE/DELETE policies for authenticated users)
```

---

## PART 5: STORAGE BUCKETS

### 5.1 Search Cache Bucket (Optional Performance Optimization)

```sql
-- ============================================================================
-- STORAGE: search_cache bucket
-- Purpose: Cache frequently accessed search results
-- ============================================================================

-- Create bucket via Supabase Dashboard or API
-- Bucket name: search_cache
-- Public: FALSE
-- File size limit: 1MB
-- Allowed MIME types: application/json

-- Storage structure:
-- search_cache/{yacht_id}/entity_index.json     -- Pre-computed entity index
-- search_cache/{yacht_id}/intent_model.json     -- Trained intent patterns
-- search_cache/{yacht_id}/popular_queries.json  -- Cached popular searches

-- RLS Policy for search_cache bucket
CREATE POLICY "search_cache_yacht_read" ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'search_cache'
        AND (storage.foldername(name))[1] = (
            SELECT yacht_id::TEXT FROM public.user_profiles WHERE id = auth.uid()
        )
    );
```

---

## PART 6: FOREIGN KEY RELATIONSHIPS

```sql
-- ============================================================================
-- FOREIGN KEYS
-- ============================================================================

-- search_sessions -> user_profiles
ALTER TABLE public.search_sessions
ADD CONSTRAINT fk_search_sessions_user
FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- entity_definitions yacht link (soft reference, no FK to allow NULL)
-- No hard FK needed as yacht_id can be NULL for global definitions

-- Ensure referential integrity for action selections
ALTER TABLE public.search_sessions
ADD CONSTRAINT fk_search_sessions_action
FOREIGN KEY (action_selected) REFERENCES public.action_registry(id) ON DELETE SET NULL;
```

---

## PART 7: SEED DATA

### 7.1 Default Entity Definitions

```sql
-- ============================================================================
-- SEED DATA: Default entity definitions
-- ============================================================================

INSERT INTO public.entity_definitions (yacht_id, entity_type, canonical_name, aliases, icon, priority) VALUES
-- Systems (NULL yacht_id = global)
(NULL, 'system', 'Propulsion', ARRAY['propulsion', 'main engines', 'drive'], 'engine', 10),
(NULL, 'system', 'Electrical', ARRAY['electrical', 'power', 'shore power', 'generator'], 'zap', 10),
(NULL, 'system', 'HVAC', ARRAY['hvac', 'air conditioning', 'ac', 'climate'], 'thermometer', 10),
(NULL, 'system', 'Navigation', ARRAY['nav', 'bridge', 'radar', 'gps'], 'compass', 10),
(NULL, 'system', 'Safety', ARRAY['safety', 'fire', 'lifesaving', 'emergency'], 'shield', 5),
(NULL, 'system', 'Deck', ARRAY['deck', 'anchor', 'windlass', 'crane'], 'anchor', 10),
(NULL, 'system', 'Interior', ARRAY['interior', 'galley', 'laundry', 'accommodation'], 'home', 10),

-- Severities
(NULL, 'severity', 'Critical', ARRAY['critical', 'urgent', 'emergency'], 'alert-triangle', 1),
(NULL, 'severity', 'High', ARRAY['high', 'important', 'priority'], 'alert-circle', 2),
(NULL, 'severity', 'Medium', ARRAY['medium', 'normal'], 'info', 3),
(NULL, 'severity', 'Low', ARRAY['low', 'minor'], 'check-circle', 4),

-- Status values
(NULL, 'status', 'Operational', ARRAY['operational', 'running', 'working', 'ok'], 'check', 10),
(NULL, 'status', 'Down', ARRAY['down', 'broken', 'failed', 'not working'], 'x-circle', 5),
(NULL, 'status', 'Maintenance', ARRAY['maintenance', 'service', 'repair'], 'tool', 10),

-- Action verbs
(NULL, 'action_verb', 'Add', ARRAY['add', 'create', 'new', 'log'], 'plus', 20),
(NULL, 'action_verb', 'Update', ARRAY['update', 'change', 'modify', 'edit'], 'edit', 20),
(NULL, 'action_verb', 'Complete', ARRAY['complete', 'finish', 'close', 'done'], 'check-square', 20),
(NULL, 'action_verb', 'View', ARRAY['view', 'show', 'find', 'search', 'look'], 'eye', 20),

-- Time references
(NULL, 'date', 'Today', ARRAY['today', 'now', 'current'], 'calendar', 30),
(NULL, 'date', 'Yesterday', ARRAY['yesterday'], 'calendar', 30),
(NULL, 'date', 'This Week', ARRAY['this week', 'week'], 'calendar', 30),
(NULL, 'date', 'Last Service', ARRAY['last service', 'previous service', 'last time'], 'clock', 30)

ON CONFLICT (yacht_id, entity_type, canonical_name) DO NOTHING;
```

---

## PART 8: API CONTRACT

### 8.1 Streaming Response Format

```typescript
// Backend must stream responses in this order:

interface SearchStreamResponse {
  // PHASE 1: Interpretation (MUST arrive first)
  interpretation: {
    session_id: string;
    interpreted_entities: Array<{
      type: string;      // 'equipment', 'system', 'fault', etc.
      value: string;     // Display name
      confidence: number; // 0.0-1.0
      icon?: string;
    }>;
    interpreted_intent: 'information' | 'action' | 'navigation' | 'recall' | 'diagnostic';
    confidence_branches?: Array<{
      interpretation: string;
      confidence: number;
    }>;
    uncertainty_shown: boolean;
  };

  // PHASE 2: Results (arrives after interpretation visible)
  results: Array<{
    result_type: string;  // 'document_chunk', 'equipment', 'fault', 'work_order'
    id: string;
    title?: string;
    content_preview?: string;
    relevance_score?: number;
    metadata: Record<string, any>;
  }>;

  // PHASE 3: Microactions (arrives with/after results)
  microactions: Array<{
    action_id: string;
    action_name: string;
    action_type: 'read' | 'mutate';
    icon: string;
    description: string;
    prefill?: Record<string, any>;
  }>;
}
```

---

## PART 9: VALIDATION CHECKLIST

Before deployment, verify:

- [ ] `search_sessions` table created with all columns
- [ ] `entity_definitions` table created with seed data
- [ ] `intent_patterns` table created with seed data
- [ ] All ALTER TABLE statements applied to existing tables
- [ ] `search_with_interpretation()` RPC returns 3 phases in order
- [ ] `record_search_action()` RPC tracks user actions
- [ ] `get_search_recall()` RPC returns user's recent activity
- [ ] RLS policies prevent cross-yacht data access
- [ ] Indexes created for performance
- [ ] Entity extraction returns results within 100ms
- [ ] Intent detection defaults to 'information' when uncertain
- [ ] Microactions respect role permissions

---

## RELATED DOCUMENTS

- `02-search-as-interface.md` - UX requirements source
- `03-interlocutor-model.md` - Behavioral model
- `IMPL_02_ledger_proof.sql.md` - Audit/proof system (uses search_sessions)
- `IMPL_03_handover_continuity.sql.md` - Handover integration
