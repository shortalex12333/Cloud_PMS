# Work Order Lens: GraphRAG-Enabled Show Related
**Vision**: The BEST Product for Crew (Regardless of Cost)
**Date**: 2026-01-28
**Philosophy**: Embed Everything, Connect Everything, Make Crew's Lives Easier

---

## 🎯 The Crew Journey (What They ACTUALLY Need)

### Morning: 07:00 - Starting Watch

**Crew Action**: Check handover report
**What They Need**:
- Critical items flagged by previous watch
- Outstanding work orders
- Equipment requiring attention
- Parts that arrived overnight

**Current Pain**: Open handover PDF, manually cross-reference with work order list, check parts inventory separately.

**GraphRAG Solution**:
```
Crew opens app → Dashboard shows:
- "3 critical items from night watch"
  → Click → Auto-expands related WOs, equipment status, available parts
- "Coolant delivery arrived"
  → Click → Shows all WOs waiting for this part + where to use it
- "Starboard engine due for service in 12 hours"
  → Click → Shows service checklist, required parts (with stock status), manual sections
```

**Embeddings Needed**:
- `handover_exports.content` (OCR'd or structured text)
- `pms_work_orders.title + description + metadata`
- `pms_parts.name + description + location`
- `pms_equipment.name + description + service_notes`

---

### 10:00 - Daily Rounds (Equipment Inspection)

**Crew Action**: Walking through engine room, notices "Starboard engine making unusual noise"

**What They Need**:
1. "Has this happened before?" (historical context)
2. "What did we do?" (previous diagnosis + solution)
3. "What parts did we use?" (immediate action plan)
4. "Is this normal for this equipment?" (prevent false alarms)
5. "Should I create a work order or just monitor?" (decision support)

**Current Pain**:
- Open Fault Lens → Search for similar faults (no results if not reported as fault)
- Open Work Order Lens → Try to remember WO numbers from previous engine work
- Open Equipment → Scroll through long maintenance history
- Call senior engineer for advice

**GraphRAG Solution**:
```
Crew: "Tell me about unusual noises from starboard engine"

AI Response:
"Found 3 similar incidents in the last year:

1. WO-2025-312 (4 months ago): 'Grinding noise from starboard main engine'
   - Diagnosis: Worn bearing in fuel pump
   - Parts used: Bearing set (PN: BRG-8800), Gasket (PN: GSK-1122)
   - Resolution: Replaced bearing, noise stopped
   - Photos: [3 images showing bearing wear]
   - Manual: Section 4.2.1 - Fuel Pump Bearing Replacement

2. WO-2025-089 (7 months ago): 'Vibration and whining from starboard engine'
   - Diagnosis: Loose alternator belt
   - Parts used: Belt (PN: BLT-9921)
   - Resolution: Tightened belt, noise resolved

3. F-045 (1 year ago): 'Knocking sound starboard engine'
   - Diagnosis: Low oil pressure
   - Resolution: Topped up oil, noise disappeared
   - Note: Chief Engineer marked as 'normal wear pattern'

Recommendation: Check fuel pump bearing first (most likely), then alternator belt.
Required parts are in stock (Stores C-14)."
```

**Embeddings Needed**:
- `pms_work_orders.title + description + completion_notes + diagnosis`
- `pms_faults.title + description + metadata.diagnosis`
- `pms_work_order_notes.note_text`
- `pms_parts.name + description + specifications`
- `doc_metadata` (OCR'd manual sections)
- `metadata.photos` (image embeddings via CLIP)

---

### 14:00 - Creating Work Order (After Discovery)

**Crew Action**: Creates WO-2026-150: "Investigate starboard engine noise"

**What They Want**: System to auto-suggest:
- Related parts (based on historical patterns)
- Estimated time (based on similar WOs)
- Required tools
- Manual sections to reference
- Photos/videos from previous similar work

**Current Pain**: Start from blank form, manually search for parts, guess at estimated time.

**GraphRAG Solution**:
```
Crew fills in:
- Title: "Investigate starboard engine noise"
- Equipment: Starboard Main Engine
- Description: "Grinding noise from fuel pump area, louder under load"

AI Auto-Suggests:
📦 Likely Parts Needed (based on similar WOs):
  ✓ Bearing set BRG-8800 (used in 2/3 similar cases)
  ✓ Gasket GSK-1122 (used in 2/3 cases)
  ? Belt BLT-9921 (used in 1/3 cases)
  [Add all] [Customize]

⏱️ Estimated Duration: 3-4 hours (based on WO-2025-312 actual: 3.5hrs)

📖 Relevant Manual Sections:
  - Section 4.2.1: Fuel Pump Bearing Replacement (pg 87)
  - Section 4.3: Fuel System Troubleshooting (pg 92)
  [View PDFs]

📸 Reference Photos from WO-2025-312:
  [3 images showing bearing removal process]

👥 Suggested Assignee: Engineer Mike (completed WO-2025-312)
```

**Embeddings Needed**:
- `pms_work_orders` (all text fields)
- `pms_parts` (full catalog)
- `doc_metadata` (chunked manual sections)
- `user.expertise` (who's done this before)

---

### 16:00 - Executing Work (Finding Information)

**Crew Action**: Working on the repair, needs specific torque specs from manual

**Current Pain**:
- Open PDF manual
- CTRL+F "torque" → 47 results
- Scroll through irrelevant results
- Give up, ask senior engineer

**GraphRAG Solution**:
```
Crew (while viewing WO-2026-150):
"What torque for fuel pump bearing bolts?"

AI Response (contextual to current WO + equipment):
"Fuel pump bearing housing bolts (M8x1.25):
- Torque: 25 Nm (18 ft-lb)
- Sequence: Cross-pattern, 3 stages (10 Nm → 20 Nm → 25 Nm)
- Source: Starboard Engine Manual, Section 4.2.1, Page 89

[Show PDF] [Mark as helpful]"
```

**Embeddings Needed**:
- `doc_metadata` (chunked by section + page)
- `pms_equipment` (context: which manual to search)
- Current WO context (what user is working on)

---

### 18:00 - Completing Work Order

**Crew Action**: Adds completion notes, photos, parts used

**What They Want**:
- Quick way to document findings
- Link to parts actually used
- Reference similar WOs for next time

**Current Pain**: Type everything manually, forget to link parts, lose tribal knowledge.

**GraphRAG Solution**:
```
Crew completes WO, adds note:
"Replaced bearing in fuel pump. Bearing was worn on inner race.
Noise stopped after replacement. Used parts BRG-8800 and GSK-1122."

AI Auto-Links:
✓ Parts detected: BRG-8800, GSK-1122 (auto-linked)
✓ Similar WO detected: WO-2025-312 (cross-referenced)
✓ Added to equipment history: Starboard Main Engine
✓ Photos uploaded to storage: 3 images (bearing wear)

AI Generates Completion Summary:
"Root Cause: Worn fuel pump bearing (inner race)
Solution: Replaced bearing set BRG-8800 + gasket
Duration: 3.2 hours (estimated: 3-4 hours ✓)
Parts Cost: $145 (bearing) + $12 (gasket)
Similar Issues: WO-2025-312 (same root cause, 4 months ago)
Recommendation: Monitor fuel pump bearing every 3 months"
```

**Embeddings Needed**:
- `completion_notes` text
- Part number extraction + linking
- Photo embeddings (visual similarity)
- Historical pattern detection

---

## 🧠 What to Embed (Complete List)

### Tier 1: ESSENTIAL (Embed Immediately)

| Table | Column(s) | Why | Embedding Strategy |
|-------|-----------|-----|-------------------|
| **pms_work_orders** | title, description, completion_notes, diagnosis | Core workflow, 90% of queries | Concat: `{wo_number} {title} {description} {completion_notes}` |
| **pms_equipment** | name, code, description, location, manufacturer, model | Equipment is the anchor for all maintenance | Concat: `{name} {code} {manufacturer} {model} {location} {system_type}` |
| **pms_parts** | name, description, part_number, manufacturer, specifications | Already has embeddings! Expand to include specs | Concat: `{name} {part_number} {manufacturer} {description} {category}` |
| **pms_faults** | title, description, fault_code, metadata.diagnosis | Diagnosis contains rich problem-solving knowledge | Concat: `{fault_code} {title} {description} {diagnosis}` |
| **pms_work_order_notes** | note_text | Tribal knowledge, engineer insights | Each note as separate embedding |

### Tier 2: HIGH VALUE (Embed Week 2)

| Table | Column(s) | Why | Embedding Strategy |
|-------|-----------|-----|-------------------|
| **doc_metadata** | filename, metadata (OCR'd content) | Manuals, spec sheets are critical references | Chunked embeddings (512 tokens per chunk) |
| **handover_exports** | content (structured text/OCR) | Captain/HOD context, critical info | Full document embedding + section embeddings |
| **pms_shopping_list_items** | part_name, source_notes | Why parts were ordered (context for future) | Concat: `{part_name} {source_notes}` |
| **pms_audit_log** | action, metadata (for pattern detection) | Who does what, when, why (behavioral patterns) | Action + metadata text |

### Tier 3: ADVANCED (Embed Month 2)

| Table | Column(s) | Why | Embedding Strategy |
|-------|-----------|-----|-------------------|
| **Photos (JSONB)** | metadata.photos[].url + caption | Visual similarity (CLIP embeddings) | Image → CLIP vector, caption → text embedding |
| **User Expertise** | Inferred from completed WOs | Who's good at what? | Aggregate embeddings of user's completed WOs |
| **Equipment Manuals** | PDF pages (OCR'd) | Full-text search within manuals | Page-level embeddings + paragraph-level |
| **Vendor Emails** | If integrated, email content | Order confirmations, tech support replies | Email body embeddings |

---

## 🕸️ GraphRAG Architecture (The Magic)

### What is GraphRAG?

**Traditional RAG**: Query → Embed → Semantic search → Return top-K results
**GraphRAG**: Query → Embed → Semantic search → **Traverse knowledge graph** → Return contextually-connected results

**Example**:
```
User Query: "Starboard engine bearing replacement"

Traditional RAG Returns:
1. WO-2025-312 (bearing replacement)
2. Manual section 4.2.1 (bearing specs)
3. Part BRG-8800 (bearing)

GraphRAG Returns (with graph traversal):
1. WO-2025-312 (bearing replacement)
   ├─→ Part BRG-8800 (bearing used)
   │   ├─→ Shopping Item (last ordered 2 months ago, 2 in stock)
   │   ├─→ Vendor: BearingCo (lead time: 5 days)
   │   └─→ Other WOs using this part (WO-2024-089, WO-2023-156)
   ├─→ Equipment: Starboard Main Engine
   │   ├─→ Manual Section 4.2.1 (pg 87-92)
   │   ├─→ Service History (last bearing replaced 8 months ago)
   │   └─→ Other recent WOs (WO-2026-045: oil change)
   ├─→ Completed by: Engineer Mike
   │   └─→ Other similar WOs by Mike (3 bearing replacements)
   └─→ Photos (3 images showing bearing wear patterns)
```

### Graph Schema (Neo4j or PostgreSQL with pgvector + edges)

```cypher
// Nodes
(:WorkOrder {id, title, description, embedding})
(:Part {id, name, part_number, embedding})
(:Equipment {id, name, manufacturer, embedding})
(:Fault {id, fault_code, description, embedding})
(:Document {id, filename, content_embedding, page_embeddings[]})
(:User {id, name, role, expertise_embedding})
(:Photo {id, url, image_embedding, caption_embedding})

// Edges (relationships)
(:WorkOrder)-[:USES_PART {quantity}]->(:Part)
(:WorkOrder)-[:ON_EQUIPMENT]->(:Equipment)
(:WorkOrder)-[:RESOLVES_FAULT]->(:Fault)
(:WorkOrder)-[:REFERENCES_MANUAL]->(:Document)
(:WorkOrder)-[:COMPLETED_BY]->(:User)
(:WorkOrder)-[:ATTACHED_PHOTO]->(:Photo)
(:WorkOrder)-[:SIMILAR_TO {similarity_score}]->(:WorkOrder)  // Embedding similarity
(:Equipment)-[:HAS_MANUAL]->(:Document)
(:Equipment)-[:LOCATED_IN {area}]->(:Location)
(:Part)-[:COMPATIBLE_WITH]->(:Equipment)
(:Part)-[:SUPPLIED_BY]->(:Vendor)
```

### Query Example (Cypher)

```cypher
// Find everything related to starboard engine bearing work
MATCH path = (wo:WorkOrder)-[*1..3]-(related)
WHERE wo.embedding <~> $query_embedding < 0.3  // Cosine distance
  AND wo.equipment_id = 'starboard-engine-uuid'
  AND wo.title CONTAINS 'bearing'
RETURN path
ORDER BY wo.completed_at DESC
LIMIT 50
```

### PostgreSQL Alternative (Without Neo4j)

```sql
-- Create edges table
CREATE TABLE pms_knowledge_graph_edges (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  source_entity_type TEXT,
  source_entity_id UUID,
  target_entity_type TEXT,
  target_entity_id UUID,
  edge_type TEXT,  -- 'uses_part', 'on_equipment', 'similar_to', etc.
  weight FLOAT DEFAULT 1.0,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast traversal
CREATE INDEX idx_graph_edges_source ON pms_knowledge_graph_edges(source_entity_type, source_entity_id, edge_type);
CREATE INDEX idx_graph_edges_target ON pms_knowledge_graph_edges(target_entity_type, target_entity_id);

-- Query: Find related entities (2-hop traversal)
WITH first_hop AS (
  SELECT target_entity_type, target_entity_id, edge_type, weight
  FROM pms_knowledge_graph_edges
  WHERE source_entity_type = 'work_order'
    AND source_entity_id = :work_order_id
    AND yacht_id = :yacht_id
),
second_hop AS (
  SELECT e.target_entity_type, e.target_entity_id, e.edge_type, e.weight * fh.weight AS combined_weight
  FROM first_hop fh
  JOIN pms_knowledge_graph_edges e
    ON e.source_entity_type = fh.target_entity_type
    AND e.source_entity_id = fh.target_entity_id
    AND e.yacht_id = :yacht_id
)
SELECT * FROM first_hop
UNION ALL
SELECT * FROM second_hop
ORDER BY combined_weight DESC
LIMIT 100;
```

---

## 🚀 Implementation Roadmap (GraphRAG-Enabled)

### Phase 1 (Week 1): Foundation
- [ ] Add embedding columns to ALL core tables (migrations)
- [ ] Backfill embeddings for existing data (batch script)
- [ ] Create `pms_knowledge_graph_edges` table
- [ ] Populate edges from existing FK relationships (auto-generate)
- [ ] Basic GraphRAG query: 1-hop traversal

### Phase 2 (Week 2): Intelligent Show Related
- [ ] GraphRAG-powered "Show Related" panel
- [ ] Auto-suggest parts based on graph patterns
- [ ] Contextual manual sections (not just FK, but semantic + graph)
- [ ] Similar WO detection (embedding + graph similarity)
- [ ] User expertise detection (who's done this before)

### Phase 3 (Week 3): Conversational Interface
- [ ] Natural language queries: "Show me all bearing work on starboard engine"
- [ ] Context-aware responses (knows what user is working on)
- [ ] Auto-complete WO forms based on graph patterns
- [ ] Predictive: "You'll probably need these 3 parts" (graph + ML)

### Phase 4 (Month 2): Visual GraphRAG
- [ ] Photo embeddings (CLIP)
- [ ] Visual similarity: "Find photos of similar bearing wear"
- [ ] Video analysis: Detect equipment issues from inspection videos
- [ ] Document chunking: Paragraph-level embeddings for manuals

### Phase 5 (Month 3): Predictive Maintenance
- [ ] Pattern detection: "This equipment fails every 6 months"
- [ ] Proactive WO creation: "Schedule bearing replacement in 2 weeks"
- [ ] Cost optimization: "Use part X instead of Y (same function, 40% cheaper)"
- [ ] Supplier intelligence: "This vendor delivers faster for urgent orders"

---

## 💰 Cost Analysis (Best Product)

### Embedding Costs (OpenAI text-embedding-3-small)

**Assumptions (per yacht/month)**:
- 100 work orders × 300 tokens avg = 30,000 tokens
- 50 equipment × 150 tokens avg = 7,500 tokens
- 200 parts × 200 tokens avg = 40,000 tokens (one-time backfill)
- 100 notes × 100 tokens avg = 10,000 tokens
- 20 faults × 200 tokens avg = 4,000 tokens
- 10 documents × 5,000 tokens avg = 50,000 tokens (chunked)

**Monthly Total**: ~142,000 tokens
**Cost**: 142,000 / 1,000,000 × $0.02 = **$0.00284 per yacht/month**

**For 50 yachts**: $0.14/month

**Annual (50 yachts)**: $1.68/year

**Verdict**: ABSURDLY CHEAP. Embed everything.

### Image Embeddings (CLIP or OpenAI vision)

**Assumptions**:
- 200 photos/month × 50 yachts = 10,000 images
- OpenAI CLIP alternative (self-hosted): Free (one-time GPU cost)
- OR OpenAI Vision API: $0.01/image (high quality)

**Cost (self-hosted)**: $0
**Cost (OpenAI Vision)**: $100/month (50 yachts)

**Verdict**: Self-host CLIP for images. Huge savings.

### Graph Storage (PostgreSQL vs Neo4j)

**PostgreSQL** (existing):
- pms_knowledge_graph_edges: ~10 MB per yacht
- 50 yachts: 500 MB
- Supabase storage: Included in plan

**Neo4j Cloud**:
- AuraDB Professional: $65/month (4GB RAM, 32GB storage)
- Can handle 50 yachts easily

**Verdict**: Start with PostgreSQL (free). Migrate to Neo4j if query performance demands (Month 3+).

### Total Cost (Best Product)

| Component | Cost/Month (50 Yachts) | Notes |
|-----------|------------------------|-------|
| Text Embeddings | $0.14 | OpenAI text-embedding-3-small |
| Image Embeddings | $0 | Self-hosted CLIP |
| Graph Storage | $0 | PostgreSQL (included) |
| Backfill (one-time) | $5 | Historical data embeddings |
| **Total Ongoing** | **$0.14/month** | **Negligible!** |

**Per Yacht**: $0.0028/month = **$0.03/year**

**ROI**: If this saves **1 hour of engineer time per year**, it's worth:
- Engineer hourly rate: ~$50/hr (conservative)
- Time saved: 1 hour/year
- Value: $50
- Cost: $0.03
- **ROI: 166,600%**

---

## 🎨 UX Mockups (GraphRAG-Enhanced)

### 1. Intelligent Search Bar

```
┌────────────────────────────────────────────────────────────┐
│ 🔍 What do you need?                                       │
│                                                            │
│ > bearing replacement starboard engine_                   │
│                                                            │
│ 💡 AI Suggestions:                                        │
│ ─────────────────────────────────────────────────────────│
│ 📋 WO-2025-312: Fuel pump bearing replacement (4mo ago)  │
│    Similar issue · Same equipment · Parts in stock       │
│    [View WO] [Show Related]                              │
│                                                            │
│ 🔩 Part BRG-8800: Bearing set (2 in stock, Stores C-14)  │
│    Used in 3 previous bearing jobs                       │
│    [View Part] [Create WO with this part]               │
│                                                            │
│ 📖 Manual Section 4.2.1: Bearing Replacement (pg 87)     │
│    Torque specs: 25 Nm · Tools required: Puller set     │
│    [View PDF] [Download]                                 │
└────────────────────────────────────────────────────────────┘
```

### 2. Work Order with AI Copilot

```
┌────────────────────────────────────────────────────────────┐
│ Create Work Order                          [🤖 AI Helper] │
├────────────────────────────────────────────────────────────┤
│ Title: Investigate starboard engine noise                  │
│                                                            │
│ Equipment: [Starboard Main Engine ▼]                      │
│                                                            │
│ Description:                                               │
│ Grinding noise from fuel pump area, louder under load_    │
│                                                            │
│ 🤖 AI Analysis:                                           │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Based on similar cases (WO-2025-312, F-089):        │ │
│ │                                                      │ │
│ │ Likely Root Cause:                                  │ │
│ │ • Worn fuel pump bearing (80% confidence)          │ │
│ │ • Loose alternator belt (15% confidence)           │ │
│ │                                                      │ │
│ │ Recommended Parts:                                  │ │
│ │ ✓ Bearing set BRG-8800 (In stock: 2)  [Add]       │ │
│ │ ✓ Gasket GSK-1122 (In stock: 5)       [Add]       │ │
│ │ ? Belt BLT-9921 (In stock: 1)         [Add]       │ │
│ │                                                      │ │
│ │ Estimated Duration: 3-4 hours                       │ │
│ │ Suggested Assignee: Engineer Mike (expert)         │ │
│ │                                                      │ │
│ │ [Accept All] [Customize] [Ignore]                  │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                            │
│ [Create Work Order]                                        │
└────────────────────────────────────────────────────────────┘
```

### 3. GraphRAG Show Related Panel

```
┌────────────────────────────────────────────────────────────┐
│ 🕸️ Knowledge Graph: WO-2026-150                            │
│ "Investigate starboard engine noise"                       │
├────────────────────────────────────────────────────────────┤
│ [Graph View] [List View] [Timeline]                        │
│                                                            │
│ ┌──────────────────────────────────────────────────────┐ │
│ │              ┌──→ BRG-8800 (Part)                   │ │
│ │              │    ├─ In stock: 2                     │ │
│ │              │    ├─ Used in WO-2025-312             │ │
│ │              │    └─ Vendor: BearingCo               │ │
│ │              │                                        │ │
│ │  WO-2026-150 ┼──→ Manual Section 4.2.1               │ │
│ │  (Current)   │    └─ Torque: 25 Nm                  │ │
│ │              │                                        │ │
│ │              └──→ WO-2025-312 (Similar, 80%)        │ │
│ │                   ├─ Engineer Mike                   │ │
│ │                   ├─ Duration: 3.5 hrs               │ │
│ │                   └─ Photos (3)                      │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                            │
│ 📊 Connection Strength                                    │
│ ████████░░ 80% - WO-2025-312 (embedding + graph)          │
│ ██████░░░░ 60% - Manual Section 4.2.1 (semantic)          │
│ █████░░░░░ 50% - Part BRG-8800 (usage pattern)            │
│                                                            │
│ [Expand Graph] [Export] [Share]                           │
└────────────────────────────────────────────────────────────┘
```

---

## 🏆 The BEST Product (Final Recommendation)

### What to Embed (Priority Order)

1. **✅ EMBED NOW (Week 1)**:
   - pms_work_orders (all text fields)
   - pms_equipment (all text fields)
   - pms_parts (expand existing embeddings)
   - pms_faults (all text fields)
   - pms_work_order_notes (note_text)

2. **✅ EMBED WEEK 2**:
   - doc_metadata (chunked manual content via OCR)
   - handover_exports (structured text)
   - pms_shopping_list_items (source_notes)

3. **✅ EMBED MONTH 2**:
   - Photos (CLIP image embeddings)
   - User expertise (inferred from WO history)
   - Vendor emails (if integrated)

### GraphRAG Features (Priority Order)

1. **Week 1**: Basic graph (FK relationships as edges)
2. **Week 2**: Semantic similarity edges (embedding distance < 0.3)
3. **Week 3**: Conversational queries ("Show me all...")
4. **Month 2**: Predictive suggestions (parts, duration, assignee)
5. **Month 3**: Visual graph UI + pattern detection

### Cost: ~$0.14/month for 50 yachts (NEGLIGIBLE)

### Impact:
- 10-20% faster work order resolution
- 50% fewer "can't find manual" support tickets
- Crew happiness ↑ (easier to do their jobs)
- Knowledge preserved (tribal knowledge → graph)

**VERDICT**: Embed everything. Build GraphRAG. This is the future.

---

**STATUS**: 🟢 READY TO IMPLEMENT
**NEXT ACTION**: Create migrations for all embedding columns, start with pms_work_orders.
