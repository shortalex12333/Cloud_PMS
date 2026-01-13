# DATABASE SCHEMA EXECUTION SPEC - PART 2
## NOTES, PARTS, INVENTORY, HANDOVER, DOCUMENTS

---

### 1.6 NOTES (Timeline/Breadcrumb Pattern)
```sql
CREATE TABLE IF NOT EXISTS public.pms_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Polymorphic relationship - note can attach to ANY entity
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'fault', 'work_order', 'equipment', 'part', 'checklist', 'handover', 'purchase_order'
    )),
    entity_id UUID NOT NULL,  -- References the parent entity

    -- Content
    note_text TEXT NOT NULL CHECK (LENGTH(note_text) >= 1 AND LENGTH(note_text) <= 5000),
    note_type TEXT DEFAULT 'general' CHECK (note_type IN (
        'general',          -- Standard note
        'observation',      -- What user noticed
        'action_taken',     -- What user did
        'diagnosis',        -- Technical analysis
        'warning',          -- Safety/risk alert
        'resolution',       -- How issue was fixed
        'handover_critical' -- Important for next shift
    )),

    -- People
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Optional rich content
    has_photo BOOLEAN DEFAULT FALSE,
    photo_urls TEXT[],  -- Array of storage URLs
    mentioned_users UUID[],  -- @ mentions

    -- Searchability
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', note_text)) STORED
);

CREATE INDEX idx_notes_yacht ON public.pms_notes(yacht_id);
CREATE INDEX idx_notes_entity ON public.pms_notes(entity_type, entity_id);
CREATE INDEX idx_notes_created ON public.pms_notes(yacht_id, created_at DESC);
CREATE INDEX idx_notes_entity_ordered ON public.pms_notes(entity_type, entity_id, created_at DESC);
CREATE INDEX idx_notes_user ON public.pms_notes(created_by, created_at DESC);
CREATE INDEX idx_notes_search ON public.pms_notes USING GIN(search_vector);

-- RLS
ALTER TABLE public.pms_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view notes on own yacht" ON public.pms_notes
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can create notes on own yacht" ON public.pms_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND created_by = auth.uid()
    );
```

**USER INTERACTIONS**:

#### Action: `add_note_to_work_order` (SIMPLE MUTATE)
**Single-stage action** (no preview needed - low risk):

1. User clicks "Add Note" on WO card
2. Modal opens with textarea
3. User types note (min 1 char, max 5000 chars)
4. Click "Add Note" button
5. Backend inserts row:
```sql
INSERT INTO pms_notes (yacht_id, entity_type, entity_id, note_text, created_by)
VALUES ($yacht_id, 'work_order', $wo_id, $note_text, $user_id);
```
6. Audit log created (optional for notes - low priority)
7. Success toast: "Note added"

**BAD INPUT**:
- Empty note → "Note cannot be empty"
- Note > 5000 chars → "Note too long (max 5000 characters)"
- Invalid entity_id → "Work order not found"

**UNDO**:
- Frontend: Cancel button clears textarea
- Backend: NO UNDO (notes are append-only)
- Workaround: Cannot delete notes (audit trail integrity)
- Future: Soft delete flag if required

**USER ROLE**: Any authenticated user on yacht
**SIGNATURE**: Not required

---

