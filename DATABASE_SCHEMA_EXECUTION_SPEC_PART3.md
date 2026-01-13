# DATABASE SCHEMA EXECUTION SPEC - PART 3
## DOCUMENT CHUNKS, SHOPPING LIST, RECEIVING, PURCHASING, AUDIT

---

### 1.11 DOCUMENT CHUNKS (RAG/Semantic Search)
```sql
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector extension

CREATE TABLE IF NOT EXISTS public.pms_document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Parent document
    document_id UUID NOT NULL REFERENCES public.pms_documents(id) ON DELETE CASCADE,

    -- Chunk data
    page_number INTEGER,
    chunk_index INTEGER NOT NULL,  -- Sequential within document
    content TEXT NOT NULL CHECK (LENGTH(content) >= 50),  -- Min 50 chars per chunk
    char_count INTEGER,

    -- Vector embedding (for semantic search)
    embedding VECTOR(1536),  -- OpenAI ada-002 dimension

    -- Entity extraction (for graph-RAG)
    fault_code_refs TEXT[],      -- Extracted fault codes: ["MTU-OVHT-01", ...]
    equipment_refs TEXT[],        -- Extracted equipment names
    part_refs TEXT[],             -- Extracted part numbers
    procedure_refs TEXT[],        -- Extracted procedure numbers

    -- Metadata
    section_title TEXT,
    heading TEXT,
    is_table BOOLEAN DEFAULT FALSE,
    is_diagram BOOLEAN DEFAULT FALSE,

    -- Relevance (computed by RAG system)
    chunk_type TEXT CHECK (chunk_type IN (
        'text', 'table', 'list', 'procedure', 'specifications', 'warning', 'note'
    )),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_doc_chunks_document ON public.pms_document_chunks(document_id, chunk_index);
CREATE INDEX idx_doc_chunks_page ON public.pms_document_chunks(document_id, page_number);
CREATE INDEX idx_doc_chunks_fault_codes ON public.pms_document_chunks USING GIN(fault_code_refs);
CREATE INDEX idx_doc_chunks_equipment ON public.pms_document_chunks USING GIN(equipment_refs);
CREATE INDEX idx_doc_chunks_parts ON public.pms_document_chunks USING GIN(part_refs);

-- Vector similarity search index
CREATE INDEX idx_doc_chunks_embedding ON public.pms_document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on dataset size

-- Full-text search
CREATE INDEX idx_doc_chunks_content ON public.pms_document_chunks
    USING GIN (to_tsvector('english', content));

-- RLS: Inherits from parent document
ALTER TABLE public.pms_document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view chunks for accessible documents" ON public.pms_document_chunks
    FOR SELECT TO authenticated
    USING (
        document_id IN (
            SELECT id FROM public.pms_documents
            WHERE yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        )
    );
```

**USER INTERACTIONS**:

#### Action: `show_manual_section` (READ)
**Workflow**:
1. User asks: "CAT 3512 overheating, show manual"
2. Backend:
   - Identifies equipment (CAT 3512)
   - Finds associated document (manual_document_id from equipment table)
   - Searches chunks for fault code OR semantic similarity to "overheating"
   - Returns top 3-5 relevant chunks with page numbers
3. Frontend displays chunks with "Open full page" button
4. No database mutation

**Query Pattern**:
```sql
-- Method 1: Fault code exact match
SELECT dc.*, d.title, d.storage_path
FROM pms_document_chunks dc
JOIN pms_documents d ON dc.document_id = d.id
WHERE d.equipment_id = $equipment_id
AND $fault_code = ANY(dc.fault_code_refs)
ORDER BY dc.page_number, dc.chunk_index
LIMIT 5;

-- Method 2: Semantic search (vector similarity)
SELECT dc.*, d.title, d.storage_path,
       1 - (dc.embedding <=> $query_embedding) AS similarity
FROM pms_document_chunks dc
JOIN pms_documents d ON dc.document_id = d.id
WHERE d.equipment_id = $equipment_id
AND 1 - (dc.embedding <=> $query_embedding) > 0.7  -- Similarity threshold
ORDER BY similarity DESC
LIMIT 5;
```

