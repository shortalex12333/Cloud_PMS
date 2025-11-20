Below is a **database plan you can drop into GitHub as “db-design.md”** and build from.
Assume **Postgres + pgvector**, cloud-only, one logical schema per yacht (or shared with `yacht_id` if you later multi-tenant).

I’ll cover:

* Core entities (yacht, user, signatures)
* PMS
* Inventory
* Hours of rest
* History & analytics
* Handover
* NAS docs & embeddings
* Celeste scraped data
* Graph RAG vs normal RAG

---

## 0. Conventions

* `id` → `uuid` primary key
* All tables have `created_at`, `updated_at` (timestamps)
* Multi-tenant isolation:

  * Either **DB-per-yacht**, or
  * Shared DB with `yacht_id uuid` on almost every table
* Vector columns use `vector(768)` (or whatever your embedding size ends up being)

---

## 1. Core: Yachts, Users, Auth, Signatures

### 1.1 `yachts`

Each vessel you serve.

```sql
yachts (
  id uuid pk,
  name text,
  imo text null,
  mmsi text null,
  flag_state text null,
  length_m numeric null,
  owner_ref text null, -- not PII, just label
  signature text unique, -- yacht install key / SHA
  nas_root_path text null,
  status text, -- active/inactive/demo
  created_at timestamptz,
  updated_at timestamptz
)
```

> **Graph RAG:** not used here
> **RAG:** no

---

### 1.2 `users`

Crew, managers, service providers.