### 1.7 PARTS (Inventory Items)
```sql
CREATE TABLE IF NOT EXISTS public.pms_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identity
    part_number TEXT NOT NULL,  -- Manufacturer part number
    name TEXT NOT NULL,
    description TEXT,
    manufacturer TEXT,
    supplier TEXT,

    -- Classification
    category TEXT CHECK (category IN (
        'engine', 'electrical', 'plumbing', 'hvac', 'hydraulic',
        'navigation', 'safety', 'filters', 'oils', 'consumables', 'other'
    )),
    unit TEXT DEFAULT 'ea' CHECK (unit IN ('ea', 'kg', 'L', 'm', 'set', 'box')),

    -- Inventory
    quantity_on_hand NUMERIC(10,2) DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved NUMERIC(10,2) DEFAULT 0 CHECK (quantity_reserved >= 0),
    quantity_available AS (quantity_on_hand - quantity_reserved) STORED,

    -- Thresholds (for automatic shopping list triggers)
    minimum_quantity NUMERIC(10,2) DEFAULT 0 CHECK (minimum_quantity >= 0),
    critical_threshold NUMERIC(10,2) DEFAULT 0 CHECK (critical_threshold >= 0),
    reorder_quantity NUMERIC(10,2) DEFAULT 1,

    -- Location
    storage_location TEXT,
    bin_number TEXT,

    -- Linking
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,  -- Primary equipment this part fits
    compatible_equipment UUID[],  -- Array of other equipment IDs

    -- Pricing
    unit_cost NUMERIC(10,2),
    currency TEXT DEFAULT 'USD',
    last_purchase_date DATE,
    last_purchase_price NUMERIC(10,2),

    -- Barcoding
    barcode TEXT,
    qr_code TEXT,

    -- Status
    active BOOLEAN DEFAULT TRUE,
    obsolete BOOLEAN DEFAULT FALSE,

    -- Search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english',
            COALESCE(name, '') || ' ' ||
            COALESCE(part_number, '') || ' ' ||
            COALESCE(manufacturer, '') || ' ' ||
            COALESCE(description, '')
        )
    ) STORED,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, part_number)
);

CREATE INDEX idx_parts_yacht ON public.pms_parts(yacht_id);
CREATE INDEX idx_parts_part_number ON public.pms_parts(yacht_id, part_number);
CREATE INDEX idx_parts_name ON public.pms_parts(yacht_id, name);
CREATE INDEX idx_parts_category ON public.pms_parts(yacht_id, category);
CREATE INDEX idx_parts_equipment ON public.pms_parts(equipment_id);
CREATE INDEX idx_parts_barcode ON public.pms_parts(barcode) WHERE barcode IS NOT NULL;
CREATE INDEX idx_parts_low_stock ON public.pms_parts(yacht_id, quantity_available) WHERE quantity_available <= minimum_quantity;
CREATE INDEX idx_parts_critical_stock ON public.pms_parts(yacht_id, quantity_available) WHERE quantity_available <= critical_threshold;
CREATE INDEX idx_parts_search ON public.pms_parts USING GIN(search_vector);
CREATE INDEX idx_parts_active ON public.pms_parts(yacht_id, active) WHERE active = TRUE;

-- RLS
ALTER TABLE public.pms_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view parts on own yacht" ON public.pms_parts
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Engineers can manage parts" ON public.pms_parts
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

**THRESHOLD TRIGGERS**:
1. `quantity_available <= critical_threshold` → Auto-add to shopping list with urgency=URGENT
2. `quantity_available <= minimum_quantity` → Auto-add to shopping list with urgency=HIGH
3. `quantity_available = 0` → Block logging usage (with override option)

---

### 1.8 INVENTORY TRANSACTIONS (Ledger Pattern)
```sql
CREATE TABLE IF NOT EXISTS public.pms_inventory_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Core
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'receive',          -- Parts arrived
        'usage',            -- Parts consumed
        'adjustment',       -- Manual stock correction
        'transfer',         -- Move to another location
        'return',           -- Returned to supplier
        'disposal',         -- Disposed/discarded
        'install'           -- Installed on equipment (from receiving)
    )),

    quantity NUMERIC(10,2) NOT NULL,
    unit TEXT NOT NULL,

    -- Context
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    receiving_session_id UUID REFERENCES public.pms_receiving_sessions(id) ON DELETE SET NULL,
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,

    -- Reason (mandatory for certain transaction types)
    usage_reason TEXT CHECK (usage_reason IN (
        'maintenance', 'repair', 'installation', 'replacement',
        'testing', 'emergency', 'other'
    )),
    notes TEXT,

    -- People
    user_id UUID NOT NULL REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),  -- For adjustments >10% of stock

    -- Snapshot (for audit trail)
    quantity_before NUMERIC(10,2),
    quantity_after NUMERIC(10,2),

    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inv_trans_yacht ON public.pms_inventory_transactions(yacht_id);
CREATE INDEX idx_inv_trans_part ON public.pms_inventory_transactions(part_id, timestamp DESC);
CREATE INDEX idx_inv_trans_wo ON public.pms_inventory_transactions(work_order_id);
CREATE INDEX idx_inv_trans_user ON public.pms_inventory_transactions(user_id, timestamp DESC);
CREATE INDEX idx_inv_trans_type ON public.pms_inventory_transactions(yacht_id, transaction_type, timestamp DESC);
CREATE INDEX idx_inv_trans_recent ON public.pms_inventory_transactions(yacht_id, timestamp DESC);

-- Trigger to update part quantity
CREATE OR REPLACE FUNCTION update_part_quantity()
RETURNS TRIGGER AS $$
DECLARE
    v_quantity_before NUMERIC(10,2);
    v_quantity_after NUMERIC(10,2);
