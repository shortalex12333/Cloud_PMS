# N8N_CAPABILITY_MATRIX.md

**Version:** 1.0
**Purpose:** Define what n8n can handle vs what requires external Python services
**Scope:** MVP-1 (n8n-first) and MVP-2 (hybrid) architecture decisions

---

## 📊 Core Capability Matrix

| Function | n8n Capability | MVP-1 Quality | MVP-2 Requirement | Notes |
|----------|----------------|---------------|-------------------|-------|
| **ROUTING & INTENT DETECTION** |
| Webhook receive | ✔ | **High** | Keep in n8n | Native functionality |
| Route to workflow | ✔ | **High** | Keep in n8n | HTTP node + Switch node |
| Call LLM for intent (Claude/GPT) | ✔ | **High** | Keep in n8n | HTTP node to API |
| Structured JSON parsing | ✔ | **High** | Keep in n8n | Native JSON handling |
| Multi-action detection | ✔ | **Medium** | Keep in n8n | LLM can return array |
| Regex pattern matching | ✔ | **High** | Keep in n8n | JavaScript code node |
| Fuzzy string matching | ⚠ | **Low** | → Python | JS Levenshtein is slow |
| **NATURAL LANGUAGE PROCESSING** |
| Basic entity extraction (regex) | ✔ | **Medium** | Keep in n8n | JavaScript regex |
| Maritime-specific NER | ❌ | N/A | → Python | Needs spaCy/transformers |
| Sentiment analysis | ⚠ | **Low** | → Python | API call or local model |
| Multi-language support | ✔ | **Medium** | Keep in n8n | LLM handles this |
| Spell correction | ⚠ | **Low** | → Python | Can use LLM but expensive |
| Abbreviation expansion | ✔ | **High** | Keep in n8n | Lookup table in code node |
| **EMBEDDINGS & VECTOR OPERATIONS** |
| Generate embeddings (OpenAI API) | ✔ | **High** | Keep in n8n | HTTP call to OpenAI |
| Generate embeddings (local model) | ❌ | N/A | → Python | Requires sentence-transformers |
| Vector similarity (cosine) | ⚠ | **Medium** | Keep in n8n | JS math, but slow for >100 |
| Batch embedding | ⚠ | **Low** | → Python | n8n loops are slow |
| Embedding caching | ✔ | **High** | Keep in n8n | Store in Supabase |
| **SEARCH & RETRIEVAL** |
| Supabase pgvector query | ✔ | **High** | Keep in n8n | HTTP/SQL node |
| Postgres full-text search | ✔ | **High** | Keep in n8n | SQL query |
| BM25 ranking | ❌ | N/A | → Python | Requires Elasticsearch or custom impl |
| Hybrid search (BM25 + vector) | ❌ | N/A | → Python | Complex merging logic |
| Cross-encoder reranking | ❌ | N/A | → Python | Needs transformer model |
| Multi-hop retrieval | ⚠ | **Low** | → Python | Too slow in n8n loops |
| Document chunking | ⚠ | **Medium** | → Python | Can do basic in JS, complex needs Python |
| **DATABASE OPERATIONS** |
| Supabase REST API calls | ✔ | **High** | Keep in n8n | Native node |
| Postgres SQL queries | ✔ | **High** | Keep in n8n | SQL node |
| RPC function calls | ✔ | **High** | Keep in n8n | HTTP node |
| Batch inserts | ✔ | **Medium** | Keep in n8n | Can loop, but slow for >1000 |
| Transaction management | ⚠ | **Medium** | Keep in n8n | Possible but error-prone |
| Complex joins (5+ tables) | ✔ | **High** | Keep in n8n | SQL handles this |
| **MICRO-ACTION EXECUTION** |
| Call action endpoints | ✔ | **High** | Keep in n8n | HTTP node |
| Parallel action execution | ✔ | **High** | Keep in n8n | Split in Batches node |
| Action validation | ✔ | **High** | Keep in n8n | JavaScript code node |
| Action logging | ✔ | **High** | Keep in n8n | Insert to DB |
| Action rollback | ⚠ | **Low** | → Python | Complex state management |
| **STREAMING & REAL-TIME** |
| Streaming responses (SSE) | ⚠ | **Low** | → Python | n8n doesn't support native SSE |
| Streaming LLM responses | ⚠ | **Low** | → Python | Can poll but not true stream |
| WebSocket connections | ❌ | N/A | → Python | Not supported |
| Long-polling | ✔ | **Medium** | Keep in n8n | HTTP node can do this |
| **DOCUMENT PROCESSING** |
| PDF text extraction | ❌ | N/A | → Python | Needs PyPDF2/pdfplumber |
| OCR processing | ❌ | N/A | → Python | Needs Tesseract/Azure OCR |
| Document parsing (DOCX) | ❌ | N/A | → Python | Needs python-docx |
| Image processing | ❌ | N/A | → Python | Needs PIL/OpenCV |
| **COMPUTATION & SCORING** |
| Simple arithmetic | ✔ | **High** | Keep in n8n | JavaScript |
| Statistical analysis | ⚠ | **Medium** | → Python | JS can do basic, complex needs NumPy |
| Matrix operations | ❌ | N/A | → Python | Needs NumPy |
| Graph traversal | ❌ | N/A | → Python | Needs NetworkX or custom impl |
| Time series analysis | ❌ | N/A | → Python | Needs pandas/statsmodels |
| **FILE & STORAGE** |
| Supabase Storage upload | ✔ | **High** | Keep in n8n | HTTP node |
| Supabase Storage download | ✔ | **High** | Keep in n8n | HTTP node |
| File format conversion | ❌ | N/A | → Python | Needs specialized libraries |
| Zip/unzip | ⚠ | **Low** | → Python | Limited JS support |
| **EXTERNAL INTEGRATIONS** |
| Call OpenAI/Anthropic API | ✔ | **High** | Keep in n8n | HTTP node |
| Call Render microservices | ✔ | **High** | Keep in n8n | HTTP node |
| Email sending | ✔ | **High** | Keep in n8n | Native node |
| SMS sending | ✔ | **High** | Keep in n8n | Twilio node |
| Slack/Teams notifications | ✔ | **High** | Keep in n8n | Native nodes |
| **ERROR HANDLING & LOGGING** |
| Try/catch logic | ✔ | **High** | Keep in n8n | Error workflow |
| Retry logic | ✔ | **High** | Keep in n8n | Built-in retry |
| Fallback workflows | ✔ | **High** | Keep in n8n | Error trigger |
| Structured logging | ✔ | **High** | Keep in n8n | Insert to log table |
| Performance monitoring | ⚠ | **Low** | → Python | n8n basic, needs APM |

