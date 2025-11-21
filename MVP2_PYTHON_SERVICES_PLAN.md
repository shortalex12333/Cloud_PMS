# MVP2_PYTHON_SERVICES_PLAN.md

**Version:** 1.0
**Purpose:** Define Python microservices architecture for CelesteOS MVP-2
**Trigger:** When MVP-1 limitations impact user experience or costs exceed $200/month
**Hosting:** Render, Railway, or Fly.io

---

## 🎯 Why Move to MVP-2?

### **Triggers for Migration:**

| Trigger | Threshold | Impact |
|---------|-----------|--------|
| **API Costs** | >$200/month | OpenAI embedding costs at scale |
| **Latency** | P95 >1000ms | User complaints about speed |
| **Search Accuracy** | <75% user satisfaction | Need BM25 + reranking |
| **User Base** | >50 active users/day | Scale requirements |
| **Custom NLP** | Maritime entity extraction | Need domain-specific models |
| **Streaming** | Users demand real-time | n8n can't do true SSE |

### **MVP-2 Goals:**

1. ✅ Reduce latency by 40-60% (target: P95 <400ms)
2. ✅ Reduce API costs by 70-80% (self-hosted embeddings)
3. ✅ Improve search accuracy by 20-30% (BM25 + reranking)
4. ✅ Enable streaming responses (SSE)
5. ✅ Support custom maritime NLP
6. ✅ Maintain n8n orchestration (don't rebuild everything)

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vercel)                        │
│                  Next.js Search Interface                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTPS POST /webhook/search
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   N8N ORCHESTRATION LAYER                    │
│  (Still handles routing, validation, workflow logic)         │
│                                                              │
│  • Receive webhook                                           │
│  • Validate yacht signature                                  │
│  • Route to appropriate Python service                       │
│  • Handle errors & fallbacks                                 │
│  • Aggregate results                                         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    │ HTTP calls to Python services
                    │
    ┌───────────────┼───────────────┬─────────────────────┐
    │               │               │                     │
    ▼               ▼               ▼                     ▼
┌──────────┐   ┌──────────┐   ┌──────────┐        ┌──────────┐
│ PYTHON   │   │ PYTHON   │   │ PYTHON   │        │ PYTHON   │
│ SERVICE  │   │ SERVICE  │   │ SERVICE  │        │ SERVICE  │
│    1     │   │    2     │   │    3     │        │    4     │
│          │   │          │   │          │        │          │
│ Search   │   │Embeddings│   │ NLP/NER  │        │Streaming │
│ Engine   │   │ Service  │   │ Service  │        │  Proxy   │
└────┬─────┘   └────┬─────┘   └────┬─────┘        └────┬─────┘
     │              │              │                    │
     └──────────────┴──────────────┴────────────────────┘
                    │
                    │ Database & Storage
                    ▼
           ┌─────────────────┐
           │    Supabase     │
           │  Postgres +     │
           │   pgvector      │
           └─────────────────┘
```

---

## 🔧 Python Microservices Breakdown

### **SERVICE 1: Search Engine Service**

**Endpoint:** `https://search-engine.render.com/api/v1/search`

**Purpose:** High-performance hybrid search (BM25 + vector + reranking)

**Tech Stack:**
- FastAPI
- rank-bm25 (Python library)
- sentence-transformers (for reranking)
- NumPy for vector operations
- Redis for caching (optional)

**API Contract:**

```python
# POST /api/v1/search
{
  "query": "CAT 3512 overheating",
  "yacht_id": "uuid",
  "search_type": "hybrid",  # "vector" | "bm25" | "hybrid"
  "top_k": 10,
  "rerank": true,
  "filters": {
    "equipment_type": ["generator"],
    "date_range": {"start": "2024-01-01", "end": "2024-12-31"}
  }
}

# Response
{
  "results": [
    {
      "id": "uuid",
      "content": "...",
      "score": 0.92,
      "metadata": {...},
      "highlights": ["CAT 3512", "overheating"]
    }
  ],
  "search_metadata": {
    "bm25_results": 25,
    "vector_results": 18,
    "reranked": true,
    "latency_ms": 150
  }
}
```

