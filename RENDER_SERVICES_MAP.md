# Render Services Deployment Map

**Last Updated:** 2026-01-08

---

## 📊 Active Render Services

### Cloud_PMS Repository Services

**Repository:** https://github.com/shortalex12333/Cloud_PMS
**Branch:** `extraction-service`

Both services below run from the **same codebase** (`extraction-service` branch), deployed as separate Render web services:

#### 1. Document Digest Service
- **Service URL:** https://celeste-digest-index.onrender.com
- **Service Name:** `celeste-digest-index`
- **Repository:** Cloud_PMS
- **Branch:** `extraction-service`
- **Runtime:** Python 3.11.8
- **Purpose:** Document ingestion, chunking, embedding, GraphRAG population
- **Main File:** `api/microaction_service.py`
- **Start Command:** `uvicorn api.microaction_service:app --host 0.0.0.0 --port $PORT`

**Endpoints:**
- `POST /webhook/ingest-docs-nas-cloud` - Document upload from local agent
- `POST /webhook/index-documents` - Trigger document indexing
- `GET /health` - Health check
- `GET /patterns` - List extraction patterns

**Security:**
- Yacht signature authentication (HMAC-SHA256)
- Rate limiting (10/min per yacht, 100/min global)
- File validation (500 MB max, content type whitelist)
- Full audit logging

**Environment Variables:**
```bash
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
OPENAI_API_KEY=<openai-key>
YACHT_SALT=e49469e09cb6529e0bfef118370cf8425b006f0abbc77475da2e0cb479af8b18
```

#### 2. Text Extraction Service
- **Service URL:** https://celeste-file-type.onrender.com
- **Service Name:** `celeste-file-type`
- **Repository:** Cloud_PMS
- **Branch:** `extraction-service`
- **Runtime:** Python 3.11.8
- **Purpose:** Extract text from PDFs, DOCX, XLSX, CSV, JSON, XML, HTML
- **Main File:** `api/microaction_service.py` (same codebase)
- **Start Command:** `uvicorn api.microaction_service:app --host 0.0.0.0 --port $PORT`

**Endpoints:**
- `POST /extract` - Extract text from document
- `POST /extract_microactions` - DEPRECATED: Use /extract
- `POST /extract_detailed` - DEPRECATED: Use /extract
- `GET /health` - Health check

**Note:** This service uses the same codebase as Document Digest Service but is deployed separately for isolation and scaling purposes.

---

### Cloud_DMG Repository Service

**Repository:** https://github.com/shortalex12333/Cloud_DMG
**Branch:** `python-implementation`

#### 3. DMG Installer / Onboarding Service
- **Service URL:** https://celesteos-cloud-onboarding.onrender.com (or similar)
- **Service Name:** `celesteos-cloud-onboarding`
- **Repository:** Cloud_DMG
- **Branch:** `python-implementation`
- **Current Commit:** 970acd6 - "Add deployment status report"
- **Runtime:** Python 3
- **Purpose:** Yacht fleet registration, activation, DMG download token generation
- **Main File:** `main.py`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Endpoints:**
- `POST /register` - Yacht registration
- `GET /activate/:yacht_id` - Email activation link
- `POST /check-activation/:yacht_id` - Credential retrieval (ONE TIME ONLY)
- `POST /user-login` - Portal user login (request 2FA code)
- `POST /verify-2fa` - Verify 2FA code, create session
- `POST /download-request` - Request DMG download token
- `GET /download/:token` - Download DMG file
- `GET /health` - Health check

**Backend:**
- **Supabase:** https://qvzmkaamzaqxpzbewjxe.supabase.co (Cloud_HQ)
- **Storage Bucket:** `installers` (DMG files)

**Environment Variables:**
```bash
SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
SUPABASE_SERVICE_KEY=<cloud-hq-service-role-key>
SMTP_HOST=<email-server>
SMTP_PORT=587
SMTP_USER=<email-user>
SMTP_PASSWORD=<email-password>
```

---

## 🗄️ Supabase Databases

### Cloud_PMS Database
- **Project ID:** vzsohavtuotocgrfkfyd
- **URL:** https://vzsohavtuotocgrfkfyd.supabase.co
- **Purpose:** Document processing, search, GraphRAG
- **Used By:**
  - celeste-digest-index.onrender.com
  - celeste-file-type.onrender.com

**Key Tables:**
- `doc_metadata` - Document metadata
- `search_document_chunks` - Text chunks for RAG
- `search_graph_nodes` - GraphRAG entities
- `search_graph_edges` - GraphRAG relationships
- `search_graph_maintenance_facts` - Maintenance knowledge

**Storage Buckets:**
- `yacht-documents` - Uploaded document files