---

### 1.12 SHOPPING LIST (Procurement Queue)
```sql
CREATE TABLE IF NOT EXISTS public.pms_shopping_list (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Item details
    part_id UUID REFERENCES public.pms_parts(id) ON DELETE SET NULL,  -- NULL if not in catalog
    part_name TEXT NOT NULL,
    part_number TEXT,
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    unit TEXT DEFAULT 'ea',

    -- Source (why is this needed?)
    source_type TEXT CHECK (source_type IN (
        'threshold_trigger',  -- Auto-added when stock < threshold
        'work_order',         -- Added from WO parts list
        'manual_request',     -- User manually added
        'predictive'          -- Predicted need
    )),
    source_id UUID,  -- WO ID, equipment ID, etc.
    reason TEXT,

    -- Priority
    urgency TEXT NOT NULL DEFAULT 'normal' CHECK (urgency IN (
        'low',       -- Nice to have
        'normal',    -- Standard reorder
        'high',      -- Low stock
        'urgent'     -- Critical/zero stock
    )),

    -- State machine
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',          -- Created but not approved
        'active',             -- Approved, ready to order
        'committed',          -- Purchase order created
        'partially_fulfilled',-- Some quantity received
        'fulfilled',          -- All received
        'installed',          -- Installed on equipment
        'cancelled',          -- No longer needed
        'missing'             -- Order placed but never arrived
    )),

    -- Procurement
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,
    quantity_ordered NUMERIC(10,2),
    quantity_received NUMERIC(10,2) DEFAULT 0,
    estimated_cost NUMERIC(10,2),
    actual_cost NUMERIC(10,2),

    -- People
    requested_by UUID NOT NULL REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),

    -- Timeline
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    ordered_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    notes TEXT
);

CREATE INDEX idx_shopping_list_yacht ON public.pms_shopping_list(yacht_id);
CREATE INDEX idx_shopping_list_part ON public.pms_shopping_list(part_id);
CREATE INDEX idx_shopping_list_status ON public.pms_shopping_list(yacht_id, status);
CREATE INDEX idx_shopping_list_urgency ON public.pms_shopping_list(yacht_id, urgency, created_at);
CREATE INDEX idx_shopping_list_active ON public.pms_shopping_list(yacht_id, created_at DESC)
    WHERE status IN ('candidate', 'active');
CREATE INDEX idx_shopping_list_po ON public.pms_shopping_list(purchase_order_id);

-- Auto-create from threshold trigger
CREATE OR REPLACE FUNCTION auto_add_to_shopping_list()
RETURNS TRIGGER AS $$
BEGIN
    -- Only trigger if stock falls below thresholds
    IF NEW.quantity_available <= NEW.critical_threshold THEN
        INSERT INTO pms_shopping_list (
            yacht_id, part_id, part_name, part_number, quantity, unit,
            source_type, urgency, requested_by, reason
        ) VALUES (
            NEW.yacht_id, NEW.id, NEW.name, NEW.part_number,
            NEW.reorder_quantity, NEW.unit,
            'threshold_trigger', 'urgent',
            (SELECT id FROM public.user_profiles WHERE role = 'chief_engineer' AND yacht_id = NEW.yacht_id LIMIT 1),
            'Stock fell to ' || NEW.quantity_available || ' (critical threshold: ' || NEW.critical_threshold || ')'
        )
        ON CONFLICT DO NOTHING;  -- Prevent duplicates
    ELSIF NEW.quantity_available <= NEW.minimum_quantity
          AND OLD.quantity_available > NEW.minimum_quantity THEN
        -- Crossing minimum threshold
        INSERT INTO pms_shopping_list (
            yacht_id, part_id, part_name, part_number, quantity, unit,
            source_type, urgency, requested_by, reason
        ) VALUES (
            NEW.yacht_id, NEW.id, NEW.name, NEW.part_number,
            NEW.reorder_quantity, NEW.unit,
            'threshold_trigger', 'high',
            (SELECT id FROM public.user_profiles WHERE role = 'chief_engineer' AND yacht_id = NEW.yacht_id LIMIT 1),
            'Stock fell to ' || NEW.quantity_available || ' (minimum: ' || NEW.minimum_quantity || ')'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_auto_shopping_list
    AFTER UPDATE OF quantity_on_hand ON public.pms_parts
    FOR EACH ROW
    WHEN (NEW.quantity_available <= NEW.minimum_quantity)
    EXECUTE FUNCTION auto_add_to_shopping_list();

-- RLS
ALTER TABLE public.pms_shopping_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view shopping list on own yacht" ON public.pms_shopping_list
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can add to shopping list" ON public.pms_shopping_list
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND requested_by = auth.uid()
    );

CREATE POLICY "HOD can approve shopping list" ON public.pms_shopping_list
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

**USER INTERACTIONS**:

#### Situational State: SHOPPING LIST MANAGEMENT

**State Transitions**:
```
CANDIDATE → ACTIVE → COMMITTED → FULFILLED → INSTALLED
            ↓                           ↓
        CANCELLED                   MISSING
