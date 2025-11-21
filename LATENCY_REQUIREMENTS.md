# LATENCY_REQUIREMENTS.md

**Version:** 1.0
**Purpose:** Define performance boundaries for CelesteOS operations
**Philosophy:** Users expect instant execution; optimize for perceived speed

---

## 🎯 Core Principle

**Users judge system speed by two metrics:**

1. **Time to First Response (TTFR)** - How quickly something appears on screen
2. **Total Operation Time (TOT)** - How long until the operation is complete

**Strategy:**
- Optimize TTFR aggressively (<200ms)
- Tolerate higher TOT if progress is visible
- Use streaming to improve perceived speed
- Show skeletons/placeholders immediately

---

## 📊 Latency Classification

### **INSTANT (<200ms)**

**Definition:** Feels immediate to users, no perceived delay

**Operations that MUST be instant:**
- Page loads
- Button clicks (visual feedback)
- Input field responses
- Search bar activation
- Navigation
- Micro-action button highlights

**Why:** Human perception threshold is ~100-200ms. Below this, interactions feel "instant".

**How to achieve:**
- Static assets via CDN
- Client-side state updates
- Optimistic UI updates
- Pre-rendered components

---

### **FAST (<500ms)**

**Definition:** Noticeable delay, but acceptable for common operations

**Operations that should be FAST:**
- Search query submission → first result appears
- Simple database lookups
- Yacht signature validation
- Intent detection (LLM call)
- Single micro-action execution
- Document preview loading

**Why:** 500ms is the threshold for "responsive" applications. Users tolerate it for active operations.

**How to achieve:**
- Efficient database indexes
- API call optimization
- Caching where possible
- Parallel requests

---

### **ACCEPTABLE (<1000ms)**

**Definition:** Users notice the wait, but won't complain for infrequent operations

**Operations that can be ACCEPTABLE:**
- Full search results with ranking
- Embedding generation (first query)
- Complex dashboard widgets loading
- Handover export (PDF generation)
- Multi-hop search (rare queries)
- Document upload + processing

**Why:** 1 second is the limit for maintaining user flow. Beyond this, users lose focus.

**How to achieve:**
- Show progress indicators
- Stream partial results
- Use background jobs when possible
- Optimize critical path only

---

### **SLOW (<3000ms)**

**Definition:** Users are waiting noticeably; must show progress

**Operations that may be SLOW:**
- Large PDF exports
- Batch operations (e.g., export all work orders)
- Predictive analysis calculations
- Complex multi-step workflows
- OCR processing
- Graph traversal (multi-hop reasoning)

**Why:** 3 seconds is tolerable IF:
- User explicitly triggered it
- Clear progress is shown
- Operation is infrequent

**How to achieve:**
- Background jobs with webhooks
- Progress bars with ETA
- Async processing
- Optimization for common cases only

---

### **BACKGROUND (>3000ms)**

**Definition:** Too slow for synchronous response; run as background job

**Operations that MUST be background:**
- Bulk document indexing
- Fleet-wide analytics
- Nightly data aggregation
- Large file uploads (>50MB)
- Retraining predictive models
- Full system backups

**Why:** Users won't wait >3 seconds for most operations. Run async and notify on completion.

**How to achieve:**
- Job queues (BullMQ, Celery)
- Webhook callbacks
- Email/Slack notifications
- Progress tracking UI

---

## 🔍 Operation-Specific Requirements

### **SEARCH OPERATIONS**

| Operation | TTFR Target | TOT Target | MVP-1 Actual | MVP-2 Target | Priority |
|-----------|-------------|------------|--------------|--------------|----------|
| **Search input focus** | <50ms | <50ms | ✅ <50ms | ✅ <50ms | 🔴 Critical |
| **Query → first result** | <300ms | <600ms | ~500ms | ~250ms | 🔴 Critical |
| **All results loaded** | N/A | <800ms | ~700ms | ~400ms | 🟡 High |
| **With reranking** | N/A | <1000ms | N/A | ~500ms | 🟢 Medium |
| **Multi-hop search** | <500ms | <2000ms | N/A | ~1200ms | 🟢 Medium |
| **Streaming results** | <200ms | Continuous | N/A | ~200ms TTFR | 🟡 High |

**Optimization Priority:**
1. Search input responsiveness (skeleton UI)
2. First result appearance (stream first, batch rest)
3. Total result quality (reranking can wait)

---

### **MICRO-ACTION EXECUTION**

