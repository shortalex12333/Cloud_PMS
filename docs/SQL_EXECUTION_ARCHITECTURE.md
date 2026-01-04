# SQL Execution Architecture
## CelesteOS Search Pipeline - Post-Entity Extraction

---

## 1. Current State Analysis

### Data Flow (from n8n workflow)
```
Webhook → Render Extract → Lane Switch → SQL Execution → Scoring → Stream Response
           ↓
    Entity Extraction Output:
    {
      lane: "NO_LLM" | "RULES_ONLY" | "GPT",
      lane_reason: "...",
      intent: "view_part_location" | "find_part" | ...,
      intent_confidence: 0.88,
      entities: [{
        type: "location" | "equipment" | "part" | "fault_code" | ...,
        value: "box 2d",
        canonical: "BOX_2D",
        weight: 2,              // Term importance (0-5)
        canonical_weight: 1.6   // Adjusted after normalization
      }],
      embedding: null | [768-dim vector],
      metadata: { latency_ms, model, entity_count }
    }
```

### Two Existing SQL Approaches

#### Approach A: Parallel "Copious" SQL (8 parallel queries)
- **Pros**: Fast, all tables searched simultaneously
- **Cons**: No prioritization, high DB load, results arrive together
- **Current Implementation**: SQL_Inventory, SQL_Equipment, SQL_Faults, SQL_WorkOrders, SQL_Documents, SQL_Certificates, SQL_Suppliers, SQL_Voyage

#### Approach B: Loop "Search Postgres" (sequential)
- **Pros**: Results stream chronologically, can early-exit on good matches
- **Cons**: Slower total time, sequential bottleneck
- **Current Implementation**: `Loop Over Tables` → `Search Postgres` → `Aggregate Results`

---

## 2. Variables Available for Routing

### From Entity Extraction
| Variable | Type | Description | Use Case |
|----------|------|-------------|----------|
| `lane` | string | NO_LLM, RULES_ONLY, GPT | Determines processing depth |
| `intent` | string | find_part, troubleshoot, check_stock | Table priority boost |
| `intent_confidence` | float | 0.0-1.0 | Threshold for auto-execute |
| `entities[].type` | string | equipment, part, location, fault_code | Table targeting |
| `entities[].value` | string | Original term | Fuzzy search |
| `entities[].canonical` | string | Normalized form | Exact match boost |
| `entities[].weight` | float | 0-5 | Term importance in query |
| `entities[].canonical_weight` | float | Adjusted weight | Final ranking signal |
| `embedding` | float[] | 768-dim vector | Vector similarity search |

### From User Context (webhook body)
| Variable | Type | Description | Use Case |
|----------|------|-------------|----------|
| `yacht_id` | UUID | Tenant isolation | WHERE clause filter |
| `user_id` | UUID | User identity | Audit logging |
| `role` | string | Engineer, Captain, etc. | Permission scoping |
| `session_id` | UUID | Conversation context | State continuity |
| `stream` | boolean | Enable SSE streaming | Response format |

---

## 3. Table-Entity Mapping

### Primary Table Routing (which tables to search based on entity type)

```
Entity Type         → Primary Tables              → Secondary Tables
─────────────────────────────────────────────────────────────────────
equipment          → pms_equipment               → pms_notes, maintenance_facts
part               → pms_parts                   → pms_inventory_stock, pms_purchase_order_items
location           → pms_inventory_stock         → pms_equipment
fault_code         → pms_faults                  → search_fault_code_catalog, search_symptom_catalog
symptom            → search_symptom_catalog      → search_symptom_reports, pms_faults
document           → doc_yacht_library           → doc_sop_procedures, search_ocred_pages
certificate        → pms_vessel_certificates     → pms_crew_certificates
work_order         → pms_work_orders             → pms_work_order_history
person             → pms_crew_certificates       → pms_suppliers
supplier           → pms_suppliers               → pms_purchase_orders
temporal           → (all tables with timestamps) → work_order_history
```

### Intent-Based Priority Boost

```javascript
const INTENT_TABLE_PRIORITY = {
  // Parts & Inventory
  find_part: ['pms_parts', 'pms_inventory_stock'],
  view_part_location: ['pms_inventory_stock', 'pms_parts'],
  view_part_stock: ['pms_inventory_stock', 'pms_parts'],
  check_stock: ['pms_inventory_stock', 'pms_parts'],

  // Equipment
  view_equipment_details: ['pms_equipment', 'pms_notes'],
  show_equipment_overview: ['pms_equipment', 'search_graph_nodes'],
  show_equipment_history: ['pms_work_order_history', 'pms_equipment'],

  // Faults & Diagnostics
  diagnose_fault: ['search_fault_code_catalog', 'pms_faults', 'search_symptom_catalog'],
  troubleshoot: ['search_fault_code_catalog', 'doc_yacht_library'],
  report_fault: ['pms_faults', 'pms_equipment'],

  // Documents
  find_document: ['doc_yacht_library', 'doc_sop_procedures', 'search_ocred_pages'],
  show_manual_section: ['doc_yacht_library', 'search_ocred_pages'],
  search_documents: ['doc_yacht_library', 'doc_metadata'],

  // Work Orders
  find_work_order: ['pms_work_orders', 'pms_work_order_history'],
  show_work_order: ['pms_work_orders'],

  // Certificates
  find_certificate: ['pms_vessel_certificates', 'pms_crew_certificates'],

  // Suppliers
  find_supplier: ['pms_suppliers', 'pms_purchase_orders'],

  // General
  general_search: ['doc_yacht_library', 'pms_equipment', 'pms_parts', 'pms_work_orders']
};
```