```

#### Action: `approve_shopping_list_item` (MUTATE)
**Stage 1**: View pending items (READ)
- Shows all items with status='candidate'
- Grouped by urgency

**Stage 2**: Approve (MUTATE)
```sql
UPDATE pms_shopping_list
SET status = 'active',
    approved_by = $user_id,
    approved_at = NOW()
WHERE id = $item_id
AND yacht_id = $yacht_id
AND status = 'candidate';
```

**USER ROLE CHECK**:
- 2nd Engineer: Can approve if estimated_cost < $500
- Chief Engineer: Can approve if estimated_cost < $5,000
- Captain: Can approve any amount
- All others: REJECTED

**BAD INPUT**:
- Already approved → "Item already approved"
- Insufficient permissions → "Only HOD can approve purchases >$500"

**UNDO**:
- Before PO created: Can change status back to 'candidate'
- After PO created: Cannot undo (must cancel PO separately)

---

### 1.13 PURCHASE ORDERS (Procurement Execution)
```sql
CREATE TABLE IF NOT EXISTS public.pms_purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- PO identity
    po_number TEXT NOT NULL,  -- PO-2024-001
    supplier_name TEXT NOT NULL,
    supplier_contact TEXT,

    -- Status
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',         -- Being created
        'submitted',     -- Sent to supplier
        'confirmed',     -- Supplier confirmed
        'shipped',       -- In transit
        'delivered',     -- Arrived (not yet received)
        'completed',     -- Fully received and closed
        'cancelled'
    )),

    -- Amounts
    total_estimated NUMERIC(10,2),
    total_actual NUMERIC(10,2),
    currency TEXT DEFAULT 'USD',

    -- People
    created_by UUID NOT NULL REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),

    -- Timeline
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    expected_delivery DATE,
    actual_delivery DATE,

    -- Documents
    invoice_path TEXT,
    packing_slip_path TEXT,

    notes TEXT,
    tracking_number TEXT,

    UNIQUE(yacht_id, po_number)
);

CREATE INDEX idx_po_yacht ON public.pms_purchase_orders(yacht_id);
CREATE INDEX idx_po_number ON public.pms_purchase_orders(yacht_id, po_number);
CREATE INDEX idx_po_status ON public.pms_purchase_orders(yacht_id, status);
CREATE INDEX idx_po_active ON public.pms_purchase_orders(yacht_id, created_at DESC)
    WHERE status IN ('draft', 'submitted', 'confirmed', 'shipped', 'delivered');