| Micro-Action | Latency Target | Actual (MVP-1) | MVP-2 Target | Notes |
|--------------|----------------|----------------|--------------|-------|
| `create_work_order` | <400ms | ~300ms | ~250ms | Database insert + validation |
| `add_to_handover` | <300ms | ~200ms | ~150ms | Simple append operation |
| `order_part` | <500ms | ~400ms | ~300ms | Supplier lookup + create PO |
| `update_hours_of_rest` | <300ms | ~250ms | ~200ms | Table update |
| `export_handover` | <2000ms | ~1500ms | ~1000ms | PDF generation |
| `view_document` | <400ms | ~500ms | ~300ms | Signed URL generation |
| `diagnose_fault` | <800ms | ~1000ms | ~500ms | Multi-table join + LLM |
| `predictive_request` | <1500ms | N/A | ~1000ms | ML inference |

**Optimization Priority:**
1. Common actions: `create_work_order`, `add_to_handover` (<300ms)
2. View operations: `view_document`, `view_equipment` (<400ms)
3. Complex operations: Use streaming or progress indicators

---

### **DATABASE OPERATIONS**

| Query Type | Target Latency | Max Acceptable | Optimization |
|------------|----------------|----------------|--------------|
| Primary key lookup | <10ms | 50ms | Indexed |
| Simple SELECT | <20ms | 100ms | Indexed columns |
| JOIN (2-3 tables) | <50ms | 200ms | Proper indexes + EXPLAIN ANALYZE |
| JOIN (4+ tables) | <100ms | 500ms | Materialized views |
| Full-text search | <100ms | 300ms | GIN index on tsvector |
| pgvector similarity | <150ms | 500ms | HNSW index |
| Aggregation (GROUP BY) | <200ms | 1000ms | Covering indexes |
| Complex analytics | <1000ms | 3000ms | Pre-computed or background |

**Rules:**
- Any query >100ms must be indexed or cached
- Any query >500ms must be background job
- Monitor slow query log weekly

---

### **EXTERNAL API CALLS**

| API | Operation | Target Latency | Timeout | Retry Strategy |
|-----|-----------|----------------|---------|----------------|
| **OpenAI** | Embedding (single text) | 200-300ms | 3000ms | 2 retries, exponential backoff |
| **OpenAI** | Chat completion | 500-1500ms | 5000ms | 1 retry |
| **Claude** | Intent detection | 200-400ms | 3000ms | 2 retries |
| **Supabase** | REST API | 50-150ms | 2000ms | 3 retries |
| **Supabase** | Storage (upload) | 500-2000ms | 10000ms | 2 retries |
| **Python Service** | Search | 100-250ms | 2000ms | 2 retries, circuit breaker |
| **Python Service** | Embeddings | 100-150ms | 2000ms | 2 retries, circuit breaker |
| **Python Service** | NLP | 50-100ms | 1000ms | 2 retries |

**Optimization:**
- Use fastest model variants (e.g., Haiku > Sonnet)
- Batch API calls when possible
- Implement circuit breakers for unstable services
- Cache aggressively

---

### **FRONTEND OPERATIONS**

| Operation | Target | Measurement | Why |
|-----------|--------|-------------|-----|
| **First Contentful Paint** | <1200ms | Lighthouse | User sees something |
| **Time to Interactive** | <2000ms | Lighthouse | User can interact |
| **Search page load** | <800ms | Custom metric | Critical page |
| **Dashboard page load** | <1500ms | Custom metric | Widget-heavy |
| **API request (client → n8n)** | <100ms | Network tab | Geographic latency |
| **Result card render** | <50ms | React DevTools | Per card |
| **Skeleton → content** | <500ms | Custom metric | Perceived speed |

**Optimization:**
- Use Next.js SSR for fast initial load
- Code splitting (lazy load dashboard widgets)
- CDN for static assets (Vercel Edge Network)
- Minimize JavaScript bundle size

---

## ⚡ Latency Budgets by User Journey

### **Journey 1: Search for Fault Information**

**User Action:** Types "CAT 3512 overheating" and presses Enter