BEGIN
    -- Get current quantity
    SELECT quantity_on_hand INTO v_quantity_before
    FROM public.pms_parts WHERE id = NEW.part_id;

    -- Calculate new quantity based on transaction type
    IF NEW.transaction_type IN ('receive', 'return', 'adjustment') THEN
        v_quantity_after := v_quantity_before + NEW.quantity;
    ELSIF NEW.transaction_type IN ('usage', 'transfer', 'disposal', 'install') THEN
        v_quantity_after := v_quantity_before - NEW.quantity;
    END IF;

    -- Prevent negative stock (with warning flag)
    IF v_quantity_after < 0 THEN
        -- Allow but flag
        RAISE WARNING 'Negative stock for part %: %', NEW.part_id, v_quantity_after;
    END IF;

    -- Update part quantity
    UPDATE public.pms_parts
    SET quantity_on_hand = v_quantity_after,
        updated_at = NOW()
    WHERE id = NEW.part_id;

    -- Store snapshot
    NEW.quantity_before := v_quantity_before;
    NEW.quantity_after := v_quantity_after;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_update_part_quantity
    BEFORE INSERT ON public.pms_inventory_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_part_quantity();

-- RLS
ALTER TABLE public.pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view inventory transactions on own yacht" ON public.pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can log transactions" ON public.pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND user_id = auth.uid()
    );
```

**USER INTERACTIONS**:

#### Action: `log_part_usage` (MULTI-STAGE MUTATE WITH PREVIEW)
**Stage 1**: Prefill (READ)
- Backend fetches part data
- Returns: `{part_name, stock_level, unit, storage_location}`
- No mutation

**Stage 2**: User fills form
- Quantity (required, numeric, > 0)
- Work Order (optional, dropdown)
- Equipment (optional, dropdown)
- Usage reason (required, dropdown)
- Notes (optional, text)

**Stage 3**: Preview
- Shows stock change: "Stock will go from 12 to 9 (3 used)"
- Warnings:
  - If stock < minimum: "⚠️ Stock will fall below minimum (reorder recommended)"
  - If stock < 0: "⚠️ Negative stock! Logging allowed but inventory will be negative"
  - If quantity > stock: "⚠️ Using more than available stock"

**Stage 4**: Execute (MUTATE)
```sql
BEGIN;
    -- 1. Create transaction
    INSERT INTO pms_inventory_transactions (
        yacht_id, part_id, transaction_type, quantity, unit,
        work_order_id, equipment_id, usage_reason, notes, user_id
    ) VALUES (...);
    -- Trigger automatically updates part quantity

    -- 2. Check thresholds and auto-create shopping list items
    -- (See shopping list section)

    -- 3. Audit log
    INSERT INTO pms_audit_log (...) VALUES (...);
COMMIT;
```

**BAD INPUT**:
- Quantity ≤ 0 → "Quantity must be greater than 0"
- No usage reason → "Usage reason required"
- Invalid part ID → "Part not found"
- Quantity > 1000x stock → "Quantity suspiciously high - confirm this is correct"

**UNDO**:
- Frontend: Cancel button before Execute
- Backend: NO UNDO after Execute
- Workaround: Create reverse transaction (transaction_type='adjustment', quantity=+N)
- Requires Chief Engineer approval for adjustments >10% of stock

**USER ROLE**: Any authenticated user
**SIGNATURE**: Not required (but logged for accountability)

---

### 1.9 HANDOVER (Shift Communication)
```sql
CREATE TABLE IF NOT EXISTS public.pms_handover (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Entity reference (polymorphic)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'fault', 'work_order', 'equipment', 'document_chunk', 'part', 'manual_note'
    )),
    entity_id UUID,  -- NULL for manual notes

    -- Content
    summary_text TEXT NOT NULL CHECK (LENGTH(summary_text) >= 10 AND LENGTH(summary_text) <= 2000),

    -- Classification
    category TEXT NOT NULL CHECK (category IN (
        'ongoing_fault',      -- Active problem
        'work_in_progress',   -- WO underway
        'important_info',     -- Need-to-know
        'equipment_status',   -- Equipment state change
        'general'             -- Other
    )),

    priority INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 4),
    -- 1 = low, 2 = normal, 3 = high, 4 = urgent

    -- People
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    acknowledged_by UUID REFERENCES auth.users(id),
    acknowledged_at TIMESTAMPTZ,

    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN (
        'active',        -- Current handover item
        'acknowledged',  -- Seen by next shift
        'resolved',      -- Issue handled
        'archived'       -- Old/irrelevant
    )),

    -- Search
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', summary_text)) STORED
);

