# Uniform Output Specification

**Version:** 1.0
**Purpose:** Standardized output format for all 9 parallel SQL nodes
**Last Updated:** 2025-12-19

---

## Design Principle

Every SQL node must return **identical structure** regardless of source table. This enables:
1. Single merge logic in JavaScript
2. Consistent frontend card rendering
3. Unified scoring and ranking
4. Simple debugging

---

## Core Output Schema

```typescript
interface SearchResult {
  // === REQUIRED FIELDS (every row) ===
  result_id: string;          // UUID as TEXT - unique identifier
  result_type: string;        // Semantic type for card rendering
  result_label: string;       // Primary display text (title)
  content: string | null;     // Secondary text (description)
  subtitle: string | null;    // Tertiary text (metadata line)

  // === SCORING ===
  match_confidence: number;   // 0.0-1.0 from SQL CASE statement
  fusion_score: number | null;// Calculated in merge step (initially null)
  vector_score: number | null;// Always null for NO_LLM
  graph_score: number | null; // Always null for NO_LLM

  // === METADATA ===
  match_metadata: JSONB;      // Search context
  source_data: JSONB;         // Full row data for drill-down

  // === OPTIONAL ===
  url: string | null;         // Direct link (for documents)
  tags: string[];             // Category tags for filtering
}
```

---

## SQL Template (Base)

```sql
SELECT
  -- ============ IDENTIFIERS ============
  t.id::TEXT as result_id,
  '{{RESULT_TYPE}}'::TEXT as result_type,

  -- ============ DISPLAY FIELDS ============
  {{PRIMARY_DISPLAY}}::TEXT as result_label,
  COALESCE({{SECONDARY_DISPLAY}}, '')::TEXT as content,
  {{TERTIARY_DISPLAY}}::TEXT as subtitle,

  -- ============ CONFIDENCE SCORING ============
  CASE
    WHEN {{EXACT_MATCH_CONDITION}} THEN 1.0
    WHEN {{PREFIX_MATCH_CONDITION}} THEN 0.90
    WHEN {{PRIMARY_CONTAINS_CONDITION}} THEN 0.85
    WHEN {{SECONDARY_CONTAINS_CONDITION}} THEN 0.70
    WHEN {{JSONB_CONTAINS_CONDITION}} THEN 0.60
    ELSE 0.50
  END as match_confidence,

  -- ============ SCORES (NULL for NO_LLM) ============
  NULL::NUMERIC as fusion_score,
  NULL::NUMERIC as vector_score,
  NULL::NUMERIC as graph_score,

  -- ============ METADATA ============
  jsonb_build_object(
    'source_table', '{{TABLE_NAME}}',
    'source_group', '{{GROUP_NAME}}',
    'match_type', 'keyword',
    'matched_query', {{ $json.fuzzy_pattern }},
    {{ADDITIONAL_METADATA}}
  ) as match_metadata,

  -- ============ SOURCE DATA ============
  to_jsonb(t.*) as source_data,

  -- ============ OPTIONAL ============
  {{URL_EXPRESSION}}::TEXT as url,
  ARRAY[{{TAG_LIST}}]::TEXT[] as tags

FROM {{TABLE_NAME}} t
{{JOIN_CLAUSES}}

WHERE t.yacht_id = {{ $json.yacht_id }}::UUID
  AND (
    {{SEARCH_CONDITIONS}}
  )

ORDER BY match_confidence DESC
LIMIT {{ $json.result_limit }};
```

---

## Result Types by Group

### GROUP 1: INVENTORY
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `part` | pms_parts | Part catalog entry |
| `stock_location` | pms_inventory_stock | Location-focused result |
| `part_with_stock` | pms_parts + stock JOIN | Part with quantity info |

### GROUP 2: EQUIPMENT
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `equipment` | pms_equipment | Equipment registry entry |
| `equipment_attention` | pms_equipment (attention_flag=true) | Equipment needing attention |
| `equipment_note` | pms_notes (equipment context) | Note about equipment |
| `equipment_bom` | pms_equipment_parts_bom | Bill of materials entry |

