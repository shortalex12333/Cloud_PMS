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

## GOLD STANDARD: End-to-End Worked Example

**Query**: "Engine is overheating, show historic data from the 2nd engineer"

This is the reference implementation for the `equipment_history` intent with person filtering.

---

### Step 1: Request Body

```http
POST /v1/search HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Yacht-Signature: sha256(yacht_id + salt)
Content-Type: application/json

{
  "query": "Engine is overheating, show historic data from the 2nd engineer"
}
```

**yacht_id** is extracted from the JWT payload (`payload.yacht_id`).

---

### Step 2: Intent Classification & Entity Extraction

The pipeline runs three modules:

#### Module A: Action Detection
```python
# Pattern matched: r"show\s+(historic|history|historical)\s+(data|records?)"
# Confidence: 0.90
{
    "action": "view_history",
    "confidence": 0.90,
    "verb": "show",
    "matched_text": "show historic data"
}
```

#### Module B: Entity Extraction
```python
# Entities extracted:
[
    {"type": "equipment", "value": "Engine", "canonical": "MAIN_ENGINE", "confidence": 0.92},
    {"type": "maritime_term", "value": "overheating", "canonical": "TEMPERATURE_HIGH", "confidence": 0.80},
    {"type": "person", "value": "2nd engineer", "canonical": "2ND_ENGINEER", "confidence": 0.85}
]
```

#### Module C: Canonicalization
```python
# Canonical mappings:
{
    "MAIN_ENGINE": "equipment",      # Resolved via resolve_entity_alias()
    "TEMPERATURE_HIGH": "symptom",   # Resolved via resolve_symptom_alias()
    "2ND_ENGINEER": "person"         # Used for filtering
}
```

#### Intent Determination
```python
# microactions[0].action = "view_history" → intent_map["view_history"] = EQUIPMENT_HISTORY
intent = QueryIntent.EQUIPMENT_HISTORY
```

---

### Step 3: Entity Resolution (Database Calls)

```sql
-- 1. Resolve equipment alias → canonical_id
SELECT resolve_entity_alias(
    p_yacht_id := 'yacht-uuid-123',
    p_entity_type := 'equipment',
    p_alias_text := 'MAIN_ENGINE'
);
-- Returns: 'equipment-uuid-456'

-- 2. Resolve symptom alias → symptom_code
SELECT resolve_symptom_alias(
    p_alias_text := 'overheating'
);
-- Returns: 'OVERHEAT'
```

---

### Step 4: Query Execution (SQL)

#### Query 4.1: Work Orders (filtered by person + symptom)
```sql
SELECT
    wo.id, wo.title, wo.description, wo.status,
    wo.created_by, wo.created_at, wo.resolution, wo.equipment_id
FROM work_orders wo
WHERE wo.yacht_id = 'yacht-uuid-123'
  AND wo.equipment_id = 'equipment-uuid-456'
  AND wo.created_by ILIKE '%2nd engineer%'
  AND wo.description ILIKE '%overheating%'
ORDER BY wo.created_at DESC
LIMIT 10;
```

#### Query 4.2: Handover Items (filtered by person + symptom)
```sql
SELECT
    hi.id, hi.summary, hi.content, hi.author, hi.created_at, hi.equipment_id
FROM handover_items hi
WHERE hi.yacht_id = 'yacht-uuid-123'
  AND hi.equipment_id = 'equipment-uuid-456'
  AND hi.author ILIKE '%2nd engineer%'
  AND hi.content ILIKE '%overheating%'
ORDER BY hi.created_at DESC
LIMIT 5;
```

#### Query 4.3: Related Documents (symptom mentions)
```sql
SELECT DISTINCT
    dc.id, dc.document_id, dc.content, dc.section_title,
    dc.page_number, dc.storage_path
FROM document_chunks dc
WHERE dc.yacht_id = 'yacht-uuid-123'
  AND dc.content ILIKE '%overheating%'
ORDER BY dc.created_at DESC
LIMIT 5;
```

#### Query 4.4: Graph Traversal (equipment → symptom edges)
```sql
-- Find historic symptom occurrences via graph
SELECT
    ge.created_at,
    gn_from.label AS equipment_label,
    gn_to.label AS symptom_label,
    ge.source_chunk_id,
    ge.confidence
FROM graph_edges ge
JOIN graph_nodes gn_from ON ge.from_node_id = gn_from.id
JOIN graph_nodes gn_to ON ge.to_node_id = gn_to.id
WHERE ge.yacht_id = 'yacht-uuid-123'
  AND ge.edge_type = 'HAS_SYMPTOM'
  AND gn_from.canonical_id = 'equipment-uuid-456'
  AND (gn_to.label ILIKE '%overheat%' OR gn_to.canonical_id = 'OVERHEAT')
ORDER BY ge.created_at DESC
LIMIT 10;
```

