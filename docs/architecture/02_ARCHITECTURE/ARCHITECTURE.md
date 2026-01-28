Understood.
Here is **architecture.md**, written at a professional engineering standard and ready to drop into GitHub *as-is*.

If you want a diagram version (Mermaid or Draw.io), I can generate that after.

---

# 🏗️ **architecture.md — CelesteOS System Architecture**

## **Version:** 1.0

## **Owner:** Engineering

## **Status:** Draft (MVP Approved)

---

# # 🎯 **Overview**

CelesteOS is a **cloud-first, AI-driven engineering intelligence system** for yachts.
All computation, RAG, embeddings, graph reasoning, and predictive analysis occur in the cloud.
Onboard hardware acts purely as a **gateway** to discover NAS documents and securely upload them.

The entire user interface (mobile + desktop) is powered by a **universal search bar** which triggers entity extraction, dynamic UI cards, and micro-actions.

---

# # 🧱 **High-Level Architecture Components**

CelesteOS consists of four major subsystems:

1. **Onboard Local Agent (Mac App)**
2. **Cloud Core (API, RAG Engine, Vector DB, Graph DB, Storage)**
3. **Frontend Applications (Mobile + Web)**
4. **Global Celeste Knowledge Layer (External scraped corpus)**

Each subsystem communicates through secure APIs and isolated per-yacht environments.

---

# # 🟦 **1. Onboard Local Agent (Mac App)**

**Purpose:**
A lightweight daemon that monitors the yacht’s NAS, extracts metadata, computes file hashes, and uploads documents to the cloud.

This agent **does not run inference**, vector search, or embeddings.

### **Responsibilities**

* Connect to NAS via SMB/NFS
* Discover all documents + metadata
* Compute SHA256 for dedupe + integrity
* Chunk + compress large files
* Queue and upload files to the cloud
* Resume interrupted uploads
* Authenticate using yacht signature
* Auto-update silently
* Log status and errors
* Provide a small onboarding GUI

### **Local Agent Workflow**

**NAS → Local Agent → Cloud Storage → Indexing Pipeline**

The agent is *eventual consistency* — it continuously scans for changes and uploads deltas.

---

# # 🟧 **2. Cloud Core Architecture**

The cloud is the **true brain** of CelesteOS.

It consists of:

### **2.1 API Gateway**

* Handles requests from mobile, web, and local agent
* Authenticated by user tokens and yacht signature
* Routes to specific microservices
* Rate limits and logging

### **2.2 Object Storage (S3 / MinIO)**

* Stores raw documents from NAS
* Stores manual pages, email exports, photos
* Stores all handover exports
* Buckets isolated per yacht

### **2.3 Postgres (Primary DB)**

* All structured data:

  * equipment
  * work orders
  * history
  * faults
  * inventory
  * handovers
  * hours of rest
  * event logs
  * yacht signatures
* Optional schema-per-yacht isolation

### **2.4 Vector DB (pgvector or Qdrant)**

* All document chunks
* All embedded work order history
* All email bodies
* All global scraped data
* Provides similarity search for RAG

### **2.5 Graph Layer**

* `graph_nodes` and `graph_edges` tables
* Maps relationships:

  * equipment → parts
  * faults → documents
  * history → components
  * global data → local models
* Supports GraphRAG pathways for deeper research

### **2.6 Embedding + Indexing Pipeline**

Runs inside a cloud worker service.

Responsibilities:

* OCR with consistent settings
* Final chunking (after optional local pre-split)
* Embeddings (single model across entire fleet)
* Metadata extraction (equipment names, part numbers, fault codes)
* Graph building (pattern extraction)
* Deduplication
* Re-index management

### **2.7 Search Engine**

* Intent detection (entity extraction)
* Semantic search via vector DB
* Graph traversal for deeper mode
* Fusion ranking
* Result card generation
* Action mapping (micro-actions)

---

# # 🟩 **3. Frontend Applications (Web + Mobile)**

## **3.1 Universal Search Bar (Core UI)**

Everything is initiated through the search bar.

Under the hood:

* Entity extraction
* Intent classification
* Context-aware micro-actions
* RAG response fusion
* Graph reasoning (if deeper mode triggered)

### **Search Input → JSON Output**

Example:

```json
{
  "action": "diagnose_fault",
  "equipment": "CAT 3516C main engine",
  "fault_code": "E047",
  "intent": "find_docs_and_history",
  "contextual_entities": {...}
}
```

UI uses this to render:

* Cards
* Buttons
* Raw answer text
* Additional suggestions

---

## **3.2 Mobile App (iOS/Android)**

Architecture:

