# GraphRAG Query Patterns for CelesteOS

This document defines the query patterns used by the Search Engine Brain (Worker 6) to transform user natural language queries into actionable GraphRAG queries.

---

## API Architecture

**GraphRAG is an internal engine, NOT a public API surface.**

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                  │
│                                                                   │
│   Search Bar ──────────────► POST /v1/search                     │
│   Action Buttons ──────────► POST /v1/actions/execute            │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    microaction_service.py                         │
│                                                                   │
│   POST /v1/search ─────► graphrag_query.query() ─────► Cards     │
│                                     │                             │
│                                     ▼                             │
│                         - Entity Resolution                       │
│                         - Intent Detection                        │
│                         - Graph Traversal                         │
│                         - Card Building                          │
│                         - Action Attachment                      │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                          RESPONSE                                 │
│                                                                   │
│   {                                                              │
│     "query": "...",                                              │
│     "intent": "diagnose_fault",                                  │
│     "entities": [...],                                           │
│     "cards": [                                                   │
│       {                                                          │
│         "type": "fault",                                         │
│         "title": "Fault E047",                                   │
│         "actions": [                                             │
│           {                                                      │
│             "label": "Create Work Order",                        │
│             "action": "create_work_order",                       │
│             "endpoint": "/v1/work-orders/create",               │
│             "method": "POST",                                    │
│             "payload_template": {...}                            │
│           }                                                      │
│         ]                                                        │
│       }                                                          │
│     ]                                                            │
│   }                                                              │
└──────────────────────────────────────────────────────────────────┘
```

### Public Endpoints (Frontend Use)

| Endpoint | Purpose | Spec |
|----------|---------|------|
| `POST /v1/search` | Unified search bar | search-engine-spec.md |
| `POST /v1/actions/execute` | All mutations | action-endpoint-contract.md |

### Internal Endpoints (n8n/Admin Only)

| Endpoint | Purpose |
|----------|---------|
| `POST /graphrag/populate` | n8n workflow: populate graph from GPT extraction |
| `POST /graphrag/query` | Internal: DO NOT call directly, use /v1/search |
| `GET /graphrag/stats` | Admin: graph statistics |

### Key Files

- `api/graphrag_query.py` - Internal GraphRAG query service
- `api/graphrag_population.py` - Graph population from n8n
- `api/microaction_service.py` - Public API layer
- `micro-action-catalogue.md` - Action definitions
- `search-engine-spec.md` - Card types (Section 8)
- `action-endpoint-contract.md` - Mutation routing

---

## Query Intent Classification

The system classifies user queries into intent categories, each with specific query patterns:

| Intent | Example Query | Primary Tables | Micro-Action |
|--------|---------------|----------------|--------------|
| `document_navigation` | "Open Cat main engine manual to lube oil section" | document_chunks, entity_aliases | `open_document` |
| `symptom_diagnosis` | "Engine is overheating, show historic data" | symptom_catalog, graph_edges, work_orders | `show_history`, `create_work_order` |
| `relationship_traversal` | "What parts are affected if heat exchanger fails?" | graph_edges, parts, equipment | `show_parts`, `create_work_order` |
| `maintenance_lookup` | "When is oil change due on generator 1?" | maintenance_templates, equipment | `show_maintenance`, `create_work_order` |
| `fault_diagnosis` | "What does error code E047 mean?" | faults, entity_aliases | `show_fault_info` |
| `part_search` | "Find filter for port main engine" | parts, graph_edges, suppliers | `show_parts`, `order_part` |

---

## 1. Document Navigation Pattern

**User Query**: "Open Cat main engine manual to lube oil section"

### Step 1: Entity Resolution
```sql
-- Resolve "Cat main engine" → canonical equipment_id
SELECT canonical_id
FROM entity_aliases
WHERE yacht_id = $yacht_id
  AND entity_type = 'equipment'
  AND alias_text_lower ILIKE '%cat%main%engine%'
ORDER BY confidence DESC
LIMIT 1;
```

### Step 2: Find Related Documents
```sql
-- Find document chunks mentioning this equipment + "lube oil"
SELECT
    dc.id AS chunk_id,
    dc.document_id,
    dc.section_title,
    dc.page_number,
    dc.section_path,
    d.title AS document_title,
    d.file_path
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
JOIN graph_nodes gn ON gn.ref_id = dc.id
WHERE dc.yacht_id = $yacht_id
  AND gn.canonical_id = $equipment_id
  AND (
      dc.content ILIKE '%lube%oil%'
      OR dc.section_title ILIKE '%lube%oil%'
      OR 'lube oil' = ANY(dc.section_path)
  )
