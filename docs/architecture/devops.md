# 🛠️ **devops.md — CelesteOS DevOps & Infrastructure Specification**

**Version:** 1.0
**Owner:** Infrastructure Engineering**
**Status:** Approved for MVP**

---

# # 🌐 **1. Core Principles**

CelesteOS infrastructure is based on **three non-negotiables**:

### **1. Security-first**

Every yacht is its *own isolated tenant*, with strict encryption, access control, and per-vessel resource boundaries.

### **2. Reliability & Redundancy**

Service must survive failure of:

* a node
* storage subsystem
* a single region
* networking issue
* Starlink outage
* individual VPS corruption

### **3. Simplicity > Cleverness**

We do not over-architect.
We favour **predictable, repeatable, observable** systems.

Quality > cost.
If we waste resources to guarantee reliability, that’s acceptable.

---

# # 🧱 **2. Infrastructure Overview (Hetzner Cloud)**

CelesteOS runs as **multiple isolated deployments**, each representing a *yacht* or *yacht group*.

A deployment includes:

```
- API Server (FastAPI / Node)
- Search Engine (Render.com Python)
- Indexing Workers (OCR & Embeddings)
- Vector DB (Supabase pgvector)
- Postgres (Supabase managed)
- Object Storage (Supabase buckets)
- n8n Workflow Orchestrator
- Reverse Proxy + Load Balancer (traefik / nginx)
- Monitoring + Logging
```

Isolation architecture ensures that failure for one yacht does **not** affect any others.

---

# # 🚢 **3. Per-Yacht Isolation Strategy**

Every yacht gets **its own environment** consisting of:

* **Dedicated S3 bucket** (Supabase Storage)
* **Dedicated DB schema** (Supabase Postgres)
* **Dedicated n8n workflows** (namespaced)
* **Dedicated worker queues**
* **Unique yacht_signature key**
* **Dedicated API namespace** (optional)

For ultra-high-security clients, you may create:

* **a dedicated VPS**
* **a dedicated Postgres instance**
* **a dedicated vector store instance**

This architecture minimises blast radius.

---

# # 📦 **4. Containerization Strategy**

The following CelesteOS services run in Docker containers:

* **API Gateway / Backend**
* **n8n Orchestrator**
* **OCR Worker**
* **Embedding Worker**
* **GraphRAG Worker**
* **Indexing Pipeline**
* **Event Processor**

Containers are deployed using:

* **Docker Compose** for small deployments
* **Nomad** or **Kubernetes (Hetzner CSI)** for multi-yacht scaling

**All containers are ephemeral**, stateless, and automatically rebuilt on update.

---

# # 🔐 **5. Secrets & Environment Management**

Use:

* **1Password Secrets Automation**
* or **Hashicorp Vault** (preferred)
* fallback: `.env.production` stored ONLY in encrypted Hetzner Volume

Secrets include:

* JWT signing keys
* yacht_signature mapping
* DB connection strings
* S3 storage keys
* embedding API keys
* Render.com microservice URLs
* n8n API keys

No secrets stored in GitHub.

---

# # 🔄 **6. DNS & Reverse Proxy**

### **6.1 DNS Structure**

Each yacht gets:

```
<yachtname>.celesteos.cloud
```

Or:

```
engine.<yachtname>.domain (custom record)
```

### **6.2 Reverse Proxy**

Use **Traefik** or **Nginx**:

* TLS termination
* ACME auto SSL via Let’s Encrypt
* Rate limiting
* IP whitelisting (optional)
* Strict CORS enforcement

### **6.3 HTTP Routing**

Routes map to:

```
/v1/api → backend API
/v1/search → search engine (proxied to Render)
/v1/ingest → upload endpoints
/mobile → mobile API
```

---

# # 📊 **7. Monitoring, Logging & Observability**

### **7.1 Metrics**

Use **Grafana + Prometheus**:

* API latency
* search latency
* worker queue depth
* indexing duration
* resource usage
* memory per container
* prediction run times
* error rate per endpoint

### **7.2 Logs**

Centralized log aggregation:

* Loki
* or Elastic if needed