---

### Step 5: Final JSON Response

```json
{
  "query": "Engine is overheating, show historic data from the 2nd engineer",
  "intent": "equipment_history",
  "entities": [
    {
      "text": "Engine",
      "type": "equipment",
      "canonical": "MAIN_ENGINE",
      "canonical_id": "equipment-uuid-456"
    },
    {
      "text": "overheating",
      "type": "maritime_term",
      "canonical": "TEMPERATURE_HIGH",
      "canonical_id": "OVERHEAT",
      "symptom_code": "OVERHEAT"
    },
    {
      "text": "2nd engineer",
      "type": "person",
      "canonical": "2ND_ENGINEER",
      "canonical_id": null
    }
  ],
  "cards": [
    {
      "type": "equipment",
      "title": "Engine",
      "equipment_id": "equipment-uuid-456",
      "symptom_detected": "overheating",
      "symptom_code": "OVERHEAT",
      "person_filter": "2ND_ENGINEER",
      "actions": [
        {
          "label": "View History",
          "action": "view_history",
          "endpoint": "/v1/work-orders/history",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456"
          },
          "constraints": {}
        },
        {
          "label": "Create Work Order",
          "action": "create_work_order",
          "endpoint": "/v1/work-orders/create",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456",
            "title": "",
            "description": "",
            "priority": ""
          },
          "constraints": {"requires_equipment_id": true}
        },
        {
          "label": "Add Note",
          "action": "add_note",
          "endpoint": "/v1/notes/create",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456",
            "note_text": ""
          },
          "constraints": {"requires_equipment_id": true, "requires_note_text": true}
        },
        {
          "label": "Add to Handover",
          "action": "add_to_handover",
          "endpoint": "/v1/handover/add-item",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456",
            "summary_text": ""
          },
          "constraints": {}
        }
      ]
    },
    {
      "type": "work_order",
      "title": "Port ME High Temp Alarm Investigation",
      "work_order_id": "wo-uuid-789",
      "status": "completed",
      "equipment_id": "equipment-uuid-456",
      "created_by": "2nd Engineer - John Smith",
      "created_at": "2024-08-15T10:30:00Z",
      "resolution": "Cleaned heat exchanger, replaced zinc anodes",
      "actions": [
        {
          "label": "View History",
          "action": "view_history",
          "endpoint": "/v1/work-orders/history",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456"
          },
          "constraints": {}
        },
        {
          "label": "Add to Handover",
          "action": "add_to_handover",
          "endpoint": "/v1/handover/add-item",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-456",
            "summary_text": ""
          },
          "constraints": {}
        }
      ]
    },
    {
      "type": "handover",
      "title": "Engine temp issue - ongoing",
      "handover_id": "hi-uuid-101",
      "author": "2nd Engineer - John Smith",
      "content": "ME overheating at 1450 RPM noted. Scheduled heat exchanger inspection...",
      "created_at": "2024-08-14T18:00:00Z",
      "actions": [
        {
          "label": "Add to Handover",
          "action": "add_to_handover",
          "endpoint": "/v1/handover/add-item",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "",
            "summary_text": ""
          },
          "constraints": {}
        }
      ]
    },
    {
      "type": "document_chunk",
      "title": "Troubleshooting - High Temperature Alarms",
      "document_id": "doc-uuid-202",
      "page_number": 147,
      "text_preview": "If engine temperature exceeds 95°C at normal RPM, check: 1) Coolant level 2) Heat exchanger fouling 3) Thermostat operation...",
      "storage_path": "/manuals/caterpillar-3512/troubleshooting.pdf",
      "actions": [
        {
          "label": "Open Document",
          "action": "open_document",
          "endpoint": "/v1/documents/open",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "storage_path": "/manuals/caterpillar-3512/troubleshooting.pdf"
          },
          "constraints": {}
        },
        {
          "label": "Add to Handover",
          "action": "add_document_to_handover",
          "endpoint": "/v1/handover/add-document",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "document_id": "doc-uuid-202",
            "context": ""
          },
          "constraints": {}
        }
      ]
    }
  ],
  "metadata": {
    "entity_count": 3,
    "card_count": 4
  }
}
```

---

### Step 6: Frontend Action Execution

When user clicks "Create Work Order" on the equipment card:

```http
POST /v1/actions/execute HTTP/1.1
Host: api.celeste7.ai
Authorization: Bearer <jwt>
X-Yacht-Signature: <signature>
Content-Type: application/json

{
  "action": "create_work_order",
  "payload": {
    "yacht_id": "yacht-uuid-123",
    "equipment_id": "equipment-uuid-456",
    "title": "Engine Overheating Investigation",
    "description": "Engine is overheating, show historic data from the 2nd engineer",
    "priority": "high"
  }
}
```

**All mutations flow through `/v1/actions/execute`** - the frontend NEVER calls individual endpoints directly.

---

### Confidence Thresholds Applied

| Stage | Threshold | Applied |
|-------|-----------|---------|
| Action detection | min_confidence >= 0.4 | `view_history` @ 0.90 ✓ |
| Entity extraction | N/A (all extracted) | 3 entities returned |
| Entity resolution | N/A (best match) | 2/3 resolved to canonical_id |
| Card generation | N/A (all shown) | 4 cards returned |

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

## Resolution & Ranking Pipeline

The `/v1/search` endpoint uses a **4-step priority pipeline** for entity resolution and a **weighted scoring formula** for result ranking.

### 4-Step Entity Resolution

Entities from user queries are resolved in priority order. Once resolved at any step, later steps are skipped.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RESOLUTION PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Query: "Engine is overheating"                                    │
│                      │                                                   │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────┐                         │
│  │ STEP 1: Regex/Canonical Rules (Weight: 0.40)│                        │
│  │ Module B pattern: "engine" → MAIN_ENGINE    │                        │
│  │ Confidence: 0.92 (from pattern match)       │                        │
│  └────────────────────────────────────────────┘                         │
│                      │                                                   │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────┐                         │
│  │ STEP 2: DB Alias Lookup (Weight: 0.30)      │                        │
│  │ SELECT resolve_entity_alias(                │                        │
│  │   'yacht-uuid', 'equipment', 'MAIN_ENGINE') │                        │
│  │ → Returns: 'equipment-uuid-456'             │                        │
│  │ Confidence: 0.90 (DB match found)           │                        │
│  └────────────────────────────────────────────┘                         │
│                      │                                                   │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────┐                         │
│  │ STEP 3: Graph Hints (Weight: 0.20)          │                        │
│  │ (SKIPPED - already resolved in Step 2)      │                        │
│  │ Would query graph_nodes by label match      │                        │
│  └────────────────────────────────────────────┘                         │
│                      │                                                   │
│                      ▼                                                   │
│  ┌────────────────────────────────────────────┐                         │
│  │ STEP 4: Vector Similarity (Weight: 0.10)    │                        │
│  │ (SKIPPED - already resolved)                │                        │
│  │ Fallback: embedding similarity search       │                        │
│  └────────────────────────────────────────────┘                         │
│                                                                          │
│  FINAL: canonical_id = 'equipment-uuid-456'                             │
│         total_score = (0.92 × 0.40) + (0.90 × 0.30) = 0.638            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Resolution Scoring Formula

```python
@dataclass
class ResolutionScore:
    regex_score: float = 0.0      # Step 1: Pattern match
    alias_score: float = 0.0      # Step 2: DB alias lookup
    graph_score: float = 0.0      # Step 3: Graph node match
    vector_score: float = 0.0     # Step 4: Embedding similarity

    @property
    def total(self) -> float:
        return (
            self.regex_score * 0.40 +
            self.alias_score * 0.30 +
            self.graph_score * 0.20 +
            self.vector_score * 0.10
        )

    @property
    def is_confident(self) -> bool:
        """True if safe for write actions"""
        return self.total >= 0.6 or self.regex_score >= 0.8
```

### Result Ranking Formula

After resolution, search results are ranked using:

```python
@dataclass
class ResultScore:
    text_score: float = 0.0       # Lexical + embedding similarity
    entity_score: float = 0.0     # Exact match on equipment_id, symptom_code
    graph_score: float = 0.0      # Connectivity to main entities
    recency_score: float = 0.0    # Newer items boosted for history queries

    @property
    def total(self) -> float:
        return (
            self.text_score * 0.30 +
            self.entity_score * 0.35 +
            self.graph_score * 0.20 +
            self.recency_score * 0.15
        )
```

### Handling Ambiguous Queries

**Rule: Low confidence = read-only actions only.**