**Capabilities:**

1. **BM25 Search**
   - Index: In-memory BM25 index of all document chunks
   - Updates: Rebuild index hourly via background job
   - Performance: <50ms for most queries

2. **Vector Search**
   - Embeddings: Stored in Postgres pgvector
   - Model: BGE-large-en-v1.5 (1024-dim)
   - Performance: <100ms via pgvector index

3. **Hybrid Fusion**
   - Strategy: Reciprocal Rank Fusion (RRF)
   - Formula: `score = 1 / (k + rank_bm25) + 1 / (k + rank_vector)` where k=60
   - Weights: Configurable per query type

4. **Reranking**
   - Model: cross-encoder/ms-marco-MiniLM-L-6-v2
   - When: Always run on top 20 results
   - Performance: ~50-100ms for 20 candidates

**Deployment:**

- Platform: Render (or Railway)
- Instance: 2 vCPU, 4GB RAM
- Scaling: Horizontal (2-4 instances behind load balancer)
- Cost: ~$25-50/month

**Latency Breakdown:**
- BM25 search: 20-50ms
- Vector search: 50-100ms
- Reranking: 50-100ms
- **Total: 150-250ms** (parallel BM25 + vector)

---

### **SERVICE 2: Embedding Service**

**Endpoint:** `https://embeddings.render.com/api/v1/embed`

**Purpose:** Generate embeddings using self-hosted sentence-transformers

**Tech Stack:**
- FastAPI
- sentence-transformers (BGE-large-en-v1.5)
- PyTorch (CPU or GPU)
- Batch processing

**API Contract:**

```python
# POST /api/v1/embed
{
  "texts": [
    "CAT 3512 overheating",
    "Port generator fault E047"
  ],
  "model": "bge-large-en-v1.5",  # or "minilm", "mpnet"
  "normalize": true
}

# Response
{
  "embeddings": [
    [0.123, 0.456, ...],  # 1024-dim vector
    [0.789, 0.012, ...]
  ],
  "model": "bge-large-en-v1.5",
  "dimensions": 1024,
  "latency_ms": 120
}
```

**Supported Models:**

| Model | Dimensions | Speed | Use Case |
|-------|------------|-------|----------|
| `bge-large-en-v1.5` | 1024 | 100-200ms/text | Primary search |
| `all-MiniLM-L6-v2` | 384 | 20-50ms/text | Fast classification |
| `multilingual-e5-large` | 1024 | 150-300ms/text | Multi-language (future) |

**Optimization:**

1. **Batching**
   - Process up to 100 texts per request
   - Amortize model loading overhead

2. **Caching**
   - Redis cache for common queries
   - TTL: 7 days
   - Cache key: `hash(text + model)`

3. **GPU Acceleration (Optional)**
   - Render GPU instances: ~$150/month
   - 5-10x speedup for batch processing
   - Cost-effective at >10,000 embeddings/day

**Deployment:**

- Platform: Render (CPU instance for MVP-2)
- Instance: 2 vCPU, 4GB RAM
- Scaling: Horizontal (2-3 instances)
- Cost: ~$25/month (CPU), ~$150/month (GPU)

**Latency:**
- Single text: 100-150ms
- Batch of 10: 200-300ms (20-30ms per text)

**Cost Savings vs OpenAI:**
- OpenAI: $0.0001 per 1K tokens ≈ $0.00015 per embedding
- Self-hosted: $0.000005 per embedding (assuming 200K embeddings/month)
- **Savings: 97%** at scale

---

### **SERVICE 3: NLP & Entity Extraction Service**

**Endpoint:** `https://nlp.render.com/api/v1/extract`

**Purpose:** Maritime-specific named entity recognition and parsing

**Tech Stack:**
- FastAPI
- spaCy (custom maritime model)
- Regex patterns for fault codes, IMO numbers, etc.
- Fuzzy matching (RapidFuzz)

**API Contract:**

