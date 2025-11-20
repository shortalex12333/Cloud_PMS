# 🚢 **CelesteOS — Engineering Intelligence for Yachts**

**The cloud-first AI system that replaces PMS complexity with one universal search bar.**

CelesteOS transforms the engineering department of a yacht into a single, intelligent, searchable knowledge system.
Every manual, note, task, history item, part, and predictive insight becomes accessible through one interface.

No modules.
No menus.
No clutter.

Just **Search → Answer → Action**.

---

# # 🎯 **What CelesteOS Does**

CelesteOS delivers four core capabilities:

---

## **1. Universal Search Across All Engineering Knowledge**

Search instantly across:

* NAS documents
* manuals
* photos
* faults
* work orders
* inventory
* emails
* notes
* handovers
* history
* global scraped marine data

Everything unified through one bar.

---

## **2. Automated Handover Generation**

* pulls relevant history
* extracts notes
* summarises issues
* includes predictive insights
* auto-builds clean drafts
* asks for missing details

Handover = 80% automated.

---

## **3. Predictive Engineering Intelligence**

Predicts:

* upcoming failures
* weak systems
* repeating faults
* parts trending towards shortage
* deviations from global behaviour

Uses:

* local vessel history
* crew behaviour
* fault logs
* manuals & RAG
* Celeste global scraped corpus
* anonymised fleet patterns

---

## **4. Two-Page Web UX**

CelesteOS web interface consists of two pages:

### **Page 1 — Global Search (Primary Interface)**

Where crew work daily.
Zero navigation.
Powered entirely by:

* search
* dynamic cards
* micro-actions
* streaming suggestions

### **Page 2 — Dashboard (HOD-Only)**

Used only for:

* configuration
* oversight
* predictive overview
* system settings
* fleet comparisons

Dashboard = visibility.
Search = action.

---

# # 🧠 **Architecture Overview**

CelesteOS is designed around a **cloud-first intelligence model** with strict per-yacht isolation.

---

## **Onboard Local Agent (Mac App)**

* connects to NAS
* reads files (read-only)
* hashes (SHA256)
* chunks & uploads to cloud
* incremental sync
* auto-updating

**No AI runs locally.
No indexing.
No inference.**

---

## **Cloud Brain**

Hosted across:

* Hetzner (backend API, workers)
* Supabase (Postgres + pgvector + Storage)
* Render.com (Python ML microservices)

Responsible for:

* OCR
* chunking
* embeddings
* RAG
* GraphRAG
* entity extraction
* intent detection
* predictive analysis
* search fusion
* micro-action mapping

All intelligence happens centrally.

---

## **Two Frontend Experiences**

* **Web App (desktop)** → Search bar-driven interface + Dashboard
* **Mobile App (iOS/Android)** → dedicated app (future)
* **Local Agent GUI** → onboarding + NAS setup only

---

# # 🧱 **Repository Structure**

```
/docs                        # Documentation
  architecture.md
  security.md
  cloud-ingestion.md         # ✅ NEW: Complete ingestion system docs
  indexing-pipeline.md
  search-engine-spec.md
  predictive-maintenance.md
  devops.md
  web-ux.md
  api-spec.md
  glossary.md
  vision.md

/ingestion-api               # ✅ NEW: Cloud ingestion service
  main.py                    # FastAPI application
  config.py                  # Configuration
  models.py                  # Pydantic models
  auth.py                    # Authentication
  storage.py                 # Temp storage manager
  supabase_client.py         # Supabase integration
  n8n_trigger.py             # Workflow trigger
  Dockerfile                 # Docker deployment
  requirements.txt
  README.md

/supabase/migrations         # ✅ NEW: Database migrations
  001_ingestion_tables.sql

/n8n                         # ✅ NEW: n8n workflow templates
  indexing-workflow.json

docker-compose.yml           # ✅ NEW: Docker Compose setup
```

Each file is a component of the full engineering blueprint.

---

# # 📝 **Key Docs Summary**

