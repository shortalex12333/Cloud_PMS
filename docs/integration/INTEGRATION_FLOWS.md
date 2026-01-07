# CelesteOS Integration Flows

This document contains all integration flow diagrams showing how components communicate.

## Table of Contents

1. [Authentication Flow](#1-authentication-flow)
2. [Search Flow](#2-search-flow)
3. [Ingestion Flow](#3-ingestion-flow)
4. [Predictive Flow](#4-predictive-flow)
5. [Handover Flow](#5-handover-flow)
6. [Work Order Creation Flow](#6-work-order-creation-flow)
7. [Document Access Flow](#7-document-access-flow)

---

## 1. Authentication Flow

User authentication and yacht context retrieval.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Supabase Auth
    participant Cloud API
    participant Supabase DB

    User->>Frontend: Enter credentials
    Frontend->>Supabase Auth: signInWithPassword()
    Supabase Auth->>Supabase Auth: Validate credentials
    Supabase Auth-->>Frontend: JWT (access_token + refresh_token)

    Frontend->>Cloud API: GET /v1/users/me<br/>(Authorization: Bearer JWT)
    Cloud API->>Cloud API: Validate JWT
    Cloud API->>Cloud API: Extract user_id from JWT
    Cloud API->>Supabase DB: SELECT * FROM users WHERE id=user_id
    Supabase DB-->>Cloud API: User record (with yacht_id, role)
    Cloud API-->>Frontend: User context

    Frontend->>Frontend: Store session + user context
    Frontend->>User: Authentication complete
```

**Key Points:**
- Frontend NEVER stores passwords
- JWT contains: `user_id`, `yacht_id`, `role`, `exp`
- All API calls include JWT in Authorization header
- Yacht context injected server-side from JWT

---

## 2. Search Flow

Universal search bar query processing.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Cloud API
    participant Search Engine
    participant Supabase

    User->>Frontend: Type search query
    Frontend->>Cloud API: GET /v1/search?q=...&yacht_id=...<br/>(Authorization: Bearer JWT)

    Cloud API->>Cloud API: Validate JWT
    Cloud API->>Cloud API: Extract yacht_id

    Cloud API->>Search Engine: POST /v1/search<br/>(yacht_id, query, mode)

    Search Engine->>Search Engine: Extract entities
    Search Engine->>Search Engine: Detect intent

    Search Engine->>Supabase: Vector search (pgvector)<br/>document_chunks
    Supabase-->>Search Engine: Top-K similar chunks

    Search Engine->>Supabase: SQL queries<br/>(equipment, faults, parts, work_orders)
    Supabase-->>Search Engine: Structured data

    opt Deep Mode
        Search Engine->>Supabase: GraphRAG traversal<br/>(graph_nodes, graph_edges)
        Supabase-->>Search Engine: Connected entities
    end

    Search Engine->>Search Engine: Fusion + ranking
    Search Engine->>Search Engine: Generate result cards
    Search Engine->>Search Engine: Generate micro-actions

    Search Engine-->>Cloud API: SearchResponse<br/>(results[], actions[])
    Cloud API-->>Frontend: SearchResponse

    Frontend->>User: Display cards + actions
```

**Key Points:**
- Cloud API acts as gateway and validates JWT
- Search Engine performs entity extraction + intent detection
- Vector search uses pgvector for semantic similarity
- GraphRAG activated for complex queries
- Results returned as typed cards with micro-actions

---

## 3. Ingestion Flow

Document upload from Local Agent to cloud indexing.

```mermaid
sequenceDiagram
    participant Local Agent
    participant Cloud API
    participant Supabase Storage
    participant n8n Pipeline
    participant Search Engine
    participant Supabase DB

    Local Agent->>Local Agent: Scan NAS for changes
    Local Agent->>Local Agent: Compute SHA256
    Local Agent->>Local Agent: Chunk file (8-32MB)

    Local Agent->>Cloud API: POST /v1/ingest/init<br/>(yacht_signature, filename, sha256, size)
    Cloud API->>Cloud API: Validate yacht_signature
    Cloud API-->>Local Agent: upload_id, storage_key, expected_chunks

    loop For each chunk
        Local Agent->>Cloud API: PATCH /v1/ingest/chunk<br/>(upload_id, chunk_index, chunk_data)
        Cloud API->>Supabase Storage: Upload chunk to temp bucket
        Cloud API-->>Local Agent: Chunk accepted
    end

    Local Agent->>Cloud API: POST /v1/ingest/complete<br/>(upload_id, total_chunks, sha256)

    Cloud API->>Cloud API: Assemble chunks
    Cloud API->>Cloud API: Verify SHA256
    Cloud API->>Supabase Storage: Move to permanent bucket
    Cloud API->>Supabase DB: INSERT INTO documents
    Cloud API->>n8n Pipeline: Trigger indexing webhook
    Cloud API-->>Local Agent: document_id, queued_for_indexing: true

    n8n Pipeline->>Supabase Storage: Fetch document
    n8n Pipeline->>n8n Pipeline: OCR (if needed)
    n8n Pipeline->>n8n Pipeline: Text cleaning
    n8n Pipeline->>n8n Pipeline: Chunking (~500 tokens)
    n8n Pipeline->>n8n Pipeline: Metadata extraction

    n8n Pipeline->>Search Engine: Generate embeddings<br/>(chunks)
    Search Engine-->>n8n Pipeline: Vectors (1536 dim)

    n8n Pipeline->>Supabase DB: INSERT INTO document_chunks<br/>(text, embedding, metadata)
    n8n Pipeline->>Supabase DB: INSERT INTO graph_nodes/edges
    n8n Pipeline->>Supabase DB: UPDATE documents SET indexed=true

    n8n Pipeline-->>Cloud API: Indexing complete
```

**Key Points:**
- Local Agent uploads in chunks for reliability
- Cloud verifies SHA256 integrity
- n8n orchestrates indexing pipeline
- OCR runs in cloud (consistent across fleet)
- Embeddings generated centrally
- Graph nodes/edges built for GraphRAG

---

## 4. Predictive Flow

Predictive maintenance calculation and insight generation.

```mermaid
sequenceDiagram
    participant Cron Job
    participant Predictive Engine
    participant Supabase DB
    participant Search Engine
    participant Dashboard

    Cron Job->>Predictive Engine: POST /internal/cron/predictive_refresh<br/>(yacht_id)

    Predictive Engine->>Supabase DB: Fetch signals<br/>(faults, work_orders, parts, search_queries)
    Supabase DB-->>Predictive Engine: Signal data

    Predictive Engine->>Supabase DB: Fetch graph data<br/>(equipment relationships)
    Supabase DB-->>Predictive Engine: Graph nodes/edges

    Predictive Engine->>Search Engine: GraphRAG analysis<br/>(equipment dependencies, fault patterns)
    Search Engine-->>Predictive Engine: Multi-hop insights

    Predictive Engine->>Predictive Engine: Calculate signal scores:<br/>- fault_signal<br/>- work_order_signal<br/>- crew_activity_signal<br/>- part_consumption_signal<br/>- global_knowledge_signal

    Predictive Engine->>Predictive Engine: Compute risk score<br/>(weighted combination)

    Predictive Engine->>Predictive Engine: Generate summary + recommendations

    Predictive Engine->>Supabase DB: UPSERT predictive_state<br/>(equipment_id, risk_score, signals, summary)

    Predictive Engine-->>Cron Job: Calculation complete

    User->>Dashboard: View Dashboard
    Dashboard->>Cloud API: GET /v1/predictive/state
    Cloud API->>Supabase DB: SELECT * FROM predictive_state
    Supabase DB-->>Cloud API: Predictive state
    Cloud API-->>Dashboard: High-risk equipment list
    Dashboard->>User: Display risk cards
```

**Key Points:**
- Runs on schedule (every 6 hours)
- Analyzes 19 signals across 5 categories
- Uses GraphRAG for multi-hop reasoning
- Risk scores: 0.00 - 1.00
- Results cached in `predictive_state` table
- Dashboard pulls cached results (fast)

---

## 5. Handover Flow

Search-triggered handover item addition.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Cloud API
    participant Supabase DB

    User->>Frontend: Search for fault/equipment
    Frontend->>Cloud API: Search request
    Cloud API-->>Frontend: Results with "Add to Handover" action

    User->>Frontend: Click "Add to Handover"
    Frontend->>Cloud API: POST /v1/handovers/items<br/>(handover_id, source_type, source_id, summary)

    Cloud API->>Cloud API: Validate JWT + yacht_id

    Cloud API->>Supabase DB: SELECT handover WHERE id=handover_id<br/>AND yacht_id=yacht_id
    Supabase DB-->>Cloud API: Handover record

    alt Handover exists and belongs to yacht
        Cloud API->>Supabase DB: INSERT INTO handover_items<br/>(handover_id, source_type, source_id, summary)
        Supabase DB-->>Cloud API: Item created
        Cloud API-->>Frontend: Success
        Frontend->>User: "Added to handover"
    else Handover not found or access denied
        Cloud API-->>Frontend: 403 Forbidden
        Frontend->>User: Error message
    end
```

**Key Points:**
- Triggered from search result micro-actions
- Server validates yacht ownership
- Can add: faults, work orders, notes, documents, predictive insights
- 80% auto-generated during handover export

---

## 6. Work Order Creation Flow

Creating work order from search action.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Cloud API
    participant Supabase DB
    participant Predictive Engine

    User->>Frontend: Search "fault code E047 main engine"
    Frontend->>Cloud API: Search request
    Cloud API-->>Frontend: Results with "Create Work Order" action

    User->>Frontend: Click "Create Work Order"
    Frontend->>Frontend: Pre-fill form<br/>(equipment_id, fault context)

    User->>Frontend: Submit work order
    Frontend->>Cloud API: POST /v1/work-orders<br/>(equipment_id, title, priority, etc.)

    Cloud API->>Cloud API: Validate JWT + yacht_id
    Cloud API->>Cloud API: Inject created_by = user_id

    Cloud API->>Supabase DB: INSERT INTO work_orders<br/>(yacht_id, equipment_id, title, status, priority, created_by)
    Supabase DB-->>Cloud API: Work order created

    Cloud API->>Supabase DB: Log event<br/>(event_type: work_order_created)

    opt Update Predictive State
        Cloud API->>Predictive Engine: POST /v1/predictive/calculate<br/>(equipment_id)
        Predictive Engine->>Supabase DB: Recalculate risk score
    end

    Cloud API-->>Frontend: Work order ID
    Frontend->>User: "Work order created"
```

**Key Points:**
- Context passed from search results
- Equipment, fault, and description pre-filled
- Yacht isolation enforced server-side
- Event logged for analytics
- Triggers predictive recalculation

---

## 7. Document Access Flow

Retrieving documents with signed URLs.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Cloud API
    participant Supabase DB
    participant Supabase Storage

    User->>Frontend: Click "Open Document" (from search)
    Frontend->>Cloud API: GET /v1/documents/{document_id}/url<br/>(Authorization: Bearer JWT)

    Cloud API->>Cloud API: Validate JWT + extract yacht_id

    Cloud API->>Supabase DB: SELECT * FROM documents<br/>WHERE id=document_id
    Supabase DB-->>Cloud API: Document record

    Cloud API->>Cloud API: Verify document.yacht_id == user.yacht_id

    alt Access granted
        Cloud API->>Supabase Storage: Create signed URL<br/>(expires in 1 hour)
        Supabase Storage-->>Cloud API: Signed URL

        Cloud API->>Supabase DB: Log event<br/>(event_type: document_accessed)

        Cloud API-->>Frontend: { url, expires_at }
        Frontend->>User: Open document in new tab
        User->>Supabase Storage: GET {signed_url}
        Supabase Storage-->>User: Document file
    else Access denied
        Cloud API-->>Frontend: 403 Forbidden
        Frontend->>User: Error message
    end
```

**Key Points:**
- Documents never exposed directly
- Signed URLs expire after 1 hour
- Yacht isolation enforced
- Access logged for audit trail
- Frontend opens in new tab (no download unless requested)

---

## Integration Layer Summary

### Frontend → Cloud API
- **Protocol:** HTTPS/REST
- **Auth:** JWT in Authorization header
- **Format:** JSON
- **Streaming:** SSE for search results

### Cloud API → Search Engine
- **Protocol:** HTTP/REST
- **Auth:** Internal service token
- **Format:** JSON
- **Includes:** yacht_id in every request

### Cloud API → Predictive Engine
- **Protocol:** HTTP/REST
- **Auth:** Internal service token
- **Format:** JSON
- **Caching:** Results cached in Supabase

### Cloud API → Supabase
- **Protocol:** REST API + Supabase SDK
- **Auth:** Service role key (backend)
- **RLS:** Yacht isolation enforced
- **Vector Search:** pgvector extension

### Local Agent → Cloud API
- **Protocol:** HTTPS/REST
- **Auth:** yacht_signature + agent_token
- **Upload:** Chunked (8-32MB)
- **Resume:** Supported via upload_id

### n8n → Services
- **Triggers:** Webhooks
- **Calls:** Supabase API, Search Engine
- **Orchestration:** Document indexing pipeline

---

## Security Boundaries

```mermaid
graph TD
    A[Frontend] -->|JWT| B[Cloud API]
    C[Local Agent] -->|yacht_signature + agent_token| B
    B -->|Service Token| D[Search Engine]
    B -->|Service Token| E[Predictive Engine]
    B -->|Service Key| F[Supabase]
    G[n8n] -->|Webhook| B
    G -->|Service Token| D
    G -->|Service Key| F
    D -->|Service Key| F
    E -->|Service Key| F

    style B fill:#f9f,stroke:#333,stroke-width:4px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```

**Trust Boundaries:**
1. **Public:** Frontend, Local Agent
2. **Gateway:** Cloud API (validates all requests)
3. **Internal:** Search Engine, Predictive Engine, n8n
4. **Data:** Supabase (enforces RLS)

---

## Yacht Isolation Enforcement

Every request path enforces yacht isolation:

1. **JWT contains `yacht_id`** (set at login)
2. **Cloud API extracts `yacht_id`** from JWT
3. **All database queries filter by `yacht_id`**
4. **RLS policies enforce yacht-level access**
5. **Cross-yacht queries are impossible**

Example SQL pattern:
```sql
SELECT * FROM work_orders
WHERE yacht_id = :yacht_id_from_jwt
  AND id = :requested_id;
```

---

## Error Handling

All integration points implement:

- **Retry logic** (exponential backoff)
- **Circuit breakers** (prevent cascade failures)
- **Timeout enforcement** (prevent hanging requests)
- **Graceful degradation** (fallback when services unavailable)
- **Error logging** (centralized observability)

---

## Performance Characteristics

| Endpoint | Expected Latency | Timeout |
|----------|-----------------|---------|
| `/v1/search` | < 500ms | 5s |
| `/v1/predictive/state` | < 200ms (cached) | 2s |
| `/v1/work-orders` | < 300ms | 3s |
| Document upload | Depends on size | 10min |
| Indexing pipeline | 30s - 5min | 15min |

---

## Monitoring Points

Key integration points to monitor:

- [ ] JWT validation success rate
- [ ] Search Engine response time
- [ ] Predictive Engine calculation time
- [ ] Supabase query performance
- [ ] Document upload success rate
- [ ] Indexing pipeline completion rate
- [ ] Signed URL expiration hits
- [ ] Cross-service error rates