```python
# POST /api/v1/extract
{
  "text": "Gen 2 SPN 4364 FMI 2 overheating",
  "extract": ["equipment", "fault_codes", "parts", "locations"]
}

# Response
{
  "entities": {
    "equipment": [
      {"text": "Gen 2", "type": "generator", "confidence": 0.95}
    ],
    "fault_codes": [
      {"text": "SPN 4364 FMI 2", "standard": "J1939", "description": "..."}
    ],
    "parts": [],
    "locations": []
  },
  "intent": {
    "primary": "diagnose_fault",
    "secondary": ["create_work_order"]
  },
  "latency_ms": 80
}
```

**Capabilities:**

1. **Equipment Detection**
   - Patterns: "Gen 1", "Stabiliser B", "Port HVAC", etc.
   - Fuzzy matching: Handle typos ("stabillizer")
   - Context-aware: Use yacht's equipment list

2. **Fault Code Extraction**
   - Standards: J1939 (SPN/FMI), MTU, CAT, Volvo Penta
   - Regex patterns: Pre-compiled for speed
   - Validation: Check against known fault code database

3. **Part Number Recognition**
   - Patterns: OEM part numbers (e.g., "MTU-X00123456")
   - Fuzzy matching: Handle OCR errors
   - Validation: Check against inventory

4. **Location Detection**
   - Patterns: "Engine Room", "Deck 3", "Port Side"
   - Standardization: Map to yacht's GA drawing zones

5. **Date/Time Extraction**
   - Relative: "last week", "yesterday", "3 months ago"
   - Absolute: "2024-01-15", "January 15th"
   - Timezone-aware: Convert to yacht's local time

**Training Data:**
- Custom maritime corpus (manuals, work orders, handovers)
- Fault code databases
- Equipment nomenclature from major OEMs

**Deployment:**

- Platform: Render
- Instance: 1 vCPU, 2GB RAM
- Scaling: Vertical (CPU-bound for spaCy)
- Cost: ~$15/month

**Latency:** 50-100ms per query

---

### **SERVICE 4: Streaming Proxy Service**

**Endpoint:** `wss://stream.render.com/api/v1/stream`

**Purpose:** Enable Server-Sent Events (SSE) for streaming LLM responses

**Tech Stack:**
- FastAPI with SSE support
- httpx (async HTTP client)
- WebSockets (optional)

**API Contract:**

```python
# GET /api/v1/stream?query=...&yacht_id=...
# Returns SSE stream

# Client receives:
event: start
data: {"type": "search_start", "query": "..."}

event: result
data: {"type": "document_chunk", "id": "...", "score": 0.92}

event: result
data: {"type": "fault", "id": "...", "score": 0.85}

event: llm_chunk
data: {"content": "Based on the fault code", "chunk_id": 1}

event: llm_chunk
data: {"content": " SPN 4364, this indicates", "chunk_id": 2}

event: complete
data: {"total_results": 5, "latency_ms": 450}
```

**Capabilities:**

1. **Progressive Search Results**
   - Stream results as they arrive from search engine
   - Don't wait for all results before showing first one

2. **LLM Streaming**
   - Proxy OpenAI/Claude streaming APIs
   - Convert to SSE format for frontend

3. **Error Handling**
   - Graceful degradation if streaming fails
   - Fallback to batch response

**Deployment:**

- Platform: Render
- Instance: 1 vCPU, 1GB RAM
- Scaling: Horizontal (behind load balancer)
- Cost: ~$10/month

**Latency:** Adds <20ms overhead, but improves perceived latency

---

## 📊 Service Dependencies & Communication

### **Service Call Flow:**

```
User Query → n8n
    │
    ├─► NLP Service (extract entities) [50-100ms]
    │       │
    │       └─► Return: entities + intent
    │
    ├─► Embedding Service (generate query embedding) [100-150ms]
    │       │
    │       └─► Return: 1024-dim vector
    │
    ├─► Search Service (hybrid search + rerank) [150-250ms]
    │       │
    │       ├─► Calls Supabase pgvector (vector search)
    │       ├─► BM25 search (in-memory)
    │       ├─► Fusion + reranking
    │       └─► Return: top 10 results
    │
    └─► Streaming Service (optional, for SSE) [realtime]
            │
            └─► Stream results to frontend
```

### **Service-to-Service Communication:**

**Option 1: Direct HTTP (Simpler)**
- Each service calls others directly via HTTP
- Pros: Simple, low latency
- Cons: Tight coupling