### GROUP 3: FAULTS
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `fault` | pms_faults | Generic fault |
| `fault_active` | pms_faults (resolved_at IS NULL) | Active/unresolved fault |
| `fault_resolved` | pms_faults (resolved_at IS NOT NULL) | Historical fault |

### GROUP 4: WORK ORDERS
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `work_order` | pms_work_orders | Active work order |
| `work_order_pending` | pms_work_orders (status=pending) | Pending WO |
| `work_order_overdue` | pms_work_orders (due_date < NOW()) | Overdue WO |
| `work_order_history` | pms_work_order_history | Completed work record |
| `work_order_note` | pms_notes (WO context) | Note on work order |

### GROUP 5: DOCUMENTS
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `document` | doc_yacht_library | Full document reference |
| `document_chunk` | doc_yacht_library (chunk_text populated) | Specific section |
| `document_manual` | doc_yacht_library (type=manual) | Manual document |
| `document_schematic` | doc_yacht_library (type=schematic) | Schematic/diagram |

### GROUP 6: CERTIFICATES
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `crew_certificate` | pms_crew_certificates | Crew qualification |
| `crew_certificate_expiring` | pms_crew_certificates (expiry < 90d) | Soon-to-expire |
| `vessel_certificate` | pms_vessel_certificates | Vessel certificate |
| `vessel_certificate_expiring` | pms_vessel_certificates (expiry < 90d) | Soon-to-expire |

### GROUP 7: SUPPLIERS
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `supplier` | pms_suppliers | Supplier/vendor |
| `supplier_preferred` | pms_suppliers (preferred=true) | Preferred supplier |
| `purchase_order` | pms_purchase_orders | PO header |
| `purchase_order_item` | pms_purchase_order_items | PO line item |

### GROUP 8: VOYAGE
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `voyage` | pms_voyage_log | Voyage record |
| `voyage_recent` | pms_voyage_log (recent) | Recent voyage |

### GROUP 9: HANDOVER
| result_type | Source | When to Use |
|-------------|--------|-------------|
| `handover_record` | dash_handover_records | Handover session |
| `handover_item` | dash_handover_items | Handover line item |
| `handover_outstanding` | dash_handover_items (status!=completed) | Outstanding item |

---

## Complete SQL Examples

### GROUP 1: Inventory SQL