---

## 🎯 Summary by Category

### ✅ **n8n Excels At (MVP-1 Core)**
- HTTP API calls (OpenAI, Claude, Supabase)
- Webhook receiving and routing
- SQL queries and database operations
- Simple JavaScript logic and regex
- JSON parsing and manipulation
- Conditional workflows and branching
- Calling external microservices
- Basic text operations

**Quality:** High reliability, low latency (<200ms for most ops)

---

### ⚠️ **n8n Can Do (But Fragile/Slow)**
- Embedding similarity (small scale, <100 vectors)
- Batch operations (slow for >1000 items)
- Fuzzy matching (JavaScript Levenshtein works but slow)
- Document chunking (basic only)
- Streaming (workarounds possible, not ideal)
- Complex transaction management

**Quality:** Medium reliability, acceptable for MVP-1, optimize in MVP-2

---

### ❌ **n8n Cannot Do (Requires Python)**
- Local transformer models (BERT, BGE, sentence-transformers)
- BM25 ranking (fast implementation)
- Cross-encoder reranking
- PDF/OCR processing
- Graph algorithms (multi-hop reasoning)
- Complex NLP (NER, POS tagging)
- Real-time streaming (SSE, WebSockets)
- Heavy matrix operations
- Time series analysis

**Quality:** Not possible in n8n, must use Python microservices

---

## 📋 Decision Summary

### **For MVP-1 (n8n-First)**

**What stays in n8n:**
- All webhook routing
- Intent detection via LLM API calls
- Database queries (Supabase/Postgres)
- Micro-action execution (HTTP calls to actions)
- Embeddings via OpenAI API
- Simple vector search via Supabase pgvector
- Basic entity extraction (regex)
- Workflow orchestration

**External dependencies (APIs only, no self-hosted):**
- OpenAI API (embeddings + chat)
- Claude API (chat completion)
- Supabase (database + storage + pgvector)

