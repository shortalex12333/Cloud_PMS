## **action-routing-workflow.md**

**CelesteOS — Intent Routing, Action Determination & RAG Display Logic**

This document defines how CelesteOS interprets user queries, determines intent, selects which retrieval pipelines to activate (RAG / GraphRAG / metadata filters), and generates action buttons that the frontend can execute.

This is the core UX flow behind the “One Search Bar”.

---

# ## 1. Overview

The workflow follows this deterministic sequence:

```
User Query
    ↓
Entity Extraction (regex + fuzzy + domain lists)
    ↓
Intent Detection (rule-based)
    ↓
Routing Engine (decide which pipelines run)
    ↓
RAG + GraphRAG + Metadata Fusion
    ↓
Action Generator (contextual micro-actions)
    ↓
Frontend receives structured card blocks
```

The frontend **never guesses** and never performs regex.
Every decision is made by the backend search engine microservice.

---

# ## 2. Entity Extraction

### 2.1 Inputs

* Raw query text
* Yacht-specific ontology
* Equipment list
* Fault codes
* Part numbers
* Document types
* Action verbs

### 2.2 Extraction Tools

1. **Regex rules**
   For matches like:

   * fault codes: `F[0-9]{3}|E[0-9]+`
   * part numbers: `\b[0-9A-Z\-]{6,}\b`
   * WO references: `wo[- ]?[0-9]+`
   * date directives: “today”, “this week”, “urgent”, etc.

2. **Fuzzy matching**
   Using RapidFuzz to match:

   * equipment names
   * manufacturer names
   * system names
   * document types (“manual”, “SOP”, “handover”)

3. **Yacht local dictionary**
   Built during indexing, containing:

   * equipment names
   * model numbers
   * common abbreviations (“MEGBX” → “Main Engine Gearbox”)

### 2.3 Output

```json
{
  "entities": {
    "equipment": "...",
    "equipment_id": "...",
    "fault_code": "...",
    "document_type": "...",
    "action_verb": "add",
    "part_number": "...",
    "system": "HVAC"
  },
  "confidence": 0.91
}
```

---

# ## 3. Intent Detection

Intent is determined **after entity extraction**.

### 3.1 Rule sources

* action verbs (“add”, “show”, “find”, “diagnose”, “order”)
* entities present (equipment? fault? part?)
* which nouns appear (doc? manual? SOP?)
* context words (“why is”, “how to”, “create”)

### 3.2 Core Intents

* `find_document`
* `diagnose_fault`
* `find_part`
* `add_note`
* `create_work_order`
* `add_to_handover`
* `predictive_overview`
* `equipment_history`
* `general_search`

### 3.3 Example

Query:

> “add note to main engine gearbox saying leak found”

Extracted:

* verb: “add”
* entity: equipment = main engine gearbox

Intent:

```
"add_note"
```

---

# ## 4. Routing Engine

This decides **which pipelines activate**.

### 4.1 Inputs

* intent
* extracted entities
* yacht_id
* known equipment
* fault metadata

### 4.2 Pipeline Activation

| Intent              | RAG | GraphRAG | Metadata Filters    |
| ------------------- | --- | -------- | ------------------- |
| find_document       | ✔   | optional | strong              |
| diagnose_fault      | ✔   | ✔        | strong              |
| find_part           | ✔   | ✔        | medium              |
| add_note            | ✖   | ✔        | strong              |
| create_work_order   | ✖   | ✔        | strong              |
| predictive_overview | ✖   | ✖        | ✔ predictive engine |
| equipment_history   | ✔   | ✔        | strong              |
| general_search      | ✔   | optional | weak                |

### 4.3 Example Routing

Query:

> “fault code e122 main engine”

Routing:

* Entities: fault_code = E122, equipment = main engine
* Intent: diagnose_fault
* Activate:

  * RAG → find docs mentioning E122
  * GraphRAG → find fault → part → system links
  * Metadata filters → limit by yacht + equipment class

---

# ## 5. Retrieval Stage (RAG + GraphRAG)

### 5.1 RAG

Vector search in:

* document_chunks
* notes
* work_order_history

### 5.2 GraphRAG

Graph search in:

* equipment → faults
* parts → systems
* symptoms → likely causes
* historical co-occurrence links

Depth: 1–3 hops.

### 5.3 Fusion

Combine:

1. entity matches
2. vector similarity
3. graph relevance
4. metadata rules
5. recency boost
6. equipment-specific boost

Final result = sorted card list.

---

# ## 6. Card Generator

Every search query yields **cards**, not plain text.

Card types include:

* DocumentCard
* EquipmentCard
* FaultCard
* WorkOrderCard
* PartCard
* PredictiveCard
* HandoverCard
* ActionCard

Example:

```json
{
  "card_type": "equipment",
  "title": "Main Engine Gearbox",
  "fields": {
    "last_service": "2024-10-01",
    "recent_faults": ["E122", "E401"],
    "related_parts": ["Seal Kit"]
  }
}
```

---

# ## 7. Micro-Action Generation

**This is the key point you asked about.**

Actions are **not guessed by frontend**.
They are injected by the backend based on:

* intent
* card type
* extracted entities
* context rules

### 7.1 Micro-actions are defined in the backend:

Examples:

| Card Type  | Possible Actions                          |
| ---------- | ----------------------------------------- |
| Equipment  | Add Note, Create Work Order, View History |
| Document   | Open Document, Add to Handover            |
| Fault      | Diagnose, Add Note, View Related Docs     |
| Part       | Order Part, View Stock                    |
| Predictive | Add to Handover, View Equipment           |

### 7.2 Example Action JSON

```json
{
  "label": "Add Note",
  "action": "add_note",
  "endpoint": "/v1/notes/create",
  "payload_template": {
    "yacht_id": "<yid>",
    "equipment_id": "<uuid>",
    "note_text": ""
  }
}
```

---

# ## 8. Frontend Flow

Frontend receives each card + micro-actions.

### **Frontend Responsibilities**

* display cards
* show action buttons
* open modal if needed
* collect user input
* POST payload to backend **exactly as defined**

### **Frontend does NOT**

* perform regex
* guess intent
* determine endpoints
* build dynamic URLs
* look up equipment IDs

All backend responsibilities.

---

# ## 9. Example Full Flow

Query:

> “open manual for starboard generator”

**Step 1 — Entity Extraction**
→ equipment = starboard generator
→ doc type = manual

**Step 2 — Intent**
`find_document`

**Step 3 — Routing**

* RAG for documents
* GraphRAG for generator parts
* metadata: doc_type=manual

**Step 4 — Fusion**
Top docs + related equipment

**Step 5 — Actions**
For DocumentCard:

```
Open Document
Add to Handover
```

**Step 6 — Frontend**
Shows:

* top manual
* “Open Document” button
* clicking → GET `/public/documents/<signed-url>`

---

# ## 10. Why This Architecture Wins

### ⭐ Predictable

Every query goes through the same pipeline.

### ⭐ Extendable

Add new actions or card types without touching frontend.

### ⭐ Safe

Role and yacht isolation enforced centrally.

### ⭐ Fast

Routing avoids RAG when not needed.

### ⭐ Intuitive

One search bar → everything.

---

# ## 11. Summary

The pipeline is:

```
Query
 → Entity Extraction
 → Intent Detection
 → Routing (RAG / GraphRAG / Metadata)
 → Fusion
 → Cards
 → Actions
 → Frontend
 → User Action
 → Backend Endpoint
 → n8n
 → Supabase
```

Regex is used **inside entity extraction**, never in the frontend.

The “route” decision framework is simple, deterministic, and driven by extracted entities → intent → routing table.

---
