# Frontend Search Contract

This document defines the exact API contract for integrating the CelesteOS frontend with `/v1/search` and `/v1/actions/execute`.

---

## Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND FLOW                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐    POST /v1/search     ┌─────────────┐                  │
│  │ Search Bar  │ ─────────────────────► │   Backend   │                  │
│  └─────────────┘                        └──────┬──────┘                  │
│                                                │                          │
│                                                ▼                          │
│                                         ┌─────────────┐                  │
│                                         │   CARDS     │                  │
│                                         │ + ACTIONS   │                  │
│                                         └──────┬──────┘                  │
│                                                │                          │
│  ┌─────────────┐    POST /v1/actions/   ◄──────┘                         │
│  │ User clicks │         execute                                          │
│  │ action btn  │ ─────────────────────► Mutation happens                 │
│  └─────────────┘                                                          │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/search` | POST | Execute search query → returns cards with actions |
| `/v1/actions/execute` | POST | Execute a card action (mutations only) |

---

## Authentication

Both endpoints require:

```http
Authorization: Bearer <JWT>
X-Yacht-Signature: <sha256(yacht_id + YACHT_SALT)>
Content-Type: application/json
```

The `yacht_id` is extracted from the JWT payload. **Never send yacht_id in the request body.**

---

## /v1/search Request

```typescript
interface SearchRequest {
  query: string;  // Natural language query
}
```

```http
POST /v1/search HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "query": "Engine is overheating"
}
```

---

## /v1/search Response

```typescript
interface SearchResponse {
  query: string;
  intent: string;
  entities: Entity[];
  cards: Card[];
  metadata: {
    entity_count: number;
    card_count: number;
  };
}

interface Entity {
  text: string;           // Original text from query
  type: string;           // equipment, part, fault_code, maritime_term, person
  canonical: string;      // Normalized form (e.g., "MAIN_ENGINE")
  canonical_id?: string;  // UUID if resolved
  symptom_code?: string;  // If type is maritime_term/symptom
  confidence: number;     // 0.0 - 1.0
}

interface Card {
  type: CardType;
  title: string;
  actions: Action[];
  [key: string]: any;     // Card-specific fields
}

type CardType =
  | "equipment"
  | "document_chunk"
  | "work_order"
  | "fault"
  | "part"
  | "handover"
  | "predictive";