```sql
WITH inventory_results AS (
  -- Search pms_parts
  SELECT
    p.id::TEXT as result_id,
    CASE
      WHEN s.id IS NOT NULL THEN 'part_with_stock'
      ELSE 'part'
    END::TEXT as result_type,
    p.name::TEXT as result_label,
    COALESCE(p.description, '')::TEXT as content,
    CONCAT(
      COALESCE(p.manufacturer, ''),
      CASE WHEN p.part_number IS NOT NULL THEN ' | ' || p.part_number ELSE '' END
    )::TEXT as subtitle,

    -- Confidence scoring
    CASE
      WHEN p.part_number = {{ $json.query_text }} THEN 1.0
      WHEN p.name = {{ $json.query_text }} THEN 0.95
      WHEN p.part_number ILIKE {{ $json.query_text }} || '%' THEN 0.90
      WHEN p.name ILIKE {{ $json.fuzzy_pattern }} THEN 0.85
      WHEN p.manufacturer ILIKE {{ $json.fuzzy_pattern }} THEN 0.80
      WHEN p.category ILIKE {{ $json.fuzzy_pattern }} THEN 0.75
      WHEN p.description ILIKE {{ $json.fuzzy_pattern }} THEN 0.70
      WHEN p.model_compatibility::TEXT ILIKE {{ $json.fuzzy_pattern }} THEN 0.60
      ELSE 0.50
    END as match_confidence,

    NULL::NUMERIC as fusion_score,
    NULL::NUMERIC as vector_score,
    NULL::NUMERIC as graph_score,

    jsonb_build_object(
      'source_table', 'pms_parts',
      'source_group', 'INVENTORY',
      'match_type', 'keyword',
      'matched_query', {{ $json.query_text }},
      'location', s.location,
      'quantity', s.quantity,
      'min_quantity', s.min_quantity,
      'category', p.category,
      'manufacturer', p.manufacturer
    ) as match_metadata,

    to_jsonb(p.*) || COALESCE(jsonb_build_object('stock', to_jsonb(s.*)), '{}') as source_data,

    NULL::TEXT as url,
    ARRAY['inventory', p.category]::TEXT[] as tags

  FROM pms_parts p
  LEFT JOIN pms_inventory_stock s ON s.part_id = p.id AND s.yacht_id = p.yacht_id

  WHERE p.yacht_id = {{ $json.yacht_id }}::UUID
    AND (
      p.part_number = {{ $json.query_text }}
      OR p.name ILIKE {{ $json.fuzzy_pattern }}
      OR p.part_number ILIKE {{ $json.query_text }} || '%'
      OR p.manufacturer ILIKE {{ $json.fuzzy_pattern }}
      OR p.description ILIKE {{ $json.fuzzy_pattern }}
      OR p.category ILIKE {{ $json.fuzzy_pattern }}
      OR p.model_compatibility::TEXT ILIKE {{ $json.fuzzy_pattern }}
    )

  UNION ALL

  -- Search by location
  SELECT
    s.id::TEXT as result_id,
    'stock_location'::TEXT as result_type,
    CONCAT('Location: ', s.location)::TEXT as result_label,
    p.name::TEXT as content,
    CONCAT('Qty: ', s.quantity, ' | ', COALESCE(p.manufacturer, 'Unknown'))::TEXT as subtitle,

    CASE
      WHEN LOWER(s.location) = LOWER({{ $json.query_text }}) THEN 0.95
      WHEN s.location ILIKE {{ $json.fuzzy_pattern }} THEN 0.90
      ELSE 0.50
    END as match_confidence,

    NULL::NUMERIC as fusion_score,
    NULL::NUMERIC as vector_score,
    NULL::NUMERIC as graph_score,

    jsonb_build_object(
      'source_table', 'pms_inventory_stock',
      'source_group', 'INVENTORY',
      'match_type', 'location',
      'matched_query', {{ $json.query_text }},
      'part_name', p.name,
      'part_number', p.part_number,
      'quantity', s.quantity
    ) as match_metadata,

    to_jsonb(s.*) || jsonb_build_object('part', to_jsonb(p.*)) as source_data,

    NULL::TEXT as url,
    ARRAY['inventory', 'location']::TEXT[] as tags

  FROM pms_inventory_stock s
  JOIN pms_parts p ON p.id = s.part_id

  WHERE s.yacht_id = {{ $json.yacht_id }}::UUID
    AND s.location ILIKE {{ $json.fuzzy_pattern }}
)

SELECT * FROM inventory_results
ORDER BY match_confidence DESC
LIMIT {{ $json.result_limit }};
```

### GROUP 3: Faults SQL