---

## 4. Biased Search Strategy

### Problem Statement
Without bias, we search ALL tables equally → slow, wasteful, poor ranking.

With bias, we use extracted signals to:
1. **Prioritize** tables likely to contain the answer
2. **Skip** tables that are clearly irrelevant
3. **Weight** results from prioritized tables higher

### Bias Score Calculation

```javascript
function calculateTableBias(table, entities, intent, intentConfidence) {
  let bias = 1.0;  // Neutral

  // 1. Intent boost (strongest signal)
  const priorityTables = INTENT_TABLE_PRIORITY[intent] || [];
  if (priorityTables.includes(table)) {
    const rank = priorityTables.indexOf(table);
    bias += (1.0 - rank * 0.2) * intentConfidence;  // 1.0 for first, 0.8 for second, etc.
  }

  // 2. Entity type match
  const entityTypes = entities.map(e => e.type);
  const tableEntityMapping = TABLE_ENTITY_MAP[table] || [];
  const matchingTypes = entityTypes.filter(t => tableEntityMapping.includes(t));
  bias += matchingTypes.length * 0.3;

  // 3. High-weight entity presence
  const highWeightEntities = entities.filter(e => e.weight >= 3);
  if (highWeightEntities.some(e => tableEntityMapping.includes(e.type))) {
    bias += 0.5;
  }

  // 4. Canonical match indicator
  const hasCanonical = entities.some(e => e.canonical && tableEntityMapping.includes(e.type));
  if (hasCanonical) {
    bias += 0.3;  // More confident match
  }

  return Math.min(3.0, bias);  // Cap at 3x
}
```

### Execution Strategy by Bias Score

| Bias Score | Strategy | Tables |
|------------|----------|--------|
| >= 2.0 | **MUST SEARCH** | Run first, in parallel |
| 1.5 - 2.0 | **SHOULD SEARCH** | Run in second wave |
| 1.0 - 1.5 | **MAY SEARCH** | Run if first waves empty |
| < 1.0 | **SKIP** | Don't search unless desperate |

---

## 5. Search Type Selection

### Based on Query Characteristics

```javascript
function selectSearchTypes(query, entities, embedding) {
  const types = [];

  // 1. Exact match (fastest)
  const hasExactCode = entities.some(e =>
    ['fault_code', 'work_order_id', 'part_number'].includes(e.type)
  );
  if (hasExactCode) types.push('EXACT');

  // 2. Canonical lookup
  const hasCanonical = entities.some(e => e.canonical);
  if (hasCanonical) types.push('CANONICAL');

  // 3. Full-text (ILIKE)
  if (query.length >= 3) types.push('FUZZY');

  // 4. Vector similarity (requires embedding)
  if (embedding && embedding.length === 768) types.push('VECTOR');

  // Priority: EXACT > CANONICAL > VECTOR > FUZZY
  return types;
}
```

### SQL Patterns by Search Type

```sql
-- EXACT: Direct ID lookup
WHERE fault_code = $1 OR part_number = $1

-- CANONICAL: Normalized match with original fallback
WHERE canonical_label = $1 OR label ILIKE '%' || $2 || '%'

-- FUZZY: ILIKE with wildcard
WHERE name ILIKE '%' || $1 || '%'
   OR description ILIKE '%' || $1 || '%'

-- VECTOR: pgvector similarity
ORDER BY embedding <=> $1::vector
LIMIT 20
```

---

## 6. Scoring Fusion Engine

### Multi-Signal Scoring Model

