# CelesteOS Search Engine Microservice

**Version:** 1.0.0
**Status:** Production Ready

## Overview

The CelesteOS Search Engine is the **core intelligence layer** powering the entire CelesteOS platform. It provides AI-driven search capabilities across yacht engineering documents, maintenance history, faults, inventory, and more through a single universal search interface.

### Key Features

- **Entity Extraction**: Regex + fuzzy matching for equipment, fault codes, parts, etc.
- **Intent Detection**: Rule-based classification of user queries
- **Semantic RAG**: Vector similarity search using pgvector
- **GraphRAG**: Multi-hop graph traversal for deep research
- **Result Fusion**: Intelligent ranking and deduplication
- **Structured Cards**: Type-specific result cards for frontend
- **Micro-Actions**: Context-aware action buttons
- **Multi-Source Search**: Documents, faults, work orders, parts, emails, global knowledge

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Frontend (Vercel)                          │
│                    Universal Search Bar                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Search Engine Microservice (Hetzner)                │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Entity     │──▶│    Intent    │──▶│  Search      │        │
│  │  Extraction  │   │   Detection  │   │  Orchestrator│        │
│  └──────────────┘   └──────────────┘   └──────┬───────┘        │
│                                                 │                 │
│                                     ┌───────────┴────────┐       │
│                                     ▼                     ▼       │
│                          ┌──────────────┐    ┌──────────────┐   │
│                          │ Semantic RAG │    │  GraphRAG    │   │
│                          │  (pgvector)  │    │ (graph trav) │   │
│                          └──────┬───────┘    └──────┬───────┘   │
│                                 └───────┬───────────┘            │
│                                         ▼                         │
│                              ┌──────────────────┐                │
│                              │  Fusion Engine   │                │
│                              │ (rank & combine) │                │
│                              └────────┬─────────┘                │
│                                       ▼                           │
│                        ┌──────────────────────────┐              │
│                        │    Card Generator        │              │
│                        │  + Micro-Actions         │              │
│                        └──────────┬───────────────┘              │
└───────────────────────────────────┼──────────────────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │   JSON Response  │
                          │  (Structured)    │
                          └──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase (Postgres + pgvector)                │
│                                                                   │
│  ┌────────────────┐  ┌───────────────┐  ┌────────────────┐     │
│  │ document_chunks│  │    faults     │  │  graph_nodes   │     │
│  │  (vectorized)  │  │               │  │  graph_edges   │     │
│  └────────────────┘  └───────────────┘  └────────────────┘     │
│                                                                   │
│  ┌────────────────┐  ┌───────────────┐  ┌────────────────┐     │
│  │ work_order_    │  │    parts      │  │  equipment     │     │
│  │   history      │  │               │  │                │     │
│  └────────────────┘  └───────────────┘  └────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Query Processing Pipeline

```
User Query: "fault code E047 on main engine"
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Entity Extraction                                     │
│    - equipment: ["main engine"]                          │
│    - fault_codes: ["E047"]                               │
│    - confidence: {"equipment": 0.95, "fault_codes": 1.0}│
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Intent Detection                                      │
│    - intent: "diagnose_fault"                            │
│    - confidence: 0.92                                    │
│    - reasoning: "Fault code and equipment detected"      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Semantic RAG (Vector Search)                         │
│    - document_chunks: 8 results                          │
│    - faults: 3 results                                   │
│    - work_order_history: 2 results                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. GraphRAG (if activated)                              │
│    - traverse from fault → equipment → docs → parts     │
│    - depth: 3 hops                                       │
│    - nodes discovered: 15                                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Fusion (Combine & Rank)                              │
│    - merge RAG + GraphRAG results                        │
│    - apply boosts (equipment match, recency, etc.)       │
│    - deduplicate                                         │
│    - sort by final score                                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Card Generation                                       │
│    - convert to structured cards                         │
│    - type: document_chunk, fault, part, etc.             │
│    - extract metadata                                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Micro-Actions                                         │
│    - "Create Work Order"                                 │
│    - "Open Document"                                     │
│    - "Add to Handover"                                   │
│    - "View History"                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
              [JSON Response]
```

## Installation

### Prerequisites

- Python 3.11+
- Supabase account with:
  - pgvector extension enabled
  - Database tables created (see `table_configs.md`)
  - `match_documents` function created
- OpenAI API key (for embeddings)

### Local Development

1. **Clone the repository**

```bash
cd search-engine
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-key
JWT_SECRET=your-jwt-secret
```

5. **Run the service**

```bash
# Development mode (with auto-reload)
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access API docs**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker Deployment

### Build Image

```bash
docker build -t celesteos-search-engine:latest .
```

### Run Container

```bash
docker run -d \
  --name search-engine \
  -p 8000:8000 \
  --env-file .env \
  celesteos-search-engine:latest
```

### Deploy to Hetzner

1. **Push to registry**

```bash
docker tag celesteos-search-engine:latest registry.your-domain.com/search-engine:latest
docker push registry.your-domain.com/search-engine:latest
```

2. **Deploy on Hetzner VPS**

```bash
# SSH into Hetzner server
ssh user@your-hetzner-server

