# CelesteOS Cloud Ingestion API

Cloud-side ingestion service for receiving and processing document uploads from CelesteOS Local Agents running on yachts.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for production deployment)
- Supabase account with database and storage
- n8n instance for workflow orchestration

### Development Setup

1. **Clone and navigate to the directory:**
   ```bash
   cd ingestion-api
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

5. **Run database migrations:**
   ```bash
   psql $DATABASE_URL -f ../supabase/migrations/001_ingestion_tables.sql
   ```

6. **Run the API:**
   ```bash
   python main.py
   ```

   The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build the image:**
   ```bash
   docker build -t celesteos-ingestion-api .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name celesteos-ingestion \
     -p 8000:8000 \
     -v /var/celesteos/uploads:/var/celesteos/uploads \
     -v $(pwd)/.env:/app/.env \
     --restart unless-stopped \
     celesteos-ingestion-api
   ```

3. **Check health:**
   ```bash
   curl http://localhost:8000/v1/health
   ```

## 📡 API Endpoints

### Public Endpoints

- `POST /v1/ingest/init` - Initialize file upload
- `PATCH /v1/ingest/upload_chunk` - Upload single chunk
- `POST /v1/ingest/complete` - Complete and trigger indexing
- `GET /v1/health` - Health check

### Internal Endpoints

- `POST /internal/indexer/start` - Start indexing (called by n8n)
- `POST /internal/cron/cleanup_uploads` - Clean expired uploads

## 🔐 Authentication

All endpoints require the `X-Yacht-Signature` header:

```bash
curl -H "X-Yacht-Signature: your-yacht-signature" \
  http://localhost:8000/v1/ingest/init
```

## 🗂️ Project Structure

```
ingestion-api/
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── models.py            # Pydantic models
├── auth.py              # Authentication middleware
├── storage.py           # Temporary storage manager
├── supabase_client.py   # Supabase integration
├── n8n_trigger.py       # n8n workflow trigger
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image definition
├── .env.example         # Environment variables template
└── README.md            # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_storage.py -v
```

## 📊 Monitoring

### Logs

View logs in real-time:
```bash
docker logs -f celesteos-ingestion
```

### Metrics

Key metrics to monitor:
- Upload success rate
- Average upload duration
- Chunk verification failures
- Storage usage
- Rate limit hits

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "celesteos-ingestion-api",
  "version": "1.0.0"
}
```

## 🔧 Configuration

All configuration via environment variables (see `.env.example`):

### Required Variables

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Service role key
- `SUPABASE_JWT_SECRET` - JWT secret for token validation
- `N8N_WEBHOOK_URL` - n8n indexing webhook URL

### Optional Variables

- `API_PORT` - API port (default: 8000)
- `TEMP_UPLOAD_DIR` - Temporary storage path
- `MAX_CHUNK_SIZE` - Maximum chunk size in bytes
- `RATE_LIMIT_PER_YACHT_HOUR` - Uploads per yacht per hour

## 🛡️ Security Features

- ✅ Yacht signature authentication
- ✅ Per-yacht data isolation
- ✅ SHA256 integrity verification
- ✅ File extension whitelist
- ✅ Rate limiting per yacht
- ✅ Size limits (chunks and files)
- ✅ Automatic expired upload cleanup

## 🐛 Troubleshooting

### Upload Fails with "Invalid yacht signature"

**Cause:** Yacht signature not found in database
**Solution:** Verify yacht exists in `yachts` table with matching signature

### Chunk Hash Mismatch

**Cause:** Corrupted data during transmission
**Solution:** Local Agent will automatically retry the chunk

### n8n Trigger Fails

**Cause:** Webhook URL unreachable or incorrect
**Solution:** Check `N8N_WEBHOOK_URL` in `.env` and verify n8n is running

### Disk Space Issues

**Cause:** Temp uploads not being cleaned up
**Solution:** Run cleanup endpoint or verify cron job is scheduled

```bash
curl -X POST http://localhost:8000/internal/cron/cleanup_uploads
```

## 📚 Documentation

- [Complete Documentation](../docs/cloud-ingestion.md)
- [API Specification](../api-spec.md)
- [Architecture Overview](../architecture.md)
- [Security Model](../security.md)

## 🤝 Contributing

1. Follow PEP 8 style guide
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## 📝 License

Copyright © 2024 CelesteOS. All rights reserved.

---

For issues or questions, see the main project documentation in `/docs/`