| Step | Component | Budget | Actual (MVP-1) | MVP-2 Target |
|------|-----------|--------|----------------|--------------|
| 1. Input blur → webhook call | Frontend | 50ms | ✅ 30ms | ✅ 30ms |
| 2. n8n receives → intent detection | n8n orchestration | 100ms | ✅ 80ms | ✅ 80ms |
| 3. Intent detection (Claude API) | External API | 300ms | ⚠️ 350ms | ✅ 250ms |
| 4. Generate embedding | OpenAI API / Python | 200ms | ⚠️ 250ms | ✅ 150ms |
| 5. Parallel search (vector + text) | Supabase / Python | 200ms | ✅ 180ms | ✅ 100ms |
| 6. Merge + return results | n8n code node | 50ms | ✅ 40ms | ✅ 30ms |
| 7. Frontend renders cards | React | 100ms | ✅ 70ms | ✅ 70ms |
| **TOTAL (TTFR)** | | **400ms** | ⚠️ **500ms** | ✅ **300ms** |
| **TOTAL (all results)** | | **1000ms** | ⚠️ **1000ms** | ✅ **710ms** |

**Bottleneck (MVP-1):** Intent detection + embedding generation (600ms)

**Fix (MVP-2):**
- Use Claude Haiku (faster): 350ms → 250ms
- Self-hosted embeddings: 250ms → 150ms
- **Total savings: 200ms**

---

### **Journey 2: Create Work Order from Fault**

**User Action:** Clicks "Create Work Order" button on fault card

| Step | Component | Budget | Actual | Notes |
|------|-----------|--------|--------|-------|
| 1. Button click → API call | Frontend | 50ms | ✅ 40ms | Optimistic UI |
| 2. n8n receives → validate | n8n | 50ms | ✅ 45ms | |
| 3. Pre-fill WO (fetch equipment) | Supabase | 100ms | ✅ 80ms | Single query |
| 4. Insert work order | Supabase | 100ms | ✅ 90ms | Indexed insert |
| 5. Link to fault | Supabase | 50ms | ✅ 40ms | Foreign key |
| 6. Return confirmation | n8n → frontend | 50ms | ✅ 35ms | |
| **TOTAL** | | **400ms** | ✅ **330ms** | |

**Optimization:** Use optimistic UI (show success immediately, revert on error)

---

### **Journey 3: Export Handover to PDF**

**User Action:** Clicks "Export Handover" in dashboard

| Step | Component | Budget | Actual | Notes |
|------|-----------|--------|--------|-------|
| 1. Button click → API call | Frontend | 50ms | ✅ 40ms | Show loading state |
| 2. Fetch handover data | Supabase | 200ms | ✅ 180ms | Multi-table join |
| 3. Generate PDF | Python service | 1500ms | ⚠️ 1800ms | Heavy operation |
| 4. Upload to Storage | Supabase Storage | 300ms | ✅ 250ms | |
| 5. Return signed URL | n8n → frontend | 50ms | ✅ 40ms | |
| **TOTAL** | | **2100ms** | ⚠️ **2310ms** | Acceptable for rare operation |

**Optimization:** Background job + email link (future)

---

## 🎯 Percentile Targets

**Why percentiles matter:**
- Average latency hides outliers
- P95/P99 shows real user experience
- Focus on worst 5% of requests

### **Target SLOs:**

| Metric | Target | Alert Threshold | Action |
|--------|--------|------------------|--------|
| **P50 (Median)** | <400ms | >600ms | Investigate bottleneck |
| **P95** | <800ms | >1200ms | Critical issue |
| **P99** | <1500ms | >2500ms | Monitor for patterns |
| **P99.9** | <3000ms | >5000ms | Acceptable if rare |

### **Per Operation Type:**

| Operation Type | P50 | P95 | P99 |
|----------------|-----|-----|-----|
| **Search** | <350ms | <700ms | <1200ms |
| **Simple Actions** | <250ms | <500ms | <800ms |
| **Complex Actions** | <600ms | <1200ms | <2000ms |
| **Exports** | <1500ms | <2500ms | <4000ms |

---

## 📊 Monitoring & Alerts

### **What to Track:**

```sql
-- Create latency tracking table
CREATE TABLE latency_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  operation_type TEXT NOT NULL,  -- 'search', 'action', 'export'
  operation_name TEXT,  -- specific operation
  yacht_id UUID,
  user_id UUID,
  latency_ms INT NOT NULL,
  ttfr_ms INT,  -- Time to first response
  components JSONB,  -- Breakdown by component
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast querying
CREATE INDEX idx_latency_logs_operation ON latency_logs(operation_type, created_at);
CREATE INDEX idx_latency_logs_yacht ON latency_logs(yacht_id, created_at);
```

### **Dashboard Queries:**

**P95 Latency by Operation:**
```sql
SELECT
  operation_type,
  operation_name,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) as p50,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99,
  COUNT(*) as total_requests
FROM latency_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY operation_type, operation_name
ORDER BY p95 DESC;
```

