# 🔍 **search-engine-spec.md — CelesteOS Search Engine Specification**

**Version:** 1.0
**Owner:** AI/Backend Engineering
**Status:** Approved For MVP

---

# # 🎯 **Purpose**

The CelesteOS search engine is the **core intelligence layer** powering the entire product.
Everything — work orders, handovers, fault diagnosis, inventory, documents — starts from a single search bar.

This document explains:

* how user queries are interpreted
* entity extraction
* intent detection
* RAG vs GraphRAG activation
* document retrieval
* fusion logic
* result card templates
* micro-actions
* streaming word-by-word UX
* multi-source search (NAS → cloud, emails, scraped data)
* backend regex → entity rules

This is NOT a workflow doc.
This is the engine specification.

---

# # 🧠 **1. Architecture Overview**

CelesteOS search engine = **Python microservice hosted on Render.com** behind the API gateway.

It performs:

* entity extraction
* intent detection
* semantic & hybrid search
* GraphRAG
* fusion
* card composition

n8n does NOT run AI logic — it only orchestrates indexing.

Supabase/Postgres stores:

* structured data (equipment, WOs, faults…)
* embeddings (pgvector)
* documents
* graph edges

The search engine interacts with Supabase via REST + SQL over RPC.

---

# # 🧩 **2. Query Interpretation Pipeline**

The engine processes every search input through **five core stages**:

1. **Text Cleaning**
2. **Entity Extraction (Python service)**
3. **Intent Detection**
4. **RAG Retrieval** (vector + metadata)
5. **Graph RAG Retrieval** (multi-hop)
6. **Fusion + Ranking**
7. **Result Card Generator**
8. **Micro-Action Generator**

Each stage is deterministic and explainable.

---

# # 🔠 **3. Entity Extraction**

### **3.1 Hosted in Python on Render.com**

We use a small Python FastAPI service on Render.com.

Why not n8n?

* n8n is slow for token-level operations
* n8n workflows are not meant to run low-latency NLP
* Regex + ML models run best in Python environments
* search requires sub-250ms response
* streaming output

Thus:

### **Frontend → Cloud API → Python Microservice → API → Supabase Retrieval**

---

### **3.2 What Entities We Extract**

**Regex + ML hybrid.**
Regex handles precision, ML handles fuzzy.

We detect:

| Entity             | Examples                                      |
| ------------------ | --------------------------------------------- |
| **equipment**      | “main engine”, “starboard gen”, “chiller 3”   |
| **fault_code**     | “E047”, “SPN 123”, “FMI 4”                    |
| **part_number**    | “2040N2”, “01-234567”                         |
| **action_word**    | “fix”, “replace”, “diagnose”, “find document” |
| **document_type**  | “manual”, “drawing”, “handover”, “invoice”    |
| **intent_markers** | “add to handover”, “create work order”        |
| **system_names**   | “black water tank”, “HVAC”                    |
| **date/time**      | “last week”, “July handover”                  |
| **severity**       | “emergency”, “critical”, “urgent”             |
| **location**       | “engine room”, “aft locker”                   |

Entities feed into intent.

---

# # 🎯 **4. Intent Detection**

Using entity + verb logic:

Examples:

---

### **Intent: diagnose_fault**

Query:

> “fault code E047 on main engine”

Detected:

* fault_code = E047
* equipment = “main engine”

---

### **Intent: find_document**

Query:

> “find CAT 3516 coolant manual”

---

### **Intent: create_work_order**

Query:

> “create a work order for stabiliser pump leak”

---

### **Intent: add_to_handover**

Query:

> “add this to handover”

---

### **Intent: find_part**

Query:

> “racor 2040 filter for gen 1”

---

### **Intent: general_search**

Fallback for ambiguous queries.

---

### **Intent: predictive_request**

Query:

> “is anything likely to fail soon?”
> “weak systems in HVAC?”

---

### **Intent determines Which RAG Mode is activated.**

---

# # 🔍 **5. RAG Modes (Semantic Retrieval)**

### **5.1 Standard RAG — default search**

Used when the query mentions:

* equipment
* document
* parts
* notes
* work orders
* general info

Process:

1. Generate embedding from query text
2. Query pgvector table `document_chunks`
3. Filter by:

   * yacht_id
   * equipment_id (if known)
   * document_type
4. Return top-K results (K = 8–15)
5. Format as cards

---

### **5.2 Multi-source RAG**

Combine:

* document chunks
* work order history
* faults
* emails
* Celeste scraped global knowledge

Return 2–4 top results from each domain.

---

# # 🕸️ **6. Graph RAG (Deep Research Mode)**

Activated when:

* user triggers “Deeper Research Mode”
* query requires multi-hop reasoning
* confidence of standard RAG is low
* intent = predictive
* multiple entities detected

### Graph traversal targets:

* equipment
* relevant faults
* part relationships
* historical patterns
* related docs
* cluster analysis

### Example:

Query:

> “recurring stabiliser issues this year”

GraphRAG explores:

* all faults linked to stabiliser
* all work orders touching stabiliser system
* all relevant parts
* all doc chunks with “stabiliser” references

Outputs aggregated insights.

---

# # 🔄 **7. Fusion Logic (Combining Agents)**

