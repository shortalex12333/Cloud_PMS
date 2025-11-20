# CelesteOS Cloud API

**Worker 3 — Cloud API Carpenter**

FastAPI-based REST API for CelesteOS yacht management system.

## 🏗️ Architecture

```
cloud/api/
├── main.py                 # FastAPI application entry point
├── app/
│   ├── core/              # Core utilities
│   │   ├── config.py      # Settings and configuration
│   │   ├── supabase.py    # Supabase client wrapper
│   │   ├── auth.py        # JWT authentication & yacht context
│   │   └── exceptions.py  # Custom exceptions
│   ├── models/            # Pydantic models
│   │   ├── base.py        # Base response models
│   │   └── auth.py        # Auth models
│   └── api/
│       └── v1/            # API v1 routes
│           └── endpoints/
│               ├── auth.py          # Authentication
│               ├── search.py        # Search (RAG)
│               ├── work_orders.py   # Work orders
│               ├── handovers.py     # Handovers
│               ├── notes.py         # Notes & comments
│               └── documents.py     # Documents & equipment
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd cloud/api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_HOURS=24
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Application
ENVIRONMENT=development  # development, staging, production
API_VERSION=v1

# CORS
CORS_ORIGINS=["http://localhost:3000","https://app.celesteos.com"]

# Storage
STORAGE_BUCKET_UPLOADS=yacht-uploads
STORAGE_BUCKET_DOCUMENTS=yacht-documents

# Indexing Pipeline (optional)
INDEXING_PIPELINE_URL=http://localhost:9000
```

### 3. Run Development Server

```bash
uvicorn main:app --reload --port 8000
```

API will be available at: `http://localhost:8000`

## 📖 API Documentation

Interactive API docs automatically available (in development mode):

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

All API endpoints require:

1. **X-Yacht-Signature header**: Identifies the yacht
2. **Authorization header**: JWT Bearer token

### Example Request

```bash
curl -X POST http://localhost:8000/v1/search \
  -H "X-Yacht-Signature: yacht-abc-123" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"query":"engine fault code 123","mode":"auto"}'
```

### Login Flow

```bash
# 1. Login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@yacht.com",
    "password": "password123",
    "yacht_signature": "yacht-abc-123"
  }'

# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {...},
  "yacht": {...}
}

# 2. Use access token in subsequent requests
curl -X GET http://localhost:8000/v1/work-orders \
  -H "X-Yacht-Signature: yacht-abc-123" \
  -H "Authorization: Bearer eyJ..."

# 3. Refresh token when expired
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ...",
    "yacht_signature": "yacht-abc-123"
  }'
```

## 🛣️ API Routes

### Authentication (`/v1/auth`)

- `POST /login` - User login
- `POST /refresh` - Refresh access token
- `POST /revoke` - Revoke token
- `GET /me` - Get current user info

### Search (`/v1/search`)

- `POST /search` - Hybrid RAG search across documents, equipment, history

### Work Orders (`/v1/work-orders`)

- `POST /work-orders` - Create work order
- `GET /work-orders` - List work orders
- `GET /work-orders/{id}` - Get work order
- `PATCH /work-orders/{id}/status` - Update status

### Handovers (`/v1/handovers`)

- `POST /handovers` - Create handover draft
- `GET /handovers/{id}` - Get handover
- `POST /handovers/{id}/items` - Add item to handover
- `GET /handovers/{id}/items` - List handover items
- `POST /handovers/{id}/export` - Export to PDF/HTML

### Notes (`/v1/notes`)

- `POST /notes` - Create note
- `GET /notes` - List notes (with filters)

### Documents & Equipment (`/v1/documents`, `/v1/equipment`)

- `GET /documents` - List documents
- `GET /documents/{id}` - Get document
- `GET /equipment` - List equipment
- `GET /equipment/{id}` - Get equipment details

## 🔧 Middleware & Features

### Yacht Context Injection

Every authenticated request automatically includes `YachtContext`:

```python
from fastapi import Depends
from app.core.auth import get_current_user, YachtContext

@router.get("/example")
async def example(context: YachtContext = Depends(get_current_user)):
    # context.yacht_id
    # context.yacht_signature
    # context.user_id
    # context.user_role
    pass
```

### Role-Based Access Control

```python
from app.core.auth import require_role

@router.delete("/admin-only")
async def admin_endpoint(context: YachtContext = Depends(require_role("admin"))):
    pass
```

### Error Handling

All errors return consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "WorkOrder not found",
    "details": {
      "resource": "WorkOrder",
      "id": "uuid-here"
    }
  }
}
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py -v
```

## 📦 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Production environment variables must be set:

- `ENVIRONMENT=production`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `JWT_SECRET` (strong random key)
- `CORS_ORIGINS` (whitelist only your domains)

### Health Check

```bash
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "version": "v1",
  "environment": "production"
}
```

## 🔌 Integration Points

### With n8n Workflows

The API works alongside n8n workflows for:
- **File ingestion**: n8n handles chunk assembly
- **Indexing pipeline**: API triggers n8n indexing workflow
- **Background jobs**: n8n runs scheduled tasks

### With Supabase

Direct integration with:
- **Database**: Postgres with pgvector
- **Storage**: Object storage for files
- **Auth** (optional): Can use Supabase Auth alongside custom JWT

## 🚧 Constraints (Worker 3 Role)

As "Cloud API Carpenter", this API implementation:

✅ **Includes:**
- All API route scaffolding
- JWT middleware and authentication
- Yacht context injection
- Supabase client integration
- Error handling and validation
- CRUD operations for PMS data

❌ **Does NOT include:**
- **Ingestion logic** (handled by n8n workflows)
- **Search/RAG logic** (delegated to search service)
- **Indexing pipeline** (separate worker/service)
- **Document processing** (OCR, chunking, embeddings)

These are delegated to specialized workers/services as per the architecture.

## 📚 Related Documentation

- `api-spec.md` - Complete API specification
- `security.md` - Security requirements
- `architecture.md` - System architecture
- `cloud/n8n-workflows/` - n8n ingestion workflows

## 🛠️ Development

### Code Style

```bash
# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

### Adding New Endpoints

1. Create route in `app/api/v1/endpoints/`
2. Define Pydantic models in `app/models/`
3. Add to router in `app/api/v1/__init__.py`
4. Test with pytest

## 📞 Support

For issues or questions, see the main project documentation.

---

**Version**: 1.0.0
**Last Updated**: 2025-11-20
**Worker**: Cloud API Carpenter (Worker 3)