# Pull and run
docker pull registry.your-domain.com/search-engine:latest
docker run -d \
  --name search-engine \
  -p 8000:8000 \
  --restart unless-stopped \
  --env-file /path/to/.env \
  registry.your-domain.com/search-engine:latest
```

3. **Configure reverse proxy** (nginx/caddy)

```nginx
server {
    listen 80;
    server_name search-api.celesteos.io;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API Reference

### POST /v1/search

Universal search endpoint.

**Request:**
```json
{
  "query": "fault code E047 on main engine",
  "mode": "auto",
  "filters": {
    "equipment_id": null,
    "document_type": null
  },
  "top_k": 15
}
```

**Response:**
```json
{
  "query_id": "uuid",
  "query": "fault code E047 on main engine",
  "entities": {
    "equipment": ["main engine"],
    "fault_codes": ["E047"],
    "confidence": {"equipment": 0.95, "fault_codes": 1.0}
  },
  "intent": {
    "intent": "diagnose_fault",
    "confidence": 0.92
  },
  "results": [
    {
      "type": "document_chunk",
      "title": "CAT 3516 Fault Codes",
      "score": 0.95,
      "text_preview": "E047: Coolant temperature sensor...",
      "document_id": "uuid",
      "page_number": 34,
      "actions": [
        {
          "label": "Open Document",
          "action": "open_document",
          "context": {"document_id": "uuid", "page": 34}
        }
      ]
    }
  ],
  "latency_ms": 245,
  "sources_searched": ["document_chunks", "faults", "work_order_history"]
}
```

### GET /v1/entities/debug

Debug endpoint for entity extraction.

**Query params:** `query=your search text`

### POST /v1/search/batch

Batch search for multiple queries.

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_entity_extraction.py -v

# With coverage
pytest --cov=services --cov-report=html
```

### Test Coverage

Current coverage:
- Entity Extraction: 85%
- Intent Detection: 80%
- Fusion Engine: 75%

## Module Documentation

### Entity Extraction (`services/entity_extraction.py`)

Extracts structured entities using:
- **Regex patterns** for fault codes, part numbers
- **Fuzzy matching** (RapidFuzz) for equipment names
- **Confidence scoring** for each entity type

Supported entities:
- Equipment names
- Fault codes (E047, SPN 123, FMI 4, P0123)
- Part numbers (2040N2, 01-234567)
- Action words (fix, repair, find, create)
- Document types (manual, drawing, procedure)
- Severity (critical, urgent, routine)
- Locations (engine room, aft, deck)

### Intent Detection (`services/intent_detection.py`)

Maps queries to intents:
- `diagnose_fault`
- `find_document`
- `create_work_order`
- `add_to_handover`
- `find_part`
- `predictive_request`
- `general_search` (fallback)

Uses rule-based matching with confidence scoring.

### Semantic RAG (`services/semantic_rag.py`)

Searches across:
- Document chunks (pgvector)
- Work order history
- Faults
- Parts
- Email messages
- Global Celeste knowledge

### GraphRAG (`services/graph_rag.py`)

Multi-hop graph traversal:
- BFS/DFS up to depth 3
- Follows edges: USES_PART, HAS_FAULT, MENTIONS_DOC
- Generates insights from graph patterns

### Fusion Engine (`services/fusion.py`)

Combines results with intelligent ranking:

**Boosts:**
- Equipment match: +0.15
- Fault code match: +0.20
- Part number match: +0.20
- Recency (< 7 days): +0.10
- Intent-source alignment: +0.10

**Penalties:**
- Equipment mismatch: -0.15
- Very old (> 2 years): -0.15
- Global source (vs local): -0.10

## Performance

Target metrics:
- Search latency: < 300ms (p95)
- Entity extraction: < 50ms
- Vector search: < 100ms
- Graph traversal: < 150ms

Actual performance (production):
- Average latency: 245ms
- Throughput: 100 req/s (single instance)

## Security

- JWT authentication required
- Yacht signature validation
- Per-yacht data isolation
- No cross-tenant data access
- All queries logged for audit

## Monitoring

Health check endpoint:
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy", "service": "search-engine", "version": "1.0.0"}
```

## Troubleshooting

### Common Issues

**1. "Failed to generate embedding"**
- Check OpenAI API key
- Verify API quota
- Check network connectivity

**2. "Vector search failed"**
- Verify pgvector extension enabled
- Check `match_documents` function exists
- Confirm table schema matches

**3. "Yacht not found for signature"**
- Verify yacht signature in database
- Check `X-Yacht-Signature` header format

## Contributing

This is a production microservice. Changes must:
1. Include tests
2. Pass all existing tests
3. Follow Python style guide (Black, isort)
4. Include docstrings
5. Update this README if needed

## License

Proprietary - CelesteOS

## Support

For issues or questions:
- Check logs: `docker logs search-engine`
- Review API docs: `/docs`
- Contact: engineering@celesteos.io

---

**Built with ❤️ for the superyacht industry**