ORDER BY
    -- Prefer exact section title matches
    CASE WHEN dc.section_title ILIKE '%lube%oil%' THEN 0 ELSE 1 END,
    dc.page_number
LIMIT 5;
```

### Step 3: Generate Micro-Action
```json
{
  "action": "open_document",
  "confidence": 0.92,
  "parameters": {
    "document_id": "uuid-here",
    "page_number": 47,
    "section_title": "Lubrication Oil System",
    "highlight_text": "lube oil"
  },
  "context": {
    "equipment": "Cat Main Engine",
    "document": "Caterpillar 3512 Service Manual"
  }
}
```

---

## 2. Symptom Diagnosis Pattern

**User Query**: "Engine is overheating, show historic data from 2nd engineer"

### Step 1: Symptom Resolution
```sql
-- Resolve "overheating" → symptom code
SELECT symptom_code, canonical_name
FROM symptom_aliases sa
JOIN symptom_catalog sc ON sa.symptom_code = sc.symptom_code
WHERE sa.alias_text_lower = 'overheating'
   OR sa.alias_text_lower ILIKE '%overheat%';
-- Returns: OVERHEAT
```

### Step 2: Entity Resolution + Equipment Discovery
```sql
-- Find all engines for this yacht
SELECT e.id, e.canonical_name, e.display_name
FROM equipment e
WHERE e.yacht_id = $yacht_id
  AND e.system_type = 'PROPULSION'
  AND (e.canonical_name ILIKE '%engine%' OR e.display_name ILIKE '%engine%');
```

### Step 3: Find Historic Graph Edges (symptom → equipment → work_orders)
```sql
-- Find past occurrences of this symptom on these engines
SELECT
    ge.created_at,
    gn_from.label AS symptom_mention,
    gn_to.label AS equipment_mention,
    ge.source_chunk_id,
    dc.content AS context,
    wo.id AS work_order_id,
    wo.description AS work_order_description,
    wo.created_by AS engineer
FROM graph_edges ge
JOIN graph_nodes gn_from ON ge.from_node_id = gn_from.id
JOIN graph_nodes gn_to ON ge.to_node_id = gn_to.id
LEFT JOIN document_chunks dc ON ge.source_chunk_id = dc.id
LEFT JOIN work_orders wo ON gn_to.ref_table = 'work_orders' AND gn_to.ref_id = wo.id
WHERE ge.yacht_id = $yacht_id
  AND ge.edge_type = 'HAS_SYMPTOM'
  AND gn_from.label ILIKE '%engine%'
  AND (
      gn_to.label ILIKE '%overheat%'
      OR gn_to.label ILIKE '%temperature%'
      OR gn_to.canonical_id IN (SELECT id FROM symptom_catalog WHERE symptom_code = 'OVERHEAT')
  )
ORDER BY ge.created_at DESC;
```

### Step 4: Filter by Person (2nd engineer)
```sql
-- Filter work orders/handovers by 2nd engineer
SELECT wo.*
FROM work_orders wo
WHERE wo.yacht_id = $yacht_id
  AND wo.created_by ILIKE '%2nd%engineer%'
  AND wo.id = ANY($work_order_ids_from_step_3);

-- Also check handover items
SELECT hi.*
FROM handover_items hi
WHERE hi.yacht_id = $yacht_id
  AND hi.author ILIKE '%2nd%engineer%'
  AND hi.content ILIKE '%overheat%';
```

### Step 5: Generate Multi-Action Response
```json
{
  "actions": [
    {
      "action": "show_history",
      "confidence": 0.88,
      "parameters": {
        "symptom": "OVERHEAT",
        "equipment_ids": ["uuid1", "uuid2"],
        "filter_by_person": "2nd Engineer",
        "results": [
          {
            "date": "2024-08-15",
            "work_order_id": "uuid",
            "description": "Port ME high temp alarm at 1450 RPM",
            "resolution": "Cleaned heat exchanger, replaced zinc anodes"
          }
        ]
      }
    },
    {
      "action": "create_work_order",
      "confidence": 0.75,
      "requires_confirmation": true,
      "parameters": {
        "equipment_id": "uuid",
        "symptom_code": "OVERHEAT",
        "suggested_title": "Engine Overheating Investigation"
      }
    }
  ]
}
```

---

## 3. Relationship Traversal Pattern

**User Query**: "What parts are affected if the heat exchanger fails?"

### Step 1: Entity Resolution
```sql
-- Resolve "heat exchanger" → equipment
SELECT id, canonical_name, display_name
FROM equipment
WHERE yacht_id = $yacht_id
  AND (canonical_name ILIKE '%heat%exchanger%' OR display_name ILIKE '%heat%exchanger%')

