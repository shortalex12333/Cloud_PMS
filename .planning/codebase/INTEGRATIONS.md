# CelesteOS External Integrations

## Overview
CelesteOS integrates with multiple cloud services and external APIs to enable email synchronization, document processing, AI-powered extraction, and third-party workflow automation.

---

## Supabase (Multi-Tenant Database Platform)

### Purpose
- Primary database (PostgreSQL)
- Authentication and JWT management
- Row-level security (RLS) enforcement
- Cloud storage for documents
- Real-time subscriptions

### Configuration
**Master Database** (Tenant routing and authentication):
```
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_ANON_KEY=<JWT token>
MASTER_SUPABASE_SERVICE_KEY=<service role token>
MASTER_SUPABASE_JWT_SECRET=<signing secret>
```

**Tenant Databases** (Per-yacht data isolation):
```
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=<service role token>
TENANT_SUPABASE_JWT_SECRET=<signing secret>
```

**Yacht-Specific Configuration** (Dynamic routing):
```
y{YACHT_ID}_SUPABASE_URL=<tenant instance URL>
y{YACHT_ID}_SUPABASE_SERVICE_KEY=<service token>
```

### Integration Points
- **Backend Client**: `integrations/supabase.py`
  - Singleton Supabase client initialization
  - Vector search with pgvector
  - RPC calls for custom functions
  - Row-level security enforcement
  - Storage bucket operations
- **Frontend Client**: `@supabase/supabase-js`
  - Real-time subscriptions to email threads
  - Document metadata queries
  - Work order mutations
- **Authentication**: JWT token validation and tenant routing
- **Storage Buckets**:
  - Documents (vessel/receiving/work_orders)
  - Email attachments
  - Evidence files
  - Handover exports

### Key Tables
- `email_watchers` - User OAuth tokens for Outlook sync
- `email_threads` - Email conversation threads
- `email_messages` - Individual email messages
- `email_links` - Associations between emails and objects (work orders, documents, etc.)
- `documents` - Evidence and reference documents
- `work_orders` - Maintenance and repair requests
- `equipment` - Vessel equipment inventory
- `parts` - Spare parts and consumables
- `receiving` - Incoming goods and inspections

---

## Microsoft Outlook / Microsoft Graph API

### Purpose
- Real-time email synchronization
- Email attachment access
- User profile information
- OAuth 2.0 authentication

### Endpoints
- **Base URL**: https://graph.microsoft.com/v1.0
- **Token URL**: https://login.microsoftonline.com/common/oauth2/v2.0/token

### OAuth Configuration (Dual-App Architecture)
**Read App** (Mail.Read scope):
```
AZURE_READ_APP_ID=41f6dc82-8127-4330-97e0-c6b26e6aa967
AZURE_READ_CLIENT_SECRET=<secret>
```

**Write App** (Mail.Send scope):
```
AZURE_WRITE_APP_ID=f0b8944b-8127-4f0f-8ed5-5487462df50c
AZURE_WRITE_CLIENT_SECRET=<secret>
```

### Integration Points
- **Graph Client**: `integrations/graph_client.py`
  - Strict read/write token separation
  - Automatic token refresh (5-minute proactive skew)
  - Rate limiting and exponential backoff
  - Error handling for expired/revoked tokens
- **Email Sync Service**: `services/email_sync_service.py`
  - Delta queries for incremental sync (Inbox/Sent)
  - Message metadata extraction (no body storage)
  - Attachment metadata collection
  - Web link retrieval for "Open in Outlook" feature
- **Email Routes**: `routes/email.py`
  - GET `/email/related` - Thread retrieval by object type
  - GET `/email/thread/{thread_id}` - Full thread with messages
  - GET `/email/message/{provider_message_id}/render` - Message content
  - GET `/email/message/{message_id}/attachments` - Attachment list
  - GET `/email/message/{provider_message_id}/attachments/{id}/download` - Download
  - POST `/email/sync/now` - Manual sync trigger

### Message Fields Selected
```
id, conversationId, subject, from, toRecipients, ccRecipients,
receivedDateTime, sentDateTime, hasAttachments, internetMessageId,
webLink, bodyPreview
```

### Features
- **Proactive Token Refresh**: Tokens refreshed 5 minutes before expiry
- **Rate Limiting**: Microsoft Graph API throttling respect
- **Delta Sync**: Incremental updates using delta links
- **Error Isolation**: Structured OAuth errors vs Celeste session errors
- **Watcher Status**: Degraded/normal health tracking per user

### Email Worker
- **Process**: `workers/email_watcher_worker.py`
- **Frequency**: Periodic sync for connected users
- **Scope**: Inbox and Sent folders
- **Output**: Email threads, messages, links to work orders/documents

---

## OpenAI API

### Purpose
- Entity extraction from documents and email
- AI-powered classification and suggestions
- Maritime domain knowledge inference

