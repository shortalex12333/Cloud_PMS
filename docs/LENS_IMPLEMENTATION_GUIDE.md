# CELESTE Lens Implementation Guide
**For Frontend Workers**
**Date**: 2026-02-08
**Main Branch**: `81cd9d3` (feat: auto-link attachments to thread's confirmed objects)

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [The Pipeline Flow](#2-the-pipeline-flow)
3. [Domain Detection & Microactions](#3-domain-detection--microactions)
4. [Data Type Serialization (RAG Output)](#4-data-type-serialization-rag-output)
5. [Lens Reference: Query Examples](#5-lens-reference-query-examples)
6. [API Endpoints](#6-api-endpoints)
7. [Current Status by Lens](#7-current-status-by-lens)

---

## 1. Architecture Overview

CELESTE is a **RAG (Retrieval-Augmented Generation)** system, NOT a general AI. It answers questions from **yacht data only**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                     │
│                    "show me open work orders"                            │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      WORKER 1: DETECTIVE                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐ │
│  │ Domain Detection │  │ Intent Detection │  │ Entity Extraction (NER) │ │
│  │ work_order (0.9) │  │ READ (0.95)      │  │ status=open             │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      f1_search_fusion (SQL)                              │
│  - Generates query embedding (OpenAI text-embedding-3-small, 1536 dim)  │
│  - Searches search_index with domain boost                               │
│  - Returns top-K results with final_score                                │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      RESPONSE ASSEMBLY                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐ │
│  │ Results (cards)  │  │ Context (meta)   │  │ Actions (microactions)  │ │
│  │ [WO objects...]  │  │ domain, intent   │  │ [view_work_order, ...]  │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                         │
│  - Renders result cards by type                                          │
│  - Shows microaction buttons based on role                               │
│  - Opens lens view on card click                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Pipeline Flow

### 2.1 Search Endpoint (`POST /search`)

**Request:**
```json
{
  "query": "show me open work orders",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "type": "work_order",
      "object_id": "uuid-here",
      "title": "WO #1006 - Steering System Inspection",
      "payload": { ... },
      "score": 0.87
    }
  ],
  "context": {
    "domain": "work_order",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.95,
    "mode": "focused"
  },
  "actions": [
    {
      "action": "view_work_order",
      "label": "View Work Order",
      "prefill": { "work_order_id": "uuid-here" }
    }
  ]
}
```

### 2.2 RAG Endpoint (`POST /api/rag/answer`)

**Request:**
```json
{
  "query": "what work orders are open",
  "top_k": 5,
  "debug": true
}
```

**Response:**
```json
{
  "answer": "The following work orders are currently open:\n- WO 1006: Steering System Inspection [1]\n- WO 1001: Generator Oil Change [2]",
  "citations": [
    {"doc_id": "uuid", "doc_type": "work_order", "title": "WO 1006"}
  ],
  "confidence": 0.85,
  "signals": {
    "domain": "work_order",
    "chunks_used": 5,
    "latency_ms": 2100
  }
}
```

---

## 3. Domain Detection & Microactions

### 3.1 How Domain Detection Works

The system uses **compound anchors** - multi-word patterns that identify domains with high confidence.

| Domain | Example Anchors |
|--------|----------------|
| `hours_of_rest` | "rest hours", "work hours", "monthly sign-off", "log my hours" |
| `work_order` | "work order", "maintenance task", "repair job" |
| `equipment` | "equipment status", "machine", "main engine" |
| `part` / `inventory` | "spare part", "part number", "stock level" |
| `fault` | "fault report", "defect", "issue" |
| `document` | "manual", "document", "PDF" |
| `receiving` | "shipment", "delivery", "receiving" |

### 3.2 How Intent Detection Works

| Intent | Trigger Patterns | Example Query |
|--------|-----------------|---------------|
| `READ` | show, view, list, check, what, who | "show me open faults" |
| `CREATE` | create, add, new, log, report | "create work order for pump" |
| `UPDATE` | update, edit, modify, change | "update work order status" |
| `APPROVE` | sign, approve, acknowledge | "sign monthly hours" |
| `DELETE` | delete, remove | "delete draft receiving" |
| `EXPORT` | export, download, print | "export rest hours report" |

### 3.3 Microaction Registry

Each `(domain, intent)` pair maps to available actions:

```
(work_order, READ) → [view_work_order, view_history, show_checklist]
(work_order, CREATE) → [create_work_order]
(work_order, UPDATE) → [update_status, add_note, add_photo, assign_task]

(hours_of_rest, READ) → [view_hours_of_rest, check_compliance]
(hours_of_rest, APPROVE) → [sign_hours_of_rest]
(hours_of_rest, UPDATE) → [update_hours_of_rest]

(equipment, READ) → [view_equipment, view_maintenance_history, view_parts, view_faults, open_manual]
(part, READ) → [view_part_details, view_usage_history]
(fault, READ) → [view_fault, view_fault_history]
```

---

## 4. Data Type Serialization (RAG Output)

When RAG retrieves data, each object type is serialized differently for the LLM context.

### 4.1 Hours of Rest

**Database fields → Serialized text:**
```
{
  "date": "2026-01-25",
  "total_rest_hours": 7.0,
  "violation_status": "non-compliant",
  "signoff_status": "pending",
  "crew_name": "John Deckhand"
}
```
↓
```
Hours of Rest - Jan 25, 2026 | Total Rest: 7.0h | Violation: non-compliant | Signoff: pending | Crew Member: John Deckhand
```

### 4.2 Work Order

**Database fields → Serialized text:**
```
{
  "code": "1006",
  "title": "Steering System Inspection",
  "status": "open",
  "priority": "high",
  "equipment_name": "Steering System",
  "assignee_name": "Chief Engineer"
}
```
↓
```
WO #1006 | Title: Steering System Inspection | Status: open | Priority: high | Equipment: Steering System | Assigned to: Chief Engineer
```

### 4.3 Equipment

**Database fields → Serialized text:**
```
{
  "name": "Main Engine",
  "serial_number": "ME-2024-001",
  "manufacturer": "Caterpillar",
  "model": "C32",
  "location": "Engine Room",
  "status": "operational"
}
```
↓
```
Equipment: Main Engine | Serial: ME-2024-001 | Manufacturer: Caterpillar | Model: C32 | Location: Engine Room | Status: operational
```

### 4.4 Part / Inventory

**Database fields → Serialized text:**
```
{
  "part_number": "CAT-FLT-001",
  "name": "Oil Filter",
  "on_hand": 5,
  "min_level": 3,
  "location": "Bin A-12",
  "unit": "pcs"
}
```
↓
```
Part: CAT-FLT-001 | Name: Oil Filter | On Hand: 5 pcs | Min Level: 3 | Location: Bin A-12
```

### 4.5 Fault

**Database fields → Serialized text:**
```
{
  "code": "E031",
  "title": "AIS Intermittent Signal",
  "status": "open",
  "priority": "medium",
  "equipment_name": "Navigation System",
  "reported_by": "Captain"
}
```
↓
```
Fault E031 | Title: AIS Intermittent Signal | Status: open | Priority: medium | Equipment: Navigation System | Reported by: Captain
```

### 4.6 Document

**Database fields → Serialized text:**
```
{
  "title": "Furuno_1835_Operator_Manual.pdf",
  "doc_type": "manual",
  "size": 2500000,
  "equipment_id": "nav-radar-001"
}
```
↓
```
Document: Furuno_1835_Operator_Manual.pdf | Type: manual | Size: 2.5MB | Linked to: nav-radar-001
```

---

## 5. Lens Reference: Query Examples

### 5.1 Hours of Rest Lens

| Query | Expected Result |
|-------|-----------------|
| "show rest violations" | List of crew with non-compliant rest |
| "who needs monthly sign-off" | Crew pending captain approval |
| "my rest hours this week" | Current user's rest records |

**Try these (production API):**
```bash
# Query 1: Violations
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "rest violations", "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"}'

# Query 2: Sign-off status
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "monthly sign off pending"}'

# Query 3: Crew rest
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "show crew rest hours"}'
```

### 5.2 Work Order Lens

| Query | Expected Result |
|-------|-----------------|
| "open work orders" | All work orders with status=open |
| "work orders for main engine" | WOs linked to main engine |
| "high priority tasks" | Urgent maintenance tasks |

**Try these:**
```bash
# Query 1: Open WOs
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "open work orders"}'

# Query 2: Equipment specific
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "work orders steering system"}'

# Query 3: Priority filter
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "urgent maintenance tasks"}'
```

### 5.3 Equipment Lens

| Query | Expected Result |
|-------|-----------------|
| "main engine status" | Equipment details + status |
| "equipment needing maintenance" | Items with overdue service |
| "navigation equipment" | All nav-related equipment |

**Try these:**
```bash
# Query 1: Status check
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "main engine status"}'

# Query 2: Maintenance due
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "equipment needing maintenance"}'

# Query 3: Category
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "show navigation equipment"}'
```

### 5.4 Parts / Inventory Lens

| Query | Expected Result |
|-------|-----------------|
| "low stock parts" | Parts below min level |
| "oil filters" | All oil filter parts |
| "parts for generator" | Parts linked to generator |

**Try these:**
```bash
# Query 1: Low stock
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "parts low in stock"}'

# Query 2: Part search
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "oil filters"}'

# Query 3: Equipment parts
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "spare parts for main engine"}'
```

### 5.5 Fault Lens

| Query | Expected Result |
|-------|-----------------|
| "open faults" | Unresolved fault reports |
| "faults on navigation" | Nav equipment faults |
| "critical issues" | High priority faults |

**Try these:**
```bash
# Query 1: Open faults
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "unresolved faults"}'

# Query 2: Equipment faults
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "faults on radar"}'

# Query 3: Priority
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "critical faults"}'
```

### 5.6 Document Lens

| Query | Expected Result |
|-------|-----------------|
| "watermaker manual" | Watermaker equipment manual |
| "engine documentation" | Engine-related docs |
| "safety procedures" | Safety procedure docs |

**Try these:**
```bash
# Query 1: Equipment manual
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "watermaker manual"}'

# Query 2: Category docs
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "engine documentation"}'

# Query 3: Doc type
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -d '{"query": "safety procedures PDF"}'
```

---

## 6. API Endpoints

### Production URLs

| Endpoint | URL | Method |
|----------|-----|--------|
| Search | `https://pipeline-core.int.celeste7.ai/search` | POST |
| RAG Answer | `https://pipeline-core.int.celeste7.ai/api/rag/answer` | POST |
| RAG Health | `https://pipeline-core.int.celeste7.ai/api/rag/health` | GET |

### Authentication

All requests require:
```
Authorization: Bearer <JWT_TOKEN>
```

For yacht-scoped requests, JWT contains `yacht_id` claim. For testing, use header:
```
X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598
X-Role: captain
```

---

## 7. Current Status by Lens

| Lens | Search | RAG | Frontend | Data |
|------|--------|-----|----------|------|
| **Hours of Rest** | ✅ 100% | ✅ Working | ⚠️ Partial | ✅ Populated |
| **Work Order** | ✅ 100% | ✅ Working | ⚠️ Partial | ✅ Populated |
| **Equipment** | ✅ 100% | ✅ Working | ⚠️ Partial | ✅ Populated |
| **Parts** | ✅ 100% | ✅ Working | ❌ Not built | ⚠️ Sparse |
| **Inventory** | ✅ 100% | ✅ Working | ❌ Not built | ⚠️ Sparse |
| **Fault** | ✅ 100% | ✅ Working | ❌ Not built | ✅ Populated |
| **Document** | ✅ 100% | ✅ Working | ⚠️ Partial | ✅ Populated |
| **Receiving** | ⚠️ Weak | ❓ Untested | ❌ Not built | ⚠️ Sparse |
| **Certificate** | ⚠️ Weak | ❓ Untested | ❌ Not built | ❌ Empty |
| **Crew** | ⚠️ Weak | ❓ Untested | ❌ Not built | ⚠️ Sparse |

### Legend
- ✅ Complete and working
- ⚠️ Partial / needs work
- ❌ Not implemented
- ❓ Not tested

---

## 8. Key Files Reference

| File | Purpose |
|------|---------|
| `apps/api/domain_microactions.py` | Domain detection, intent detection, microaction registry |
| `apps/api/rag/context_builder.py` | Serializers for each data type, embedding generation |
| `apps/api/rag/answer_generator.py` | GPT answer generation with citations |
| `apps/api/pipeline_service.py` | Main API service, search endpoint |
| `apps/api/routes/rag_endpoint.py` | RAG answer endpoint |

---

## 9. Testing Checklist for Frontend Workers

Before building a lens view:

1. **Verify search works:**
   ```bash
   curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query": "<your domain query>", "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"}'
   ```

2. **Check domain detection:**
   - Response should have `context.domain` matching your lens
   - Response should have `context.intent` = READ for view queries

3. **Check microactions:**
   - Response should have `actions` array with relevant buttons
   - Actions should match user role

4. **Check result payload:**
   - `results[].payload` contains the data for your card
   - All expected fields are present

5. **Test RAG:**
   ```bash
   curl -X POST "https://pipeline-core.int.celeste7.ai/api/rag/answer" \
     -H "Authorization: Bearer $TOKEN" \
     -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
     -d '{"query": "<your question>", "debug": true}'
   ```

---

*Generated by Claude Code - 2026-02-08*