```sql
SELECT
  f.id::TEXT as result_id,
  CASE
    WHEN f.resolved_at IS NULL THEN 'fault_active'
    ELSE 'fault_resolved'
  END::TEXT as result_type,
  COALESCE(f.fault_code || ': ', '') || f.title as result_label,
  COALESCE(f.description, '')::TEXT as content,
  CONCAT(
    'Severity: ', f.severity::TEXT,
    ' | ',
    CASE
      WHEN f.resolved_at IS NULL THEN 'ACTIVE'
      ELSE 'Resolved: ' || TO_CHAR(f.resolved_at, 'YYYY-MM-DD')
    END
  )::TEXT as subtitle,

  -- Confidence scoring
  CASE
    WHEN f.fault_code = {{ $json.query_text }} THEN 1.0
    WHEN f.fault_code ILIKE {{ $json.query_text }} || '%' THEN 0.90
    WHEN f.title ILIKE {{ $json.fuzzy_pattern }} THEN 0.85
    WHEN LOWER(f.severity::TEXT) = LOWER({{ $json.query_text }}) THEN 0.85
    WHEN f.description ILIKE {{ $json.fuzzy_pattern }} THEN 0.70
    ELSE 0.50
  END as match_confidence,

  NULL::NUMERIC as fusion_score,
  NULL::NUMERIC as vector_score,
  NULL::NUMERIC as graph_score,

  jsonb_build_object(
    'source_table', 'pms_faults',
    'source_group', 'FAULTS',
    'match_type', 'keyword',
    'matched_query', {{ $json.query_text }},
    'fault_code', f.fault_code,
    'severity', f.severity::TEXT,
    'is_active', (f.resolved_at IS NULL),
    'detected_at', f.detected_at,
    'equipment_id', f.equipment_id
  ) as match_metadata,

  to_jsonb(f.*) as source_data,

  NULL::TEXT as url,
  ARRAY[
    'fault',
    f.severity::TEXT,
    CASE WHEN f.resolved_at IS NULL THEN 'active' ELSE 'resolved' END
  ]::TEXT[] as tags

FROM pms_faults f
WHERE f.yacht_id = {{ $json.yacht_id }}::UUID
  AND (
    f.fault_code = {{ $json.query_text }}
    OR f.fault_code ILIKE {{ $json.query_text }} || '%'
    OR f.title ILIKE {{ $json.fuzzy_pattern }}
    OR f.description ILIKE {{ $json.fuzzy_pattern }}
    OR f.severity::TEXT ILIKE {{ $json.fuzzy_pattern }}
  )

ORDER BY
  f.resolved_at IS NULL DESC,  -- Active faults first
  match_confidence DESC,
  f.detected_at DESC

LIMIT {{ $json.result_limit }};
```

### GROUP 5: Documents SQL

```sql
SELECT
  dl.id::TEXT as result_id,
  CASE
    WHEN dl.is_chunk = true THEN 'document_chunk'
    WHEN dl.document_type = 'manual' THEN 'document_manual'
    WHEN dl.document_type = 'schematic' THEN 'document_schematic'
    ELSE 'document'
  END::TEXT as result_type,
  dl.document_name::TEXT as result_label,
  COALESCE(
    CASE WHEN dl.chunk_text IS NOT NULL
      THEN LEFT(dl.chunk_text, 300)
      ELSE NULL
    END,
    ''
  )::TEXT as content,
  CONCAT(
    COALESCE(dl.document_type, 'document'),
    CASE WHEN dl.department IS NOT NULL THEN ' | ' || dl.department ELSE '' END,
    CASE WHEN dl.page_num IS NOT NULL THEN ' | Page ' || dl.page_num ELSE '' END
  )::TEXT as subtitle,

  -- Confidence scoring
  CASE
    WHEN dl.document_name ILIKE {{ $json.fuzzy_pattern }} THEN 0.90
    WHEN LOWER(dl.document_type) = LOWER({{ $json.query_text }}) THEN 0.85
    WHEN dl.fault_code_matches::TEXT ILIKE {{ $json.fuzzy_pattern }} THEN 0.85
    WHEN dl.equipment_covered::TEXT ILIKE {{ $json.fuzzy_pattern }} THEN 0.80
    WHEN dl.chunk_text ILIKE {{ $json.fuzzy_pattern }} THEN 0.75
    WHEN dl.entities_found::TEXT ILIKE {{ $json.fuzzy_pattern }} THEN 0.65
    ELSE 0.50
  END as match_confidence,

  NULL::NUMERIC as fusion_score,
  NULL::NUMERIC as vector_score,
  NULL::NUMERIC as graph_score,

  jsonb_build_object(
    'source_table', 'doc_yacht_library',
    'source_group', 'DOCUMENTS',
    'match_type', 'keyword',
    'matched_query', {{ $json.query_text }},
    'document_type', dl.document_type,
    'department', dl.department,
    'page_num', dl.page_num,
    'chunk_index', dl.chunk_index,
    'times_helpful', dl.times_helpful,
    'effectiveness_score', dl.effectiveness_score
  ) as match_metadata,

  to_jsonb(dl.*) as source_data,

  dl.document_path::TEXT as url,
  ARRAY[
    'document',
    COALESCE(dl.document_type, 'unknown'),
    COALESCE(dl.department, 'general')
  ]::TEXT[] as tags

FROM doc_yacht_library dl
WHERE dl.yacht_id = {{ $json.yacht_id }}
  AND (
    dl.document_name ILIKE {{ $json.fuzzy_pattern }}
    OR dl.document_type ILIKE {{ $json.fuzzy_pattern }}
    OR dl.equipment_covered::TEXT ILIKE {{ $json.fuzzy_pattern }}
    OR dl.fault_code_matches::TEXT ILIKE {{ $json.fuzzy_pattern }}
    OR dl.chunk_text ILIKE {{ $json.fuzzy_pattern }}
    OR dl.department ILIKE {{ $json.fuzzy_pattern }}
  )

ORDER BY
  dl.effectiveness_score DESC NULLS LAST,
  match_confidence DESC

LIMIT {{ $json.result_limit }};
```

