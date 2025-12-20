# n8n GraphRAG Wiring Contract

This document defines the exact HTTP node configurations for connecting n8n workflows to the GraphRAG population API.

---

## Overview

```
Index_docs                      Graph_RAG_Digest
    │                                │
    │ inserts document_chunks        │ reads chunks (status=pending)
    │ with metadata                  │ calls GPT for extraction
    │                                │
    └────────────────────────────────┼───────────────────────────────────►
                                     │
                                     ▼
                          POST /graphrag/populate
                                     │
                                     ▼
                           ┌─────────────────┐
                           │ Population API  │
                           │ - resolve alias │
                           │ - insert nodes  │
                           │ - insert edges  │
                           │ - insert maint  │
                           │ - update status │
                           └─────────────────┘
```

---

## 1. Graph_RAG_Digest → /graphrag/populate

### HTTP Request Node Configuration

| Setting | Value |
|---------|-------|
| Method | `POST` |
| URL | `https://extract.core.celeste7.ai/graphrag/populate` |
| Authentication | None (handled via headers) |
| Send Headers | Yes |
| Send Body | Yes |
| Body Content Type | JSON |

### Headers

```json
{
  "Authorization": "Bearer {{ $credentials.supabaseJwt }}",
  "X-Yacht-Signature": "{{ $credentials.yachtSignature }}",
  "Content-Type": "application/json"
}
```

### Request Body

```json
{
  "chunk_id": "{{ $json.chunk_id }}",
  "entities": {{ JSON.stringify($json.gpt_extraction.entities || []) }},
  "relationships": {{ JSON.stringify($json.gpt_extraction.relationships || []) }},
  "maintenance": {{ JSON.stringify($json.gpt_extraction.maintenance || []) }},
  "force_reprocess": false
}
```

### Entity Format (from GPT)

```json
{
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
  ]
}
```

Valid entity types: `equipment`, `part`, `fault`, `symptom`, `supplier`, `person`, `location`

### Relationship Format (from GPT)

```json
{
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
  ]
}
```

Valid relationship types: `USES_PART`, `HAS_SYMPTOM`, `HAS_FAULT`, `PART_OF`, `REQUIRES_TOOL`, `MENTIONED_IN`

### Maintenance Format (from GPT)

```json
{
  "maintenance": [
    {
      "equipment": "Main Engine",
      "part": "Oil Filter",
      "interval": "500 hours",
      "action": "replace",
      "action_description": "Replace engine oil and filter",
      "tools": ["Filter wrench", "Oil drain pan"]
    }
  ]
}
```

### Expected Response

**Success (200):**
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

**Idempotent Skip (200):**
```json
{
  "success": true,
  "status": "success",
  "chunk_id": "uuid-chunk-456",
  "nodes_inserted": 3,
  "nodes_resolved": 2,
  "edges_inserted": 2,
  "maintenance_inserted": 1,
  "errors": ["Already processed - idempotent skip"]
}
```

**Concurrent Block (200):**
```json
{
  "success": false,
  "status": "processing",
  "chunk_id": "uuid-chunk-456",
  "nodes_inserted": 0,
  "edges_inserted": 0,
  "errors": ["Already processing - concurrent request blocked"]
}
```

### n8n JSON Export (HTTP Request Node)

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://extract.core.celeste7.ai/graphrag/populate",
    "authentication": "none",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "=Bearer {{ $credentials.supabaseJwt }}"
        },
        {
          "name": "X-Yacht-Signature",
          "value": "={{ $credentials.yachtSignature }}"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": []
    },
    "specifyBody": "json",
    "jsonBody": "={\n  \"chunk_id\": \"{{ $json.chunk_id }}\",\n  \"entities\": {{ JSON.stringify($json.gpt_extraction.entities || []) }},\n  \"relationships\": {{ JSON.stringify($json.gpt_extraction.relationships || []) }},\n  \"maintenance\": {{ JSON.stringify($json.gpt_extraction.maintenance || []) }},\n  \"force_reprocess\": false\n}",
    "options": {
      "timeout": 30000,
      "response": {
        "response": {
          "fullResponse": false
        }
      }
    }
  },
  "name": "POST /graphrag/populate",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2,
  "position": [800, 300]
}
```

---

## 2. Index_docs → Chunk Metadata

When inserting into `document_chunks`, populate these fields:

| Field | Source | Example |
|-------|--------|---------|
| `page_number` | PDF page index (0-based → 1-based) | `47` |
| `section_title` | First heading on page / TOC extraction | `"Lubrication System"` |
| `section_path` | Breadcrumb from TOC | `["Chapter 5", "Maintenance", "Lubrication System"]` |
| `system_tag` | Derived from path/filename | `"PROPULSION"` |
| `graph_extraction_status` | Initial value | `"pending"` |

### System Tag Heuristics

```javascript
// In n8n Code node during Index_docs
function deriveSystemTag(filePath, content) {
  const pathLower = filePath.toLowerCase();

  // Check directory path
  if (pathLower.includes('/engine/') || pathLower.includes('propulsion'))
    return 'PROPULSION';
  if (pathLower.includes('/generator/') || pathLower.includes('electrical'))
    return 'ELECTRICAL';
  if (pathLower.includes('/hvac/') || pathLower.includes('climate'))
    return 'HVAC';
  if (pathLower.includes('/hydraulic/'))
    return 'HYDRAULIC';
  if (pathLower.includes('/navigation/'))
    return 'NAVIGATION';
  if (pathLower.includes('/safety/'))
    return 'SAFETY';
  if (pathLower.includes('/deck/'))
    return 'DECK';

  // Check filename
  if (pathLower.includes('cat') || pathLower.includes('engine'))
    return 'PROPULSION';
  if (pathLower.includes('mtu'))
    return 'PROPULSION';
  if (pathLower.includes('gen'))
    return 'ELECTRICAL';

  return 'GENERAL';
}
```

### Section Title Extraction

```javascript
// In n8n Code node during PDF processing
function extractSectionTitle(pageText) {
  const lines = pageText.split('\n').filter(l => l.trim());

  // Look for heading patterns
  for (const line of lines.slice(0, 5)) {
    const trimmed = line.trim();

    // Skip page numbers
    if (/^\d+$/.test(trimmed)) continue;

    // Skip very short lines
    if (trimmed.length < 3) continue;

    // Skip lines that look like body text (too long)
    if (trimmed.length > 100) continue;

    // Check for heading indicators
    if (/^[A-Z][A-Z\s]+$/.test(trimmed)) return trimmed;  // ALL CAPS
    if (/^\d+\.\d*\s+\w/.test(trimmed)) return trimmed;   // Numbered heading
    if (/^Chapter\s+\d/i.test(trimmed)) return trimmed;   // Chapter X
    if (/^Section\s+\d/i.test(trimmed)) return trimmed;   // Section X

    // First non-trivial line as fallback
    if (trimmed.length > 10 && trimmed.length < 80) {
      return trimmed;
    }
  }

  return null;
}
```

### n8n Code Node for Chunk Insert

```javascript
// After PDF splitting, before Supabase insert
const items = $input.all();
const results = [];