UNION

SELECT canonical_id, null, alias_text
FROM entity_aliases
WHERE yacht_id = $yacht_id
  AND entity_type = 'equipment'
  AND alias_text_lower ILIKE '%heat%exchanger%';
```

### Step 2: Traverse Graph for USES_PART Relationships
```sql
-- Direct parts used by heat exchanger
SELECT
    p.id,
    p.canonical_name,
    p.display_name,
    p.part_number,
    p.manufacturer,
    ge.confidence,
    'direct' AS relationship_level
FROM graph_edges ge
JOIN parts p ON ge.to_canonical_id = p.id
WHERE ge.yacht_id = $yacht_id
  AND ge.from_canonical_id = $heat_exchanger_id
  AND ge.edge_type = 'USES_PART';
```

### Step 3: Traverse for PART_OF (Parent Equipment) Impact
```sql
-- What equipment depends on heat exchanger?
SELECT
    e.id,
    e.canonical_name,
    e.display_name,
    'parent' AS relationship_type
FROM graph_edges ge
JOIN equipment e ON ge.from_canonical_id = e.id
WHERE ge.yacht_id = $yacht_id
  AND ge.to_canonical_id = $heat_exchanger_id
  AND ge.edge_type = 'PART_OF';
-- Example: Main Engine → uses → Heat Exchanger
-- So Main Engine is affected if heat exchanger fails
```

### Step 4: Get Parts for Affected Parent Equipment
```sql
-- Parts for parent equipment that may need attention
WITH affected_equipment AS (
    SELECT from_canonical_id AS equipment_id
    FROM graph_edges
    WHERE yacht_id = $yacht_id
      AND to_canonical_id = $heat_exchanger_id
      AND edge_type IN ('PART_OF', 'USES_PART', 'REQUIRES_TOOL')
)
SELECT
    p.id,
    p.canonical_name,
    p.part_number,
    p.manufacturer,
    e.display_name AS parent_equipment,
    'cascading' AS relationship_level
FROM graph_edges ge
JOIN parts p ON ge.to_canonical_id = p.id
JOIN equipment e ON ge.from_canonical_id = e.id
WHERE ge.from_canonical_id IN (SELECT equipment_id FROM affected_equipment)
  AND ge.edge_type = 'USES_PART';
```

### Step 5: Generate Response
```json
{
  "action": "show_parts",
  "confidence": 0.91,
  "parameters": {
    "query_equipment": "Heat Exchanger",
    "direct_parts": [
      {"name": "Zinc Anode Kit", "part_number": "ZA-3512-001", "relationship": "direct"},
      {"name": "O-Ring Seal Kit", "part_number": "OR-HEX-002", "relationship": "direct"},
      {"name": "Tube Bundle", "part_number": "TB-HEX-003", "relationship": "direct"}
    ],
    "affected_equipment": [
      {"name": "Port Main Engine", "impact": "Cooling system failure"},
      {"name": "Starboard Main Engine", "impact": "Cooling system failure"}
    ],
    "cascading_parts": [
      {"name": "Coolant Filter", "equipment": "Port Main Engine", "part_number": "CF-3512-001"}
    ]
  },
  "suggested_actions": [
    {
      "action": "create_work_order",
      "confidence": 0.65,
      "requires_confirmation": true,
      "parameters": {
        "title": "Heat Exchanger Inspection",
        "parts_to_check": ["ZA-3512-001", "OR-HEX-002"]
      }
    }
  ]
}
```

---

## 4. Maintenance Lookup Pattern

**User Query**: "When is oil change due on generator 1?"

### Step 1: Entity Resolution
```sql
SELECT canonical_id
FROM entity_aliases
WHERE yacht_id = $yacht_id
  AND entity_type = 'equipment'
  AND alias_text_lower IN ('generator 1', 'gen 1', 'g1', 'generator 1')
ORDER BY confidence DESC
LIMIT 1;
```

### Step 2: Get Maintenance Templates
```sql
SELECT
    mt.id,
    mt.interval_hours,
    mt.interval_days,
    mt.interval_description,
    mt.action,
    mt.action_description,
    mt.tools_required,
    mt.estimated_duration_hours,
    p.canonical_name AS part_name,
    p.part_number
FROM maintenance_templates mt
LEFT JOIN parts p ON mt.part_id = p.id
WHERE mt.yacht_id = $yacht_id
  AND mt.equipment_id = $generator_1_id
  AND (
      mt.action = 'replace'
      OR mt.action_description ILIKE '%oil%change%'
      OR p.canonical_name ILIKE '%oil%filter%'
      OR p.canonical_name ILIKE '%lube%oil%'
  );