-- Auto-generate PO number
CREATE OR REPLACE FUNCTION generate_po_number(p_yacht_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_year TEXT;
    v_count INTEGER;
BEGIN
    v_year := TO_CHAR(NOW(), 'YYYY');
    SELECT COUNT(*) + 1 INTO v_count
    FROM public.pms_purchase_orders
    WHERE yacht_id = p_yacht_id
    AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    RETURN 'PO-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS
ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view POs on own yacht" ON public.pms_purchase_orders
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "HOD can manage POs" ON public.pms_purchase_orders
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

---

### 1.14 RECEIVING SESSIONS (Checkbox = Truth)
```sql
CREATE TABLE IF NOT EXISTS public.pms_receiving_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Session identity
    session_number TEXT NOT NULL,  -- RCV-2024-001
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,

    -- State machine (CRITICAL: Checkbox = Truth pattern)
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',    -- Delivery notification received, items not yet scanned
        'active',       -- User scanning items
        'review',       -- User reviewing before commit
        'committed'     -- Items moved to inventory (IMMUTABLE after this)
    )),

    -- People
    received_by UUID NOT NULL REFERENCES auth.users(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    committed_at TIMESTAMPTZ,
    committed_by UUID REFERENCES auth.users(id),

    -- Metadata
    delivery_note_number TEXT,
    supplier_name TEXT,
    notes TEXT,

    UNIQUE(yacht_id, session_number)
);

CREATE TABLE IF NOT EXISTS public.pms_receiving_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Parent session
    receiving_session_id UUID NOT NULL REFERENCES public.pms_receiving_sessions(id) ON DELETE CASCADE,

    -- Item
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE RESTRICT,
    shopping_list_item_id UUID REFERENCES public.pms_shopping_list(id) ON DELETE SET NULL,

    -- Expected vs actual
    expected_quantity NUMERIC(10,2),
    delivered_quantity NUMERIC(10,2) NOT NULL CHECK (delivered_quantity >= 0),
    unit TEXT NOT NULL,

    -- CRITICAL: Checkbox = Truth
    checked BOOLEAN NOT NULL DEFAULT FALSE,  -- Only checked items go to inventory

    -- Status
    status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN (
        'ok',           -- Item as expected
        'damaged',      -- Item damaged
        'wrong_item',   -- Wrong part delivered
        'short',        -- Quantity less than expected
        'excess'        -- Quantity more than expected
    )),

    -- Destination
    installed BOOLEAN DEFAULT FALSE,  -- TRUE if installed directly (not to stores)
    installed_equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,

    notes TEXT,
    photo_urls TEXT[]
);

CREATE INDEX idx_receiving_sessions_yacht ON public.pms_receiving_sessions(yacht_id);
CREATE INDEX idx_receiving_sessions_status ON public.pms_receiving_sessions(yacht_id, status);
CREATE INDEX idx_receiving_sessions_po ON public.pms_receiving_sessions(purchase_order_id);
CREATE INDEX idx_receiving_items_session ON public.pms_receiving_items(receiving_session_id);
CREATE INDEX idx_receiving_items_part ON public.pms_receiving_items(part_id);

-- CRITICAL: Commit trigger (Checkbox = Truth enforcement)
CREATE OR REPLACE FUNCTION commit_receiving_session()
RETURNS TRIGGER AS $$
DECLARE
    v_item RECORD;
BEGIN
    -- Only process if transitioning TO committed
    IF NEW.status = 'committed' AND OLD.status != 'committed' THEN

        -- Process ONLY checked items
        FOR v_item IN
            SELECT *
            FROM pms_receiving_items
            WHERE receiving_session_id = NEW.id
            AND checked = TRUE  -- CHECKBOX = TRUTH
        LOOP
            IF v_item.installed = FALSE THEN
                -- Add to inventory
                INSERT INTO pms_inventory_transactions (
                    yacht_id, part_id, transaction_type, quantity, unit,
                    receiving_session_id, user_id, notes
                ) VALUES (
                    NEW.yacht_id, v_item.part_id, 'receive',
                    v_item.delivered_quantity, v_item.unit,
                    NEW.id, NEW.committed_by,
                    'Received via ' || NEW.session_number
                );
            ELSE
                -- Installed directly on equipment
                INSERT INTO pms_inventory_transactions (
                    yacht_id, part_id, transaction_type, quantity, unit,
                    receiving_session_id, equipment_id, user_id, notes
                ) VALUES (
                    NEW.yacht_id, v_item.part_id, 'install',
                    v_item.delivered_quantity, v_item.unit,
                    NEW.id, v_item.installed_equipment_id, NEW.committed_by,
                    'Installed directly from delivery'
                );
            END IF;

            -- Update shopping list item
            IF v_item.shopping_list_item_id IS NOT NULL THEN
                UPDATE pms_shopping_list
                SET quantity_received = quantity_received + v_item.delivered_quantity,
                    status = CASE
                        WHEN quantity_received + v_item.delivered_quantity >= quantity_ordered THEN 'fulfilled'
                        ELSE 'partially_fulfilled'
                    END,
                    received_at = NOW()
                WHERE id = v_item.shopping_list_item_id;
            END IF;
        END LOOP;

        -- Record commit timestamp
        NEW.committed_at := NOW();
        NEW.committed_by := auth.uid();

        -- Update PO status
        IF NEW.purchase_order_id IS NOT NULL THEN
            UPDATE pms_purchase_orders
            SET status = 'completed',
                actual_delivery = CURRENT_DATE
            WHERE id = NEW.purchase_order_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_commit_receiving
    BEFORE UPDATE OF status ON public.pms_receiving_sessions
    FOR EACH ROW
    EXECUTE FUNCTION commit_receiving_session();

-- RLS
ALTER TABLE public.pms_receiving_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_receiving_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view receiving on own yacht" ON public.pms_receiving_sessions
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can manage receiving" ON public.pms_receiving_sessions
    FOR ALL TO authenticated
    USING (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );

CREATE POLICY "Users can view receiving items" ON public.pms_receiving_items
    FOR SELECT TO authenticated
    USING (
        receiving_session_id IN (
            SELECT id FROM pms_receiving_sessions
            WHERE yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        )
    );

CREATE POLICY "Users can manage receiving items" ON public.pms_receiving_items
    FOR ALL TO authenticated
    USING (
        receiving_session_id IN (
            SELECT id FROM pms_receiving_sessions
            WHERE yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        )
    );
```

**USER INTERACTIONS**:

#### Situational Action: RECEIVING WORKFLOW (Multi-stage, high-risk)

**Stage 1**: Create Session (MUTATE)
- User scans packing slip or manually enters delivery note number
- Creates receiving_session with status='candidate'
- Lists expected items from PO

**Stage 2**: Scan Items (MUTATE for each item)
- User scans barcode or manually selects part
- Enters delivered quantity
- **Checks checkbox** if item is correct
- Marks status (ok/damaged/wrong_item/short/excess)
- Can add photos
- Session status → 'active'

**Stage 3**: Review (READ)
- Shows summary:
  - ✓ 5 items checked (will be added to inventory)
  - ⚠️ 2 items unchecked (will NOT be added)
  - Total value: $2,450
- User confirms understanding

**Stage 4**: Commit (HIGH-RISK MUTATE)
- Session status → 'committed'
- Trigger executes:
  - Creates inventory transactions for ONLY checked items
  - Updates shopping list items
  - Updates part quantities
  - Marks PO as completed
- **IMMUTABLE after commit** (no undo)

**SIGNATURE REQUIRED**: YES (for commits >$1000 or >10 items)
```json
{
  "user_id": "...",
  "timestamp": "2026-01-11T15:30:00Z",
  "action": "commit_receiving",
  "session_id": "...",
  "hash": "sha256(...)",
  "items_count": 7,
  "total_value": 2450.00
}
```

**BAD INPUT**:
- Unchecked item with quantity → WARNING: "Item not checked - will NOT be added to inventory"
- Delivered quantity > expected * 2 → WARNING: "Delivered quantity much higher than expected - confirm this is correct"
- Status = 'damaged' but checked → ERROR: "Cannot add damaged items to inventory - uncheck or change status to 'ok'"

**UNDO/CANCEL**:
- Before commit: Can delete session entirely
- After commit: **NO UNDO** (inventory already updated)
- Workaround: Create adjustment transactions manually

---

### 1.15 AUDIT LOG (Universal Accountability)
```sql
CREATE TABLE IF NOT EXISTS public.pms_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Action details
    action TEXT NOT NULL,  -- e.g., 'create_work_order', 'log_part_usage', 'commit_receiving'
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,

    -- Who
    user_id UUID NOT NULL REFERENCES auth.users(id),
    user_role TEXT,  -- Snapshot of role at time of action
    user_ip INET,

    -- What changed
    old_values JSONB,
    new_values JSONB,
    changes_summary TEXT,  -- Human-readable: "Changed status from 'active' to 'completed'"

    -- Signature (for high-risk actions)
    signature JSONB,  -- {"hash": "...", "timestamp": "...", "method": "user_password"}

    -- Context
    session_id TEXT,  -- Browser session ID
    request_id TEXT,  -- API request ID for tracing
    metadata JSONB DEFAULT '{}'::jsonb,

    -- When
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_yacht ON public.pms_audit_log(yacht_id);
CREATE INDEX idx_audit_entity ON public.pms_audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_user ON public.pms_audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON public.pms_audit_log(yacht_id, action, created_at DESC);
CREATE INDEX idx_audit_created ON public.pms_audit_log(yacht_id, created_at DESC);

-- Partition by month for performance (optional for large installations)
-- CREATE TABLE pms_audit_log_2024_01 PARTITION OF pms_audit_log
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Helper function to create audit log entries
CREATE OR REPLACE FUNCTION create_audit_log(
    p_yacht_id UUID,
    p_action TEXT,
    p_entity_type TEXT,
    p_entity_id UUID,
    p_user_id UUID,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_signature JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_audit_id UUID;
    v_user_role TEXT;
BEGIN
    -- Get current user role
    SELECT role INTO v_user_role
    FROM public.user_profiles
    WHERE id = p_user_id;

    INSERT INTO pms_audit_log (
        yacht_id, action, entity_type, entity_id,
        user_id, user_role, old_values, new_values, signature
    ) VALUES (
        p_yacht_id, p_action, p_entity_type, p_entity_id,
        p_user_id, v_user_role, p_old_values, p_new_values, p_signature
    )
    RETURNING id INTO v_audit_id;

    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS: Users can view audit logs for their yacht
ALTER TABLE public.pms_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view audit log on own yacht" ON public.pms_audit_log
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

-- No INSERT/UPDATE/DELETE policies - only via function
```

**AUDIT LOG PATTERNS**:

#### Which actions require audit logs?
**ALWAYS AUDIT** (High-risk MUTATE actions):
- create_work_order_from_fault
- mark_work_order_complete
- log_part_usage
- commit_receiving_session
- approve_purchase_order
- update_equipment_status (if critical equipment)

**OPTIONALLY AUDIT** (Medium-risk):
- add_note_to_work_order
- add_to_handover
- update_user_profile

**NEVER AUDIT** (READ actions):
- show_manual_section
- check_stock_level
- view_equipment_history

#### Audit Log Entry Example:
```json
{
  "id": "...",
  "yacht_id": "...",
  "action": "create_work_order_from_fault",
  "entity_type": "work_order",
  "entity_id": "wo-uuid",
  "user_id": "user-uuid",
  "user_role": "engineer",
  "old_values": null,
  "new_values": {
    "title": "Fix: Generator 2 - MTU-OVHT-01",
    "fault_id": "fault-uuid",
    "priority": "high",
    "status": "candidate"
  },
  "changes_summary": "Created work order WO-2024-089 from fault F-2024-123",
  "signature": {
    "timestamp": "2026-01-11T15:30:00Z",
    "hash": "sha256(user_password + action_data)"
  },
  "created_at": "2026-01-11T15:30:00Z"
}
```

---

## PART 4: USER ROLE DECISION MATRIX

| Action | Crew | Engineer | 2nd Eng | Chief Eng | Captain | Admin |
|--------|------|----------|---------|-----------|---------|-------|
| **READ ACTIONS** ||||||||
| View faults | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View WOs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View equipment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View inventory | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Show manual section | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **LOW-RISK MUTATE** ||||||||
| Add note | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Add to handover | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create fault | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MEDIUM-RISK MUTATE** ||||||||
| Create WO | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Diagnose fault | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Log part usage | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update equipment | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **HIGH-RISK MUTATE** ||||||||
| Close WO | ❌ | ❌ | ✅* | ✅ | ✅ | ✅ |
| Approve shopping ($<500) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Approve shopping ($<5k) | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Approve shopping ($>5k) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Commit receiving | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Upload certificate | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **ADMIN ONLY** ||||||||
| Manage users | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Delete documents | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Modify audit logs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌** |

*2nd Engineer can close WOs only if hours_spent < 8
**No one can modify audit logs (immutable)

---

## PART 5: SIGNATURE REQUIREMENTS

### When Signatures Are Required:

1. **High-Value Actions**:
   - Approve purchases >$1,000
   - Commit receiving sessions >$1,000 or >10 items
   - Close work orders with hours_spent >20

2. **Safety-Critical Actions**:
   - Mark critical equipment as 'failed'
   - Override safety lockouts
   - Modify certificate expiry dates

3. **Compliance Actions**:
   - Submit hours of rest logs
   - Generate audit packs
   - Export compliance reports

### Signature Format:
```json
{
  "user_id": "uuid",
  "timestamp": "2026-01-11T15:30:00Z",
  "action": "approve_purchase",
  "entity_id": "po-uuid",
  "hash": "sha256(user_password_hash + action_data + timestamp)",
  "method": "password"  // Future: "biometric", "hardware_key"
}
```

### Signature Verification:
```sql
CREATE OR REPLACE FUNCTION verify_signature(
    p_signature JSONB,
    p_user_id UUID,
    p_action TEXT,
    p_entity_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_expected_hash TEXT;
    v_user_password_hash TEXT;
BEGIN
    -- Get user's password hash from auth.users
    -- Compute expected hash
    -- Compare with provided hash
    -- Return TRUE if match

    RETURN TRUE;  -- Simplified for spec
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## SUMMARY: DATABASE EXECUTION RULES

### Row-Level Security (RLS)
- ✅ EVERY table has RLS enabled
- ✅ EVERY query filtered by yacht_id
- ✅ Users can ONLY access their yacht's data
- ✅ Admin role can access all yachts (for support)

### Foreign Keys
- ✅ CASCADE delete for yacht-owned data
- ✅ SET NULL for cross-references
- ✅ RESTRICT for active references (e.g., part in use)

### Audit Trail
- ✅ High-risk mutations ALWAYS create audit log
- ✅ Audit logs are IMMUTABLE (no UPDATE/DELETE)
- ✅ Signatures stored in audit log for verification

### Timestamps
- ✅ ALWAYS use TIMESTAMPTZ (UTC)
- ✅ created_at, updated_at on mutable tables
- ✅ Specific timestamps for state changes (approved_at, completed_at, etc.)

### Indexes
- ✅ yacht_id on every table
- ✅ Foreign keys indexed
- ✅ Status/state fields indexed for filtering
- ✅ Full-text search for user-facing content
- ✅ Vector indexes for semantic search

This completes the foundational database schema specification. Ready for implementation.