* React Native or Swift/Kotlin
* Auth via yacht signature + user token
* Calls cloud API only
* No local inference
* No local DB (only small offline cache)

Features:

* Search everything
* Add to handover
* Create work order
* Upload photos (auto-indexed)
* Barcode scanning
* Notes & voice-to-text

---

## **3.3 Web App (Vercel)**

For fleet managers / engineers.

Features:

* Same search bar
* Predictive dashboards
* Work orders list
* Fleet overview
* Handover management

Serverless pages → Cloud API.

---

# # 🟥 **4. Global Celeste Knowledge Layer**

A separate knowledge corpus maintained by CelesteOS.

Contains:

* Manufacturer manuals
* Bulletins
* Forum Q&A
* Common failures
* General engineering patterns
* Industry documentation

This is indexed into:

* `celeste_documents`
* `celeste_chunks`

Used for:

* backfilling weak data on yachts
* cross-vessel transfer learning
* benchmarking predictive maintenance

Isolated from yacht data; no crossover except inference.

---

# # 🔄 **End-to-End Data Flow (NAS → Cloud → User)**

Here is the core operational pipeline:

### **Step 1: Local Agent**

* Scans NAS
* Hashes files
* Uploads documents
* Tags with yacht signature

### **Step 2: Cloud Storage**

* Raw file stored
* SHA256 verified

### **Step 3: Indexing Pipeline**

* OCR
* Chunking
* Embedding
* Metadata extraction
* Graph linkage
* Stores chunks in vector DB
* Stores structured metadata in Postgres

### **Step 4: Search**

User types query →

* Entity extraction
* Intent detection
* Vector search
* Graph traversal (optional deeper mode)
* Retrieve chunks, docs, faults, parts
* Fusion + card generation

### **Step 5: Micro Actions**

User taps one of:

* Create work order
* Add to handover
* Open manual
* Show history
* Order part
* Add comment
* Predictive insight

### **Step 6: Writes Back**

Operations stored in:

* work_orders
* handover_drafts
* notes
* history
* hours_of_rest
* purchase logs

---

# # 🌐 **Network & Isolation Model**

### **Per-yacht isolation**

* Dedicated S3 bucket or bucket prefix
* Dedicated DB schema
* Yacht signature validates incoming upload
* No cross-yacht data mixing

### **Authentication**

* YachtSignature + UserToken
* Cloud issues temporary signed URLs for file access
* Crew do not need direct NAS access

### **Traffic**

* Local Agent → Cloud: Document upload
* Mobile/Web → Cloud: Search and actions
* Cloud → Mobile/Web: Presigned document URL streaming

---

# # ⚙️ **Graph RAG vs Standard RAG Usage**

### **Standard RAG (Default)**

Used for:

* Searching manuals
* Work order notes
* Handover content
* Emails
* Celeste scraped data
* Part descriptions

### **Graph RAG (Deep Mode)**

Used for:

* Fault diagnosis with system relationships
* Predictive maintenance
* Pattern tracing across history
* Equipment → part → fault relationship mapping
* Complex multi-input queries

**Trigger conditions:**

* “deeper research mode” toggle
* detected multi-hop intent
* low-confidence standard RAG
* predictive request

---

# # 📡 **Error Handling & Reliability**

* Resumable uploads in Local Agent
* Duplicate detection via SHA256
* Cloud retries indexing jobs via queue
* Failed OCR sent to fallback model
* Search timeouts handled gracefully
* Fallback global knowledge used if local docs incomplete

---

# # 🔐 **Safety & Privacy Summary**

* AES-256 encrypted storage
* TLS 1.3 encrypted transport
* Yacht-specific isolation zone
* No PII required
* NAS read-only
* Document access via time-limited presigned URLs
* Logs anonymised
* No local indexing on mobile devices

---

# # 🧩 **Tech Stack Summary**

### **Onboard**

* macOS app (Swift or Electron wrapper)
* Python worker for file ops
* SMB client
* Background daemon (LaunchAgent)

### **Cloud**

* Hetzner VPS (per yacht or group)
* Postgres + pgvector
* S3/MinIO
* Worker queues (Celery/Sidekiq equivalent)
* OCR container
* Embedding container
* Graph builder
* API gateway (FastAPI or Go)

### **Frontend**

* Mobile: React Native or Swift/Kotlin
* Web: Next.js (Vercel)

---

# # 🏁 **Conclusion**

This architectural design ensures:

* Seamless cloud-first operation
* Predictable performance
* Per-yacht isolation
* Intelligent RAG + Graph RAG search
* Real-time mobile access
* Reliable NAS ingestion
* Scalable multi-yacht deployments

This file now serves as the **technical backbone** for the entire project.

---