```

### Step 3: Get Current Running Hours (from external system)
```sql
-- This would integrate with equipment monitoring
-- For now, assume API call to get current_hours
SELECT running_hours
FROM equipment_telemetry
WHERE equipment_id = $generator_1_id
ORDER BY timestamp DESC
LIMIT 1;
```

### Step 4: Calculate Next Due
```json
{
  "action": "show_maintenance",
  "confidence": 0.94,
  "parameters": {
    "equipment": "Generator 1",
    "maintenance_item": "Engine Oil Change",
    "interval": "500 hours",
    "current_hours": 12847,
    "last_service_hours": 12500,
    "next_due_hours": 13000,
    "hours_remaining": 153,
    "parts_required": [
      {"name": "Lube Oil Filter", "part_number": "1R-0750"},
      {"name": "Engine Oil 15W-40", "quantity": "32 liters"}
    ],
    "estimated_time": "2 hours"
  },
  "suggested_actions": [
    {
      "action": "create_work_order",
      "confidence": 0.70,
      "requires_confirmation": true,
      "parameters": {
        "title": "Generator 1 - Oil Change (Due at 13000 hrs)",
        "equipment_id": "uuid"
      }
    }
  ]
}
```

---

## 5. Fault Diagnosis Pattern

**User Query**: "What does error code E047 mean?"

### Step 1: Fault Code Lookup
```sql
SELECT
    f.fault_code,
    f.canonical_name,
    f.severity,
    f.category,
    f.description,
    f.resolution_steps
FROM faults f
WHERE f.yacht_id = $yacht_id
  AND f.fault_code = 'E047';
```

### Step 2: Find Related Documentation
```sql
SELECT
    dc.id,
    dc.content,
    dc.section_title,
    dc.page_number,
    d.title AS document_title
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE dc.yacht_id = $yacht_id
  AND dc.content ILIKE '%E047%'
ORDER BY
    CASE WHEN dc.section_title ILIKE '%error%code%' THEN 0
         WHEN dc.section_title ILIKE '%troubleshoot%' THEN 1
         WHEN dc.section_title ILIKE '%fault%' THEN 2
         ELSE 3 END
LIMIT 5;
```

### Step 3: Get Historic Occurrences
```sql
SELECT
    wo.id,
    wo.created_at,
    wo.description,
    wo.resolution
FROM work_orders wo
WHERE wo.yacht_id = $yacht_id
  AND (wo.description ILIKE '%E047%' OR wo.fault_code = 'E047')
ORDER BY wo.created_at DESC
LIMIT 5;
```

---

## SQL Helper Views

### View: Equipment with All Aliases
```sql
CREATE OR REPLACE VIEW v_equipment_aliases AS
SELECT
    e.id,
    e.yacht_id,
    e.canonical_name,
    e.display_name,
    e.oem,
    e.model,
    e.system_type,
    array_agg(DISTINCT ea.alias_text) AS aliases
FROM equipment e
LEFT JOIN entity_aliases ea ON ea.canonical_id = e.id AND ea.entity_type = 'equipment'
GROUP BY e.id;
```

### View: Symptom Quick Lookup
```sql
CREATE OR REPLACE VIEW v_symptom_lookup AS
SELECT
    sc.symptom_code,
    sc.canonical_name,
    sc.category,
    array_agg(DISTINCT sa.alias_text) AS aliases
FROM symptom_catalog sc
LEFT JOIN symptom_aliases sa ON sa.symptom_code = sc.symptom_code
GROUP BY sc.symptom_code, sc.canonical_name, sc.category;
```

---

## Confidence Scoring

Each query pattern uses confidence scoring based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Alias Match Quality | 30% | Exact match = 1.0, Partial = 0.7, Fuzzy = 0.4 |
| Graph Edge Confidence | 25% | Stored confidence from extraction |
| Document Source | 20% | OEM manual = 1.0, Service log = 0.8, Handover = 0.6 |
| Recency | 15% | More recent = higher confidence |
| Context Match | 10% | Query context matches document context |

### Minimum Thresholds
- `open_document`: 0.60 (lower risk, reversible)
- `show_history`: 0.50 (informational only)
- `create_work_order`: 0.80 (requires confirmation)
- `order_part`: 0.90 (financial impact)

---

## Implementation Notes

1. **Always resolve aliases first** - Never use raw user text directly in graph queries
2. **Yacht isolation is mandatory** - Every query MUST include `WHERE yacht_id = $yacht_id`
3. **Multiple actions are common** - Most queries return informational action + suggested mutation
4. **Mutations require confirmation** - Set `requires_confirmation: true` for any data changes
5. **Context preservation** - Include source chunk IDs for audit trail