**Option 2: Message Queue (More Scalable)**
- Services communicate via Redis pub/sub or RabbitMQ
- Pros: Decoupled, async
- Cons: Added complexity

**Recommendation:** Start with Option 1 (direct HTTP) for MVP-2, migrate to Option 2 if needed.

---

## 🗄 Data Storage & Caching

### **What Goes Where:**

| Data Type | Storage | Why |
|-----------|---------|-----|
| Document chunks (text) | Supabase Postgres | Source of truth |
| Document embeddings | Supabase pgvector | Indexed for vector search |
| BM25 index | Search Service (in-memory) | Fast lookups |
| Embedding cache | Redis (optional) | Reduce embedding calls |
| Model weights | Docker image | Fast startup |
| Search results cache | Redis (optional) | Cache popular queries |

### **Cache Strategy:**

**Embedding Cache (Redis):**
```
Key: hash(text + model_name)
Value: JSON-serialized embedding vector
TTL: 7 days
Est. size: ~2KB per embedding
Est. total: <100MB for 10K cached embeddings
```

**Search Results Cache (Redis):**
```
Key: hash(query + filters)
Value: JSON search results
TTL: 1 hour
Est. size: ~10KB per query
Est. total: <10MB for 1K cached queries
```

**Redis Hosting:**
- Upstash (free tier: 10MB, $10/month for 1GB)
- Render Redis add-on (~$10/month)

---

## 🚀 Deployment Strategy

### **Platform: Render**

**Why Render:**
- ✅ Auto-scaling
- ✅ Zero-downtime deploys
- ✅ Built-in monitoring
- ✅ Free SSL
- ✅ Docker support
- ✅ Background workers
- ✅ Affordable ($7/month starter instances)

**Alternatives:**
- Railway (similar pricing, good DX)
- Fly.io (edge deployment, more complex)
- AWS ECS (overkill for MVP-2)

### **Service Deployment Plan:**

| Service | Instance Type | Cost/month | Replicas | Total Cost |
|---------|---------------|------------|----------|------------|
| Search Engine | 2 vCPU, 4GB | $25 | 2 | $50 |
| Embedding Service | 2 vCPU, 4GB | $25 | 1-2 | $25-50 |
| NLP Service | 1 vCPU, 2GB | $15 | 1 | $15 |
| Streaming Proxy | 1 vCPU, 1GB | $10 | 1 | $10 |
| Redis (Upstash) | - | $10 | 1 | $10 |
| **Total** | - | - | - | **$110-135/month** |

**Plus existing:**
- n8n Cloud: ~$20/month
- Supabase: ~$25/month
- OpenAI API (reduced): ~$20/month
- **Grand Total: ~$175-200/month**

**Cost comparison to MVP-1:**
- MVP-1: ~$200/month (mostly OpenAI API)
- MVP-2: ~$200/month (but 10x capacity)
- **Breakeven at ~50 active users/day**

---

## 🔄 CI/CD Pipeline

### **GitHub Actions Workflow:**

```yaml
name: Deploy Python Services

on:
  push:
    branches: [main]
    paths:
      - 'services/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [search-engine, embeddings, nlp, streaming]
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t ${{ matrix.service }} services/${{ matrix.service }}
      - name: Deploy to Render
        uses: render-deploy-action@v1
        with:
          service-id: ${{ secrets.RENDER_SERVICE_ID }}
          api-key: ${{ secrets.RENDER_API_KEY }}
```

### **Docker Images:**

