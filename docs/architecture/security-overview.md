## **security-overview.md** **CelesteOS Security & Safety Model**

CelesteOS is engineered with a **zero-trust**, cloud-first security model designed to protect sensitive engineering data, crew information, vessel documents, and operational history across all yachts.

This document outlines how user safety, access control, and data protection are enforced across the entire platform.

---

# ## **1. Identity & Authentication**

### **1.1 Microsoft SSO (Primary Auth)**

All human users authenticate through **Microsoft Entra ID / Outlook SSO**.

* Eliminates password reuse
* Enforces organisation-wide security policies
* Integrates seamlessly with maritime IT already using Outlook
* Reduces attack surface

### **1.2 Multi-Factor Authentication (MFA)**

MFA is enforced through the Microsoft Authenticator app.
MFA is only requested when:

* logging in from a new device
* high-risk IP/location
* long period of inactivity

Day-to-day UX remains smooth.

### **1.3 Supabase Auth Backend**

Supabase Auth manages:

* JWT access tokens
* refresh tokens
* session lifecycle
* revocation
* device-aware authentication

CelesteOS does **not** handle raw passwords.

---

# ## **2. Role-Based Access Control (RBAC)**

Each user belongs to:

* a **yacht**
* a **role** (Engineer, HOD, ETO, Manager, etc)

Permissions are enforced at:

* frontend (UI-level gating)
* backend (API-level enforcement)
* database (Row-Level Security)

This ensures users:

* only see their yacht’s data
* only perform role-appropriate actions

---

# ## **3. Multi-Yacht Data Isolation**

Isolation is enforced using:

### **3.1 Dedicated `yacht_id` on every table row**

Every piece of data in the platform includes:

```
yacht_id: uuid
```

### **3.2 Row-Level Security (RLS)**

All Supabase tables enforce:

* `auth.uid()` → user_id
* user_id → yacht_id
* queries filtered by yacht_id

No crew member can see into another yacht, ever.

### **3.3 Dedicated storage buckets**

Each yacht has:

```
/yachts/<yacht_id>/raw
/yachts/<yacht_id>/indexed
/yachts/<yacht_id>/handover
```

Buckets are isolated with signed URLs and strict policies.

---

# ## **4. Local Agent Security (Mac Studio / Mac Mini)**

The local ingestion agent (onboard hardware) is not a login device.

### **4.1 One-time provisioning**

During setup, the agent is issued:

* `yacht_id`
* `agent_secret` (hashed in DB)
* optional: device fingerprint

### **4.2 All agent → cloud communication**

* HMAC signatures or JWT using `agent_secret`
* mutual TLS (optional, recommended)
* rate-limited endpoints

### **4.3 No crew credentials stored on hardware**

The agent operates entirely as a service account.

### **4.4 Read-only access**

Agent mounts NAS in read-only mode to prevent tampering.

---

# ## **5. Data Upload Integrity**

### **5.1 SHA256 fingerprinting**

Every file uploaded includes:

* SHA256 hash
* last modified timestamp
* source path

Used for:

* deduplication
* integrity checks
* detecting changes

### **5.2 Incremental Sync**

Only changed files are re-uploaded, ensuring:

* efficiency
* reduced bandwidth
* safety for long-running ingestion jobs

### **5.3 Transport Security**

All uploads via:

* HTTPS / TLS 1.3
* optionally mTLS for agents

---

# ## **6. Encryption**

### **6.1 In Transit**

All communication:

* HTTPS
* TLS 1.3
* HSTS enforced

### **6.2 At Rest**

Supabase automatically encrypts:

* Postgres storage
* object storage
* backups
* metadata

No plaintext storage anywhere.

---

# ## **7. Application Safety & Guardrails**

### **7.1 No lateral movement**

No page or API call allows users to “traverse” beyond:

* their yacht
* their permissions
* their data scope

### **7.2 Intent Validation**

Before executing any user action (e.g., “create work order”), backend validates:

* authenticated user
* role
* yacht
* intent
* input safety

### **7.3 Search Safety**

Search engine never:

* exposes another yacht’s data
* leaks tokens
* leaks file paths
* provides unsafe content

### **7.4 No hallucinations for actions**

The backend uses deterministic rules:

* regex validation
* metadata checks
* permission checks

If ambiguous → system asks a clarifying question.

---

# ## **8. Logging & Audit**

The system logs:

* logins
* failed attempts
* API actions
* file uploads
* config changes
* agent communication

Stored in `event_logs` per yacht.

Audit supports:

* ISM compliance
* engineering accountability
* incident reconstruction

---

# ## **9. Incident Recovery & Backups**

### **9.1 Supabase PITR**

Point-in-time recovery enables restoration to any minute in the last 7–30 days.

### **9.2 Multi-region backups**

Object storage backups can be mirrored to another region.

### **9.3 Disaster Recovery**

If catastrophic:

* restore DB snapshot
* relink storage buckets
* redeploy containers
  Estimated downtime < **45 minutes**.

---

# ## **10. Hardening Measures**

* Strict CORS
* Content-Security-Policy
* SameSite cookies
* Secure httpOnly tokens
* API rate limiting
* No unauthenticated endpoints
* Minimal exposed surface
* Dependency scanning
* Regular container rebuilds

---

# ## **11. Summary**

CelesteOS enforces security through:

* **Microsoft SSO + MFA**
* **Supabase Auth JWTs**
* **Role-based access control**
* **Per-yacht data isolation**
* **Row-level security**
* **Strict bucket isolation**
* **Secure local ingestion agent**
* **SHA256 integrity checks**
* **TLS everywhere**
* **Predictable, deterministic backend logic**
* **Continuous logging and auditing**
* **Fast recovery capability**

CelesteOS prioritises **safety, isolation, and operational resilience** above all else — with minimal friction for engineers and maximum protection for vessel data.

---