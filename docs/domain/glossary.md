# 📖 **glossary.md — CelesteOS Terminology**

**Version:** 1.0
**Owner:** Product & Engineering
**Status:** Approved

---

# # 🧱 **A — Core System Terms**

---

## **CelesteOS**

The cloud-first engineering intelligence system for yachts.
Acts as the vessel’s *brain* for documents, maintenance history, faults, inventory, and predictive insights.

---

## **Cloud Brain**

The central AI engine hosted in the cloud.
Responsible for:

* RAG
* GraphRAG
* embeddings
* indexing
* search
* predictive maintenance

All intelligence lives here — *never* locally.

---

## **Local Agent (Mac App)**

A macOS application installed on the yacht’s Mac Studio/Mac Mini.
It performs:

* NAS discovery
* SHA256 hashing
* chunking
* secure upload to cloud
* incremental sync
* auto-updating

Does *not* run AI or local search.

---

## **Yacht Signature**

A cryptographic identity assigned to each yacht.
Used to:

* authenticate uploads
* route documents into the correct tenant
* enforce per-yacht isolation
* bind all cloud resources to a specific vessel

---

## **Tenant / Yacht Tenant**

A segregated environment containing all data and documents for one yacht.
Includes:

* storage bucket
* Postgres schema
* vector index
* graph index
* API namespace

Prevents cross-yacht data access.

---

# # 🔡 **B — Document & Indexing Terms**

---

## **NAS (Network-Attached Storage)**

The yacht’s local file server.
Source of:

* manuals
* photos
* logs
* engineering documents

CelesteOS reads NAS data **read-only**.

---

## **SHA256**

Cryptographic fingerprint of a file.
Used for:

* integrity checking
* deduplication
* upload verification
* change detection

---

## **Chunk**

A split portion of a document used for:

* text processing
* embeddings
* search indexing

Chunks are usually 250–800 tokens.

---

## **Metadata Extraction**

Process of identifying:

* equipment mentions
* fault codes
* part numbers
* system names
* headings
* manufacturer keywords

Stored in each chunk’s metadata.

---

## **OCR**

Optical Character Recognition.
Used to extract text from:

* scanned PDFs
* images
* photographed documents

Performed in the cloud.

---

## **Embedding**

Numerical vector representation of text.
Used for semantic search (RAG).
Stored in pgvector.

---

## **Indexing Pipeline**

Cloud workflow that:

* verifies file integrity
* stores raw file
* extracts text
* chunks content
* embeds chunks
* builds graph nodes
* populates vector DB

n8n orchestrates; Python handles logic.

---

# # 🔍 **C — Search & AI Terms**

---

## **Universal Search Bar**

The single input field powering all user interaction.
Handles:

* document search
* notes
* fault diagnosis
* creating work orders
* predictive queries
* part discovery
* handover actions

Core interface of CelesteOS.

---

## **Entity Extraction**

Identifying structured entities in a query:

* equipment
* fault codes
* parts
* actions
* document types

Runs in Python microservice.

---

## **Intent Detection**

Infers user intention from query:

* diagnose fault
* create work order
* find document
* add to handover
* order part
* show predictive insight

Controls how the engine responds.

---

## **RAG (Retrieval-Augmented Generation)**

Semantic search technique that retrieves relevant document chunks using embeddings.

Used for:

* manual lookup
* fault code interpretation
* document Q&A
* handover summaries

---

## **GraphRAG**

Graph-based reasoning on:

* equipment
* faults
* parts
* historical links
* document references

Used for deeper research and predictive analysis.

---

## **Fusion Logic**

Combines:

* semantic search
* graph traversal
* metadata search
* structured queries

Produces final ranked results for UI.

---

## **Search Result Card**

Structured UI element returned by the search engine, containing:

* title
* preview text
* metadata
* micro-actions

Types: document, fault, part, work order, predictive, handover.

---

## **Micro-Action**

Contextual button attached to result cards:

* Create WO
* Add to Handover
* Open Document
* Order Part
* Show History
* View Predictive Risk

Determined by intent + entity type.

---

# # ⚓ **D — Maintenance & Operations Terms**

---

## **Equipment**

A system, subsystem, or component onboard the yacht:

* main engines
* generators
* stabilisers
* HVAC
* pumps
* electrical panels

Central element for linking faults, parts, and tasks.

---

## **Fault**

An engineering issue or error, often with a code:

* E047
* SPN/FMI
* “Overheat”

Linked to equipment and work orders.

---

## **Work Order (WO)**

Task created to:

* fix a fault
* perform scheduled maintenance
* record an intervention

Stored in PMS schema.

---

## **Work Order History**

Execution details of completed tasks:

* notes
* parts used
* time taken
* equipment affected
* steps performed

Indexed for RAG.

---

## **Part / Spare**

Inventory item used in repairs.
Includes:

* stock level
* minimum quantity
* location
* compatibility

Can be linked to equipment via graph.

---

## **Handover**

Document summarising engineering status during crew change.
Automatically generated by CelesteOS.

---

## **Handover Item**

Entry in a handover representing:

* fault
* work order
* note
* document snippet
* predictive insight

---

# # 🔮 **E — Predictive Maintenance Terms**

---

## **Predictive Maintenance**

System that uses:

* local history
* crew behaviour
* global knowledge
* graph analysis
* signals and scoring
  to predict upcoming failures.

---

## **Risk Score**

Value from **0.00 to 1.00** indicating likelihood of upcoming failure.

---

## **Global Knowledge Layer**

Federated scraped data including:

* forums
* OEM bulletins
* historical patterns
* known fault chains

Enhances predictions for yachts with limited history.

---

## **Crew Pain Index**

Metric derived from:

* repeated search queries
* notes
* mobile photos
* fault mentions

Signals rising crew concern.

---

## **Fault Cascade**

Chain of related events:

* cooling issue → overheat → shutdown
  GraphRAG models these patterns.

---

# # 🔐 **F — Security & Identity Terms**

---

## **Access Token (JWT)**

Short-lived token for authenticated actions.

---

## **Refresh Token**

Longer-lived token used to obtain new access tokens.

---

## **Signed URL**

Short-lived URL for accessing a secure file in object storage.

---

## **Row-Level Security (RLS)**

DB-level rule ensuring a user can only access rows belonging to their yacht.

---

## **Upload Queue**

Temporary record of files uploaded by the Local Agent awaiting indexing.

---

# # 🧩 **G — System Infrastructure Terms**

---

## **Supabase**

Managed Postgres + storage provider used for:

* structured data
* pgvector
* storage buckets

---

## **n8n**

Workflow orchestrator for:

* indexing pipeline
* cron tasks
* ingestion automation

---

## **Render.com**

Runs:

* entity extraction microservice
* search engine ML logic

---

## **Hetzner VPS**

Hosts:

* containers
* backend API
* reverse proxy
* monitoring stack

---

## **Object Storage**

Used for:

* raw NAS documents
* processed exports
* handover PDFs
* global scraped corpus

---

# # 🏁 **H — UX & Interaction Terms**

---

## **Universal Interface**

The concept that *everything* is done through the search bar.

---

## **Contextual UI**

UI that adapts dynamically based on:

* detected intent
* detected entities
* card type
* metadata level

---

## **Result Streaming**

Real-time streaming of:

* RAG answers
* cards
* suggestions
* micro-actions

Avoids blocking or waiting.

---

## **Deeper Research Mode**

User-activated mode enabling multi-hop GraphRAG for complex diagnosis.

---

## **Zero Menu Philosophy**

Navigation-free UX:
The user never hunts for screens — they search.

---

# # 🏁 **Conclusion**

This glossary defines all key concepts across:

* Architecture
* AI/ML
* UX
* DevOps
* Predictive maintenance
* Ingestion pipeline
* Data isolation

It ensures **shared language** across engineering, design, and product teams.

---