### **architecture.md**

Explains the overall system: local agent → cloud brain → indexing → search → predictive.

### **security.md**

Per-yacht isolation, encryption, threats, token model, storage rules.

### **local-agent-spec.md**

DMG app behaviour, NAS sync engine, SHA256, resumable uploads.

### **indexing-pipeline.md**

OCR pipeline, chunking, embeddings, metadata extraction, RAG indexing.

### **search-engine-spec.md**

Entity extraction, intent detection, semantic search, GraphRAG, card logic.

### **predictive-maintenance.md**

Signals, global knowledge, fleet patterns, scoring, recommendations.

### **devops.md**

Hetzner infra, DNS, routing, backups, monitoring, container deployment.

### **web-ux.md**

Two-page UX: search page + dashboard page.

### **vision.md**

Foundation principles for product decisions.

### **glossary.md**

Shared language for engineering + product.

---

# # 🔍 **Search = The Interface**

CelesteOS replaces navigation and modules with **one universal search bar** that handles:

* fault code interpretation
* manual lookup
* creating work orders
* adding to handover
* predictive diagnostics
* finding parts
* ordering parts
* viewing history
* extracting notes
* querying inventory

Every query produces:

* dynamic result cards
* context-aware micro-actions
* predictable behaviour

Search is the system.
The dashboard is optional.

---

# # 🔮 **Predictive Maintenance**

CelesteOS uses:

* local vessel history
* crew behaviour
* fault logs
* part consumption
* global scraped corpus
* manufacturer patterns
* anonymised fleet statistics

to produce:

* risk scores
* upcoming failure predictions
* weak system alerts
* part shortage forecasts
* cross-yacht comparison insights

Predictive results appear as search cards and dashboard widgets.

---

# # 🔐 **Security & Isolation**

Every yacht has:

* its own S3 bucket
* its own Postgres schema
* its own vector DB
* its own graph index
* its own API tenancy
* its own yacht_signature

No cross-yacht leakage is possible.
Global knowledge is anonymised.

---

# # ⚙️ **Local Agent**

Runs on macOS only.
Job is simple:

* ingest
* hash
* chunk
* upload
* retry
* sync

Does **not**:

* index
* embed
* store data
* run inference

This keeps yachts light, secure, and maintainable.

---

# # 🔧 **Cloud Indexing**

Every uploaded document passes through:

* OCR
* text cleaning
* chunking
* embeddings
* metadata extraction
* graph linking

The result is a **searchable, intelligent knowledge graph**.

---

# # 🚀 **Status**

**✅ Cloud Ingestion System — COMPLETE**

The cloud-side ingestion API is fully implemented and production-ready:

* ✅ FastAPI-based REST API with three endpoints
* ✅ Chunked file upload with SHA256 verification
* ✅ Yacht signature authentication
* ✅ Temporary storage management with automatic cleanup
* ✅ Supabase integration for database and object storage
* ✅ n8n workflow triggering for indexing pipeline
* ✅ Comprehensive error handling and retry logic
* ✅ Docker deployment ready
* ✅ Database migrations included
* ✅ Full documentation

See `/ingestion-api/` for implementation and `/docs/cloud-ingestion.md` for complete documentation.

---

**Remaining Components:**

* local agent build
* indexing pipeline (n8n template provided)
* search engine
* dashboard
* web UI
* predictive workers
* mobile version

---

# # 🛠️ **Next Steps**

Choose where development begins:

### **→ Build Local Agent**

Swift + Python runtime.

### **→ Build Cloud API**

Hetzner + Supabase.

### **→ Build Indexing Pipeline**

n8n + OCR + embeddings + metadata.

### **→ Build Search Engine**

Entity extraction + intent detection + GraphRAG.

### **→ Build Web UI**

Two pages: Search + Dashboard.

### **→ Build Predictive Workers**

Rule-based + GraphRAG scoring.

---

# # 📜 **License**

Proprietary.
Not for public distribution.

---