### Configuration
```
OPENAI_API_KEY=sk-proj-<key>
AI_MODEL=gpt-4o-mini (default)
```

### Integration Points
- **AI Extractor**: `extraction/ai_extractor_openai.py`
  - AsyncOpenAI client for async/await support
  - Lazy-load pattern (only initialized when API key present)
  - Graceful degradation if API unavailable
- **Prompt Engineering**: Maritime-specific entity extraction
  - Equipment names (Caterpillar, Volvo Penta, etc.)
  - Location on board (engine room, bridge, etc.)
  - Parts and consumables
  - Vessel systems and components

### Use Cases
1. **Document OCR Processing**: Extract entity candidates from uploaded images
2. **Email Body Extraction**: Entity detection from email text
3. **Micro-Action Extraction**: Detect user intent and actions
4. **Entity Completion**: Generate missing entity fields
5. **Smart Linking**: Suggest document/email associations

### Request Pattern
```python
prompt = f"""Extract maritime entities from text:
- Equipment with brands
- Locations on board (explicit mentions only)
- Parts and consumables
- Work descriptions

Return JSON: {{
  "entities": {{
    "equipment": [...],
    "org": [...],
    "location_on_board": [...],
    "parts": [...]
  }}
}}"""

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    timeout=30
)
```

### Fallback Strategy
- If API unavailable: Return empty extraction (graceful degradation)
- User can manually add entities via UI
- No blocking failures on AI extraction

---

## Image Processing Microservice (OCR)

### Purpose
- Document image upload processing
- Optical Character Recognition (OCR)
- Document classification

### Endpoint
```
IMAGE_PROCESSOR_URL=https://image-processing-givq.onrender.com
```

### Integration
- **Proxy Route**: `routes/receiving_upload.py`
  - Endpoint: `POST /api/receiving/{receiving_id}/upload`
  - Multipart file upload with metadata
  - JWT token passthrough to OCR service
  - RLS enforcement via token

### Request Parameters
```
- file: UploadFile (image)
- receiving_id: UUID
- comment: Optional string
- doc_type: invoice|packing_slip|photo|other
- Authorization: Bearer <JWT>
```

### Response
```json
{
  "document_id": "uuid",
  "storage_path": "yacht_id/receiving/receiving_id/...",
  "ocr_text": "extracted text",
  "confidence": 0.95
}
```

### Workflow
1. User uploads image via frontend
2. Backend proxies to image-processing service with JWT
3. Service performs OCR and stores in Supabase Storage
4. Returns document metadata
5. Extraction pipeline triggered on OCR text
6. User reviews and adjusts extracted entities (optional)
7. User signs (SIGNED variant) to accept and create records

---

## n8n Workflow Automation

### Purpose
- Complex multi-step workflow orchestration
- Business logic automation
- System integration

### Configuration
```
N8N_BASE_URL=<n8n instance URL>
N8N_AUTH_TOKEN=<optional bearer token>
```

### Dispatcher
- **File**: `action_router/dispatchers/n8n_dispatcher.py`
- **Pattern**: Forward complex actions to n8n webhooks
- **Registry**: Centralized mapping in `N8N_WORKFLOWS`

### Workflow Mappings
```python
N8N_WORKFLOWS = {
    # Work Orders
    "create_work_order": "/webhook/create_work_order",
    "create_work_order_fault": "/webhook/create_work_order",

    # Handovers
    "add_to_handover": "/webhook/add_to_handover",
    "add_document_to_handover": "/webhook/add_document_to_handover",
    "add_part_to_handover": "/webhook/add_part_to_handover",
    "add_predictive_to_handover": "/webhook/add_predictive_to_handover",
    "export_handover": "/webhook/export_handover",

    # Inventory
    "order_part": "/webhook/order_part",
}
```

### Integration Pattern
- **Deprecated**: N8N handler type marked for phase-out
- **Status**: All production handlers are now INTERNAL (Python)
- **Legacy**: n8n_dispatcher.py maintained for reference

### Request Format
```
POST {N8N_BASE_URL}{workflow_path}
Headers:
  - Content-Type: application/json
  - Authorization: Bearer {N8N_AUTH_TOKEN} (if configured)
Body: JSON payload with action params + user context
Timeout: 30 seconds
```

---

## Email Linking & Association System

### Purpose
- Link emails to work orders, documents, equipment, parts
- Suggest associations via AI
- Track email evidence for tasks

### Integration Points
- **Linking Ladder**: `services/linking_ladder.py`
  - Candidate entity finder for suggestions
  - Linking validation and persistence
- **Email RAG System**: `email_rag/` directory
  - Semantic search over email corpus
  - Entity extraction from email bodies
  - Context-aware linking suggestions
- **API Routes**: `routes/email.py`
  - `POST /email/link/add` - Create manual link
  - `POST /email/link/accept` - Accept suggestion
  - `POST /email/link/change` - Modify target
  - `POST /email/link/remove` - Soft delete