```sql
users (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  email text unique,
  name text,
  role text, -- 'chief_engineer', 'eto', 'captain', 'manager', 'vendor', etc.
  auth_provider text, -- 'password', 'oauth', 'sso'
  is_active bool default true,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

### 1.3 `user_tokens`

For API tokens, device tokens, session keys.

```sql
user_tokens (
  id uuid pk,
  user_id uuid fk users.id,
  yacht_id uuid fk yachts.id,
  token_hash text, -- bcrypt or similar, NEVER raw
  token_type text, -- 'api', 'device', 'refresh'
  issued_at timestamptz,
  expires_at timestamptz null,
  last_used_at timestamptz null,
  metadata jsonb,
  created_at timestamptz
)
```

---

### 1.4 `yacht_signatures`

You might fold this into `yachts`, but if you want explicit tracking:

```sql
yacht_signatures (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  signature text unique, -- generated at install
  public_key text null,
  created_at timestamptz
)
```

Used by mobile + agent to route uploads to the correct bucket.

---

## 2. PMS (Planned Maintenance System)

### 2.1 `equipment`

Master list of all systems, subsystems, components.

```sql
equipment (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  parent_id uuid fk equipment.id null,
  name text,
  code text null, -- tag / label, e.g. ME1, GEN2
  description text,
  location text, -- engine room, aft, etc.
  manufacturer text,
  model text,
  serial_number text,
  installed_date date null,
  criticality text, -- low/med/high
  system_type text, -- 'main_engine', 'generator', 'hvac', etc.
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

> **Graph RAG:**
>
> * Nodes for `equipment`
> * Edges to parts, faults, docs, work_orders

---

### 2.2 `work_orders`

Planned & corrective maintenance.

```sql
work_orders (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  equipment_id uuid fk equipment.id null,
  title text,
  description text,
  type text, -- 'scheduled', 'corrective', 'unplanned'
  priority text, -- 'routine','important','critical'
  status text, -- 'planned','in_progress','completed','deferred','cancelled'
  due_date date null,
  due_hours int null,
  last_completed_date date null,
  last_completed_hours int null,
  frequency jsonb null, -- {type:'hours'|'days'|'months', value:int}
  created_by uuid fk users.id,
  updated_by uuid fk users.id null,
  created_at timestamptz,
  updated_at timestamptz
)
```

> **RAG:**
>
> * Work orders themselves are structured; usually you’ll RAG on **history**, not this table.

---

### 2.3 `work_order_history`

Completed executions, notes, parts usage.

```sql
work_order_history (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  work_order_id uuid fk work_orders.id,
  equipment_id uuid fk equipment.id,
  completed_by uuid fk users.id,
  completed_at timestamptz,
  notes text,
  hours_logged int null,
  status_on_completion text, -- 'completed','partial','failed'
  parts_used jsonb, -- [{part_id, quantity}]
  documents_used jsonb, -- [{document_id, chunk_ids}]
  faults_related jsonb, -- [{fault_id}]
  metadata jsonb,
  created_at timestamptz
)
```

> **RAG:**
>
> * `notes` should be vectorised into a separate `work_order_history_embeddings` table or a `vector` column.
>   **Graph RAG:**
> * edges: `EQUIPMENT -[HAD_FAULT]-> FAULT`
> * edges: `EQUIPMENT -[USED_PART]-> PART`
> * edges: `WORK_ORDER -[USES_DOC]-> DOCUMENT_CHUNK`

---

### 2.4 `faults`

Fault events and codes.

```sql
faults (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  equipment_id uuid fk equipment.id,
  fault_code text null,
  title text,
  description text,
  severity text, -- 'low','medium','high'
  detected_at timestamptz,
  resolved_at timestamptz null,
  resolved_by uuid fk users.id null,
  work_order_id uuid fk work_orders.id null,
  metadata jsonb,
  created_at timestamptz
)
```

> **RAG:**
>
> * `description` vectorised for lookup by natural language.
>   **Graph RAG:**
> * Node `FAULT` plus edges to `EQUIPMENT`, `WORK_ORDER`, `PART`, `DOC_CHUNK`.

---

## 3. Inventory

### 3.1 `parts`

Master list of parts/spares.

```sql
parts (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  name text,
  part_number text,
  manufacturer text,
  description text,
  category text, -- filter, gasket, belt, etc.
  model_compatibility jsonb, -- ['CAT3516', 'MTU4000']
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

> **RAG:**
>
> * `description` and maybe `model_compatibility` into vector search if engineers search by “the big green coolant hose”.
>   **Graph RAG:**
> * Node `PART`, edges to `EQUIPMENT`, `WORK_ORDER_HISTORY`, `SUPPLIER`.

---

### 3.2 `stock_locations`

Where things are physically stored.

```sql
stock_locations (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  name text, -- "Engine Room Locker A"
  description text,
  deck text null,
  position text null, -- shelf/bin labels
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

### 3.3 `stock_levels`

Current inventory per location.

```sql
stock_levels (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  part_id uuid fk parts.id,
  location_id uuid fk stock_locations.id,
  quantity int,
  min_quantity int,
  max_quantity int null,
  reorder_quantity int null,
  last_counted_at timestamptz null,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

### 3.4 `suppliers`

Vendors & OEMs.

```sql
suppliers (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  name text,
  contact_name text null,
  email text null,
  phone text null,
  address jsonb,
  preferred bool default false,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

### 3.5 `purchase_orders`

For later integration with predictive & costing.

```sql
purchase_orders (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  supplier_id uuid fk suppliers.id,
  po_number text,
  status text, -- 'draft','sent','partially_received','closed'
  ordered_at timestamptz,
  received_at timestamptz null,
  currency text null,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)

purchase_order_lines (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  purchase_order_id uuid fk purchase_orders.id,
  part_id uuid fk parts.id,
  description text,
  quantity_ordered int,
  quantity_received int default 0,
  unit_price numeric null,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

## 4. Hours of Rest (HOR)

Low-frequency but needed for compliance. Keep it lean.

```sql
hours_of_rest_records (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  user_id uuid fk users.id,
  date date,
  hours_worked numeric(5,2),
  hours_of_rest numeric(5,2),
  violations bool default false,
  notes text,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

> No RAG or graph needed here for MVP. Use simple reports.

---

## 5. Handover

### 5.1 `handover_drafts`

In-progress, 50%-auto-populated handovers.

```sql
handover_drafts (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  period_start date null,
  period_end date null,
  title text,
  description text, -- freeform summary (can be AI generated)
  created_by uuid fk users.id,
  status text, -- 'draft','finalised'
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

### 5.2 `handover_items`

Link specific content (faults, WOs, docs, notes) to a draft.

```sql
handover_items (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  handover_id uuid fk handover_drafts.id,
  source_type text, -- 'work_order','fault','doc_chunk','note','part'
  source_id uuid,   -- references depending on type
  summary text,     -- AI generated short summary
  detail text,      -- optional longer text
  importance text,  -- 'low','normal','high'
  created_at timestamptz,
  updated_at timestamptz
)
```

### 5.3 `handover_exports`

Final exported docs.

```sql
handover_exports (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  handover_id uuid fk handover_drafts.id,
  format text, -- 'pdf','html'
  storage_path text, -- in object storage
  exported_at timestamptz,
  exported_by uuid fk users.id,
  metadata jsonb
)
```

> **RAG:**
>
> * `handover_items.summary/detail` into vector search for future “what happened in March?” queries.
>   **Graph RAG:**
> * edges: `HANDOVER_ITEM -> EQUIPMENT/FAULT/PART` to track long-term patterns.

---

## 6. History & Analytics

Separate from PMS history (which is `work_order_history`, `faults`).

### 6.1 `search_queries`

For analytics + predictive patterns.

```sql
search_queries (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  user_id uuid fk users.id null,
  query_text text,
  interpreted_intent text null, -- 'diagnose_fault','find_manual','create_work_order'
  entities jsonb, -- {equipment_id, fault_code, ...}
  latency_ms int null,
  success bool null,
  created_at timestamptz
)
```

> **RAG:**
>
> * optional; you might later embed queries to cluster pain points.
>   **Graph:**
> * edges from `USER` to `EQUIPMENT`/`FAULT` for usage patterns.

---

### 6.2 `event_log`

General-purpose logging (create/update/delete, etc.).

```sql
event_log (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  user_id uuid fk users.id null,
  event_type text, -- 'create_work_order','add_note','login','export_handover'
  entity_type text,
  entity_id uuid null,
  metadata jsonb,
  created_at timestamptz
)
```

Used later for dashboards and billing if needed.

---

## 7. NAS Docs & Embeddings (Core for Search / RAG)

### 7.1 `documents`

One row per file ingested from NAS / email / upload.

```sql
documents (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  source text, -- 'nas','email','upload','migration'
  original_path text null, -- NAS path or email id
  filename text,
  content_type text,
  size_bytes bigint,
  sha256 text,
  storage_path text, -- where stored in object storage
  equipment_ids uuid[] null, -- optional fast link
  tags text[] null, -- 'manual','schematic','handover','invoice'
  indexed bool default false,
  indexed_at timestamptz null,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

---

### 7.2 `document_chunks`

The actual chunks you search over.

```sql
document_chunks (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  document_id uuid fk documents.id,
  chunk_index int,
  text text,
  page_number int null,
  embedding vector(768), -- pgvector
  equipment_ids uuid[] null,
  fault_codes text[] null,
  tags text[] null,
  metadata jsonb,
  created_at timestamptz
)
```

> **RAG:**
>
> * This is your main **regular RAG** surface for “find me relevant paragraphs/pages”.
>   **Graph RAG:**
> * `DOC_CHUNK` becomes a node in `graph_nodes` and gets edges to `EQUIPMENT`, `FAULT`, `PART`.

---

### 7.3 `email_messages` (optional for MVP, but useful)

If you index email bodies.

```sql
email_messages (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  external_id text, -- message-id or provider ID
  subject text,
  sender text,
  recipients text[],
  sent_at timestamptz,
  body_text text,
  embedding vector(768),
  in_reply_to text null,
  thread_id text null,
  metadata jsonb,
  created_at timestamptz
)
```

---

## 8. Celeste Scraped Data (Global Knowledge)

This is shared across yachts. Use a separate `celeste` schema without `yacht_id`.

### 8.1 `celeste_documents`

```sql
celeste_documents (
  id uuid pk,
  source_url text,
  domain text,
  manufacturer text null,
  model text null,
  doc_type text, -- 'forum_thread','manual','service_bulletin'
  title text,
  sha256 text,
  fetched_at timestamptz,
  metadata jsonb
)
```

### 8.2 `celeste_chunks`

```sql
celeste_chunks (
  id uuid pk,
  document_id uuid fk celeste_documents.id,
  chunk_index int,
  text text,
  embedding vector(768),
  equipment_tags text[] null,
  fault_codes text[] null,
  metadata jsonb,
  created_at timestamptz
)
```

> **RAG:**
>
> * Use for “global” answers when onboard docs are weak.
>   **Graph RAG:**
> * Link global nodes to yacht equipment models to transfer knowledge across fleet.

---

## 9. Graph RAG Tables

Instead of jamming graph into every table, keep explicit graph tables.

### 9.1 `graph_nodes`

```sql
graph_nodes (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  node_type text, -- 'equipment','part','fault','doc_chunk','work_order','handover_item'
  ref_table text, -- 'equipment','parts','faults','document_chunks',...
  ref_id uuid,    -- id in ref_table
  label text,
  properties jsonb,
  created_at timestamptz
)
```

### 9.2 `graph_edges`

```sql
graph_edges (
  id uuid pk,
  yacht_id uuid fk yachts.id,
  from_node_id uuid fk graph_nodes.id,
  to_node_id uuid fk graph_nodes.id,
  edge_type text, -- 'USES_PART','HAS_FAULT','MENTIONED_IN','REFERS_TO','PARENT_OF'
  weight numeric null,
  properties jsonb,
  created_at timestamptz
)
```

Where Graph RAG is useful:

* “Show relationships between this fault and all systems it’s affected.”
* “What other equipment uses the same parts as this main engine?”
* “What docs and previous work orders cluster around this system?”
* “Which components are central nodes in failure graphs?”

Where Regular RAG is enough:

* “What does this fault code mean?”
* “Show me the procedure for changing this filter.”
* “Summarise last month’s handover.”
* “Find that email about the generator overheating.”

---

## 10. Quick Map: Use Case → Tables → RAG / Graph

**Search fault & get answer**

* Tables: `faults`, `document_chunks`, `work_order_history`
* RAG: `document_chunks.embedding`, `work_order_history.notes`
* Optional graph: link fault ↔ equipment ↔ parts

**Create work order from search**

* Tables: `equipment`, `work_orders`
* No RAG, just structured

**Auto-build handover**

* Tables: `handover_drafts`, `handover_items`, `work_order_history`, `faults`, `document_chunks`
* RAG: summarise `notes`, `doc_chunks`
* Graph: track links for predictive

**Predictive maintenance**

* Tables: `faults`, `work_order_history`, `parts`, `search_queries`, `graph_edges`
* Graph RAG: explore which equipment is central in failure network
* RAG: pull relevant text when explaining “why”

**Inventory search**

* Tables: `parts`, `stock_levels`, `document_chunks`
* RAG: free-text part description/doc search
* Optional graph: parts ↔ equipment ↔ suppliers

**Global scraped knowledge**

* Tables: `celeste_documents`, `celeste_chunks`
* RAG-only at first, later graph them to models.

---
