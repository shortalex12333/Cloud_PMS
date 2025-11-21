# MVP1_WORKFLOW_DESIGN.md

**Version:** 1.0
**Purpose:** Define n8n-only workflow architecture for CelesteOS MVP-1
**Target Latency:** <800ms end-to-end for most operations
**External Dependencies:** OpenAI API, Claude API, Supabase only

---

## 🎯 MVP-1 Philosophy

**Core Principle:** Everything runs in n8n workflows, calling only external APIs (no self-hosted Python).

**Design Goals:**
1. ✅ Minimize latency (<500ms for common operations)
2. ✅ Maximize reliability (99% uptime)
3. ✅ Keep infrastructure dead simple
4. ✅ Validate product-market fit before optimizing
5. ✅ Make migration to MVP-2 seamless

---

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vercel)                        │
│                  Next.js Search Interface                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTPS POST /webhook/search
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      N8N CLOUD                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ WORKFLOW 1: Main Search Entry Point                  │  │
│  │  - Receive webhook                                    │  │
│  │  - Validate yacht signature                           │  │
│  │  - Route to intent detection                          │  │
│  └────────────┬────────────────────────────────────────────┘  │
│               │                                               │
│  ┌────────────▼────────────────────────────────────────┐    │
│  │ WORKFLOW 2: Intent Detection & Action Extraction    │    │
│  │  - Call Claude API (structured JSON output)          │    │
│  │  - Extract micro-actions                             │    │
│  │  - Extract entities (equipment, dates, etc.)         │    │
│  │  - Determine search strategy                         │    │
│  └────────────┬────────────────────────────────────────┘    │
│               │                                               │
│               ├──► Search Required? ──► WORKFLOW 3: Search   │
│               ├──► Action Direct? ───► WORKFLOW 4: Action    │
│               └──► Unsupported? ────► WORKFLOW 5: Fallback   │
│                                                              │
└───────────────────┬──────────────────────────────────────────┘
                    │
                    │ External API Calls
                    │
    ┌───────────────┼───────────────┬─────────────────────┐
    │               │               │                     │
    ▼               ▼               ▼                     ▼