**Base Image:**
```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install fastapi uvicorn sentence-transformers

# Copy service code
COPY . /app
WORKDIR /app

# Expose port
EXPOSE 8000

# Run service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Optimization:**
- Multi-stage builds to reduce image size
- Layer caching for faster builds
- Pre-download model weights in Docker build

---

## 📈 Performance Benchmarks

### **Expected Performance (MVP-2 vs MVP-1):**

| Operation | MVP-1 Latency | MVP-2 Latency | Improvement |
|-----------|---------------|---------------|-------------|
| Query embedding | 200-300ms (OpenAI API) | 100-150ms (self-hosted) | **~50% faster** |
| Vector search | 100-150ms | 50-100ms | **~40% faster** |
| BM25 search | N/A | 20-50ms | **New capability** |
| Hybrid search | N/A | 150-250ms | **New capability** |
| Reranking | N/A | 50-100ms | **New capability** |
| Entity extraction | 300-400ms (LLM-based) | 50-100ms (spaCy) | **~75% faster** |
| **Total search latency** | **600-800ms** | **250-400ms** | **~50% faster** |

### **Throughput:**

| Service | Requests/sec | Concurrent Users |
|---------|--------------|------------------|
| Search Engine | ~50 | ~200 |
| Embedding Service | ~20 (batch of 10) | ~100 |
| NLP Service | ~100 | ~300 |
| Streaming Proxy | ~200 (lightweight) | ~500 |

---

## 🛡 Error Handling & Resilience

### **Fallback Strategy:**

1. **Search Service Down**
   - Fallback: n8n calls Supabase pgvector directly
   - Performance: Degraded (no BM25, no reranking)
   - User impact: Lower search quality

2. **Embedding Service Down**
   - Fallback: Use OpenAI API
   - Performance: Slower + costs more
   - User impact: Minimal

3. **NLP Service Down**
   - Fallback: Use LLM for entity extraction
   - Performance: Slower + costs more
   - User impact: Minimal

4. **Streaming Service Down**
   - Fallback: Return batch results
   - Performance: Same total latency, worse perceived latency
   - User impact: No streaming

### **Health Checks:**

```python
# GET /health
{
  "status": "healthy",
  "service": "search-engine",
  "version": "1.0.0",
  "uptime_seconds": 12345,
  "dependencies": {
    "postgres": "healthy",
    "redis": "healthy",
    "bm25_index": "loaded"
  }
}
```

n8n polls health endpoints every 60 seconds, marks services as degraded if unhealthy.

---

## 🔧 Development & Testing

### **Local Development:**

```bash
# Run all services with Docker Compose
docker-compose up

# Services available at:
# - Search: http://localhost:8001
# - Embeddings: http://localhost:8002
# - NLP: http://localhost:8003
# - Streaming: http://localhost:8004
```

### **Testing Strategy:**

1. **Unit Tests**
   - pytest for Python services
   - Coverage target: >80%

2. **Integration Tests**
   - Test n8n → Python service calls
   - Mock Supabase responses

3. **Load Tests**
   - Locust or k6
   - Target: 100 concurrent users
   - Validate latency under load

4. **Accuracy Tests**
   - Ground truth dataset of 1000 queries
   - Measure: precision@10, recall@10
   - Baseline: MVP-1 performance

---

## 📋 Migration Checklist

**Phase 1: Deploy Services (Week 1)**
- [ ] Deploy Search Engine service
- [ ] Deploy Embedding service
- [ ] Deploy NLP service
- [ ] Deploy Streaming service (optional)
- [ ] Set up Redis cache
- [ ] Configure health checks

**Phase 2: Update n8n (Week 2)**
- [ ] Add HTTP nodes for Python services
- [ ] Implement fallback logic
- [ ] Update error handling
- [ ] Add monitoring

**Phase 3: A/B Testing (Week 3)**
- [ ] Route 10% traffic to MVP-2
- [ ] Monitor latency & errors
- [ ] Gather user feedback
- [ ] Compare costs

**Phase 4: Full Cutover (Week 4)**
- [ ] Route 100% traffic to MVP-2
- [ ] Keep MVP-1 as fallback
- [ ] Monitor for 1 week
- [ ] Decommission MVP-1 (optional)

---

## ✅ Success Criteria

**MVP-2 is successful if:**

1. ✅ P95 latency <400ms (vs 800ms in MVP-1)
2. ✅ Search accuracy >85% (vs ~75% in MVP-1)
3. ✅ API costs <$50/month (vs $150+ in MVP-1)
4. ✅ Uptime >99.5%
5. ✅ Streaming responses work smoothly
6. ✅ Total infrastructure cost <$200/month
7. ✅ Can handle 200+ concurrent users

---

**END OF MVP2 PYTHON SERVICES PLAN**