for (const item of items) {
  const filePath = item.json.file_path;
  const pageNum = item.json.page_index + 1;  // 0-based to 1-based
  const pageText = item.json.content;

  results.push({
    json: {
      ...item.json,
      page_number: pageNum,
      section_title: extractSectionTitle(pageText),
      section_path: [],  // Can be populated from TOC if available
      system_tag: deriveSystemTag(filePath, pageText),
      graph_extraction_status: 'pending',
      extracted_entity_count: 0,
      extracted_relationship_count: 0
    }
  });
}

return results;
```

---

## 3. Workflow Position

### Graph_RAG_Digest Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Trigger         │────►│ Query Pending   │────►│ Loop Each Chunk │
│ (schedule/      │     │ Chunks          │     │                 │
│  webhook)       │     └─────────────────┘     └────────┬────────┘
└─────────────────┘                                      │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ POST            │◄────│ Transform GPT   │◄────│ Call GPT for    │
│ /graphrag/      │     │ Response        │     │ Entity Extract  │
│ populate        │     └─────────────────┘     └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Log Result /    │
│ Handle Errors   │
└─────────────────┘
```

### Index_docs Flow (updated section)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Download File   │────►│ Split into      │────►│ Extract         │
│ from Storage    │     │ Pages/Chunks    │     │ Metadata        │◄── NEW
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Trigger         │◄────│ Insert into     │◄────│ Generate        │
│ Graph_RAG_      │     │ document_chunks │     │ Embeddings      │
│ Digest          │     └─────────────────┘     └─────────────────┘
└─────────────────┘
```

---

## 4. Error Handling

### In Graph_RAG_Digest

```javascript
// After HTTP Request node
const response = $input.first().json;

if (!response.success || response.status === 'processing') {
  // Log but don't fail - chunk will be retried
  console.log(`Chunk ${response.chunk_id}: ${response.errors.join(', ')}`);
  return [];  // Skip to next chunk
}

// Check for partial success
if (response.status === 'partial') {
  // Some entities/edges failed but others succeeded
  console.warn(`Chunk ${response.chunk_id}: partial success - ${response.errors.join(', ')}`);
}

return $input.all();
```

### Retry Logic

| Status | Retry? | When |
|--------|--------|------|
| `success` | No | Done |
| `processing` | Yes | Next run (concurrent blocked) |
| `partial` | Optional | If you want full extraction |
| `failed` | Yes | Next run with `force_reprocess: true` |

---

## 5. Verification

After wiring is complete, verify with these queries:

```sql
-- 1. Check chunks with pending status (should decrease over time)
SELECT COUNT(*) FROM document_chunks
WHERE graph_extraction_status = 'pending';

-- 2. Check chunks with successful extraction
SELECT COUNT(*), AVG(extracted_entity_count) as avg_entities
FROM document_chunks
WHERE graph_extraction_status = 'success';

-- 3. Check graph nodes created
SELECT node_type, COUNT(*)
FROM graph_nodes
GROUP BY node_type;

-- 4. Check graph edges created
SELECT edge_type, COUNT(*)
FROM graph_edges
GROUP BY edge_type;

-- 5. Check maintenance templates
SELECT COUNT(*) FROM maintenance_templates;

-- 6. Check chunks with metadata
SELECT COUNT(*) FROM document_chunks
WHERE section_title IS NOT NULL;
```

---

## 6. Credentials Setup

In n8n, create credentials with:

| Name | Value |
|------|-------|
| `supabaseJwt` | Service role JWT with yacht_id claim |
| `yachtSignature` | `sha256(yacht_id + YACHT_SALT)` |

The JWT must contain:
```json
{
  "yacht_id": "yacht-uuid-123",
  "role": "service_role",
  "exp": ...
}
```