When `ResolutionScore.is_confident == False`:
1. Return cards with read-only actions (`view_history`, `open_document`)
2. Suppress write actions (`create_work_order`, `order_part`)
3. Include `requires_confirmation: true` on any suggested mutations

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONFIDENCE → ACTION MATRIX                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Score >= 0.8 (HIGH)       → All actions enabled                        │
│  ├── create_work_order     ✓                                            │
│  ├── order_part            ✓                                            │
│  └── add_to_handover       ✓                                            │
│                                                                          │
│  Score 0.6-0.8 (MEDIUM)    → Write actions need confirmation            │
│  ├── create_work_order     ✓ (requires_confirmation: true)              │
│  ├── order_part            ✗ suppressed                                 │
│  └── add_to_handover       ✓                                            │
│                                                                          │
│  Score < 0.6 (LOW)         → Read-only actions only                     │
│  ├── view_history          ✓                                            │
│  ├── open_document         ✓                                            │
│  └── create_work_order     ✗ suppressed                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### SQL: Step-by-Step Resolution

```sql
-- STEP 1: Already done in Python (Module B patterns)

-- STEP 2: DB Alias Lookup
SELECT resolve_entity_alias(
    p_yacht_id := $yacht_id,
    p_entity_type := 'equipment',
    p_alias_text := $canonical
);
-- Returns: canonical_id (UUID) or NULL

-- STEP 2b: Symptom Alias Lookup
SELECT resolve_symptom_alias(
    p_alias_text := $symptom_text
);
-- Returns: symptom_code (e.g., 'OVERHEAT') or NULL

-- STEP 3: Graph Hints (if Step 2 returns NULL)
SELECT canonical_id
FROM graph_nodes
WHERE yacht_id = $yacht_id
  AND node_type = $entity_type
  AND (
      label ILIKE '%' || $value || '%'
      OR label ILIKE '%' || $canonical || '%'
  )
LIMIT 1;

-- STEP 4: Vector Similarity (if Step 3 returns NULL)
-- Would use pgvector extension:
-- SELECT id FROM equipment
-- WHERE yacht_id = $yacht_id
-- ORDER BY embedding <-> query_embedding
-- LIMIT 1;
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

---

## n8n Graph_RAG_Digest Integration

The `Graph_RAG_Digest` n8n workflow calls `POST /graphrag/populate` to populate the graph tables after GPT extraction.

### Workflow Flow

```
┌─────────────────────┐
│  Index_docs         │  Chunks document into document_chunks
│  (n8n workflow)     │  Sets extraction_status = 'pending'
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Graph_RAG_Digest   │  Reads chunks with status='pending'
│  (n8n workflow)     │  Calls GPT for entity/relationship extraction
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  POST /graphrag/    │  Population service
│  populate           │  Resolves entities → inserts graph tables
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Database Updates   │
│  - graph_nodes      │  Entities with canonical_id
│  - graph_edges      │  Relationships with source_chunk_id
│  - maintenance_     │  Extracted maintenance facts
│    templates        │
│  - document_chunks  │  extraction_status = success/failed/partial
└─────────────────────┘
```

### Request Body Format

```json
POST /graphrag/populate HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer <jwt_with_yacht_id>
X-Yacht-Signature: <signature>
Content-Type: application/json

{
  "chunk_id": "uuid-chunk-456",
  "entities": [
    {
      "label": "Main Engine",
      "type": "equipment",
      "confidence": 0.95,
      "properties": {
        "oem": "Caterpillar",
        "model": "3512"
      }
    },
    {
      "label": "Oil Filter",
      "type": "part",
      "confidence": 0.90,
      "properties": {
        "part_number": "1R-0750"
      }
    },
    {
      "label": "overheating",
      "type": "symptom",
      "confidence": 0.85
    }
  ],
  "relationships": [
    {
      "from": "Main Engine",
      "to": "Oil Filter",
      "type": "uses_part",
      "confidence": 0.88
    },
    {
      "from": "Main Engine",
      "to": "overheating",
      "type": "has_symptom",
      "confidence": 0.82
    }
  ],
  "maintenance": [
    {
      "equipment": "Main Engine",
      "part": "Oil Filter",
      "interval": "500 hours",
      "action": "replace",
      "action_description": "Replace engine oil and filter",
      "tools": ["Filter wrench", "Oil drain pan"]
    }
  ],
  "force_reprocess": false
}
```

### Response Format

```json
{
  "success": true,
  "status": "success",
  "chunk_id": "uuid-chunk-456",
  "nodes_inserted": 3,
  "nodes_resolved": 2,
  "edges_inserted": 2,
  "maintenance_inserted": 1,
  "errors": []
}
```

### Idempotency Rules

| Existing Status | force_reprocess | Behavior |
|-----------------|-----------------|----------|
| `success` | `false` | **SKIP** - Returns existing counts |
| `success` | `true` | **REPROCESS** - Deletes and re-inserts |
| `processing` | any | **BLOCK** - Returns error (concurrent request) |
| `failed` | any | **REPROCESS** - Retries extraction |
| `partial` | any | **REPROCESS** - Completes extraction |
| `pending` | any | **PROCESS** - First-time extraction |

### Database Fields Populated

#### document_chunks (updated)
```sql
UPDATE document_chunks SET
  graph_extraction_status = 'success',  -- pending/processing/success/failed/partial/empty
  extracted_entity_count = 3,
  extracted_relationship_count = 2,
  graph_extraction_errors = NULL        -- Array of error messages if failed