interface Action {
  label: string;                    // Button text
  action: string;                   // Action identifier
  endpoint: string;                 // Backend endpoint
  method: "GET" | "POST";           // HTTP method
  payload_template: Record<string, any>;  // Pre-filled payload
  constraints: Record<string, any>; // Validation rules
}
```

---

## /v1/actions/execute Request

When user clicks an action button, send the action with filled payload:

```typescript
interface ExecuteActionRequest {
  action: string;                   // From card.actions[].action
  payload: Record<string, any>;     // Filled payload_template
}
```

```http
POST /v1/actions/execute HTTP/1.1
Host: api.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "action": "create_work_order",
  "payload": {
    "yacht_id": "yacht-uuid-123",
    "equipment_id": "equipment-uuid-456",
    "title": "Engine Overheating Investigation",
    "description": "User reported engine overheating",
    "priority": "high"
  }
}
```

---

## Card-Specific Fields

### Equipment Card
```json
{
  "type": "equipment",
  "title": "Main Engine",
  "equipment_id": "uuid",
  "symptom_detected": "overheating",
  "symptom_code": "OVERHEAT",
  "person_filter": "2ND_ENGINEER",
  "actions": [...]
}
```

### Document Chunk Card
```json
{
  "type": "document_chunk",
  "title": "Troubleshooting - High Temperature",
  "document_id": "uuid",
  "page_number": 147,
  "text_preview": "If engine temperature exceeds 95°C...",
  "storage_path": "/manuals/caterpillar-3512/troubleshooting.pdf",
  "actions": [...]
}
```

### Work Order Card
```json
{
  "type": "work_order",
  "title": "Port ME High Temp Alarm Investigation",
  "work_order_id": "uuid",
  "status": "completed",
  "equipment_id": "uuid",
  "created_by": "2nd Engineer - John Smith",
  "created_at": "2024-08-15T10:30:00Z",
  "resolution": "Cleaned heat exchanger",
  "actions": [...]
}
```

### Fault Card
```json
{
  "type": "fault",
  "title": "Fault E047",
  "fault_code": "E047",
  "equipment_id": "uuid",
  "summary": "Coolant temperature sensor out of range",
  "severity": "warning",
  "actions": [...]
}
```

### Part Card
```json
{
  "type": "part",
  "title": "Oil Filter",
  "part_id": "uuid",
  "name": "Oil Filter",
  "part_number": "1R-0750",
  "in_stock": 3,
  "location": "Engine Room Locker A",
  "actions": [...]
}
```

### Handover Card
```json
{
  "type": "handover",
  "title": "Engine temp issue - ongoing",
  "handover_id": "uuid",
  "author": "2nd Engineer - John Smith",
  "content": "ME overheating at 1450 RPM noted...",
  "created_at": "2024-08-14T18:00:00Z",
  "actions": [...]
}
```

---

# Worked Examples

## Example 1: Fault Diagnosis

**User types:** "What does error code E047 mean?"

### Request

```http
POST /v1/search HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "query": "What does error code E047 mean?"
}
```

### Response

```json
{
  "query": "What does error code E047 mean?",
  "intent": "diagnose_fault",
  "entities": [
    {
      "text": "E047",
      "type": "fault_code",
      "canonical": "E047",
      "canonical_id": "fault-uuid-789",
      "confidence": 0.95
    }
  ],
  "cards": [
    {
      "type": "fault",
      "title": "Fault E047",
      "fault_code": "E047",
      "equipment_id": null,
      "summary": "Coolant temperature sensor reading out of expected range. May indicate sensor failure or actual overheating condition.",
      "severity": "warning",
      "actions": [
        {
          "label": "Diagnose Fault",
          "action": "diagnose_fault",
          "endpoint": "/v1/faults/diagnose",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "code": "E047",
            "equipment_id": ""
          },
          "constraints": {}
        },
        {
          "label": "Create Work Order",
          "action": "create_work_order_fault",
          "endpoint": "/v1/work-orders/create",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "suspected_fault_code": "E047",
            "equipment_id": "",
            "description": ""
          },
          "constraints": {}
        },
        {
          "label": "Add Note",
          "action": "add_note",
          "endpoint": "/v1/notes/create",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "",
            "note_text": ""
          },
          "constraints": {
            "requires_equipment_id": true,
            "requires_note_text": true
          }
        }
      ]
    },
    {
      "type": "document_chunk",
      "title": "Error Codes - Cooling System",
      "document_id": "doc-uuid-101",
      "page_number": 234,
      "text_preview": "E047: Coolant Temperature Sensor Fault. This code indicates the ECM has detected a voltage outside the expected range from the coolant temperature sensor...",
      "storage_path": "/manuals/caterpillar-3512/error-codes.pdf",
      "actions": [
        {
          "label": "Open Document",
          "action": "open_document",
          "endpoint": "/v1/documents/open",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "storage_path": "/manuals/caterpillar-3512/error-codes.pdf"
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
            "document_id": "doc-uuid-101",
            "context": ""
          },
          "constraints": {}
        }
      ]
    }
  ],
  "metadata": {
    "entity_count": 1,
    "card_count": 2
  }
}
```

### Frontend Renders

```
┌─────────────────────────────────────────────────────────────────┐
│  🔴 Fault E047                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  Severity: warning                                              │
│                                                                 │
│  Coolant temperature sensor reading out of expected range.      │
│  May indicate sensor failure or actual overheating condition.   │
│                                                                 │
│  [Diagnose Fault] [Create Work Order] [Add Note]               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📄 Error Codes - Cooling System                                │
│  ─────────────────────────────────────────────────────────────  │
│  Page: 234                                                      │
│                                                                 │
│  E047: Coolant Temperature Sensor Fault. This code indicates    │
│  the ECM has detected a voltage outside the expected range...   │
│                                                                 │
│  [Open Document] [Add to Handover]                             │
└─────────────────────────────────────────────────────────────────┘
```

### User Clicks "Create Work Order"

```http
POST /v1/actions/execute HTTP/1.1
Host: api.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "action": "create_work_order_fault",
  "payload": {
    "yacht_id": "yacht-uuid-123",
    "suspected_fault_code": "E047",
    "equipment_id": "equipment-uuid-456",
    "description": "Investigate E047 fault - coolant temperature sensor"
  }
}
```

---

## Example 2: Equipment History with Person Filter

**User types:** "Engine is overheating, show historic data from the 2nd engineer"

### Request

```http
POST /v1/search HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "query": "Engine is overheating, show historic data from the 2nd engineer"
}
```

### Response

```json
{
  "query": "Engine is overheating, show historic data from the 2nd engineer",
  "intent": "equipment_history",
  "entities": [
    {
      "text": "Engine",
      "type": "equipment",
      "canonical": "MAIN_ENGINE",
      "canonical_id": "equipment-uuid-456",
      "confidence": 0.92
    },
    {
      "text": "overheating",
      "type": "maritime_term",
      "canonical": "TEMPERATURE_HIGH",
      "canonical_id": "OVERHEAT",
      "symptom_code": "OVERHEAT",
      "confidence": 0.80
    },
    {
      "text": "2nd engineer",
      "type": "person",
      "canonical": "2ND_ENGINEER",
      "canonical_id": null,
      "confidence": 0.85
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
          "constraints": {
            "requires_equipment_id": true
          }
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
          "constraints": {
            "requires_equipment_id": true,
            "requires_note_text": true
          }
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

### Frontend Renders

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ Engine                                                      │
│  ─────────────────────────────────────────────────────────────  │
│  Symptom: overheating (OVERHEAT)                               │
│  Filtered by: 2nd Engineer                                      │
│                                                                 │
│  [View History] [Create Work Order] [Add Note] [Add to Handover]│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📋 Port ME High Temp Alarm Investigation                       │
│  ─────────────────────────────────────────────────────────────  │
│  Status: ✅ completed                                           │
│  Created by: 2nd Engineer - John Smith                          │
│  Date: 2024-08-15                                               │
│                                                                 │
│  Resolution: Cleaned heat exchanger, replaced zinc anodes       │
│                                                                 │
│  [View History] [Add to Handover]                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📝 Engine temp issue - ongoing                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Author: 2nd Engineer - John Smith                              │
│  Date: 2024-08-14                                               │
│                                                                 │
│  ME overheating at 1450 RPM noted. Scheduled heat exchanger     │
│  inspection...                                                  │
│                                                                 │
│  [Add to Handover]                                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  📄 Troubleshooting - High Temperature Alarms                   │
│  ─────────────────────────────────────────────────────────────  │
│  Page: 147                                                      │
│                                                                 │
│  If engine temperature exceeds 95°C at normal RPM, check:       │
│  1) Coolant level 2) Heat exchanger fouling...                  │
│                                                                 │
│  [Open Document] [Add to Handover]                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 3: Part Search

**User types:** "Find oil filter for generator"

### Request

```http
POST /v1/search HTTP/1.1
Host: extract.core.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "query": "Find oil filter for generator"
}
```

### Response

```json
{
  "query": "Find oil filter for generator",
  "intent": "find_part",
  "entities": [
    {
      "text": "oil filter",
      "type": "part",
      "canonical": "OIL_FILTER",
      "canonical_id": "part-uuid-111",
      "confidence": 0.85
    },
    {
      "text": "generator",
      "type": "equipment",
      "canonical": "GENERATOR",
      "canonical_id": "equipment-uuid-222",
      "confidence": 0.92
    }
  ],
  "cards": [
    {
      "type": "part",
      "title": "Lube Oil Filter",
      "part_id": "part-uuid-111",
      "name": "Lube Oil Filter",
      "part_number": "1R-0750",
      "manufacturer": "Caterpillar",
      "in_stock": 4,
      "location": "Engine Room Locker B",
      "actions": [
        {
          "label": "Check Stock",
          "action": "view_stock",
          "endpoint": "/v1/inventory/stock",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "part_id": "part-uuid-111"
          },
          "constraints": {}
        },
        {
          "label": "Order Part",
          "action": "order_part",
          "endpoint": "/v1/inventory/order-part",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "part_id": "part-uuid-111",
            "qty": ""
          },
          "constraints": {
            "requires_confirmation": true
          }
        },
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
      "type": "part",
      "title": "Oil Filter Element",
      "part_id": "part-uuid-112",
      "name": "Oil Filter Element",
      "part_number": "1R-0751",
      "manufacturer": "Caterpillar",
      "in_stock": 2,
      "location": "Engine Room Locker B",
      "actions": [
        {
          "label": "Check Stock",
          "action": "view_stock",
          "endpoint": "/v1/inventory/stock",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "part_id": "part-uuid-112"
          },
          "constraints": {}
        },
        {
          "label": "Order Part",
          "action": "order_part",
          "endpoint": "/v1/inventory/order-part",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "part_id": "part-uuid-112",
            "qty": ""
          },
          "constraints": {
            "requires_confirmation": true
          }
        },
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
      "type": "equipment",
      "title": "Generator 1",
      "equipment_id": "equipment-uuid-222",
      "actions": [
        {
          "label": "View History",
          "action": "view_history",
          "endpoint": "/v1/work-orders/history",
          "method": "GET",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-222"
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
            "equipment_id": "equipment-uuid-222",
            "title": "",
            "description": "",
            "priority": ""
          },
          "constraints": {
            "requires_equipment_id": true
          }
        },
        {
          "label": "Add Note",
          "action": "add_note",
          "endpoint": "/v1/notes/create",
          "method": "POST",
          "payload_template": {
            "yacht_id": "yacht-uuid-123",
            "equipment_id": "equipment-uuid-222",
            "note_text": ""
          },
          "constraints": {
            "requires_equipment_id": true,
            "requires_note_text": true
          }
        }
      ]
    }
  ],
  "metadata": {
    "entity_count": 2,
    "card_count": 3
  }
}
```

### Frontend Renders

```
┌─────────────────────────────────────────────────────────────────┐
│  🔧 Lube Oil Filter                                             │
│  ─────────────────────────────────────────────────────────────  │
│  Part Number: 1R-0750                                           │
│  Manufacturer: Caterpillar                                      │
│  In Stock: 4 units                                              │
│  Location: Engine Room Locker B                                 │
│                                                                 │
│  [Check Stock] [Order Part] [Add to Handover]                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  🔧 Oil Filter Element                                          │
│  ─────────────────────────────────────────────────────────────  │
│  Part Number: 1R-0751                                           │
│  Manufacturer: Caterpillar                                      │
│  In Stock: 2 units                                              │
│  Location: Engine Room Locker B                                 │
│                                                                 │
│  [Check Stock] [Order Part] [Add to Handover]                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ Generator 1                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Related equipment for this part search                         │
│                                                                 │
│  [View History] [Create Work Order] [Add Note]                 │
└─────────────────────────────────────────────────────────────────┘
```

### User Clicks "Order Part" (with confirmation required)

```http
POST /v1/actions/execute HTTP/1.1
Host: api.celeste7.ai
Authorization: Bearer eyJhbGci...
X-Yacht-Signature: 7f83b1657ff1fc53b...
Content-Type: application/json

{
  "action": "order_part",
  "payload": {
    "yacht_id": "yacht-uuid-123",
    "part_id": "part-uuid-111",
    "qty": 2
  }
}
```

---

## Error Handling

### Search Errors

```json
{
  "error": "invalid_request",
  "message": "Query cannot be empty",
  "status": 400
}
```

```json
{
  "error": "unauthorized",
  "message": "Invalid or expired JWT",
  "status": 401
}
```

```json
{
  "error": "yacht_mismatch",
  "message": "X-Yacht-Signature does not match JWT yacht_id",
  "status": 403
}
```

### Action Errors

```json
{
  "error": "action_not_found",
  "message": "Unknown action: invalid_action",
  "status": 400
}
```

```json
{
  "error": "validation_failed",
  "message": "Missing required field: equipment_id",
  "status": 422
}
```

```json
{
  "error": "constraint_violation",
  "message": "Action requires confirmation but was not confirmed",
  "status": 400
}
```

---

## Frontend Implementation Notes

### 1. Never Call Endpoints Directly

All mutations MUST go through `/v1/actions/execute`. Never call the endpoints in `action.endpoint` directly.

```typescript
// ❌ WRONG
fetch(action.endpoint, {
  method: action.method,
  body: JSON.stringify(filledPayload)
});

// ✅ CORRECT
fetch('/v1/actions/execute', {
  method: 'POST',
  body: JSON.stringify({
    action: action.action,
    payload: filledPayload
  })
});
```

### 2. Handle Action Constraints

Check `constraints` before enabling action buttons:

```typescript
const canExecute = (action: Action, formData: Record<string, any>) => {
  const constraints = action.constraints;

  if (constraints.requires_equipment_id && !formData.equipment_id) {
    return false;
  }
  if (constraints.requires_note_text && !formData.note_text) {
    return false;
  }
  if (constraints.requires_confirmation) {
    // Show confirmation dialog before executing
  }
  return true;
};
```

### 3. Pre-fill Payload Template

Use `payload_template` as starting values, let user fill empty strings:

```typescript
const fillPayload = (template: Record<string, any>, userInput: Record<string, any>) => {
  const filled = { ...template };
  for (const [key, value] of Object.entries(userInput)) {
    if (key in filled && value) {
      filled[key] = value;
    }
  }
  return filled;
};
```

### 4. Card Type Rendering

```typescript
const CardIcon: Record<CardType, string> = {
  equipment: '⚙️',
  document_chunk: '📄',
  work_order: '📋',
  fault: '🔴',
  part: '🔧',
  handover: '📝',
  predictive: '🔮'
};
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-11-21 | Initial contract with 3 worked examples |