**Slow Queries (outliers):**
```sql
SELECT
  operation_name,
  latency_ms,
  components,
  created_at
FROM latency_logs
WHERE latency_ms > 2000
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY latency_ms DESC
LIMIT 50;
```

**Component Breakdown:**
```sql
-- Requires components JSONB like:
-- { "intent_detection": 300, "embedding": 250, "search": 180, "rendering": 70 }

SELECT
  operation_name,
  AVG((components->>'intent_detection')::int) as avg_intent,
  AVG((components->>'embedding')::int) as avg_embedding,
  AVG((components->>'search')::int) as avg_search,
  AVG((components->>'rendering')::int) as avg_rendering
FROM latency_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND components IS NOT NULL
GROUP BY operation_name;
```

---

## 🚨 Alert Rules

### **Critical Alerts (Page Immediately):**

1. **P95 search latency >1200ms for 5 minutes**
   - Indicates systemic issue
   - Check: API status, database performance, n8n health

2. **Error rate >5% for any operation**
   - Major degradation
   - Check: Service logs, API status

3. **Service health check fails 3 times in a row**
   - Service is down
   - Check: Render dashboard, restart if needed

### **Warning Alerts (Slack/Email):**

1. **P95 search latency >800ms for 15 minutes**
   - Gradual degradation
   - Investigate: Slow queries, API latency

2. **Error rate >2% for 10 minutes**
   - Elevated errors
   - Check: Logs for patterns

3. **Embedding cache hit rate <40%**
   - Cache inefficiency
   - Review: Cache strategy, TTL settings

---

## 🔧 Optimization Techniques

### **1. Caching**

| What | Where | TTL | Expected Hit Rate |
|------|-------|-----|-------------------|
| Query embeddings | Supabase | 7 days | >60% |
| Common searches | Redis | 1 hour | >40% |
| Document URLs | In-memory | 5 min | >80% |
| User sessions | Supabase | 24 hours | >90% |

### **2. Parallelization**

**Before (Sequential):**
```
Intent (300ms) → Embedding (250ms) → Search (180ms) = 730ms
```

**After (Parallel):**
```
Intent (300ms)
    ↓
Embedding (250ms) || Equipment lookup (100ms)
    ↓
Search (180ms) = 530ms total
```

**Savings: 200ms (27% faster)**

### **3. Indexing**

**Required Indexes:**
```sql
-- Vector similarity (HNSW)
CREATE INDEX idx_chunks_embedding ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Full-text search
CREATE INDEX idx_chunks_search ON document_chunks
USING gin (search_vector);

-- Equipment lookup
CREATE INDEX idx_equipment_yacht_name ON equipment(yacht_id, name);

-- Fault code lookup
CREATE INDEX idx_faults_yacht_code ON faults(yacht_id, fault_code);
```

### **4. Streaming**

**Impact on Perceived Latency:**

**Before (Batch):**
- TTFR: 700ms
- User waits 700ms before seeing anything

**After (Streaming):**
- TTFR: 200ms (first result)
- Results continue streaming
- **Perceived latency: 71% better**

---

## ✅ Performance Checklist

**Before MVP-1 Launch:**
- [ ] All database queries <100ms (check with EXPLAIN ANALYZE)
- [ ] All critical indexes created
- [ ] Embedding cache enabled and tested
- [ ] API timeouts configured (max 5 seconds)
- [ ] Retry logic implemented (exponential backoff)
- [ ] Error handling for all external APIs
- [ ] Latency logging enabled
- [ ] Dashboard queries optimized
- [ ] Load testing completed (100 concurrent users)
- [ ] P95 latency <800ms confirmed

**MVP-2 Optimization Targets:**
- [ ] P95 latency <400ms
- [ ] TTFR <200ms for search
- [ ] Streaming responses working
- [ ] BM25 search <50ms
- [ ] Local embeddings <150ms
- [ ] Component-level latency tracking
- [ ] Automated alerts configured
- [ ] Horizontal scaling tested

---

## 📈 Continuous Improvement

**Monthly Review:**
1. Analyze P95/P99 trends
2. Identify slowest operations
3. Review slow query log
4. Update indexes as needed
5. Optimize bottlenecks
6. Test improvements
7. Deploy optimizations

**Quarterly Review:**
1. Re-evaluate latency targets
2. Compare to competitors
3. Gather user feedback
4. Plan infrastructure upgrades
5. Update documentation

---

**END OF LATENCY REQUIREMENTS**