┌─────────┐   ┌──────────┐   ┌──────────┐        ┌──────────┐
│ OpenAI  │   │  Claude  │   │ Supabase │        │ Supabase │
│   API   │   │   API    │   │ Database │        │ Storage  │
│         │   │          │   │(Postgres)│        │  (S3)    │
└─────────┘   └──────────┘   └──────────┘        └──────────┘
```

---

## 🔄 Core Workflows

### **WORKFLOW 1: Main Entry Point**

**Trigger:** Webhook POST `/webhook/search`

**Purpose:** Validate request and route to correct workflow

**Steps:**

1. **Receive Webhook**
   - Node: Webhook (POST)
   - Input: `{ query: string, yacht_signature: string, user_id?: string }`
   - Validation: Check required fields

2. **Validate Yacht Signature**
   - Node: Supabase Query
   - SQL: `SELECT id, status FROM yachts WHERE signature = $1`
   - Error if not found or status != 'active'

3. **Log Request**
   - Node: Supabase Insert
   - Table: `search_logs`
   - Fields: `{ yacht_id, query, timestamp, user_id }`

4. **Route to Intent Detection**
   - Node: HTTP Request (n8n webhook)
   - Target: WORKFLOW 2
   - Method: Async (don't wait for full completion)

**Latency Target:** <50ms

---

### **WORKFLOW 2: Intent Detection & Entity Extraction**

**Trigger:** Called from WORKFLOW 1

**Purpose:** Determine what the user wants using Claude/GPT

**Steps:**

1. **Call LLM for Intent**
   - Node: HTTP Request (Claude API)
   - Model: `claude-3-haiku-20240307` (fast, cheap)
   - Prompt template:
     ```
     You are an intent classifier for a maritime engineering system.

     User query: "{query}"

     Extract:
     1. micro_actions: array of actions (e.g., ["create_work_order", "add_to_handover"])
     2. entities: { equipment: string[], parts: string[], dates: string[] }
     3. search_required: boolean
     4. urgency: "low" | "medium" | "high"

     Respond ONLY with valid JSON.
     ```
   - Timeout: 3 seconds
   - Retry: 2 times with backoff

2. **Parse JSON Response**
   - Node: Code (JavaScript)
   - Validation: Check for required fields
   - Fallback: If parse fails, assume `search_required: true`

3. **Route Based on Intent**
   - Node: Switch
   - Cases:
     - `search_required === true` → WORKFLOW 3 (Search)
     - `micro_actions.length > 0 && !search_required` → WORKFLOW 4 (Direct Action)
     - `micro_actions.length === 0` → WORKFLOW 5 (Unsupported)

**Latency Target:** <400ms (Claude Haiku is fast)

**Cost:** ~$0.001 per query

---

### **WORKFLOW 3: Search & Retrieval**

**Trigger:** Called from WORKFLOW 2 when search required

**Purpose:** Find relevant documents, faults, equipment, parts

**Steps:**

1. **Generate Query Embedding**
   - Node: HTTP Request (OpenAI Embeddings API)
   - Model: `text-embedding-3-small`
   - Input: User query (cleaned)
   - Output: 1536-dim vector
   - Cache: Check Supabase cache first (key: hash of query)

2. **Parallel Search Branches**
   - Node: Split In Batches (parallel mode)
   - Branch A: **Vector Search** (pgvector)
   - Branch B: **Full-Text Search** (Postgres tsvector)
   - Branch C: **Equipment Lookup** (if entity detected)
   - Branch D: **Fault Code Lookup** (if pattern matches fault code)

3. **Vector Search (Branch A)**
   - Node: Supabase SQL Query
   - Table: `document_chunks`
   - Query:
     ```sql
     SELECT id, content, metadata, embedding <=> $1::vector AS distance
     FROM document_chunks
     WHERE yacht_id = $2
     ORDER BY embedding <=> $1::vector
     LIMIT 10;
     ```
   - Threshold: distance < 0.3

4. **Full-Text Search (Branch B)**
   - Node: Supabase SQL Query
   - Table: `document_chunks`
   - Query:
     ```sql
     SELECT id, content, metadata, ts_rank(search_vector, query) AS rank
     FROM document_chunks, plainto_tsquery('english', $1) query
     WHERE yacht_id = $2 AND search_vector @@ query
     ORDER BY rank DESC
     LIMIT 10;
     ```

5. **Equipment Lookup (Branch C)**
   - Node: Supabase SQL Query (conditional)
   - Table: `equipment`
   - Query:
     ```sql
     SELECT * FROM equipment
     WHERE yacht_id = $1
     AND (name ILIKE $2 OR model ILIKE $2)
     LIMIT 5;
     ```

6. **Fault Code Lookup (Branch D)**
   - Node: Supabase SQL Query (conditional)
   - Triggered if query matches regex: `[A-Z]{3,4}\s?\d{3,4}`
   - Table: `faults`
   - Query:
     ```sql
     SELECT * FROM faults
     WHERE yacht_id = $1
     AND fault_code ILIKE $2
     ORDER BY created_at DESC
     LIMIT 5;
     ```

7. **Merge Results**
   - Node: Code (JavaScript)
   - Deduplicate by ID
   - Score merging: `final_score = 0.6 * vector_score + 0.4 * text_rank`
   - Sort by final score descending
   - Limit: Top 10 results

8. **Build Result Cards**
   - Node: Code (JavaScript)
   - For each result:
     - Determine card type (document, fault, equipment, part)
     - Extract metadata
     - Attach micro-actions based on card type
     - Format for frontend

9. **Return Response**
   - Node: Respond to Webhook
   - Format:
     ```json
     {
       "results": [
         {
           "type": "document_chunk",
           "id": "uuid",
           "title": "...",
           "preview": "...",
           "score": 0.85,
           "actions": ["open_document", "add_to_handover"]
         }
       ],
       "metadata": {
         "query": "...",
         "total_results": 10,
         "latency_ms": 450
       }
     }
     ```

**Latency Target:** <600ms

**Breakdown:**
- Embedding generation: 200-300ms
- Parallel searches: 100-200ms
- Merging + formatting: 50-100ms

---

### **WORKFLOW 4: Direct Micro-Action Execution**

**Trigger:** Called from WORKFLOW 2 when action is directly executable (no search needed)

**Purpose:** Execute micro-actions immediately

**Examples:**
- "Update my hours of rest"
- "Export handover to PDF"
- "Show me today's tasks"

**Steps:**

1. **Validate Action**
   - Node: Code (JavaScript)
   - Check: Does action exist in registry?
   - Check: Does user have permission?

2. **Call Action Endpoint**
   - Node: HTTP Request
   - Endpoint: `https://api.celeste7.ai/webhook/actions/{action_name}`
   - Method: POST
   - Body: `{ yacht_id, user_id, params: {...} }`