### Linking Ladder Algorithm
1. Extract candidate entities from email
2. Semantic similarity to work orders/documents
3. Temporal proximity scoring (recent items prioritized)
4. Confidence scoring with threshold
5. Present suggestions to user for acceptance

### Evidence Workflow
- `POST /email/evidence/save-attachment` - Save email attachment as document
- Stores to Supabase Storage with yacht_id isolation
- Links automatically to relevant records
- Maintains audit trail of evidence source

---

## Email Embedding & Semantic Search

### Purpose
- Vector-based semantic search over emails
- Context-aware similarity matching
- Multi-modal search (keyword + semantic)

### Integration
- **Embedding Service**: `services/email_embedding_service.py`
  - OpenAI embedding model (text-embedding-3-small)
  - Async embedding generation
  - Batch processing for efficiency
- **Search Routes**: `routes/email.py` and `routes/search_streaming.py`
  - `GET /email/search?q=query&limit=10` - Hybrid search

### Vector Database
- **Backend**: Supabase pgvector extension
- **Dimensions**: 1536 (OpenAI embeddings)
- **Storage**: `email_embeddings` table
- **Index**: Vector HNSW index for performance

---

## Rate Limiting

### Purpose
- Respect Microsoft Graph API quotas
- Prevent service exhaustion
- Graceful degradation under load

### Implementation
- **Rate Limiter**: `services/rate_limiter.py` (MicrosoftRateLimiter)
- **Storage**: Supabase rate_limit_counters
- **Strategy**: Token bucket algorithm
- **Exponential Backoff**: Automatic retry with increasing delays

### Throttling Patterns
- Per-user rate limiting
- Per-endpoint rate limiting
- Tenant-wide quotas
- Graceful 429 handling with retry-after headers

---

## Feature Flags

### Purpose
- Gradual rollout of new features
- A/B testing capabilities
- Quick disable without redeployment

### Configuration
- **File**: `integrations/feature_flags.py`
- **Storage**: Supabase feature_flags table
- **Environment Variables**:
  ```
  FAULT_LENS_V1_ENABLED=true
  EMAIL_TRANSPORT_ENABLED=true
  ```

### Usage
```python
if check_email_feature("EMAIL_TRANSPORT", yacht_id):
    # Enable email sync for yacht
```

---

## Authentication & JWT

### Token Architecture
- **Master Issuer**: Master Supabase for central auth
- **Tenant Tokens**: JWT signed with tenant-specific secret
- **Scope Separation**: Read tokens (Mail.Read), Write tokens (Mail.Send)
- **Service Tokens**: Service role for backend operations

### JWT Claims
```json
{
  "iss": "supabase",
  "sub": "user_id",
  "email": "user@example.com",
  "yacht_id": "uuid",
  "role": ["Engineer", "HOD", "Manager"],
  "iat": 1234567890,
  "exp": 1234654290
}
```

### Validation
- **Auth Middleware**: `middleware/auth.py`
- **JWT Validator**: `action_router/validators/jwt_validator.py`
- **Token Refresh**: Automatic via graph_client proactive refresh

---

## CORS & Cross-Origin Security

### Configuration
```
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,https://app.celeste7.ai
```

### Enforcement
- FastAPI CORS middleware
- Preflight request handling
- Credentials with SameSite cookies

---

## Monitoring & Observability

### Logging
- Structured logging to Supabase
- Email watcher status tracking
- Rate limit monitoring
- Error telemetry

### Health Checks
- Supabase connectivity verification
- Microsoft Graph API health
- OpenAI API availability
- n8n webhook accessibility

---

## Security Patterns

### Multi-Layer Isolation
1. **Authentication**: JWT validation at API boundary
2. **Tenant Isolation**: yacht_id in all queries
3. **Row-Level Security**: Supabase RLS policies
4. **Token Separation**: Read/Write scope isolation
5. **Rate Limiting**: Abuse prevention

### Credential Management
- All secrets in environment variables
- Service role tokens for backend only
- Anon tokens with RLS enforcement for client
- OAuth token refresh on demand

### Data Protection
- No email body storage (metadata only)
- No sensitive data in logs
- Encryption in transit (HTTPS)
- Encryption at rest (Supabase managed)

---

## Configuration File Patterns

### Environment Files
- `.env` - Local development
- `.env.local` - Machine-specific overrides
- `.env.test` - Test environment
- `.env.production` - Production deployment

### Required Integrations Checklist
- [ ] Supabase (master + tenant databases)
- [ ] Microsoft Azure OAuth apps (read + write)
- [ ] OpenAI API key
- [ ] Image processing service URL
- [ ] n8n base URL (optional for deprecated actions)
- [ ] Redis connection string
- [ ] CORS allowed origins