---

## Merge Node Output Processing

After all 9 SQL nodes return results, the merge JavaScript node:

```javascript
// ===============================================
// MERGE ALL RESULTS
// ===============================================

const allResults = [];

// Collect from all SQL nodes
const sqlNodes = [
  'SQL_Inventory',
  'SQL_Equipment',
  'SQL_Faults',
  'SQL_WorkOrders',
  'SQL_Documents',
  'SQL_Certificates',
  'SQL_Suppliers',
  'SQL_Voyage',
  'SQL_Handover'
];

for (const nodeName of sqlNodes) {
  try {
    const nodeResults = $(nodeName).all();
    for (const item of nodeResults) {
      if (item.json && item.json.result_id) {
        allResults.push({
          ...item.json,
          source_node: nodeName
        });
      }
    }
  } catch (e) {
    // Node returned null/error - expected for most categories
    continue;
  }
}

// ===============================================
// DEDUPLICATION
// ===============================================

const seen = new Map();
const deduped = [];

for (const result of allResults) {
  const key = result.result_id;
  if (!seen.has(key)) {
    seen.set(key, result);
    deduped.push(result);
  } else {
    // Keep higher confidence version
    const existing = seen.get(key);
    if (result.match_confidence > existing.match_confidence) {
      seen.set(key, result);
      // Replace in deduped array
      const idx = deduped.findIndex(r => r.result_id === key);
      if (idx >= 0) deduped[idx] = result;
    }
  }
}

// ===============================================
// CALCULATE FUSION SCORES
// ===============================================

const context = $('Prepare SQL Parameters').first().json;
const intent = context.intent || 'general_search';

// Intent-based boosts
const INTENT_BOOSTS = {
  'diagnose_issue': {
    'fault': 0.15,
    'fault_active': 0.20,
    'document_manual': 0.10,
    'work_order_history': 0.10,
    'handover_record': 0.05
  },
  'find_document': {
    'document': 0.15,
    'document_manual': 0.20,
    'document_schematic': 0.15
  },
  'find_part': {
    'part': 0.15,
    'part_with_stock': 0.20,
    'stock_location': 0.10
  }
  // Add more intents as needed
};

const boosts = INTENT_BOOSTS[intent] || {};

for (const result of deduped) {
  const baseConfidence = result.match_confidence || 0.5;
  const intentBoost = boosts[result.result_type] || 0;

  result.fusion_score = Math.min(1.0, baseConfidence + intentBoost);
}

// ===============================================
// SORT BY FUSION SCORE
// ===============================================

deduped.sort((a, b) => b.fusion_score - a.fusion_score);

// ===============================================
// BUILD RESPONSE
// ===============================================

// Group by result_type for summary
const byType = {};
for (const result of deduped) {
  const type = result.result_type;
  if (!byType[type]) byType[type] = 0;
  byType[type]++;
}

return {
  success: true,
  total_results: deduped.length,
  groups_searched: sqlNodes.length,
  groups_with_results: new Set(deduped.map(r => r.source_node)).size,
  results_by_type: byType,
  results: deduped
};
```