**Latency profile:**
- Webhook → Intent detection: **150-300ms**
- Database queries: **50-150ms**
- Embedding generation: **200-400ms** (OpenAI API)
- Total user-facing latency: **~500-800ms**

---

### **For MVP-2 (Hybrid with Python)**

**What moves to Python microservices:**
- BM25 search (FastAPI + rank-bm25)
- Local embeddings (sentence-transformers)
- Cross-encoder reranking
- Document processing (PDF extraction, chunking)
- Multi-hop reasoning (graph traversal)
- Predictive analytics (time series)
- Streaming responses (SSE)

**Infrastructure:**
- Hosted on Render (or Railway/Fly.io)
- FastAPI Python services
- n8n calls via HTTP
- Stateless design for horizontal scaling

**Latency improvements:**
- BM25 search: **50-100ms** (vs 200ms+ in n8n workaround)
- Reranking: **100-200ms** (impossible in n8n)
- Local embeddings: **100-300ms** (vs 200-400ms API)
- Streaming: **Real-time** (vs polling workarounds)

---

## 🔑 Key Architectural Decisions

### **1. Embeddings Strategy**

| Use Case | MVP-1 Solution | MVP-2 Solution | Why |
|----------|----------------|----------------|-----|
| Document search | OpenAI text-embedding-3-small | BGE-large (self-hosted) | Cost reduction at scale |
| Micro-action classification | Same as above | Lightweight classifier model | Faster, specialized |
| Fault similarity | Same as above | Same as above | Consistent search |
| Multi-language | OpenAI (supports 100+ languages) | mBERT or XLM-R | Control & cost |

**Decision:** Use single embedding model in MVP-1 for simplicity. Split into specialized models in MVP-2 for performance.

---

### **2. Search Strategy**

| Method | MVP-1 | MVP-2 | Notes |
|--------|-------|-------|-------|
| Semantic search | Supabase pgvector + OpenAI embeddings | Supabase pgvector + BGE-large | Vector search |
| Keyword search | Postgres full-text search | BM25 (Python service) | Better ranking |
| Hybrid | Merge results in n8n | Python hybrid search service | Proper fusion |
| Reranking | None | Cross-encoder (Python) | Accuracy boost |

**Decision:** Start with pgvector + full-text search in MVP-1. Add BM25 + reranking in MVP-2 for accuracy.

---

### **3. Streaming Strategy**

| Approach | MVP-1 | MVP-2 |
|----------|-------|-------|
| LLM streaming | Poll OpenAI/Claude (fake streaming) | Python SSE proxy | True streaming |
| Search results | Return all at once | Progressive loading | Better UX |
| Long operations | Webhook callback | WebSocket updates | Real-time |

**Decision:** Accept non-streaming in MVP-1. Build Python SSE service for MVP-2.

---

## 🚨 Risk Assessment

### **MVP-1 Risks**

| Risk | Severity | Mitigation |
|------|----------|------------|
| API costs (OpenAI embeddings) | Medium | Cache aggressively, batch requests |
| n8n performance on high load | Medium | Optimize workflows, add rate limiting |
| No true streaming | Low | Users accept brief delays in MVP |
| Limited NLP accuracy (regex only) | Medium | Use LLM for entity extraction as fallback |
| Vendor lock-in (OpenAI) | Low | Design abstraction layer for embeddings |

### **MVP-2 Risks**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Managing Python microservices | High | Use managed hosting (Render), keep stateless |
| Latency of Python HTTP calls | Medium | Deploy in same region, optimize payloads |
| Complexity of hybrid architecture | High | Clear API contracts, comprehensive testing |
| Cost of hosting | Medium | Start small, scale horizontally as needed |

---

## 📌 Recommendation

**Start with MVP-1 (n8n-first):**
- Validate product-market fit
- Keep infrastructure simple
- Use API-based embeddings (OpenAI)
- Accept 500-800ms latency
- Focus on core micro-actions

**Move to MVP-2 when:**
- Embedding costs exceed $200/month
- User base exceeds 50 active users
- Latency complaints emerge
- Need custom NLP/NER for maritime domain
- Predictive features require heavy ML

**Estimated timeline:**
- MVP-1: 4-6 weeks
- MVP-2 transition: 3-4 weeks
- Full hybrid system: 8-10 weeks total

---

**END OF CAPABILITY MATRIX**