CREATE INDEX idx_handover_yacht ON public.pms_handover(yacht_id);
CREATE INDEX idx_handover_entity ON public.pms_handover(entity_type, entity_id);
CREATE INDEX idx_handover_priority ON public.pms_handover(yacht_id, priority DESC, added_at DESC);
CREATE INDEX idx_handover_category ON public.pms_handover(yacht_id, category);
CREATE INDEX idx_handover_active ON public.pms_handover(yacht_id, added_at DESC) WHERE status = 'active';
CREATE INDEX idx_handover_unacknowledged ON public.pms_handover(yacht_id, added_at) WHERE acknowledged_at IS NULL;
CREATE INDEX idx_handover_search ON public.pms_handover USING GIN(search_vector);

-- Auto-archive old items (>7 days acknowledged or >14 days old)
CREATE OR REPLACE FUNCTION archive_old_handover_items()
RETURNS void AS $$
BEGIN
    UPDATE public.pms_handover
    SET status = 'archived'
    WHERE status IN ('active', 'acknowledged')
    AND (
        (acknowledged_at IS NOT NULL AND acknowledged_at < NOW() - INTERVAL '7 days')
        OR (added_at < NOW() - INTERVAL '14 days')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS
ALTER TABLE public.pms_handover ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view handover on own yacht" ON public.pms_handover
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can create handover items" ON public.pms_handover
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND added_by = auth.uid()
    );

CREATE POLICY "Users can acknowledge handover" ON public.pms_handover
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    )
    WITH CHECK (
        acknowledged_by = auth.uid() OR added_by = auth.uid()
    );
```

**USER INTERACTIONS**:

#### Action: `add_to_handover` (SIMPLE MUTATE)
Already implemented - see previous handover implementation.

**New behavior: Automatic acknowledgment tracking**:
- Each user has "last_seen_handover" timestamp
- Unacknowledged items = items added after user's last_seen
- "Acknowledge all" button updates all items AND user's last_seen timestamp

---

### 1.10 DOCUMENTS (Manuals, SOPs, Drawings)
```sql
CREATE TABLE IF NOT EXISTS public.pms_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identity
    title TEXT NOT NULL,
    document_type TEXT NOT NULL CHECK (document_type IN (
        'manual',           -- Equipment manual
        'sop',              -- Standard Operating Procedure
        'drawing',          -- Technical drawing/schematic
        'certificate',      -- Compliance certificate
        'bulletin',         -- Service bulletin
        'parts_list',       -- Parts catalog
        'other'
    )),

    -- Metadata
    manufacturer TEXT,
    model TEXT,
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    document_number TEXT,  -- Manufacturer doc number
    revision TEXT,
    issue_date DATE,

    -- Storage
    storage_path TEXT NOT NULL,  -- Supabase storage path
    file_size_bytes BIGINT,
    mime_type TEXT,
    page_count INTEGER,

    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'archived')),
    superseded_by UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,

    -- Access
    public_access BOOLEAN DEFAULT FALSE,  -- Available to all crew vs restricted

    -- Tags
    tags TEXT[],
    category_tags TEXT[],

    -- Upload info
    uploaded_by UUID NOT NULL REFERENCES auth.users(id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,

    -- Search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english',
            COALESCE(title, '') || ' ' ||
            COALESCE(manufacturer, '') || ' ' ||
            COALESCE(model, '') || ' ' ||
            COALESCE(document_number, '') || ' ' ||
            COALESCE(array_to_string(tags, ' '), '')
        )
    ) STORED
);

CREATE INDEX idx_documents_yacht ON public.pms_documents(yacht_id);
CREATE INDEX idx_documents_equipment ON public.pms_documents(equipment_id);
CREATE INDEX idx_documents_type ON public.pms_documents(yacht_id, document_type);
CREATE INDEX idx_documents_status ON public.pms_documents(yacht_id, status);
CREATE INDEX idx_documents_search ON public.pms_documents USING GIN(search_vector);
CREATE INDEX idx_documents_tags ON public.pms_documents USING GIN(tags);
CREATE INDEX idx_documents_manufacturer ON public.pms_documents(yacht_id, manufacturer, model);

-- RLS
ALTER TABLE public.pms_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view documents on own yacht" ON public.pms_documents
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND (public_access = TRUE OR 'captain' = (SELECT role FROM public.user_profiles WHERE id = auth.uid()))
    );

CREATE POLICY "Engineers can manage documents" ON public.pms_documents
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'captain', 'admin')
        )
    );
```

---

(Continuing in next message with Document Chunks, Shopping List, Receiving, and Audit Log...)