---

## Frontend Card Type Mapping

```javascript
const CARD_CONFIG = {
  // Inventory
  'part': { icon: 'package', color: 'green', actions: ['view', 'check_stock', 'order'] },
  'part_with_stock': { icon: 'package', color: 'green', actions: ['view', 'check_stock', 'order'] },
  'stock_location': { icon: 'map-pin', color: 'blue', actions: ['view', 'count'] },

  // Equipment
  'equipment': { icon: 'cpu', color: 'blue', actions: ['view', 'create_wo', 'history'] },
  'equipment_attention': { icon: 'alert-triangle', color: 'orange', actions: ['view', 'create_wo'] },
  'equipment_note': { icon: 'message-square', color: 'gray', actions: ['view'] },

  // Faults
  'fault': { icon: 'alert-circle', color: 'red', actions: ['view', 'create_wo'] },
  'fault_active': { icon: 'alert-triangle', color: 'red', actions: ['view', 'acknowledge', 'create_wo'] },
  'fault_resolved': { icon: 'check-circle', color: 'gray', actions: ['view'] },

  // Work Orders
  'work_order': { icon: 'clipboard', color: 'purple', actions: ['view', 'update_status'] },
  'work_order_pending': { icon: 'clock', color: 'yellow', actions: ['view', 'start'] },
  'work_order_overdue': { icon: 'alert-triangle', color: 'red', actions: ['view', 'update_status'] },
  'work_order_history': { icon: 'archive', color: 'gray', actions: ['view'] },

  // Documents
  'document': { icon: 'file-text', color: 'gray', actions: ['open', 'pin'] },
  'document_manual': { icon: 'book', color: 'blue', actions: ['open', 'pin'] },
  'document_schematic': { icon: 'layout', color: 'purple', actions: ['open', 'pin'] },
  'document_chunk': { icon: 'file-text', color: 'gray', actions: ['open', 'view_context'] },

  // Certificates
  'crew_certificate': { icon: 'award', color: 'green', actions: ['view'] },
  'crew_certificate_expiring': { icon: 'alert-circle', color: 'orange', actions: ['view', 'renew'] },
  'vessel_certificate': { icon: 'shield', color: 'blue', actions: ['view'] },
  'vessel_certificate_expiring': { icon: 'alert-circle', color: 'orange', actions: ['view', 'schedule_survey'] },

  // Suppliers
  'supplier': { icon: 'briefcase', color: 'blue', actions: ['view', 'contact'] },
  'supplier_preferred': { icon: 'star', color: 'yellow', actions: ['view', 'contact'] },
  'purchase_order': { icon: 'shopping-cart', color: 'green', actions: ['view'] },

  // Voyage
  'voyage': { icon: 'navigation', color: 'blue', actions: ['view'] },

  // Handover
  'handover_record': { icon: 'refresh-cw', color: 'purple', actions: ['view'] },
  'handover_item': { icon: 'check-square', color: 'purple', actions: ['view', 'complete'] },
  'handover_outstanding': { icon: 'alert-circle', color: 'orange', actions: ['view', 'complete'] }
};
```

---

## Summary

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| result_id | YES | SQL | UUID as TEXT |
| result_type | YES | SQL | From CARD_CONFIG keys |
| result_label | YES | SQL | Primary display text |
| content | YES (can be empty) | SQL | Secondary text |
| subtitle | YES (can be empty) | SQL | Metadata line |
| match_confidence | YES | SQL | 0.0-1.0 |
| fusion_score | YES | Merge JS | After intent boost |
| vector_score | NO | Always NULL | NO_LLM |
| graph_score | NO | Always NULL | NO_LLM |
| match_metadata | YES | SQL | JSONB context |
| source_data | YES | SQL | Full row JSONB |
| url | NO | SQL | For documents |
| tags | YES | SQL | Array of strings |