3. **Handle Response**
   - Node: Switch
   - Cases:
     - Success (200) → Format success response
     - Validation error (400) → Format error message
     - Server error (500) → Retry once, then error

4. **Return to User**
   - Node: Respond to Webhook
   - Format:
     ```json
     {
       "action_executed": true,
       "action_name": "update_hours_of_rest",
       "result": { ... },
       "message": "Hours of rest updated successfully"
     }
     ```

**Latency Target:** <300ms

---

### **WORKFLOW 5: Unsupported Action Fallback**

**Trigger:** Called from WORKFLOW 2 when intent is unclear or unsupported

**Purpose:** Gracefully handle requests we can't fulfill

**Steps:**

1. **Check if Similar Action Exists**
   - Node: Code (JavaScript)
   - Use Levenshtein distance to find closest supported action
   - Threshold: distance < 3

2. **Generate Fallback Message**
   - Node: Code (JavaScript)
   - Template:
     ```
     I can't do "{unsupported_action}" yet, but I can:
     - {similar_action_1}
     - {similar_action_2}

     Would you like me to try one of these instead?
     ```

3. **Log Feature Request**
   - Node: Supabase Insert
   - Table: `feature_requests`
   - Fields: `{ yacht_id, user_id, query, timestamp }`

4. **Return Response**
   - Node: Respond to Webhook
   - Format:
     ```json
     {
       "supported": false,
       "message": "...",
       "suggestions": ["...", "..."],
       "logged_as_feature_request": true
     }
     ```

**Latency Target:** <200ms

---

## 🔧 Supporting Workflows

### **WORKFLOW 6: Embedding Cache Maintenance**

**Trigger:** Cron (every hour)

**Purpose:** Pre-compute embeddings for common queries

**Steps:**
1. Query `search_logs` for top 100 queries
2. Check which don't have cached embeddings
3. Generate embeddings for missing queries
4. Store in `embedding_cache` table

**Latency:** N/A (background job)

---

### **WORKFLOW 7: Error Recovery**

**Trigger:** Any workflow error

**Purpose:** Graceful degradation

**Steps:**
1. Log error to `error_logs` table
2. Send alert if critical (Slack/email)
3. Return user-friendly error message
4. Retry if transient error (API timeout)

---

## 📈 Optimization Strategies

### **1. Caching**

| What | Where | TTL | Why |
|------|-------|-----|-----|
| Query embeddings | Supabase table | 7 days | Avoid OpenAI API cost |
| Common queries | Redis (future) | 1 hour | Speed up frequent searches |
| User sessions | Supabase | 24 hours | Reduce auth checks |
| Document chunks | Supabase | Permanent | Already indexed |

### **2. Parallelization**

- All search branches run in parallel (vector, text, equipment, faults)
- Use n8n "Split In Batches" node with parallel execution
- Target: Reduce total search time by 40-60%

### **3. Batching**

- Batch embedding requests when possible (up to 100 texts per call)
- Batch database inserts (logs, feature requests)
- Trade-off: Slight latency increase for better throughput

### **4. Connection Pooling**

- Use Supabase connection pooler for database queries
- Keep n8n HTTP connections persistent where possible
- Reduce connection overhead by ~20-30ms per query

---

## 🚨 Error Handling Patterns

### **Pattern 1: Retry with Backoff**

**When:** External API timeout (OpenAI, Claude)

**Strategy:**
```javascript
// Exponential backoff: 1s, 2s, 4s
retries: 3
backoffStrategy: 'exponential'
maxBackoff: 5000ms
```

### **Pattern 2: Circuit Breaker**

**When:** API consistently failing (>50% error rate)

**Strategy:**
- After 5 consecutive failures, mark service as "degraded"
- Skip API call for 60 seconds
- Use fallback (e.g., skip embeddings, use text search only)
- Auto-recover after timeout

### **Pattern 3: Graceful Degradation**

**When:** Non-critical component fails

**Examples:**
- Embedding API down → Use full-text search only
- Full-text search slow → Return vector results only
- Equipment lookup fails → Still show document results

---

## 🎛 Configuration & Tuning

### **Environment Variables**

```bash
# External APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Supabase
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# Performance
MAX_SEARCH_RESULTS=10
EMBEDDING_CACHE_TTL=604800  # 7 days
QUERY_TIMEOUT_MS=5000
RETRY_ATTEMPTS=3

# Features
ENABLE_VECTOR_SEARCH=true
ENABLE_TEXT_SEARCH=true
ENABLE_ENTITY_LOOKUP=true
```