### Cloud_HQ Database
- **Project ID:** qvzmkaamzaqxpzbewjxe
- **URL:** https://qvzmkaamzaqxpzbewjxe.supabase.co
- **Purpose:** Yacht fleet management, user accounts, DMG distribution
- **Used By:**
  - celesteos-cloud-onboarding.onrender.com

**Key Tables:**
- `fleet_registry` - Yacht identities + shared_secret
- `user_accounts` - Portal user accounts
- `user_sessions` - Active sessions
- `twofa_codes` - 2FA verification codes
- `download_links` - DMG download tokens
- `audit_log` - Activity tracking
- `security_events` - Security incidents

**Storage Buckets:**
- `installers` - DMG installer files

---

## 🔄 Deployment Process

### For Cloud_PMS Services (extraction-service branch)

1. **Make changes** in Cloud_PMS repository
2. **Commit and push** to `extraction-service` branch:
   ```bash
   git add -A
   git commit -m "feat: Your change description"
   git push origin extraction-service
   ```
3. **Auto-deploy** on Render (if enabled) for both services:
   - celeste-digest-index
   - celeste-file-type

### For Cloud_DMG Service (python-implementation branch)

1. **Make changes** in Cloud_DMG repository
2. **Commit and push** to `python-implementation` branch:
   ```bash
   git add -A
   git commit -m "feat: Your change description"
   git push origin python-implementation
   ```
3. **Auto-deploy** on Render (if enabled):
   - celesteos-cloud-onboarding

---

## 🧪 Testing Endpoints

### Document Digest Service
```bash
# Health check
curl https://celeste-digest-index.onrender.com/health

# Upload test document (requires yacht signature)
curl -X POST https://celeste-digest-index.onrender.com/webhook/ingest-docs-nas-cloud \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -H "X-Yacht-Signature: <hmac-sha256-signature>" \
  -F "file=@test.pdf" \
  -F 'data={"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","filename":"test.pdf","content_type":"application/pdf","file_size":1000,"system_path":"Test","directories":["Test"],"doc_type":"manual","system_tag":"testing","local_path":"/tmp/test.pdf"}'
```

### Text Extraction Service
```bash
# Health check
curl https://celeste-file-type.onrender.com/health

# Extract text from document
curl -X POST https://celeste-file-type.onrender.com/extract \
  -F "file=@document.pdf"
```

### DMG Onboarding Service
```bash
# Health check
curl https://celesteos-cloud-onboarding.onrender.com/health

# Register yacht
curl -X POST https://celesteos-cloud-onboarding.onrender.com/register \
  -H "Content-Type: application/json" \
  -d '{"yacht_name":"Test Yacht","contact_email":"test@example.com"}'
```

---

## 📝 Notes

- **Same Codebase, Different Services:** `celeste-digest-index` and `celeste-file-type` run from the same `extraction-service` branch but are deployed as separate Render services for isolation and scaling.

- **Auto-Deploy:** All services should have auto-deploy enabled on Render to automatically deploy when code is pushed to their respective branches.

- **Branch Isolation:**
  - Cloud_PMS: `extraction-service` branch
  - Cloud_DMG: `python-implementation` branch
  - Never merge to `main` unless coordinating with team

- **Environment Variables:** Each service requires different environment variables. Verify in Render Dashboard → Service → Environment before deploying.

- **Database Separation:**
  - Cloud_PMS database (vzsohavtuotocgrfkfyd) = Document processing
  - Cloud_HQ database (qvzmkaamzaqxpzbewjxe) = Fleet management, DMG distribution

---

## 🔐 Security

- All services use **service_role** keys for Supabase access
- Document services require **YACHT_SALT** for signature verification
- DMG service requires **SMTP credentials** for email notifications
- All traffic over **HTTPS/TLS 1.2+**
- Rate limiting enabled on all upload endpoints
- Full audit logging on all operations

---

## 📞 Troubleshooting

### Service not responding
1. Check Render Dashboard → Logs for errors
2. Verify environment variables are set
3. Check branch is correct in Render settings
4. Verify health endpoint returns 200

### RLS Policy Issues (403 errors)
- See `FIX_RLS_POLICIES.md` for Cloud_PMS database
- Verify service_role has full access policies on all tables

### Deployment not auto-triggering
1. Check Render Dashboard → Service → Settings
2. Verify "Auto-Deploy" is enabled
3. Verify branch name matches (case-sensitive)
4. Check GitHub webhook is active

---

## 📚 Related Documentation

- `SECURITY_IMPLEMENTATION_COMPLETE.md` - Security implementation for document processing
- `NETWORK_RESILIENCE_COMPLETE.md` - Network resilience for yacht satellite connectivity
- `FIX_RLS_POLICIES.md` - RLS policy troubleshooting for Cloud_PMS database
- `RENDER_DEPLOYMENT.md` - Detailed deployment guide for DMG service (in Cloud_DMG repo)