CelesteOS uses **hybrid fusion**:

### Inputs:

* Standard RAG results
* Graph RAG results
* Entity hit scores
* Metadata matches
* Manual filters (document_type, equipment_id)

### Ranking Boosts:

* equipment match
* fault code match
* part-number match
* recent history
* exact term match

### Ranking Penalties:

– long irrelevant chunks
– mismatched equipment
– out-of-date docs
– low semantic similarity

Final output is a sorted list **converted into Search Result Cards**.

---

# # 🧩 **8. Result Card Templates**

Search results do NOT return raw text.
They return structured **cards**.

Types:

### **8.1 Document Chunk Card**

```json
{
  "type": "document_chunk",
  "title": "CAT 3516 Cooling System",
  "document_id": "uuid",
  "chunk_index": 5,
  "page_number": 34,
  "text_preview": "...",
  "actions": ["open_document", "add_to_handover"]
}
```

---

### **8.2 Fault Card**

```json
{
  "type": "fault",
  "fault_code": "E047",
  "equipment_id": "uuid",
  "summary": "Overheating event detected multiple times"
}
```

---

### **8.3 Work Order Card**

```json
{
  "type": "work_order",
  "title": "Replace coolant temp sensor",
  "status": "completed",
  "actions": ["view", "add_to_handover"]
}
```

---

### **8.4 Part Card**

```json
{
  "type": "part",
  "name": "Racor 2040 Filter",
  "in_stock": 6,
  "location": "Engine Room Locker A",
  "actions": ["add_to_work_order", "order_part"]
}
```

---

### **8.5 Predictive Insight Card**

```json
{
  "type": "predictive",
  "equipment": "HVAC",
  "risk_score": 0.74,
  "summary": "HVAC compressor shows repeat high-pressure faults"
}
```

---

# # 🎛️ **9. Micro-Action Generator**

Based on:

* entities
* intent
* card type

Dynamically attaches:

| Action                  | Trigger                               |
| ----------------------- | ------------------------------------- |
| Create Work Order       | equipment detected + fault or symptom |
| Add to Handover         | any technical info                    |
| Open Document           | document chunk card                   |
| Order Part              | part card                             |
| View History            | equipment identified                  |
| Show Predictive Insight | equipment match                       |
| Add Note                | user-driven                           |
| Attach Photo            | mobile only                           |

Micro-actions must be:

* context aware
* simple
* never more than 2–4 buttons

---

# # 📡 **10. Multi-Source Search Integration**

Search hits come from:

### **10.1 NAS Documents (via cloud storage)**

* Already indexed → document_chunks in pgvector

### **10.2 Emails**

* `email_messages` embeddings
* attachments stored + indexed

### **10.3 Celeste Global Knowledge**

* fallback when local docs insufficient

### **10.4 Structured Data**

Direct Postgres queries:

* equipment table
* parts
* faults
* work orders

The engine merges them.

---

# # 🟦 **11. Streaming Input + Streaming Output**

### **11.1 Input Streaming**

As user types, frontend sends:

```
/v1/search?partial=true
```

Engine runs:

* light entity extraction
* lightweight similarity search

Used for:

* auto-complete
* quick previews
* suggested actions (“Create WO?”, “Open manual?”)

---

### **11.2 Output Streaming**

Full search returns:

* streamed tokens
* streamed cards
* streamed micro-actions

UI updates in real time:
“No thinking… just showing.”

---

# # 🧮 **12. Backend Regex Safety Rules**

To avoid hallucinations, backend enforces **hard regex validation**:

* Fault codes must match known patterns
* Equipment must map to exact `equipment.name`
* Part numbers validated against table
* Document types validated against allowed set
* No unsupported actions generated
* If entity uncertain → ask clarifying Q

**CelesteOS never guesses.**

If ambiguity ≥ threshold:

> “Did you mean the starboard generator or port generator?”

---

# # 🔌 **13. Interactions with Supabase**

### **13.1 Vector Search**

`SELECT * FROM document_chunks ORDER BY embedding <-> query_embed LIMIT 10;`

### **13.2 Metadata Filters**

Apply filters via RLS-secured RPC.

### **13.3 Graph Queries**

Pull from:

* `graph_nodes`
* `graph_edges`

Perform BFS/DFS up to depth 3.

### **13.4 Structured Search**

Used for non-RAG tasks:

* “show inventory”
* “hours of rest”
* “purchase history”

---

# # 🧬 **14. How The UX Dynamically Adapts**

The UI changes based on:

* entity type
* intent
* confidence
* card type

Examples:

**Query:** “racor filter 2040”
→ show part card + inventory count + “Order Part”

**Query:** “fault 123 main engine”
→ show fault details + manual page + create WO

**Query:** “handover items”
→ show handover draft + add-options

**Query:** “E047 history”
→ show aggregated fault timeline

Every UI component derives from backend intent.

---

# # 🧱 **15. Summary**

The CelesteOS search engine:

* interprets natural language
* extracts entities
* identifies intent
* combines RAG + GraphRAG
* ranks + fuses results
* outputs structured cards
* attaches context-aware micro-actions
* streams UI updates
* ensures safety via regex + backend validation

It is the **central intelligence layer** of the system, powering the “one search bar” philosophy.

---