### **Performance Tuning Knobs**

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| `MAX_SEARCH_RESULTS` | 10 | 5-20 | Latency vs completeness |
| `VECTOR_DISTANCE_THRESHOLD` | 0.3 | 0.1-0.5 | Precision vs recall |
| `PARALLEL_SEARCH_TIMEOUT` | 2000ms | 1000-5000ms | Speed vs reliability |
| `EMBEDDING_BATCH_SIZE` | 100 | 50-200 | Cost vs latency |

---

## 📊 Monitoring & Metrics

### **Key Metrics to Track**

| Metric | Target | Alert Threshold | Source |
|--------|--------|-----------------|--------|
| P95 latency | <800ms | >1200ms | n8n workflow logs |
| Error rate | <1% | >5% | Error logs table |
| OpenAI API cost | <$50/day | >$100/day | OpenAI dashboard |
| Search accuracy (user feedback) | >80% | <70% | User ratings |
| Embedding cache hit rate | >60% | <40% | Cache logs |

### **Dashboard Queries**

```sql
-- Average latency by workflow
SELECT
  workflow_name,
  AVG(latency_ms) as avg_latency,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency
FROM workflow_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY workflow_name;

-- Error rate by type
SELECT
  error_type,
  COUNT(*) as count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM error_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY error_type;

-- Top queries (for cache optimization)
SELECT
  query,
  COUNT(*) as frequency,
  AVG(latency_ms) as avg_latency
FROM search_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY query
ORDER BY frequency DESC
LIMIT 100;
```

---

## 🔄 Migration Path to MVP-2

### **What Changes in MVP-2:**

1. **Add Python microservices** for:
   - BM25 search
   - Local embeddings
   - Reranking
   - Streaming

2. **n8n workflows update** to:
   - Call Python services instead of OpenAI API
   - Handle streaming responses
   - Route complex NLP to Python

3. **Database changes:**
   - Add BM25 index (if using Elasticsearch)
   - Store local embedding metadata
   - Add reranking scores

### **Migration Strategy:**

**Phase 1: Add Python services (no n8n changes yet)**
- Deploy Python services on Render
- Test in parallel with existing MVP-1
- Compare performance metrics

**Phase 2: Update n8n workflows**
- Add new HTTP nodes pointing to Python services
- Keep OpenAI as fallback
- A/B test with 10% traffic

**Phase 3: Full cutover**
- Switch all traffic to Python services
- Keep OpenAI for backup/failover
- Monitor for 1 week

**Phase 4: Cleanup**
- Remove OpenAI dependency (optional)
- Optimize Python services
- Update documentation

---

## ✅ MVP-1 Checklist

**Before Launch:**

- [ ] All 7 workflows deployed and tested
- [ ] Embedding cache primed with common queries
- [ ] Error handling tested (API failures, timeouts)
- [ ] Monitoring dashboard set up
- [ ] Alert webhooks configured (Slack/email)
- [ ] Rate limiting configured (prevent abuse)
- [ ] Yacht signature validation working
- [ ] All micro-actions mapped to endpoints
- [ ] Frontend integration tested
- [ ] Load testing completed (100 concurrent users)
- [ ] Cost monitoring enabled (OpenAI, n8n)
- [ ] Backup/recovery procedures documented

**Week 1 Post-Launch:**

- [ ] Monitor latency (target: P95 <800ms)
- [ ] Monitor error rate (target: <1%)
- [ ] Check embedding cache hit rate (target: >50%)
- [ ] Review top queries for optimization
- [ ] Gather user feedback on accuracy
- [ ] Identify slow workflows for optimization

---

## 📝 Summary

**MVP-1 is a fully functional n8n-based system that:**

✅ Handles search requests in <800ms
✅ Uses OpenAI/Claude APIs only (no custom hosting)
✅ Supports all core micro-actions
✅ Gracefully handles errors and unsupported requests
✅ Scales to 100+ concurrent users
✅ Costs <$200/month (API + n8n + Supabase)
✅ Can be deployed in 4-6 weeks
✅ Provides clear migration path to MVP-2

**Key Limitations:**
- No streaming responses
- Higher API costs at scale
- Limited NLP customization
- No BM25 or reranking
- No local embedding control

**These limitations are acceptable for validating product-market fit.**

---

**END OF MVP1 WORKFLOW DESIGN**