### **7.3 Alerts**

On:

* ingestion failures
* indexing failures
* search failures
* high error rate
* CVE security events
* node crashes
* CPU > 80%

Notifications to:

* Slack
* PagerDuty
* Email fallback

---

# # 🔁 **8. Backup Strategy**

Since quality > cost, backups are **redundant + frequent**.

### **8.1 Supabase/PG Backups**

* Full backup every 6 hours
* PITR (Point-In-Time Recovery) enabled
* Retention: 90 days

### **8.2 Object Storage Backups**

* Daily snapshot to secondary region
* Optionally: duplicate to AWS S3 for redundancy
* Retention: 90 days

### **8.3 n8n Workflows**

* Versioned
* Auto-export nightly
* Stored in backup bucket

### **8.4 Disaster Recovery**

If catastrophic:

* create new Supabase project
* restore DB
* re-link buckets
* redeploy containers
* re-issue yacht_signatures

Recovery expected: **< 45 minutes**

---

# # 🧲 **9. Deployment Flow (CI/CD)**

### **Branching**

* `main` = production
* `develop` = staging
* `hotfix/*`
* `feature/*`

### **CI Pipeline (GitHub Actions or GitLab)**

* lint
* test
* container build
* scan for vulnerabilities
* push to GHCR Docker registry

### **CD Pipeline**

If `main`:

* deploy to Hetzner servers
* restart containers with zero downtime
* clear CDN caches
* notify team

Staging environment also available.

---

# # 🕸️ **10. Cloud Worker Architecture**

Workers include:

### **10.1 OCR Worker**

* consumes “ocr” queue
* processes scanned PDFs/images
* returns page text

### **10.2 Embedding Worker**

* consumes “embed” queue
* sends text to embedding model
* stores embedding vectors

### **10.3 GraphRAG Worker**

* builds nodes/edges in graph table
* updates graph relationships

### **10.4 Cleanup Worker**

* deletes stale incomplete uploads
* removes unused chunks
* cleans orphan rows

All workers run with:

* concurrency limits
* resource throttling
* retry logic
* circuit breakers

---

# # 🔄 **11. Isolation of Upload Buckets**

Each yacht has:

```
/yachts/<yacht_id>/raw/
/yachts/<yacht_id>/indexed/
/yachts/<yacht_id>/handover/
/yachts/<yacht_id>/backups/
```

Permissions enforced via:

* signed URLs
* row-level security
* cloud gateway token validation
* yacht_signature binding

No crew can access other yacht storage.
Backend ensures yacht_signature matches bucket path.

---

# # 🧬 **12. Handling Heavy Cloud Loads**

CelesteOS is document-heavy (manuals, PDFs, drawings).
Cloud architecture must assume:

* multi-gigabyte uploads
* large manuals
* concurrency from email indexing
* global knowledge ingestion

### Scaling Strategy:

* horizontal scaling of ingestion workers
* auto-scaling on Render / Hetzner
* async queues (low latency)
* streaming uploads (no memory overflow)

**We prioritise quality indexing over speed**.
If indexing takes hours → acceptable.
If accuracy drops → unacceptable.

---

# # 🔐 **13. Zero-Trust Principle**

Everything assumes “untrusted actor” unless verified.

### Applied Through:

* token validation
* strict RLS on DB
* yacht_signature
* no direct port exposure
* deny-all default firewall
* all container-to-container traffic behind private network

This prevents lateral movement on a compromised VPS.

---

# # 🔥 **14. Summary**

CelesteOS DevOps engineering is aligned with:

### **✔ Security-first**

Per-yacht isolation, encrypted storage, strict boundary enforcement.

### **✔ Reliability-first**

Backups, multi-region redundancy, monitoring.

### **✔ Cloud-first**

All compute happens off-vessel for consistency.

### **✔ Simplicity & maintainability**

Predictable deployments, containerization, clear pipelines.

### **✔ Scalability**

Workers, queues, autoscaling, fleet-level structure.

Cost efficiency is *secondary*.
We prioritise **quality, accuracy, and resilience** to produce a yacht-grade product.

---