```javascript
const SIGNAL_WEIGHTS = {
  S_exact_match: 0.30,      // Exact code/ID match
  S_canonical_match: 0.20,  // Canonical form match
  S_fuzzy_match: 0.15,      // Substring/ILIKE match
  S_vector_similarity: 0.10,// Embedding cosine similarity
  S_entity_weight: 0.10,    // Original entity weight
  S_table_bias: 0.10,       // Table priority from routing
  S_recency: 0.05           // Recent data preference
};

function calculateFusionScore(result, queryContext) {
  const signals = {};

  // Exact match
  signals.S_exact_match = result.matched_column_type === 'exact' ? 1.0 :
                          result.matched_column_type === 'code' ? 0.9 : 0;

  // Canonical match
  signals.S_canonical_match = queryContext.entities.some(e =>
    e.canonical && result.canonical_label === e.canonical
  ) ? 1.0 : 0;

  // Fuzzy match quality
  const fuzzyScore = result.keyword_confidence || 0;
  signals.S_fuzzy_match = fuzzyScore;

  // Vector similarity (if available)
  signals.S_vector_similarity = result.vector_score || 0;

  // Entity weight contribution
  const matchedEntity = queryContext.entities.find(e =>
    result.content?.toLowerCase().includes(e.value.toLowerCase())
  );
  signals.S_entity_weight = matchedEntity ?
    Math.min(1.0, matchedEntity.canonical_weight / 3) : 0;

  // Table bias
  signals.S_table_bias = Math.min(1.0, (result._table_bias || 1.0) / 3);

  // Recency
  const ageDays = result.created_at ?
    (Date.now() - new Date(result.created_at)) / (1000*60*60*24) : 365;
  signals.S_recency = Math.max(0, 1 - ageDays/365);

  // Weighted sum
  let score = 0;
  for (const [signal, weight] of Object.entries(SIGNAL_WEIGHTS)) {
    score += weight * (signals[signal] || 0);
  }

  return { score, signals };
}
```

---

## 7. Recommended Architecture

### Hybrid Approach: Biased Parallel with Streaming

```
                    ┌─────────────────────────────────────────┐
                    │           Entity Extraction              │
                    │  {lane, intent, entities[], embedding}   │
                    └───────────────────┬─────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────┐
                    │         Calculate Table Biases           │
                    │   For each table: bias = f(intent,       │
                    │   entities, weights, canonical)          │
                    └───────────────────┬─────────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
    ┌───────▼───────┐          ┌────────▼────────┐         ┌────────▼────────┐
    │ WAVE 1: HIGH  │          │ WAVE 2: MEDIUM  │         │ WAVE 3: LOW     │
    │ bias >= 2.0   │          │ bias 1.5-2.0    │         │ bias 1.0-1.5    │
    │ (parallel)    │          │ (if needed)     │         │ (if desperate)  │
    └───────┬───────┘          └────────┬────────┘         └────────┬────────┘
            │                           │                           │
            └───────────────────────────┼───────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────┐
                    │          Fusion Scoring Engine           │
                    │   Combine: exact + canonical + fuzzy +   │
                    │   vector + entity_weight + bias + recency│
                    └───────────────────┬─────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────┐
                    │           Stream to Client               │
                    │   Results arrive as each wave completes  │
                    │   (chronological UX benefit)             │
                    └─────────────────────────────────────────┘
```

### n8n Implementation Strategy

1. **Wave Execution** via Split-In-Batches by bias tier
2. **Early Exit** if Wave 1 returns high-confidence results
3. **Progressive Streaming** send results as each wave completes
4. **Fallback** to full parallel if no high-bias tables identified

---

## 8. Table Schema Reference

### Primary Search Tables

| Table | Columns for Search | Entity Types | Notes |
|-------|-------------------|--------------|-------|
| `pms_parts` | name, part_number, manufacturer, description, category | part | Core parts catalog |
| `pms_inventory_stock` | location, quantity | location, part | Stock levels |
| `pms_equipment` | name, code, manufacturer, model, serial_number, location | equipment | Equipment registry |
| `pms_faults` | fault_code, title, description | fault_code, equipment | Active/historical faults |
| `pms_work_orders` | title, description, type, status | work_order, equipment | Maintenance tasks |
| `doc_yacht_library` | document_name, chunk_text, equipment_covered | document, equipment | Document search |
| `search_fault_code_catalog` | code, name, description, symptoms, causes | fault_code, symptom | Diagnostic reference |
| `search_symptom_catalog` | code, label, description | symptom | Symptom patterns |
| `pms_vessel_certificates` | certificate_name, certificate_type, certificate_number | certificate | Vessel certs |
| `pms_suppliers` | name, contact_name, email, phone | supplier | Vendor contacts |

---

## 9. Implementation Checklist

### Phase 1: Table Routing (Day 1-2)
- [ ] Create `calculateTableBias()` function
- [ ] Build `TABLE_ENTITY_MAP` constant
- [ ] Implement `INTENT_TABLE_PRIORITY` lookup
- [ ] Test bias calculation with sample queries

### Phase 2: Wave Execution (Day 2-3)
- [ ] Modify n8n to split tables by bias tier
- [ ] Implement Wave 1 parallel execution
- [ ] Add early-exit logic on high-confidence results
- [ ] Add Wave 2/3 conditional execution

### Phase 3: Scoring Fusion (Day 3-4)
- [ ] Implement multi-signal scoring
- [ ] Add entity weight contribution
- [ ] Add canonical match bonus
- [ ] Tune signal weights empirically

### Phase 4: Streaming (Day 4-5)
- [ ] Modify response format for incremental results
- [ ] Implement SSE streaming in n8n webhook response
- [ ] Test with real frontend

### Phase 5: Testing & Tuning (Day 5-6)
- [ ] Run against 600-query stress test
- [ ] Measure latency improvements
- [ ] Tune bias thresholds
- [ ] Document final configuration

---

*Version: 1.0*
*Last Updated: 2025-12-26*
*Owner: Engineering*