WHERE id = $chunk_id;
```

#### graph_nodes (inserted)
```sql
INSERT INTO graph_nodes (yacht_id, node_type, ref_table, ref_id, label, canonical_id, properties)
VALUES
  ($yacht_id, 'equipment', 'document_chunks', $chunk_id, 'Main Engine', 'equipment-uuid-123', '{"oem": "Caterpillar"}'),
  ($yacht_id, 'part', 'document_chunks', $chunk_id, 'Oil Filter', 'part-uuid-456', '{"part_number": "1R-0750"}'),
  ($yacht_id, 'symptom', 'document_chunks', $chunk_id, 'overheating', 'OVERHEAT', '{}')
ON CONFLICT (yacht_id, ref_id, label, node_type) DO UPDATE SET
  canonical_id = EXCLUDED.canonical_id,
  properties = EXCLUDED.properties;
```

#### graph_edges (inserted)
```sql
INSERT INTO graph_edges (yacht_id, edge_type, from_node_id, to_node_id, from_label, to_label, source_chunk_id, confidence, properties)
VALUES
  ($yacht_id, 'USES_PART', $node_1_id, $node_2_id, 'Main Engine', 'Oil Filter', $chunk_id, 0.88, '{}'),
  ($yacht_id, 'HAS_SYMPTOM', $node_1_id, $node_3_id, 'Main Engine', 'overheating', $chunk_id, 0.82, '{}')
ON CONFLICT (yacht_id, edge_type, from_label, to_label, source_chunk_id) DO UPDATE SET
  confidence = EXCLUDED.confidence;
```

#### maintenance_templates (inserted)
```sql
INSERT INTO maintenance_templates (yacht_id, source_chunk_id, equipment_id, part_id, interval_hours, action, action_description, tools_required, raw_extraction)
VALUES
  ($yacht_id, $chunk_id, 'equipment-uuid-123', 'part-uuid-456', 500, 'replace', 'Replace engine oil and filter', '["Filter wrench", "Oil drain pan"]', '{"equipment_label": "Main Engine", "confidence": 0.90}')
ON CONFLICT (source_chunk_id, equipment_id, part_id, action) DO UPDATE SET
  interval_hours = EXCLUDED.interval_hours,
  action_description = EXCLUDED.action_description;
```

### n8n Code Node Example

```javascript
// In n8n Code node after GPT extraction
const extractionResult = $input.first().json;
const chunkId = $input.first().json.chunk_id;

// Call population endpoint
const response = await this.helpers.httpRequest({
  method: 'POST',
  url: 'https://extract.core.celeste7.ai/graphrag/populate',
  headers: {
    'Authorization': `Bearer ${$credentials.supabaseJwt}`,
    'X-Yacht-Signature': $credentials.yachtSignature,
    'Content-Type': 'application/json'
  },
  body: {
    chunk_id: chunkId,
    entities: extractionResult.entities || [],
    relationships: extractionResult.relationships || [],
    maintenance: extractionResult.maintenance || [],
    force_reprocess: false
  }
});

return { json: response };
```

### Verification Queries

After population, verify with:

```sql
-- Check extraction status
SELECT id, graph_extraction_status, extracted_entity_count, extracted_relationship_count
FROM document_chunks
WHERE id = $chunk_id;

-- Check nodes created
SELECT node_type, label, canonical_id
FROM graph_nodes
WHERE ref_id = $chunk_id;

-- Check edges created
SELECT edge_type, from_label, to_label, confidence
FROM graph_edges
WHERE source_chunk_id = $chunk_id;

-- Check maintenance templates
SELECT equipment_id, part_id, interval_hours, action
FROM maintenance_templates
WHERE source_chunk_id = $chunk_id;
```
